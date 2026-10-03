from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.db.models import Sum, Q, F, Count, Max, Exists, OuterRef
from django.contrib.auth import login, logout
from django.utils import timezone
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import (
    ResultChange,
    User, LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult, WardResult
)
from .serializers import (
    ResultChangeSerializer,
    UserSerializer, LoginSerializer,
    LocalGovernmentAreaSerializer, WardSerializer,
    PollingUnitSerializer, PoliticalPartySerializer,
    ElectionResultSerializer, ElectionResultCreateSerializer,
    ElectionResultSummarySerializer, WardResultSerializer, WardResultCreateSerializer
)


def request_dataset(request):
    """Which portal/dataset this request is scoped to.

    Frontends send it via the ``X-Dataset`` header (preferred) or a ``?dataset=``
    query param. Defaults to 'main' (the original my-app portal)."""
    return (
        request.headers.get('X-Dataset')
        or request.query_params.get('dataset')
        or 'main'
    )


def visible_lga_ids(user):
    """LGA ids a user may access.

    Returns None for unrestricted access (admins / superusers), an empty set for
    anonymous users, or the set of assigned LGA ids for a clerk."""
    if not user or not user.is_authenticated:
        return set()
    if getattr(user, 'is_admin', False):
        return None
    return set(user.assigned_lgas.values_list('id', flat=True))


class IsAdmin(permissions.BasePermission):
    """Allow only admin users (role=admin or superuser)."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_admin', False)
        )


class CSRFTokenView(APIView):
    """Get CSRF token for frontend"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        token = get_token(request)
        return Response({'csrfToken': token})


class LoginView(APIView):
    """Login endpoint for clerks"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Logout endpoint"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """Get current authenticated user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class LocalGovernmentAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Local Government Areas"""
    queryset = LocalGovernmentArea.objects.all()
    serializer_class = LocalGovernmentAreaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset().filter(dataset=request_dataset(self.request))
        ids = visible_lga_ids(self.request.user)
        if ids is not None:
            qs = qs.filter(id__in=ids)
        return qs

    @action(detail=True, methods=['get'])
    def wards(self, request, pk=None):
        """Get all wards for an LGA"""
        lga = self.get_object()
        wards = lga.wards.all()
        serializer = WardSerializer(wards, many=True)
        return Response(serializer.data)


class WardViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Wards"""
    queryset = Ward.objects.select_related('lga').all()
    serializer_class = WardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(dataset=request_dataset(self.request))
        ids = visible_lga_ids(self.request.user)
        if ids is not None:
            queryset = queryset.filter(lga_id__in=ids)
        lga_id = self.request.query_params.get('lga', None)
        if lga_id:
            queryset = queryset.filter(lga_id=lga_id)
        return queryset
    
    @action(detail=True, methods=['get'])
    def polling_units(self, request, pk=None):
        """Get all polling units for a ward"""
        ward = self.get_object()
        polling_units = ward.polling_units.all()
        serializer = PollingUnitSerializer(polling_units, many=True)
        return Response(serializer.data)


class PollingUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Polling Units"""
    queryset = PollingUnit.objects.select_related('ward', 'ward__lga').all()
    serializer_class = PollingUnitSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(dataset=request_dataset(self.request))
        ids = visible_lga_ids(self.request.user)
        if ids is not None:
            queryset = queryset.filter(ward__lga_id__in=ids)
        ward_id = self.request.query_params.get('ward', None)
        lga_id = self.request.query_params.get('lga', None)
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        if lga_id:
            queryset = queryset.filter(ward__lga_id=lga_id)
        # Lets the entry form tick polling units that already have results.
        return queryset.annotate(
            has_results=Exists(ElectionResult.objects.filter(polling_unit=OuterRef('pk')))
        )
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get all results for a polling unit"""
        polling_unit = self.get_object()
        results = polling_unit.results.select_related('party', 'entered_by').all()
        serializer = ElectionResultSerializer(results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def stats(self, request):
        """Public coverage stats for the landing page: total polling units plus a
        per-LGA → ward breakdown of polling unit counts."""
        dataset = request_dataset(request)
        ward_counts = {
            row['ward_id']: row['pu_count']
            for row in PollingUnit.objects.filter(dataset=dataset)
            .values('ward_id').annotate(pu_count=Count('id'))
        }

        reported_by_lga = dict(
            ElectionResult.objects.filter(dataset=dataset)
            .values('polling_unit__ward__lga_id')
            .annotate(n=Count('polling_unit', distinct=True))
            .values_list('polling_unit__ward__lga_id', 'n')
        )
        by_lga = []
        for lga in LocalGovernmentArea.objects.filter(dataset=dataset).prefetch_related('wards').all():
            wards = [
                {'ward': w.name, 'polling_units': ward_counts.get(w.id, 0)}
                for w in lga.wards.all()
            ]
            by_lga.append({
                'lga': lga.name,
                'ward_count': len(wards),
                'polling_units': sum(w['polling_units'] for w in wards),
                'reported_polling_units': reported_by_lga.get(lga.id, 0),
                'wards': wards,
            })

        total_pus = PollingUnit.objects.filter(dataset=dataset).count()
        reported_pus = (
            ElectionResult.objects.filter(dataset=dataset)
            .values('polling_unit').distinct().count()
        )

        return Response({
            'total_polling_units': total_pus,
            'reported_polling_units': reported_pus,
            'reported_percent': round(reported_pus / total_pus * 100, 1) if total_pus else 0.0,
            'total_wards': Ward.objects.filter(dataset=dataset).count(),
            'total_lgas': LocalGovernmentArea.objects.filter(dataset=dataset).count(),
            'by_lga': by_lga,
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def progress(self, request):
        """Result-entry progress for the dashboard.

        A polling unit counts as 'reported' once it has at least one result row.
        Returns overall + per-LGA/ward completion for everyone logged in; the
        per-clerk breakdown is included only for admins."""
        dataset = request_dataset(request)
        ids = visible_lga_ids(request.user)  # None = all (admin), else assigned set

        pu_qs = PollingUnit.objects.filter(dataset=dataset)
        lga_qs = LocalGovernmentArea.objects.filter(dataset=dataset)
        result_qs = ElectionResult.objects.filter(dataset=dataset)
        if ids is not None:
            pu_qs = pu_qs.filter(ward__lga_id__in=ids)
            lga_qs = lga_qs.filter(id__in=ids)
            result_qs = result_qs.filter(polling_unit__ward__lga_id__in=ids)

        reported_pu_ids = set(result_qs.values_list('polling_unit_id', flat=True).distinct())

        # ward_id -> {'total': n, 'reported': n}
        ward_total, ward_reported = {}, {}
        for row in pu_qs.values('id', 'ward_id'):
            wid = row['ward_id']
            ward_total[wid] = ward_total.get(wid, 0) + 1
            if row['id'] in reported_pu_ids:
                ward_reported[wid] = ward_reported.get(wid, 0) + 1

        by_lga = []
        total_pus = reported_pus = 0
        for lga in lga_qs.prefetch_related('wards').all():
            wards, lga_total, lga_reported, wards_complete = [], 0, 0, 0
            for w in lga.wards.all():
                t = ward_total.get(w.id, 0)
                r = ward_reported.get(w.id, 0)
                lga_total += t
                lga_reported += r
                if t > 0 and r >= t:
                    wards_complete += 1
                wards.append({
                    'ward': w.name, 'total': t, 'reported': r,
                    'percent': round(r / t * 100, 1) if t else 0.0,
                })
            total_pus += lga_total
            reported_pus += lga_reported
            by_lga.append({
                'lga': lga.name,
                'total': lga_total,
                'reported': lga_reported,
                'percent': round(lga_reported / lga_total * 100, 1) if lga_total else 0.0,
                'ward_count': len(wards),
                'wards_complete': wards_complete,
                'wards': wards,
            })

        data = {
            'is_admin': bool(getattr(request.user, 'is_admin', False)),
            'overall': {
                'total': total_pus,
                'reported': reported_pus,
                'percent': round(reported_pus / total_pus * 100, 1) if total_pus else 0.0,
            },
            'by_lga': by_lga,
        }

        # Per-clerk breakdown — admins only
        if data['is_admin']:
            data['by_clerk'] = [
                {
                    'username': row['entered_by__username'],
                    'polling_units': row['pus'],
                    'last_activity': row['last'],
                }
                for row in ElectionResult.objects.filter(
                    dataset=dataset, entered_by__isnull=False
                ).values('entered_by__username').annotate(
                    pus=Count('polling_unit', distinct=True),
                    last=Max('updated_at'),
                ).order_by('-pus')
            ]

        return Response(data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def latest(self, request):
        """Public feed of the most recently reported polling units, newest first.

        For the projector ticker: place names and time only, never who entered it.
        ``?limit=`` (1..50, default 15)."""
        dataset = request_dataset(request)
        try:
            limit = min(50, max(1, int(request.query_params.get('limit', 15))))
        except (TypeError, ValueError):
            limit = 15
        rows = list(
            ElectionResult.objects.filter(dataset=dataset)
            .values('polling_unit')
            .annotate(last=Max('updated_at'))
            .order_by('-last')[:limit]
        )
        units = {
            pu.id: pu for pu in PollingUnit.objects.filter(id__in=[r['polling_unit'] for r in rows])
            .select_related('ward__lga')
        }
        return Response([
            {
                'lga': units[r['polling_unit']].ward.lga.name,
                'ward': units[r['polling_unit']].ward.name,
                'polling_unit': units[r['polling_unit']].name,
                'code': units[r['polling_unit']].code,
                'at': r['last'],
            }
            for r in rows if r['polling_unit'] in units
        ])

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def recent_entries(self, request):
        """Paginated feed of the latest polling-unit submissions with ward + LGA,
        so an admin can audit suspicious results. Admin only.

        One row per polling unit (its most recent submission), newest first.
        Query params: ?page= (1-based) and ?page_size= (5..50, default 15)."""
        dataset = request_dataset(request)
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(50, max(5, int(request.query_params.get('page_size', 15))))
        except (TypeError, ValueError):
            page_size = 15

        # Distinct polling units ordered by their most recent entry (SQLite-safe:
        # dedup via GROUP BY rather than DISTINCT ON).
        base = (
            ElectionResult.objects
            .filter(dataset=dataset, entered_by__isnull=False)
            .values('polling_unit')
            .annotate(last=Max('updated_at'))
            .order_by('-last')
        )
        total = base.count()
        start = (page - 1) * page_size
        page_rows = list(base[start:start + page_size])
        last_by_pu = {r['polling_unit']: r['last'] for r in page_rows}
        pu_ids = [r['polling_unit'] for r in page_rows]

        # Hydrate only this page's polling units (name / ward / lga / clerk).
        picked = {}
        for r in (
            ElectionResult.objects
            .filter(dataset=dataset, polling_unit_id__in=pu_ids)
            .select_related('polling_unit__ward__lga', 'entered_by')
        ):
            if r.polling_unit_id not in picked and r.updated_at == last_by_pu.get(r.polling_unit_id):
                picked[r.polling_unit_id] = r

        results = []
        for pid in pu_ids:  # preserve newest-first order
            r = picked.get(pid)
            if not r:
                continue
            results.append({
                'clerk': r.entered_by.username,
                'lga': r.polling_unit.ward.lga.name,
                'ward': r.polling_unit.ward.name,
                'polling_unit': r.polling_unit.name,
                'at': r.updated_at,
            })

        num_pages = (total + page_size - 1) // page_size
        return Response({
            'results': results,
            'count': total,
            'page': page,
            'page_size': page_size,
            'num_pages': num_pages,
            'has_next': page < num_pages,
            'has_prev': page > 1,
        })


class PoliticalPartyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Political Parties"""
    queryset = PoliticalParty.objects.all()
    serializer_class = PoliticalPartySerializer
    permission_classes = [permissions.AllowAny]  # Public access for landing page


class ElectionResultViewSet(viewsets.ModelViewSet):
    """ViewSet for Election Results"""
    queryset = ElectionResult.objects.select_related(
        'polling_unit', 'polling_unit__ward', 'polling_unit__ward__lga',
        'party', 'entered_by'
    ).all()
    serializer_class = ElectionResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(dataset=request_dataset(self.request))
        ids = visible_lga_ids(self.request.user)
        if ids is not None:
            queryset = queryset.filter(polling_unit__ward__lga_id__in=ids)
        polling_unit_id = self.request.query_params.get('polling_unit', None)
        lga_id = self.request.query_params.get('lga', None)
        party_id = self.request.query_params.get('party', None)

        if polling_unit_id:
            queryset = queryset.filter(polling_unit_id=polling_unit_id)
        if lga_id:
            queryset = queryset.filter(polling_unit__ward__lga_id=lga_id)
        if party_id:
            queryset = queryset.filter(party_id=party_id)
        
        return queryset
    
    def _assert_lga_allowed(self, lga_id):
        """Block clerks from touching an LGA they are not assigned to."""
        ids = visible_lga_ids(self.request.user)
        if ids is not None and lga_id not in ids:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You are not assigned to this LGA.')

    def perform_create(self, serializer):
        """Set the user who entered the result"""
        pu = serializer.validated_data.get('polling_unit')
        if pu is not None:
            self._assert_lga_allowed(pu.ward.lga_id)
        serializer.save(entered_by=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create/update election results for a polling unit"""
        serializer = ElectionResultCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        polling_unit_id = serializer.validated_data['polling_unit_id']
        results_data = serializer.validated_data['results']

        try:
            polling_unit = PollingUnit.objects.get(
                id=polling_unit_id, dataset=request_dataset(request)
            )
        except PollingUnit.DoesNotExist:
            return Response(
                {'error': 'Polling unit not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        self._assert_lga_allowed(polling_unit.ward.lga_id)
        
        created_results = []
        updated_results = []
        
        for result_item in results_data:
            party_id = result_item.get('party_id')
            votes = result_item.get('votes', 0)
            
            if not party_id:
                continue
            
            try:
                party = PoliticalParty.objects.get(id=party_id)
            except PoliticalParty.DoesNotExist:
                continue
            
            result, created = ElectionResult.objects.update_or_create(
                polling_unit=polling_unit,
                party=party,
                defaults={
                    'votes': votes,
                    'entered_by': request.user,
                    'updated_at': timezone.now()
                }
            )
            
            if created:
                created_results.append(result)
            else:
                updated_results.append(result)
        
        return Response({
            'message': f'Created {len(created_results)} results, updated {len(updated_results)} results',
            'polling_unit': PollingUnitSerializer(polling_unit).data,
            'created': ElectionResultSerializer(created_results, many=True).data,
            'updated': ElectionResultSerializer(updated_results, many=True).data,
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of results grouped by LGA and party, with ward overrides applied."""
        dataset = request_dataset(request)
        ward_overrides = {
            (wr.ward_id, wr.party_id): wr.votes
            for wr in WardResult.objects.filter(dataset=dataset)
        }
        pu_totals = {
            (row['polling_unit__ward_id'], row['party_id']): row['total']
            for row in ElectionResult.objects.filter(dataset=dataset).values(
                'polling_unit__ward_id', 'party_id'
            ).annotate(total=Sum('votes'))
        }

        summary_data = []
        for lga in LocalGovernmentArea.objects.filter(dataset=dataset).prefetch_related('wards').all():
            for party in PoliticalParty.objects.all():
                total = sum(
                    ward_overrides.get((w.id, party.id), pu_totals.get((w.id, party.id), 0))
                    for w in lga.wards.all()
                )
                if total > 0:
                    summary_data.append({
                        'lga': lga.name,
                        'party': party.abbreviation,
                        'votes': total
                    })

        serializer = ElectionResultSummarySerializer(summary_data, many=True)
        return Response(serializer.data)

    def _scoped_lgas(self, request):
        """LGAs this user may export, narrowed by ``?lga=``/``?ward=``."""
        dataset = request_dataset(request)
        lgas = LocalGovernmentArea.objects.filter(dataset=dataset)
        ids = visible_lga_ids(request.user)
        if ids is not None:
            lgas = lgas.filter(id__in=ids)
        return lgas

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Polling-unit results for a spreadsheet: the whole state (``?lga=`` /
        ``?ward=`` to narrow), limited to the LGAs the user may see.

        Returns parties (column order), one row per polling unit with its votes
        per party, and the ward overrides in scope."""
        lgas = self._scoped_lgas(request)
        lga_id, ward_id = request.query_params.get('lga'), request.query_params.get('ward')
        wards = Ward.objects.filter(lga__in=lgas)
        if lga_id:
            wards = wards.filter(lga_id=lga_id)
        if ward_id:
            wards = wards.filter(id=ward_id)
        wards = wards.select_related('lga').order_by('lga__name', 'name')
        parties = list(PoliticalParty.objects.all().order_by('name'))

        votes = {}
        last = {}
        for r in ElectionResult.objects.filter(polling_unit__ward__in=wards).values(
            'polling_unit_id', 'party_id', 'votes', 'updated_at', 'entered_by__username'
        ):
            votes.setdefault(r['polling_unit_id'], {})[r['party_id']] = r['votes']
            prev = last.get(r['polling_unit_id'])
            if prev is None or r['updated_at'] > prev[0]:
                last[r['polling_unit_id']] = (r['updated_at'], r['entered_by__username'] or '')

        rows = []
        for pu in PollingUnit.objects.filter(ward__in=wards).select_related('ward__lga').order_by(
            'ward__lga__name', 'ward__name', 'code', 'name'
        ):
            v = votes.get(pu.id, {})
            rows.append({
                'lga': pu.ward.lga.name, 'ward': pu.ward.name, 'code': pu.code or '', 'polling_unit': pu.name,
                'reported': pu.id in votes,
                'votes': {p.abbreviation: v.get(p.id, 0) for p in parties},
                'total': sum(v.values()),
                'entered_by': last.get(pu.id, (None, ''))[1],
                'updated_at': last.get(pu.id, (None, None))[0],
            })

        overrides = {}
        for wr in WardResult.objects.filter(ward__in=wards).select_related('ward__lga', 'party'):
            # Only the parties actually overridden: the rest keep their polling-unit sums.
            row = overrides.setdefault(wr.ward_id, {'lga': wr.ward.lga.name, 'ward': wr.ward.name, 'votes': {}})
            row['votes'][wr.party.abbreviation] = wr.votes
        override_rows = sorted(overrides.values(), key=lambda r: (r['lga'], r['ward']))
        for r in override_rows:
            r['total'] = sum(r['votes'].values())

        return Response({
            'generated_at': timezone.now(),
            'parties': [{'abbreviation': p.abbreviation, 'name': p.name, 'color': p.color} for p in parties],
            'polling_units': rows,
            'ward_overrides': override_rows,
        })

    @action(detail=False, methods=['get'])
    def lga_report(self, request):
        """Everything the printable LGA summary needs for ``?lga=<id>``:
        party totals and a ward-by-ward breakdown (ward overrides applied)."""
        try:
            lga = self._scoped_lgas(request).get(id=request.query_params.get('lga'))
        except (LocalGovernmentArea.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'LGA not found'}, status=status.HTTP_404_NOT_FOUND)

        parties = list(PoliticalParty.objects.all())
        wards = list(lga.wards.order_by('name'))
        overrides = {(w, p): v for w, p, v in WardResult.objects.filter(ward__lga=lga)
                     .values_list('ward_id', 'party_id', 'votes')}
        pu_sums = {
            (r['polling_unit__ward_id'], r['party_id']): r['total']
            for r in ElectionResult.objects.filter(polling_unit__ward__lga=lga)
            .values('polling_unit__ward_id', 'party_id').annotate(total=Sum('votes'))
        }
        pu_total = dict(PollingUnit.objects.filter(ward__lga=lga).values('ward_id')
                        .annotate(n=Count('id')).values_list('ward_id', 'n'))
        pu_reported = dict(ElectionResult.objects.filter(polling_unit__ward__lga=lga)
                           .values('polling_unit__ward_id')
                           .annotate(n=Count('polling_unit', distinct=True))
                           .values_list('polling_unit__ward_id', 'n'))
        overridden = {w for (w, _p) in overrides}

        ward_rows = []
        for w in wards:
            v = {p.abbreviation: overrides.get((w.id, p.id), pu_sums.get((w.id, p.id), 0)) for p in parties}
            ward_rows.append({
                'ward': w.name, 'votes': v, 'total': sum(v.values()),
                'override': w.id in overridden,
                'reported': pu_reported.get(w.id, 0), 'polling_units': pu_total.get(w.id, 0),
            })
        totals = {p.abbreviation: sum(r['votes'][p.abbreviation] for r in ward_rows) for p in parties}
        return Response({
            'generated_at': timezone.now(),
            'lga': {'id': lga.id, 'name': lga.name},
            'parties': [{'abbreviation': p.abbreviation, 'name': p.name, 'color': p.color} for p in parties],
            'totals': totals,
            'total_votes': sum(totals.values()),
            'wards': ward_rows,
            'reported': sum(r['reported'] for r in ward_rows),
            'polling_units': sum(r['polling_units'] for r in ward_rows),
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def chart_data(self, request):
        """Get data formatted for charts - Public access for landing page. Ward overrides take priority."""
        dataset = request_dataset(request)
        lgas = LocalGovernmentArea.objects.filter(dataset=dataset)
        parties = PoliticalParty.objects.all()

        # Bulk fetch to avoid N+1 queries
        ward_overrides = {
            (wr.ward_id, wr.party_id): wr.votes
            for wr in WardResult.objects.filter(dataset=dataset)
        }
        pu_totals = {
            (row['polling_unit__ward_id'], row['party_id']): row['total']
            for row in ElectionResult.objects.filter(dataset=dataset).values(
                'polling_unit__ward_id', 'party_id'
            ).annotate(total=Sum('votes'))
        }
        ward_lga = {w.id: w.lga_id for w in Ward.objects.filter(dataset=dataset)}

        def effective_votes(ward_id, party_id):
            if (ward_id, party_id) in ward_overrides:
                return ward_overrides[(ward_id, party_id)]
            return pu_totals.get((ward_id, party_id), 0)

        bar_data = []
        for lga in lgas:
            lga_data = {'lga': lga.name}
            lga_ward_ids = [wid for wid, lid in ward_lga.items() if lid == lga.id]
            for party in parties:
                lga_data[party.abbreviation] = sum(
                    effective_votes(wid, party.id) for wid in lga_ward_ids
                )
            bar_data.append(lga_data)

        radial_data = []
        for party in parties:
            total = sum(effective_votes(wid, party.id) for wid in ward_lga)
            radial_data.append({
                'party': party.abbreviation,
                'votes': total,
                'fill': party.color,
                'logo_url': request.build_absolute_uri(party.logo.url) if party.logo else None,
            })

        return Response({
            'bar': bar_data,
            'radial': radial_data,
            'line': bar_data.copy()
        })


class WardResultViewSet(viewsets.ModelViewSet):
    """ViewSet for Ward-level result overrides."""
    queryset = WardResult.objects.select_related('ward', 'ward__lga', 'party', 'entered_by').all()
    serializer_class = WardResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().filter(dataset=request_dataset(self.request))
        ids = visible_lga_ids(self.request.user)
        if ids is not None:
            queryset = queryset.filter(ward__lga_id__in=ids)
        ward_id = self.request.query_params.get('ward')
        lga_id = self.request.query_params.get('lga')
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        if lga_id:
            queryset = queryset.filter(ward__lga_id=lga_id)
        return queryset

    def perform_create(self, serializer):
        ward = serializer.validated_data.get('ward')
        if ward is not None:
            ids = visible_lga_ids(self.request.user)
            if ids is not None and ward.lga_id not in ids:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('You are not assigned to this LGA.')
        serializer.save(entered_by=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create/update ward result overrides."""
        serializer = WardResultCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ward_id = serializer.validated_data['ward_id']
        results_data = serializer.validated_data['results']

        try:
            ward = Ward.objects.get(id=ward_id, dataset=request_dataset(request))
        except Ward.DoesNotExist:
            return Response({'error': 'Ward not found'}, status=status.HTTP_404_NOT_FOUND)

        _ids = visible_lga_ids(request.user)
        if _ids is not None and ward.lga_id not in _ids:
            return Response({'error': 'You are not assigned to this LGA.'},
                            status=status.HTTP_403_FORBIDDEN)

        created_results, updated_results = [], []

        for item in results_data:
            party_id = item.get('party_id')
            votes = item.get('votes', 0)
            if not party_id:
                continue
            try:
                party = PoliticalParty.objects.get(id=party_id)
            except PoliticalParty.DoesNotExist:
                continue

            result, created = WardResult.objects.update_or_create(
                ward=ward, party=party,
                defaults={'votes': votes, 'entered_by': request.user, 'updated_at': timezone.now()}
            )
            (created_results if created else updated_results).append(result)

        return Response({
            'message': f'Created {len(created_results)}, updated {len(updated_results)} ward results',
            'ward': WardSerializer(ward).data,
            'created': WardResultSerializer(created_results, many=True).data,
            'updated': WardResultSerializer(updated_results, many=True).data,
        }, status=status.HTTP_201_CREATED)


class ClerkViewSet(viewsets.ViewSet):
    """Admin-only management of clerk -> LGA assignments (current dataset)."""
    permission_classes = [IsAdmin]

    def _serialize(self, clerk, dataset):
        # Only surface assignments that belong to the active dataset
        assigned = list(
            clerk.assigned_lgas.filter(dataset=dataset).values_list('id', flat=True)
        )
        pu_count = ElectionResult.objects.filter(
            dataset=dataset, entered_by=clerk
        ).values('polling_unit').distinct().count()
        return {
            'id': clerk.id,
            'username': clerk.username,
            'email': clerk.email,
            'assigned_lga_ids': assigned,
            'polling_units_entered': pu_count,
        }

    def list(self, request):
        dataset = request_dataset(request)
        clerks = User.objects.filter(role=User.CLERK).order_by('username')
        return Response([self._serialize(c, dataset) for c in clerks])

    def create(self, request):
        """Create a clerk account, optionally assigned to LGAs in the current dataset.

        Body: ``username``, ``password``, optional ``first_name``,
        ``last_name``, ``email`` and ``lga_ids``."""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        dataset = request_dataset(request)
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        lga_ids = request.data.get('lga_ids', [])

        errors = {}
        if not username:
            errors['username'] = ['Username is required.']
        elif User.objects.filter(username__iexact=username).exists():
            errors['username'] = ['A user with that username already exists.']
        if not isinstance(lga_ids, list):
            errors['lga_ids'] = ['lga_ids must be a list.']

        candidate = User(
            username=username,
            first_name=(request.data.get('first_name') or '').strip(),
            last_name=(request.data.get('last_name') or '').strip(),
            email=(request.data.get('email') or '').strip(),
            role=User.CLERK,
        )
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            errors['password'] = list(exc.messages)

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        candidate.set_password(password)
        candidate.save()
        candidate.assigned_lgas.set(LocalGovernmentArea.objects.filter(id__in=lga_ids, dataset=dataset))
        return Response(self._serialize(candidate, dataset), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Replace a clerk's LGA assignments for the current dataset.

        Assignments in *other* datasets are preserved; only the ones for this
        dataset are swapped for the supplied ``lga_ids``."""
        dataset = request_dataset(request)
        try:
            clerk = User.objects.get(pk=pk, role=User.CLERK)
        except User.DoesNotExist:
            return Response({'error': 'Clerk not found'}, status=status.HTTP_404_NOT_FOUND)

        lga_ids = request.data.get('lga_ids', [])
        if not isinstance(lga_ids, list):
            return Response({'error': 'lga_ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the ids exist within this dataset
        new_lgas = list(LocalGovernmentArea.objects.filter(id__in=lga_ids, dataset=dataset))

        # Keep any assignments the clerk has in other datasets untouched
        keep_other = clerk.assigned_lgas.exclude(dataset=dataset)
        clerk.assigned_lgas.set(list(keep_other) + new_lgas)

        return Response(self._serialize(clerk, dataset))



class ResultChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only change history of results for the current dataset, newest first.

    Filters: ``?lga=``, ``?ward=``, ``?polling_unit=``, ``?kind=pu|ward``."""
    serializer_class = ResultChangeSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = ResultChange.objects.filter(dataset=request_dataset(self.request))
        for param, field in (('lga', 'lga_id'), ('ward', 'ward_id'), ('polling_unit', 'polling_unit_id'), ('kind', 'kind')):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

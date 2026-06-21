from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.db.models import Sum, Q, F, Count
from django.contrib.auth import login, logout
from django.utils import timezone
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import (
    User, LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult, WardResult
)
from .serializers import (
    UserSerializer, LoginSerializer,
    LocalGovernmentAreaSerializer, WardSerializer,
    PollingUnitSerializer, PoliticalPartySerializer,
    ElectionResultSerializer, ElectionResultCreateSerializer,
    ElectionResultSummarySerializer, WardResultSerializer, WardResultCreateSerializer
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
        queryset = super().get_queryset()
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
        queryset = super().get_queryset()
        ward_id = self.request.query_params.get('ward', None)
        lga_id = self.request.query_params.get('lga', None)
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        if lga_id:
            queryset = queryset.filter(ward__lga_id=lga_id)
        return queryset
    
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
        ward_counts = {
            row['ward_id']: row['pu_count']
            for row in PollingUnit.objects.values('ward_id').annotate(pu_count=Count('id'))
        }

        by_lga = []
        for lga in LocalGovernmentArea.objects.prefetch_related('wards').all():
            wards = [
                {'ward': w.name, 'polling_units': ward_counts.get(w.id, 0)}
                for w in lga.wards.all()
            ]
            by_lga.append({
                'lga': lga.name,
                'ward_count': len(wards),
                'polling_units': sum(w['polling_units'] for w in wards),
                'wards': wards,
            })

        return Response({
            'total_polling_units': PollingUnit.objects.count(),
            'total_wards': Ward.objects.count(),
            'total_lgas': LocalGovernmentArea.objects.count(),
            'by_lga': by_lga,
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
        queryset = super().get_queryset()
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
    
    def perform_create(self, serializer):
        """Set the user who entered the result"""
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
            polling_unit = PollingUnit.objects.get(id=polling_unit_id)
        except PollingUnit.DoesNotExist:
            return Response(
                {'error': 'Polling unit not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
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
        ward_overrides = {
            (wr.ward_id, wr.party_id): wr.votes
            for wr in WardResult.objects.all()
        }
        pu_totals = {
            (row['polling_unit__ward_id'], row['party_id']): row['total']
            for row in ElectionResult.objects.values(
                'polling_unit__ward_id', 'party_id'
            ).annotate(total=Sum('votes'))
        }

        summary_data = []
        for lga in LocalGovernmentArea.objects.prefetch_related('wards').all():
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

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def chart_data(self, request):
        """Get data formatted for charts - Public access for landing page. Ward overrides take priority."""
        lgas = LocalGovernmentArea.objects.all()
        parties = PoliticalParty.objects.all()

        # Bulk fetch to avoid N+1 queries
        ward_overrides = {
            (wr.ward_id, wr.party_id): wr.votes
            for wr in WardResult.objects.all()
        }
        pu_totals = {
            (row['polling_unit__ward_id'], row['party_id']): row['total']
            for row in ElectionResult.objects.values(
                'polling_unit__ward_id', 'party_id'
            ).annotate(total=Sum('votes'))
        }
        ward_lga = {w.id: w.lga_id for w in Ward.objects.all()}

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
        queryset = super().get_queryset()
        ward_id = self.request.query_params.get('ward')
        lga_id = self.request.query_params.get('lga')
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        if lga_id:
            queryset = queryset.filter(ward__lga_id=lga_id)
        return queryset

    def perform_create(self, serializer):
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
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return Response({'error': 'Ward not found'}, status=status.HTTP_404_NOT_FOUND)

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

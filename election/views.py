from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Q, F
from django.contrib.auth import login, logout
from django.utils import timezone
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import (
    User, LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult
)
from .serializers import (
    UserSerializer, LoginSerializer,
    LocalGovernmentAreaSerializer, WardSerializer,
    PollingUnitSerializer, PoliticalPartySerializer,
    ElectionResultSerializer, ElectionResultCreateSerializer,
    ElectionResultSummarySerializer
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
            return Response({
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Logout endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
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
        """Get summary of results grouped by LGA and party"""
        results = ElectionResult.objects.values(
            'polling_unit__ward__lga__name',
            'party__abbreviation'
        ).annotate(
            total_votes=Sum('votes')
        ).order_by('polling_unit__ward__lga__name', 'party__abbreviation')
        
        summary_data = [
            {
                'lga': item['polling_unit__ward__lga__name'],
                'party': item['party__abbreviation'],
                'votes': item['total_votes']
            }
            for item in results
        ]
        
        serializer = ElectionResultSummarySerializer(summary_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def chart_data(self, request):
        """Get data formatted for charts - Public access for landing page"""
        # Bar chart data - votes by LGA and party
        bar_data = []
        lgas = LocalGovernmentArea.objects.all()
        parties = PoliticalParty.objects.all()
        
        for lga in lgas:
            lga_data = {'lga': lga.name}
            for party in parties:
                total_votes = ElectionResult.objects.filter(
                    polling_unit__ward__lga=lga,
                    party=party
                ).aggregate(total=Sum('votes'))['total'] or 0
                lga_data[party.abbreviation] = total_votes
            bar_data.append(lga_data)
        
        # Radial chart data - total votes per party
        radial_data = []
        for party in parties:
            total_votes = ElectionResult.objects.filter(party=party).aggregate(
                total=Sum('votes')
            )['total'] or 0
            radial_data.append({
                'party': party.abbreviation,
                'votes': total_votes,
                'fill': party.color,
                'logo_url': request.build_absolute_uri(party.logo.url) if party.logo else None,
            })
        
        # Line chart data - same as bar but formatted for line chart
        line_data = bar_data.copy()
        
        return Response({
            'bar': bar_data,
            'radial': radial_data,
            'line': line_data
        })

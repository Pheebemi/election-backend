from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    User, LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult, WardResult
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'first_name', 'last_name']
        read_only_fields = ['id', 'role']


class LoginSerializer(serializers.Serializer):
    """Serializer for login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class LocalGovernmentAreaSerializer(serializers.ModelSerializer):
    """Serializer for LGA"""
    wards_count = serializers.IntegerField(source='wards.count', read_only=True)
    
    class Meta:
        model = LocalGovernmentArea
        fields = ['id', 'name', 'code', 'wards_count', 'created_at', 'updated_at']


class WardSerializer(serializers.ModelSerializer):
    """Serializer for Ward"""
    lga_name = serializers.CharField(source='lga.name', read_only=True)
    polling_units_count = serializers.IntegerField(source='polling_units.count', read_only=True)
    
    class Meta:
        model = Ward
        fields = ['id', 'name', 'code', 'lga', 'lga_name', 'polling_units_count', 'created_at', 'updated_at']


class PollingUnitSerializer(serializers.ModelSerializer):
    """Serializer for Polling Unit"""
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    lga_name = serializers.CharField(source='ward.lga.name', read_only=True)
    lga_id = serializers.IntegerField(source='ward.lga.id', read_only=True)
    
    class Meta:
        model = PollingUnit
        fields = ['id', 'name', 'code', 'ward', 'ward_name', 'lga_name', 'lga_id', 'registered_voters', 'created_at', 'updated_at']


class PoliticalPartySerializer(serializers.ModelSerializer):
    """Serializer for Political Party"""
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = PoliticalParty
        fields = ['id', 'name', 'abbreviation', 'color', 'logo', 'logo_url', 'created_at', 'updated_at']
        read_only_fields = ['logo_url']

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and hasattr(obj.logo, 'url'):
            url = obj.logo.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None


class ElectionResultSerializer(serializers.ModelSerializer):
    """Serializer for Election Result"""
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    polling_unit_name = serializers.CharField(source='polling_unit.name', read_only=True)
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    lga_name = serializers.CharField(source='lga.name', read_only=True)
    entered_by_username = serializers.CharField(source='entered_by.username', read_only=True)
    
    class Meta:
        model = ElectionResult
        fields = [
            'id', 'polling_unit', 'polling_unit_name', 'ward_name', 'lga_name',
            'party', 'party_name', 'party_abbreviation', 'party_color',
            'votes', 'entered_by', 'entered_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['entered_by']


class ElectionResultCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating election results"""
    polling_unit_id = serializers.IntegerField()
    results = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField()
        )
    )
    
    def validate(self, attrs):
        polling_unit_id = attrs.get('polling_unit_id')
        results = attrs.get('results')
        
        if not PollingUnit.objects.filter(id=polling_unit_id).exists():
            raise serializers.ValidationError('Polling unit does not exist')
        
        if not results:
            raise serializers.ValidationError('Results list cannot be empty')
        
        return attrs


class ElectionResultSummarySerializer(serializers.Serializer):
    """Serializer for election result summaries"""
    lga = serializers.CharField()
    party = serializers.CharField()
    votes = serializers.IntegerField()


class WardResultSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    lga_name = serializers.CharField(source='ward.lga.name', read_only=True)
    lga_id = serializers.IntegerField(source='ward.lga.id', read_only=True)
    party_name = serializers.CharField(source='party.name', read_only=True)
    party_abbreviation = serializers.CharField(source='party.abbreviation', read_only=True)
    party_color = serializers.CharField(source='party.color', read_only=True)
    entered_by_username = serializers.CharField(source='entered_by.username', read_only=True)

    class Meta:
        model = WardResult
        fields = [
            'id', 'ward', 'ward_name', 'lga_name', 'lga_id',
            'party', 'party_name', 'party_abbreviation', 'party_color',
            'votes', 'entered_by', 'entered_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = ['entered_by']


class WardResultCreateSerializer(serializers.Serializer):
    ward_id = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField(child=serializers.IntegerField()))

    def validate(self, attrs):
        if not Ward.objects.filter(id=attrs.get('ward_id')).exists():
            raise serializers.ValidationError('Ward does not exist')
        if not attrs.get('results'):
            raise serializers.ValidationError('Results list cannot be empty')
        return attrs


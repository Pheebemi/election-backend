from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult
)

admin.site.site_header = "Taraba Election Portal Admin"
admin.site.site_title = "Election Admin"
admin.site.index_title = "Welcome to Election Portal Administration"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""
    list_display = ['username', 'email', 'role', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['role', 'is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


@admin.register(LocalGovernmentArea)
class LocalGovernmentAreaAdmin(admin.ModelAdmin):
    """Admin interface for LGA"""
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    """Admin interface for Ward"""
    list_display = ['name', 'lga', 'code', 'created_at']
    list_filter = ['lga', 'created_at']
    search_fields = ['name', 'code', 'lga__name']
    autocomplete_fields = ['lga']


@admin.register(PollingUnit)
class PollingUnitAdmin(admin.ModelAdmin):
    """Admin interface for Polling Unit"""
    list_display = ['name', 'ward', 'lga', 'code', 'registered_voters', 'created_at']
    list_filter = ['ward__lga', 'ward', 'created_at']
    search_fields = ['name', 'code', 'ward__name', 'ward__lga__name']
    autocomplete_fields = ['ward']
    
    def lga(self, obj):
        return obj.ward.lga.name
    lga.short_description = 'LGA'


@admin.register(PoliticalParty)
class PoliticalPartyAdmin(admin.ModelAdmin):
    """Admin interface for Political Party"""
    list_display = ['name', 'abbreviation', 'color', 'logo', 'created_at']
    search_fields = ['name', 'abbreviation']
    list_filter = ['created_at']


@admin.register(ElectionResult)
class ElectionResultAdmin(admin.ModelAdmin):
    """Admin interface for Election Result"""
    list_display = ['polling_unit', 'party', 'votes', 'entered_by', 'created_at']
    list_filter = ['party', 'polling_unit__ward__lga', 'created_at']
    search_fields = [
        'polling_unit__name', 'party__name', 'party__abbreviation',
        'entered_by__username'
    ]
    autocomplete_fields = ['polling_unit', 'party', 'entered_by']
    readonly_fields = ['created_at', 'updated_at']

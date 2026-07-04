from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult, WardResult,
    ApcLocalGovernmentArea, ApcWard, ApcPollingUnit,
    ApcElectionResult, ApcWardResult,
)

admin.site.site_header = "Taraba Election Portal Admin"
admin.site.site_title = "Election Admin"
admin.site.index_title = "Welcome to Election Portal Administration"


# ---------------------------------------------------------------------------
# Dataset scoping helpers
#
# The base admins below only ever show the 'main' (my-app) dataset. A parallel
# set of "(APC)" admins, registered against proxy models, show only the 'apc'
# dataset. Same tables, cleanly separated in the admin index.
# ---------------------------------------------------------------------------

class MainScopedMixin:
    """Restrict an admin's list & edit views to one dataset (default 'main')."""
    dataset_key = 'main'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(dataset=self.dataset_key)


class ApcScopedMixin(MainScopedMixin):
    """Show only the 'apc' dataset, and make sure new/edited rows stay in it."""
    dataset_key = 'apc'
    autocomplete_fields = []  # avoid main-scoped autocomplete endpoints

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit LGA / Ward / Polling Unit pickers to the apc dataset
        rel_model = db_field.related_model
        if rel_model is not None and any(f.name == 'dataset' for f in rel_model._meta.fields):
            kwargs['queryset'] = rel_model._default_manager.filter(dataset='apc')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.dataset = 'apc'  # LGA needs this explicitly; children re-derive it on save()
        super().save_model(request, obj, form, change)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""
    list_display = ['username', 'email', 'role', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['role', 'is_staff', 'is_active']
    filter_horizontal = BaseUserAdmin.filter_horizontal + ('assigned_lgas',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & assignments', {'fields': ('role', 'assigned_lgas')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


# ---- Main (my-app) portal -------------------------------------------------

@admin.register(LocalGovernmentArea)
class LocalGovernmentAreaAdmin(MainScopedMixin, admin.ModelAdmin):
    """Admin interface for LGA"""
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(Ward)
class WardAdmin(MainScopedMixin, admin.ModelAdmin):
    """Admin interface for Ward"""
    list_display = ['name', 'lga', 'code', 'created_at']
    list_filter = ['lga', 'created_at']
    search_fields = ['name', 'code', 'lga__name']
    autocomplete_fields = ['lga']


@admin.register(PollingUnit)
class PollingUnitAdmin(MainScopedMixin, admin.ModelAdmin):
    """Admin interface for Polling Unit"""
    list_display = ['name', 'ward', 'lga', 'code', 'registered_voters', 'created_at']
    list_filter = ['ward__lga', 'created_at']
    search_fields = ['name', 'code', 'ward__name', 'ward__lga__name']
    autocomplete_fields = ['ward']

    def lga(self, obj):
        return obj.ward.lga.name
    lga.short_description = 'LGA'


@admin.register(PoliticalParty)
class PoliticalPartyAdmin(admin.ModelAdmin):
    """Admin interface for Political Party (shared across all datasets)"""
    list_display = ['name', 'abbreviation', 'color', 'logo', 'created_at']
    search_fields = ['name', 'abbreviation']
    list_filter = ['created_at']


@admin.register(ElectionResult)
class ElectionResultAdmin(MainScopedMixin, admin.ModelAdmin):
    """Admin interface for Election Result"""
    list_display = ['polling_unit', 'party', 'votes', 'entered_by', 'created_at']
    list_filter = ['party', 'polling_unit__ward__lga', 'created_at']
    search_fields = [
        'polling_unit__name', 'party__name', 'party__abbreviation',
        'entered_by__username'
    ]
    autocomplete_fields = ['polling_unit', 'party', 'entered_by']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WardResult)
class WardResultAdmin(MainScopedMixin, admin.ModelAdmin):
    list_display = ['ward', 'party', 'votes', 'entered_by', 'updated_at']
    list_filter = ['ward__lga', 'party']
    search_fields = ['ward__name', 'party__name']
    readonly_fields = ['created_at', 'updated_at']


# ---- APC portal -----------------------------------------------------------

@admin.register(ApcLocalGovernmentArea)
class ApcLocalGovernmentAreaAdmin(ApcScopedMixin, admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(ApcWard)
class ApcWardAdmin(ApcScopedMixin, admin.ModelAdmin):
    list_display = ['name', 'lga', 'code', 'created_at']
    list_filter = ['lga', 'created_at']
    search_fields = ['name', 'code', 'lga__name']


@admin.register(ApcPollingUnit)
class ApcPollingUnitAdmin(ApcScopedMixin, admin.ModelAdmin):
    list_display = ['name', 'ward', 'lga', 'code', 'registered_voters', 'created_at']
    list_filter = ['ward__lga', 'created_at']
    search_fields = ['name', 'code', 'ward__name', 'ward__lga__name']

    def lga(self, obj):
        return obj.ward.lga.name
    lga.short_description = 'LGA'


@admin.register(ApcElectionResult)
class ApcElectionResultAdmin(ApcScopedMixin, admin.ModelAdmin):
    list_display = ['polling_unit', 'party', 'votes', 'entered_by', 'created_at']
    list_filter = ['party', 'polling_unit__ward__lga', 'created_at']
    search_fields = [
        'polling_unit__name', 'party__name', 'party__abbreviation',
        'entered_by__username'
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ApcWardResult)
class ApcWardResultAdmin(ApcScopedMixin, admin.ModelAdmin):
    list_display = ['ward', 'party', 'votes', 'entered_by', 'updated_at']
    list_filter = ['ward__lga', 'party']
    search_fields = ['ward__name', 'party__name']
    readonly_fields = ['created_at', 'updated_at']

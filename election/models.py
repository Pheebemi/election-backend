from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model with clerk/admin distinction"""
    CLERK = 'clerk'
    ADMIN = 'admin'
    ROLE_CHOICES = [
        (CLERK, 'Data Clerk'),
        (ADMIN, 'Admin'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CLERK)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_clerk(self):
        return self.role == self.CLERK
    
    @property
    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser


class LocalGovernmentArea(models.Model):
    """Local Government Area (LGA) model"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Local Government Area'
        verbose_name_plural = 'Local Government Areas'
    
    def __str__(self):
        return self.name


class Ward(models.Model):
    """Ward model - belongs to an LGA"""
    name = models.CharField(max_length=100)
    lga = models.ForeignKey(LocalGovernmentArea, on_delete=models.CASCADE, related_name='wards')
    code = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lga', 'name']
        unique_together = ['name', 'lga']
    
    def __str__(self):
        return f"{self.name} ({self.lga.name})"


class PollingUnit(models.Model):
    """Polling Unit model - belongs to a Ward"""
    name = models.CharField(max_length=100)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='polling_units')
    code = models.CharField(max_length=30, null=True, blank=True)
    registered_voters = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ward__lga', 'ward', 'name']
        unique_together = ['name', 'ward']
    
    def __str__(self):
        return f"{self.name} ({self.ward.name}, {self.ward.lga.name})"
    
    @property
    def lga(self):
        return self.ward.lga


class PoliticalParty(models.Model):
    """Political Party model"""
    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=7, default='#000000', help_text='Hex color code')
    logo = models.ImageField(upload_to='party_logos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Political Parties'
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"
    
    @property
    def logo_url(self):
        if self.logo and hasattr(self.logo, 'url'):
            return self.logo.url
        return None


class ElectionResult(models.Model):
    """Election Result model - votes per party per polling unit"""
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='results')
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, related_name='results')
    votes = models.IntegerField(default=0)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_results')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['polling_unit', 'party']
        unique_together = ['polling_unit', 'party']
        indexes = [
            models.Index(fields=['polling_unit', 'party']),
            models.Index(fields=['party']),
        ]
    
    def __str__(self):
        return f"{self.party.abbreviation}: {self.votes} votes at {self.polling_unit.name}"
    
    @property
    def lga(self):
        return self.polling_unit.lga
    
    @property
    def ward(self):
        return self.polling_unit.ward


class WardResult(models.Model):
    """Ward-level result override — replaces polling unit aggregation for this ward+party when present."""
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='ward_results')
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, related_name='ward_results')
    votes = models.IntegerField(default=0)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='entered_ward_results')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ward', 'party']
        unique_together = ['ward', 'party']
        indexes = [
            models.Index(fields=['ward', 'party']),
            models.Index(fields=['ward']),
        ]

    def __str__(self):
        return f"{self.party.abbreviation}: {self.votes} votes at Ward {self.ward.name} (override)"

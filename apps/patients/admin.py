"""Admin configuration for the patients app."""
from django.contrib import admin

from .models import PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "gender", "created_at")
    search_fields = ("user__email", "emergency_contact_name")

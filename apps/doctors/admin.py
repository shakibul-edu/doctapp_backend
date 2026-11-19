"""Admin configuration for the doctors app."""
from django.contrib import admin

from .models import DoctorAssistant, DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "professional_name",
        "specialty",
        "verification_status",
        "experience_years",
        "consultation_fee",
    )
    list_filter = ("verification_status", "specialty")
    search_fields = ("professional_name", "medical_registration_number", "user__email")


@admin.register(DoctorAssistant)
class DoctorAssistantAdmin(admin.ModelAdmin):
    list_display = ("doctor", "assistant", "active", "can_manage_chambers")
    list_filter = ("active", "can_manage_chambers")

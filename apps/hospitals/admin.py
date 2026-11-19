"""Admin configuration for the hospitals app."""
from django.contrib import admin

from .models import Chamber, Hospital


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "address")


@admin.register(Chamber)
class ChamberAdmin(admin.ModelAdmin):
    list_display = ("chamber_name", "doctor", "hospital", "active", "consultation_fee_override")
    list_filter = ("active",)

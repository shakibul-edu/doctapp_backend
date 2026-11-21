"""Admin configuration for the appointments app."""
from django.contrib import admin

from .models import Appointment, AvailabilitySchedule, ScheduleException


@admin.register(AvailabilitySchedule)
class AvailabilityScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "chamber", "weekday", "start_time", "end_time", "active")
    list_filter = ("weekday", "active", "doctor")


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ("doctor", "chamber", "exception_type", "date", "active")
    list_filter = ("exception_type", "active", "date")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "chamber", "start_at", "status")
    list_filter = ("status", "doctor", "chamber")
    readonly_fields = ("consultation_fee_snapshot", "created_at", "updated_at")

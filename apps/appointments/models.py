"""Doctor schedules and appointment booking models."""
import uuid

from django.conf import settings
from django.db import models

from apps.doctors.models import DoctorProfile
from apps.hospitals.models import Chamber


class AvailabilitySchedule(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="availability_schedules",
    )
    chamber = models.ForeignKey(
        Chamber,
        on_delete=models.CASCADE,
        related_name="availability_schedules",
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    appointment_duration_minutes = models.PositiveSmallIntegerField(default=30)
    break_start = models.TimeField(blank=True, null=True)
    break_end = models.TimeField(blank=True, null=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "chamber", "weekday", "start_time"),
                name="unique_doctor_chamber_weekday_schedule",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="schedule_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(appointment_duration_minutes__gt=0),
                name="schedule_positive_duration",
            ),
        ]

    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class ScheduleException(models.Model):
    class ExceptionType(models.TextChoices):
        LEAVE = "LEAVE", "Leave"
        HOLIDAY = "HOLIDAY", "Holiday"
        TEMPORARY_UNAVAILABLE = "TEMPORARY_UNAVAILABLE", "Temporary unavailable"
        MODIFIED_HOURS = "MODIFIED_HOURS", "Modified working hours"
        ONE_TIME = "ONE_TIME", "One-time schedule change"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="schedule_exceptions",
    )
    chamber = models.ForeignKey(
        Chamber,
        on_delete=models.CASCADE,
        related_name="schedule_exceptions",
        blank=True,
        null=True,
    )
    exception_type = models.CharField(max_length=32, choices=ExceptionType.choices)
    date = models.DateField(db_index=True)
    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    break_start = models.TimeField(blank=True, null=True)
    break_end = models.TimeField(blank=True, null=True)
    active = models.BooleanField(default=True, db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_datetime", "start_time"]


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"
        NO_SHOW = "NO_SHOW", "No show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    chamber = models.ForeignKey(
        Chamber,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    consultation_fee_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    patient_notes = models.TextField(blank=True)
    cancellation_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="appointment_end_after_start",
            ),
        ]

    @property
    def is_active(self):
        return self.status in {self.Status.PENDING, self.Status.CONFIRMED}

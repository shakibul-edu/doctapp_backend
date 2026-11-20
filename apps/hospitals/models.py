"""Hospital and chamber models."""
import uuid

from django.db import models

from apps.doctors.models import DoctorProfile


class Hospital(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    contact_number = models.CharField(max_length=30, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Chamber(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="chambers",
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        related_name="chambers",
        blank=True,
        null=True,
    )
    chamber_name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    consultation_fee_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["chamber_name"]

    def __str__(self):
        return f"{self.chamber_name} ({self.doctor.professional_name})"

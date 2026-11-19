"""Doctor profile and assistant relationship models."""
import uuid

from django.conf import settings
from django.db import models


class DoctorProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    professional_name = models.CharField(max_length=200)
    profile_picture = models.ImageField(upload_to="doctor_profiles/%Y/%m/", blank=True, null=True)
    bio = models.TextField(blank=True)
    specialty = models.CharField(max_length=100, db_index=True)
    qualifications = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    medical_registration_number = models.CharField(max_length=100, unique=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    languages = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["professional_name"]

    def __str__(self):
        return self.professional_name


class DoctorAssistant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="assistants",
    )
    assistant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_assistant_relationships",
    )
    active = models.BooleanField(default=True)
    can_view_patient_profiles = models.BooleanField(default=False)
    can_manage_chambers = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("doctor", "assistant"), name="unique_doctor_assistant")
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.assistant.email} -> {self.doctor.professional_name}"

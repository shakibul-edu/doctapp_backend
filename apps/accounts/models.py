"""Custom User model for DocTapp."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the unique login identifier.
    Supports UUID primary key, role-based access, and account status tracking.
    """

    class Role(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        DOCTOR = "DOCTOR", "Doctor"
        ASSISTANT = "ASSISTANT", "Assistant"

    class AccountStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        REJECTED = "REJECTED", "Rejected"
        SUSPENDED = "SUSPENDED", "Suspended"

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Authentication
    email = models.EmailField(
        "email address",
        unique=True,
        db_index=True,
    )

    # Personal info
    first_name = models.CharField("first name", max_length=150)
    last_name = models.CharField("last name", max_length=150)
    phone_number = models.CharField(
        "phone number",
        max_length=20,
        blank=True,
        default="",
    )
    profile_image = models.ImageField(
        "profile image",
        upload_to="profile_images/%Y/%m/",
        blank=True,
        null=True,
    )

    # Role & status
    role = models.CharField(
        "role",
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
    )
    account_status = models.CharField(
        "account status",
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
    )

    # Permissions
    is_active = models.BooleanField("active", default=True)
    is_staff = models.BooleanField("staff status", default=False)

    # Timestamps
    created_at = models.DateTimeField("date created", auto_now_add=True)
    updated_at = models.DateTimeField("date updated", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

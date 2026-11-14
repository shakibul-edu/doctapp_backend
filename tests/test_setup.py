"""Tests to verify the Django project foundation is set up correctly."""
import uuid

import pytest
from django.db import connection

from apps.accounts.models import User


@pytest.mark.django_db
class TestDjangoSetup:
    """Verify Django starts and basic configuration works."""

    def test_django_starts_successfully(self, client):
        """Django should start and serve the admin login page."""
        response = client.get("/admin/login/")
        assert response.status_code == 200

    def test_database_connection(self):
        """Database connection should work."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        assert result == (1,)


@pytest.mark.django_db
class TestCustomUserModel:
    """Verify the custom User model works correctly."""

    def test_create_user(self, user_data):
        """Should create a regular user with email authentication."""
        user = User.objects.create_user(**user_data)
        assert user.email == user_data["email"]
        assert user.first_name == user_data["first_name"]
        assert user.last_name == user_data["last_name"]
        assert user.phone_number == user_data["phone_number"]
        assert user.check_password(user_data["password"])
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_without_email_raises_error(self):
        """Should raise ValueError when creating user without email."""
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email="", password="test123")

    def test_create_superuser(self):
        """Should create a superuser with correct permissions."""
        user = User.objects.create_superuser(
            email="super@example.com",
            password="SuperPass123!",
            first_name="Super",
            last_name="Admin",
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.account_status == User.AccountStatus.ACTIVE

    def test_create_superuser_invalid_is_staff(self):
        """Should raise ValueError if superuser has is_staff=False."""
        with pytest.raises(ValueError, match="Superuser must have is_staff=True"):
            User.objects.create_superuser(
                email="super2@example.com",
                password="SuperPass123!",
                first_name="Super",
                last_name="Admin",
                is_staff=False,
            )

    def test_create_superuser_invalid_is_superuser(self):
        """Should raise ValueError if superuser has is_superuser=False."""
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True"):
            User.objects.create_superuser(
                email="super3@example.com",
                password="SuperPass123!",
                first_name="Super",
                last_name="Admin",
                is_superuser=False,
            )

    def test_uuid_primary_key(self, create_user):
        """User primary key should be a UUID."""
        assert isinstance(create_user.id, uuid.UUID)
        assert create_user.pk == create_user.id

    def test_email_is_unique(self, create_user, user_data):
        """Should not allow duplicate emails."""
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            User.objects.create_user(**user_data)

    def test_user_string_representation(self, create_user):
        """User string representation should be the email."""
        assert str(create_user) == create_user.email

    def test_full_name_property(self, create_user):
        """full_name should return first_name + last_name."""
        assert create_user.full_name == f"{create_user.first_name} {create_user.last_name}"

    def test_default_role_is_patient(self, create_user):
        """Default role should be PATIENT."""
        assert create_user.role == User.Role.PATIENT

    def test_default_account_status_is_pending(self, create_user):
        """Default account status should be PENDING."""
        assert create_user.account_status == User.AccountStatus.PENDING

    def test_user_roles_exist(self):
        """All expected user roles should be defined."""
        roles = [choice[0] for choice in User.Role.choices]
        assert "PATIENT" in roles
        assert "DOCTOR" in roles
        assert "ASSISTANT" in roles

    def test_account_statuses_exist(self):
        """All expected account statuses should be defined."""
        statuses = [choice[0] for choice in User.AccountStatus.choices]
        assert "PENDING" in statuses
        assert "ACTIVE" in statuses
        assert "REJECTED" in statuses
        assert "SUSPENDED" in statuses

    def test_timestamps_are_set(self, create_user):
        """created_at and updated_at should be automatically set."""
        assert create_user.created_at is not None
        assert create_user.updated_at is not None

    def test_email_normalized(self):
        """Email should be normalized (lowercased domain)."""
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="test123",
            first_name="Test",
            last_name="User",
        )
        assert user.email == "Test@example.com"

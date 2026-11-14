"""Shared pytest fixtures for DocTapp tests."""
import pytest

from apps.accounts.models import User


@pytest.fixture
def user_data():
    """Return valid user creation data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "+8801712345678",
    }


@pytest.fixture
def create_user(db, user_data):
    """Create and return a regular user."""
    return User.objects.create_user(**user_data)


@pytest.fixture
def create_superuser(db):
    """Create and return a superuser."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
    )

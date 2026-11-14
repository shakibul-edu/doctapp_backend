"""Authentication and authorization API tests."""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


def register_payload(**overrides):
    payload = {
        "email": "new@example.com",
        "password": "SecurePass123!",
        "first_name": "New",
        "last_name": "Patient",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestAuthenticationAPI:
    def test_registration_defaults_to_active_patient(self, api_client):
        response = api_client.post(
            "/api/v1/accounts/register/", register_payload(), format="json"
        )

        assert response.status_code == 201
        user = User.objects.get(email="new@example.com")
        assert user.role == User.Role.PATIENT
        assert user.account_status == User.AccountStatus.ACTIVE
        assert user.check_password("SecurePass123!")

    def test_duplicate_email_is_rejected(self, api_client, create_user):
        response = api_client.post(
            "/api/v1/accounts/register/",
            register_payload(email=create_user.email),
            format="json",
        )

        assert response.status_code == 400
        assert "email" in response.data

    def test_invalid_password_is_rejected(self, api_client):
        response = api_client.post(
            "/api/v1/accounts/register/",
            register_payload(password="password"),
            format="json",
        )

        assert response.status_code == 400
        assert "password" in response.data

    def test_login_and_me(self, api_client, create_user):
        create_user.account_status = User.AccountStatus.ACTIVE
        create_user.save(update_fields=("account_status",))

        login = api_client.post(
            "/api/v1/accounts/login/",
            {"email": create_user.email, "password": "SecurePass123!"},
            format="json",
        )

        assert login.status_code == 200
        assert {"access", "refresh"} <= login.data.keys()
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        me = api_client.get("/api/v1/accounts/me/")
        assert me.status_code == 200
        assert me.data["email"] == create_user.email
        assert "password" not in me.data

    def test_pending_account_cannot_login(self, api_client, create_user):
        response = api_client.post(
            "/api/v1/accounts/login/",
            {"email": create_user.email, "password": "SecurePass123!"},
            format="json",
        )
        assert response.status_code == 400

    def test_suspended_account_cannot_use_protected_api(self, api_client, create_user):
        create_user.account_status = User.AccountStatus.SUSPENDED
        create_user.save(update_fields=("account_status",))
        token = RefreshToken.for_user(create_user).access_token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get("/api/v1/accounts/me/")

        assert response.status_code == 403

    def test_refresh_rotation_and_logout_blacklist(self, api_client, create_user):
        create_user.account_status = User.AccountStatus.ACTIVE
        create_user.save(update_fields=("account_status",))
        login = api_client.post(
            "/api/v1/accounts/login/",
            {"email": create_user.email, "password": "SecurePass123!"},
            format="json",
        )
        refresh = login.data["refresh"]

        rotated = api_client.post(
            "/api/v1/accounts/token/refresh/", {"refresh": refresh}, format="json"
        )
        assert rotated.status_code == 200
        assert rotated.data["refresh"] != refresh

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        logout = api_client.post(
            "/api/v1/accounts/logout/", {"refresh": rotated.data["refresh"]}, format="json"
        )
        assert logout.status_code == 204
        blacklisted = api_client.post(
            "/api/v1/accounts/token/refresh/",
            {"refresh": rotated.data["refresh"]},
            format="json",
        )
        assert blacklisted.status_code == 401

    def test_profile_cannot_change_role_or_status(self, api_client, create_user):
        create_user.account_status = User.AccountStatus.ACTIVE
        create_user.save(update_fields=("account_status",))
        api_client.force_authenticate(create_user)

        response = api_client.patch(
            "/api/v1/accounts/me/",
            {"role": User.Role.DOCTOR, "account_status": User.AccountStatus.SUSPENDED},
            format="json",
        )

        assert response.status_code == 200
        create_user.refresh_from_db()
        assert create_user.role == User.Role.PATIENT
        assert create_user.account_status == User.AccountStatus.ACTIVE

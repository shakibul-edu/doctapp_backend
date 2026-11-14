"""Reusable permissions for account and role-based API access."""
from rest_framework.permissions import BasePermission

from .models import User


class IsAccountActive(BasePermission):
    """Allow only authenticated users with an active account."""

    message = "Your account is inactive or suspended."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.account_status == User.AccountStatus.ACTIVE
        )


class _RolePermission(BasePermission):
    role = None

    def has_permission(self, request, view):
        return IsAccountActive().has_permission(request, view) and request.user.role == self.role


class IsPatient(_RolePermission):
    role = User.Role.PATIENT


class IsDoctor(_RolePermission):
    role = User.Role.DOCTOR


class IsAssistant(_RolePermission):
    role = User.Role.ASSISTANT


class IsDoctorOrAssistant(_RolePermission):
    def has_permission(self, request, view):
        return IsAccountActive().has_permission(request, view) and request.user.role in {
            User.Role.DOCTOR,
            User.Role.ASSISTANT,
        }


class IsOwner(BasePermission):
    """Allow access when the authenticated user owns the requested object."""

    def has_object_permission(self, request, view, obj):
        return obj == request.user or getattr(obj, "user", None) == request.user

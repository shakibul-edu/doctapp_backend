from rest_framework.permissions import BasePermission

from apps.accounts.permissions import IsAccountActive


class IsPatientProfileOwner(BasePermission):
    def has_permission(self, request, view):
        return IsAccountActive().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or obj.user_id == request.user.id

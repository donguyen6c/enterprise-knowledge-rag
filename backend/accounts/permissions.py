from rest_framework.permissions import BasePermission

from accounts.models import UserRole


class IsApplicationAdmin(BasePermission):
    """Allows only the two application-level administrator roles."""

    message = "Chỉ System Admin hoặc Organization Admin mới có quyền quản trị."

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if user.role == UserRole.SYSTEM_ADMIN:
            return True

        return (
            user.role == UserRole.ORG_ADMIN
            and user.organization_id is not None
            and user.organization.is_active
        )


class IsSystemAdmin(BasePermission):
    """Allows organization-wide settings to be managed only by System Admin."""

    message = "Chỉ System Admin mới có quyền quản lý tổ chức."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.SYSTEM_ADMIN
        )

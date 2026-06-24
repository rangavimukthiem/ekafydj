"""
apps.core — Custom DRF Permissions
"""
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Only users with role=admin can perform this action."""

    message = "You must be an EKAFY administrator to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsOperatorOrAdmin(BasePermission):
    """Users with role=admin or role=operator."""

    message = "You must be an operator or administrator to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "operator")
        )


class IsViewerOrAbove(BasePermission):
    """Any authenticated EKAFY user (viewer, operator, admin)."""

    message = "You must be authenticated to access this resource."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

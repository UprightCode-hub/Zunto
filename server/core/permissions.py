#server/core/permissions.py
from rest_framework import permissions
from accounts.seller_utils import is_active_seller


class IsSeller(permissions.BasePermission):
    """Allow access only to authenticated seller users."""

    message = 'Seller account required for this action.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or getattr(user, 'role', None) == 'admin':
            return True
        return is_active_seller(user)


class IsSellerOrAdmin(permissions.BasePermission):
    """Allow access to seller-only actions while preserving admin override."""

    message = 'Seller account required for this action.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, 'role', None)
        if user.is_staff or role == 'admin':
            return True
        return is_active_seller(user)



class IsAdminOrStaff(permissions.BasePermission):
    """Allow platform admin access (staff flag or role=admin)."""

    message = 'Admin privileges required for this action.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        role = getattr(user, 'role', None)
        return bool(user.is_staff or role == 'admin')

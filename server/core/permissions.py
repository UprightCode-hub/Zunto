#server/core/permissions.py
from rest_framework import permissions


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
        return role == 'seller'

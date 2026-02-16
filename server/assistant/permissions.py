#server/assistant/permissions.py
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    """
    
    def has_permission(self, request, view):
                                                     
        if request.method in permissions.SAFE_METHODS:
            return True
        
                                                
        return request.user and request.user.is_staff


class IsStaffUser(permissions.BasePermission):
    """
    Permission class to restrict access to staff users only.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

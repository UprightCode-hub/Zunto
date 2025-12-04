# orders/permissions.py
from rest_framework import permissions


class IsOrderOwner(permissions.BasePermission):
    """
    Permission to check if user is the owner of the order
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.customer == request.user


class IsSellerOfOrderItem(permissions.BasePermission):
    """
    Permission to check if user is the seller of the order item
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        return obj.seller == request.user
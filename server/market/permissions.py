#server/market/permissions.py
from rest_framework import permissions


class IsSellerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow sellers of a product to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
                                                     
        if request.method in permissions.SAFE_METHODS:
            return True
        
                                                          
        return obj.seller == request.user


class IsProductSeller(permissions.BasePermission):
    """
    Permission to check if user is the seller of the product
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
                                                    
        if hasattr(obj, 'seller'):
            return obj.seller == request.user
        elif hasattr(obj, 'product'):
            return obj.product.seller == request.user
        return False

# reviews/permissions.py
from rest_framework import permissions


class IsReviewerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow reviewers to edit their own reviews.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the reviewer
        return obj.reviewer == request.user


class IsSellerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow sellers to respond to reviews.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if user is the seller
        if hasattr(obj, 'product'):
            return obj.product.seller == request.user
        elif hasattr(obj, 'seller'):
            return obj.seller == request.user
        
        return False
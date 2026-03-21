#server/reviews/permissions.py
from rest_framework import permissions


class IsReviewerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow reviewers to edit their own reviews.
    """
    
    def has_object_permission(self, request, view, obj):
                                                     
        if request.method in permissions.SAFE_METHODS:
            return True
        
                                                            
        return obj.reviewer == request.user


class IsSellerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow sellers to respond to reviews.
    """
    
    def has_object_permission(self, request, view, obj):
                                                     
        if request.method in permissions.SAFE_METHODS:
            return True
        
                                     
        if hasattr(obj, 'product'):
            return obj.product.seller == request.user
        elif hasattr(obj, 'seller'):
            return obj.seller == request.user
        
        return False

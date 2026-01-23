"""
Custom Middleware for Zunto Assistant API
Production-safe CSRF handling
Created by: Wisdom Ekwugha
"""


class DisableCSRFForAPIMiddleware:
    """
    Selectively disable CSRF for specific public API endpoints.
    
    SECURITY NOTE: Only disables CSRF for health check endpoints.
    All other endpoints maintain full CSRF protection.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of endpoints that are truly public and don't need CSRF
        public_endpoints = [
            '/assistant/api/chat/health/',
            '/assistant/api/tts/health/',
            '/assistant/api/docs/',
            '/assistant/api/about/',
        ]
        
        # Disable CSRF only for explicitly public endpoints
        if request.path in public_endpoints:
            setattr(request, '_dont_enforce_csrf_checks', True)
        
        response = self.get_response(request)
        return response
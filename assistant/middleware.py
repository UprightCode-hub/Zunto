
class DisableCSRFForAPIMiddleware:
    """
    Disable CSRF for API endpoints during local testing.
    REMOVE THIS IN PRODUCTION!
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Disable CSRF for assistant API endpoints
        if request.path.startswith('/assistant/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        
        response = self.get_response(request)
        return response

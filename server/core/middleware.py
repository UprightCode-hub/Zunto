#server/core/middleware.py
import uuid


class CorrelationIdMiddleware:
    """Attach request context metadata for tracing and multi-device diagnostics."""

    correlation_header_name = 'HTTP_X_CORRELATION_ID'
    correlation_response_header = 'X-Correlation-ID'

    client_viewport_header_name = 'HTTP_X_CLIENT_VIEWPORT'
    client_platform_header_name = 'HTTP_X_CLIENT_PLATFORM'
    client_viewport_response_header = 'X-Client-Viewport'
    client_platform_response_header = 'X-Client-Platform'

    allowed_viewports = {'mobile', 'tablet', 'desktop'}
    allowed_platforms = {'phone', 'tablet', 'laptop-desktop', 'server'}

    @classmethod
    def _normalize_value(cls, raw_value, allowed_values):
        if not raw_value:
            return 'unknown'
        value = str(raw_value).strip().lower()
        return value if value in allowed_values else 'unknown'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(self.correlation_header_name)
        correlation_id = incoming if incoming else str(uuid.uuid4())
        request.correlation_id = correlation_id

        request.client_viewport = self._normalize_value(
            request.META.get(self.client_viewport_header_name),
            self.allowed_viewports,
        )
        request.client_platform = self._normalize_value(
            request.META.get(self.client_platform_header_name),
            self.allowed_platforms,
        )

        response = self.get_response(request)
        response[self.correlation_response_header] = correlation_id
        response[self.client_viewport_response_header] = request.client_viewport
        response[self.client_platform_response_header] = request.client_platform
        return response

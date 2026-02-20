#server/core/middleware.py
import logging
import time
import uuid

from django.conf import settings


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


class RequestTimingMiddleware:
    """Record request latency and flag slow API responses for observability."""

    duration_header = 'X-Response-Time-Ms'

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')

    def __call__(self, request):
        started_at = time.monotonic()
        response = self.get_response(request)

        elapsed_ms = round((time.monotonic() - started_at) * 1000, 2)
        request.response_time_ms = elapsed_ms
        response[self.duration_header] = str(elapsed_ms)

        threshold_ms = getattr(settings, 'SLOW_REQUEST_THRESHOLD_MS', 1500)
        path = getattr(request, 'path', '') or ''
        if elapsed_ms >= threshold_ms and (path.startswith('/api/') or path == '/health/'):
            self.logger.warning(
                'slow_request_detected',
                extra={
                    'event': 'slow_request_detected',
                    'path': path,
                    'method': getattr(request, 'method', ''),
                    'duration_ms': elapsed_ms,
                    'correlation_id': getattr(request, 'correlation_id', ''),
                },
            )

        return response

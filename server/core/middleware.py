import uuid


class CorrelationIdMiddleware:
    """Attach correlation_id to every request/response for audit tracing."""

    header_name = 'HTTP_X_CORRELATION_ID'
    response_header = 'X-Correlation-ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(self.header_name)
        correlation_id = incoming if incoming else str(uuid.uuid4())
        request.correlation_id = correlation_id

        response = self.get_response(request)
        response[self.response_header] = correlation_id
        return response

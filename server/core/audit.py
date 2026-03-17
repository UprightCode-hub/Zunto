#server/core/audit.py
import json
import logging
from django.utils import timezone


logger = logging.getLogger('audit')


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def audit_event(request, *, action, endpoint=None, session_id=None, extra=None):
    payload = {
        'timestamp': timezone.now().isoformat(),
        'correlation_id': getattr(request, 'correlation_id', None),
        'user_id': request.user.id if getattr(request, 'user', None) and request.user.is_authenticated else None,
        'session_id': session_id,
        'endpoint': endpoint or request.path,
        'action': action,
        'ip': _client_ip(request),
    }
    if extra:
        payload.update(extra)

    logger.info(json.dumps(payload, default=str))

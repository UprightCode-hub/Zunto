from django.core.cache import cache


VIEW_COOLDOWN_SECONDS = 10 * 60


def _viewer_key(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return f"u:{user.id}"

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
    if ip_address:
        return f"ip:{ip_address}"

    session = getattr(request, 'session', None)
    session_key = getattr(session, 'session_key', None)
    if session_key:
        return f"s:{session_key}"

    return 'anonymous'


def should_count_view(request, product_id):
    """Return True only once per viewer/product within cooldown window."""
    dedupe_key = f"product_view:{_viewer_key(request)}:{product_id}"
    return cache.add(dedupe_key, True, timeout=VIEW_COOLDOWN_SECONDS)

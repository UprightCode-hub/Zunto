#server/core/tasks.py
import logging
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

import requests

if __import__('importlib').util.find_spec('celery') is not None:
    from celery import shared_task
else:  # pragma: no cover
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from core.health_monitor import evaluate_health_snapshot


logger = logging.getLogger('security.health')


def _health_alert_email_enabled() -> bool:
    return bool(getattr(settings, 'HEALTH_ALERT_NOTIFY_EMAIL_ENABLED', False))


def _health_alert_recipients():
    recipients = getattr(settings, 'HEALTH_ALERT_RECIPIENTS', None) or []
    if recipients:
        return [item for item in recipients if item]

    admin_email = getattr(settings, 'ADMIN_EMAIL', '')
    return [admin_email] if admin_email else []


def _health_alert_cache_key(snapshot, alerts):
    status_value = str(snapshot.get('status') or 'unknown')
    kinds = sorted(str(item.get('kind') or 'unknown') for item in alerts)
    signature = f"{status_value}:{'|'.join(kinds)}"
    digest = sha256(signature.encode('utf-8')).hexdigest()[:16]
    return digest


def _health_alert_channel_cache_key(snapshot, alerts, channel):
    signature = _health_alert_cache_key(snapshot, alerts)
    return f'health-alert:{channel}:{signature}'


def _health_alert_webhook_enabled() -> bool:
    return bool(getattr(settings, 'HEALTH_ALERT_NOTIFY_WEBHOOK_ENABLED', False))


def _send_health_alert_webhook(snapshot, alerts):
    if not _health_alert_webhook_enabled():
        return {'sent': False, 'reason': 'disabled'}

    webhook_url = str(getattr(settings, 'HEALTH_ALERT_WEBHOOK_URL', '') or '').strip()
    if not webhook_url:
        return {'sent': False, 'reason': 'no_webhook_url'}

    cooldown_seconds = int(getattr(settings, 'HEALTH_ALERT_NOTIFY_WEBHOOK_COOLDOWN_SECONDS', 300))
    cache_key = _health_alert_channel_cache_key(snapshot, alerts, 'webhook')
    if cache.get(cache_key):
        return {'sent': False, 'reason': 'cooldown_active'}

    kinds = sorted({str(item.get('kind') or 'unknown') for item in alerts})
    payload = {
        'status': snapshot.get('status'),
        'alerts': alerts,
        'alert_kinds': kinds,
        'database': snapshot.get('database'),
        'cache': snapshot.get('cache'),
        'celery': snapshot.get('celery'),
        'queue_depth': snapshot.get('queue_depth'),
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('health_monitor_webhook_delivery_failed', extra={'error': str(exc), 'webhook_url': webhook_url})
        return {'sent': False, 'reason': 'delivery_failed', 'error': str(exc)}

    cache.set(cache_key, True, timeout=max(60, cooldown_seconds))
    return {'sent': True, 'reason': 'delivered', 'webhook': webhook_url}

def _send_health_alert_email(snapshot, alerts):
    if not _health_alert_email_enabled():
        return {'sent': False, 'reason': 'disabled'}

    recipients = _health_alert_recipients()
    if not recipients:
        return {'sent': False, 'reason': 'no_recipients'}

    cooldown_seconds = int(getattr(settings, 'HEALTH_ALERT_NOTIFY_EMAIL_COOLDOWN_SECONDS', 900))
    cache_key = _health_alert_channel_cache_key(snapshot, alerts, 'email')
    if cache.get(cache_key):
        return {'sent': False, 'reason': 'cooldown_active'}

    kinds = sorted({str(item.get('kind') or 'unknown') for item in alerts})
    subject = f"[Zunto] Health alert: {snapshot.get('status')} ({', '.join(kinds) if kinds else 'degraded'})"
    message = (
        "Automated health monitor detected an unhealthy state.\n\n"
        f"Status: {snapshot.get('status')}\n"
        f"Database: {snapshot.get('database')}\n"
        f"Cache: {snapshot.get('cache')}\n"
        f"Celery: {snapshot.get('celery')}\n"
        f"Queue Depth: {snapshot.get('queue_depth')}\n"
        f"Alerts: {alerts}\n"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning('health_monitor_email_delivery_failed', extra={'error': str(exc), 'recipients': recipients})
        return {'sent': False, 'reason': 'delivery_failed', 'error': str(exc)}

    cache.set(cache_key, True, timeout=max(60, cooldown_seconds))
    return {'sent': True, 'reason': 'delivered', 'recipients': recipients}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={'max_retries': 3})
def monitor_system_health_alerts(self):
    snapshot = evaluate_health_snapshot()
    alerts = snapshot.get('diagnostics', {}).get('alerts', [])

    if snapshot.get('status') != 'healthy' or alerts:
        logger.warning('health_monitor_unhealthy_state', extra={'snapshot': snapshot, 'alerts': alerts})
        email_result = _send_health_alert_email(snapshot, alerts)
        webhook_result = _send_health_alert_webhook(snapshot, alerts)
    else:
        logger.info('health_monitor_ok', extra={'snapshot': snapshot})
        email_result = {'sent': False, 'reason': 'healthy'}
        webhook_result = {'sent': False, 'reason': 'healthy'}

    return {
        'status': snapshot.get('status'),
        'alert_count': len(alerts),
        'email': email_result,
        'webhook': webhook_result,
    }

#server/core/tasks.py
import logging

if __import__('importlib').util.find_spec('celery') is not None:
    from celery import shared_task
else:  # pragma: no cover
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from core.health_monitor import evaluate_health_snapshot


logger = logging.getLogger('security.health')


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={'max_retries': 3})
def monitor_system_health_alerts(self):
    snapshot = evaluate_health_snapshot()
    alerts = snapshot.get('diagnostics', {}).get('alerts', [])

    if snapshot.get('status') != 'healthy' or alerts:
        logger.warning('health_monitor_unhealthy_state', extra={'snapshot': snapshot, 'alerts': alerts})
    else:
        logger.info('health_monitor_ok', extra={'snapshot': snapshot})

    return {
        'status': snapshot.get('status'),
        'alert_count': len(alerts),
    }

#server/core/health_monitor.py
from core.views import (
    _check_cache_health,
    _check_celery_health,
    _check_database_health,
    _check_queue_depth_health,
    _celery_alerts_from_details,
)


def evaluate_health_snapshot():
    db_status, db_error = _check_database_health()
    cache_status, cache_error = _check_cache_health()
    celery_status, celery_details = _check_celery_health(include_details=True)
    queue_status, queue_details = _check_queue_depth_health(include_details=True)

    alerts = []
    if celery_details:
        alerts.extend(_celery_alerts_from_details(celery_details))

    if queue_details and isinstance(queue_details, dict):
        threshold = int(queue_details.get('threshold') or 0)
        for queue_name, depth in (queue_details.get('queues') or {}).items():
            if int(depth) >= threshold:
                alerts.append({
                    'kind': 'redis_queue_depth_high',
                    'queue': queue_name,
                    'current': int(depth),
                    'threshold': threshold,
                })

    status_value = 'healthy' if all(v == 'ok' for v in [db_status, cache_status, celery_status, queue_status]) else 'unhealthy'

    return {
        'status': status_value,
        'database': db_status,
        'cache': cache_status,
        'celery': celery_status,
        'queue_depth': queue_status,
        'errors': {
            'database': db_error,
            'cache': cache_error,
        },
        'diagnostics': {
            'celery': celery_details,
            'queue_depth': queue_details,
            'alerts': alerts,
        },
    }

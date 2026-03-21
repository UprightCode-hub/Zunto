#server/ZuntoProject/celery.py
import importlib.util
import os

if importlib.util.find_spec('celery') is not None:
    from celery import Celery
    from celery.schedules import crontab
else:
    Celery = None

    def crontab(*args, **kwargs):
        return {'args': args, 'kwargs': kwargs}

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')

if Celery is not None:
    app = Celery('ZuntoProject')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

    app.conf.beat_schedule = {
        'detect-abandoned-carts': {
            'task': 'cart.tasks.detect_abandoned_carts',
            'schedule': crontab(minute=0),
        },
        'send-abandonment-reminders': {
            'task': 'cart.tasks.send_abandonment_reminders',
            'schedule': crontab(hour=2, minute=0),
        },
    }

    @app.task(bind=True)
    def debug_task(self):
        print(f'Request: {self.request!r}')
else:
    class _NoopCeleryApp:
        """Fallback app used in environments where Celery dependency is unavailable."""

        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    app = _NoopCeleryApp()

    @app.task(bind=True)
    def debug_task(*args, **kwargs):
        return None

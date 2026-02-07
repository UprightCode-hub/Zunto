# ZuntoProject/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')

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
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from notifications.models import EmailLog


class Command(BaseCommand):
    help = 'Operational report for email delivery health and Celery worker status.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=60, help='Lookback window in minutes')

    def handle(self, *args, **options):
        minutes = options['minutes']
        since = timezone.now() - timedelta(minutes=minutes)

        logs = EmailLog.objects.filter(created_at__gte=since)
        total = logs.count()
        sent = logs.filter(status='sent').count()
        failed = logs.filter(status='failed').count()
        pending = logs.filter(status='pending').count()

        failure_rate = (failed / total) if total else 0.0
        self.stdout.write(f'Window: last {minutes} minutes')
        self.stdout.write(f'Total emails: {total}')
        self.stdout.write(f'Sent: {sent}')
        self.stdout.write(f'Failed: {failed}')
        self.stdout.write(f'Pending: {pending}')
        self.stdout.write(f'Failure rate: {failure_rate:.2%}')

        top_failed = (
            logs.filter(status='failed')
            .values('template__template_type')
            .order_by('template__template_type')
        )
        if failed:
            self.stdout.write('Failed templates:')
            counts = {}
            for row in top_failed:
                key = row['template__template_type'] or 'unknown'
                counts[key] = counts.get(key, 0) + 1
            for key, value in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f'  - {key}: {value}')

        self._print_celery_status()

        threshold = getattr(settings, 'EMAIL_ALERT_FAILURE_RATE_THRESHOLD', 0.05)
        min_samples = getattr(settings, 'EMAIL_ALERT_MIN_SAMPLES', 50)
        if total >= min_samples and failure_rate >= threshold:
            self.stdout.write(self.style.ERROR(
                f'ALERT: failure rate {failure_rate:.2%} exceeds threshold {threshold:.2%} (samples={total})'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Email failure-rate threshold check passed'))

    def _print_celery_status(self):
        try:
            from ZuntoProject.celery import app
            inspect = app.control.inspect(timeout=1.0)
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}

            worker_count = len(active.keys())
            active_jobs = sum(len(v or []) for v in active.values())
            reserved_jobs = sum(len(v or []) for v in reserved.values())
            scheduled_jobs = sum(len(v or []) for v in scheduled.values())

            self.stdout.write(f'Celery workers: {worker_count}')
            self.stdout.write(f'Active jobs: {active_jobs}')
            self.stdout.write(f'Reserved jobs: {reserved_jobs}')
            self.stdout.write(f'Scheduled jobs: {scheduled_jobs}')
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'Unable to inspect Celery workers: {exc}'))

#server/assistant/management/commands/cleanup_assistant_archives.py
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from assistant.models import ConversationSession, ConversationLog


class Command(BaseCommand):
    help = 'Archive/cleanup stale assistant sessions and logs to prevent table bloat.'

    def add_arguments(self, parser):
        parser.add_argument('--session-days', type=int, default=30)
        parser.add_argument('--log-days', type=int, default=90)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        now = timezone.now()
        session_cutoff = now - timedelta(days=options['session_days'])
        log_cutoff = now - timedelta(days=options['log_days'])

        sessions_qs = ConversationSession.objects.filter(last_activity__lt=session_cutoff)
        logs_qs = ConversationLog.objects.filter(created_at__lt=log_cutoff)

        session_count = sessions_qs.count()
        log_count = logs_qs.count()

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN: {session_count} sessions and {log_count} logs would be deleted.'
            ))
            return

        sessions_qs.delete()
        logs_qs.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {session_count} stale sessions and {log_count} stale logs.'
        ))

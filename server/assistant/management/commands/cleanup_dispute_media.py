from django.core.management.base import BaseCommand
from django.utils import timezone

from assistant.models import DisputeMedia
from assistant.services.dispute_storage import dispute_storage


class Command(BaseCommand):
    help = 'Delete dispute evidence files past retention window and mark records as deleted.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500, help='Maximum records to process')
        parser.add_argument('--dry-run', action='store_true', help='Preview deletions without applying')

    def handle(self, *args, **options):
        now = timezone.now()
        limit = max(1, options['limit'])
        dry_run = options['dry_run']

        queryset = DisputeMedia.objects.filter(
            is_deleted=False,
            retention_expires_at__isnull=False,
            retention_expires_at__lte=now,
        ).order_by('retention_expires_at')[:limit]

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('No expired dispute media found.'))
            return

        deleted_files = 0
        marked_records = 0

        for media in queryset:
            if not dry_run:
                if dispute_storage.delete(media.file.name):
                    deleted_files += 1
                media.mark_deleted()
                marked_records += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: {total} media records would be cleaned.'))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Cleaned {marked_records} dispute media records; deleted {deleted_files} files from storage.'
            )
        )

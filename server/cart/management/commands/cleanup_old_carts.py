#server/cart/management/commands/cleanup_old_carts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartAbandonment


class Command(BaseCommand):
    help = 'Clean up old guest carts without abandonment records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete guest carts older than this many days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        carts_with_abandonments = CartAbandonment.objects.values_list('cart_id', flat=True)
        
        old_guest_carts = Cart.objects.filter(
            user=None,
            updated_at__lt=cutoff_date
        ).exclude(
            id__in=carts_with_abandonments
        )
        
        count = old_guest_carts.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} old guest carts (older than {days} days).')
            )
            if count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Cart IDs preview (first 10): {list(old_guest_carts.values_list("id", flat=True)[:10])}')
                )
        else:
            old_guest_carts.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {count} old guest carts (preserved carts with abandonment records).')
            )
        
        self.stdout.write(
            self.style.WARNING('\nNote: Abandonment tracking is handled by scheduled Celery task "detect_abandoned_carts".')
        )

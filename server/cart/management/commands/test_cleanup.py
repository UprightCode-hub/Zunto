#server/cart/management/commands/test_cleanup.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartAbandonment


class Command(BaseCommand):
    help = 'Show statistics about guest carts eligible for cleanup'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Check carts older than this many days'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        total_guest_carts = Cart.objects.filter(user=None).count()
        old_guest_carts = Cart.objects.filter(user=None, updated_at__lt=cutoff_date).count()
        
        carts_with_abandonments = CartAbandonment.objects.values_list('cart_id', flat=True)
        protected_carts = Cart.objects.filter(
            user=None,
            updated_at__lt=cutoff_date,
            id__in=carts_with_abandonments
        ).count()
        
        eligible_for_deletion = old_guest_carts - protected_carts
        
        self.stdout.write(self.style.SUCCESS('\n=== Guest Cart Cleanup Statistics ==='))
        self.stdout.write(f'Total guest carts: {total_guest_carts}')
        self.stdout.write(f'Guest carts older than {days} days: {old_guest_carts}')
        self.stdout.write(f'Protected (have abandonment records): {protected_carts}')
        self.stdout.write(self.style.WARNING(f'Eligible for deletion: {eligible_for_deletion}'))
        
        if eligible_for_deletion > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nRun "python manage.py cleanup_old_carts --days={days}" to delete them')
            )
        else:
            self.stdout.write(self.style.SUCCESS('\nNo carts eligible for cleanup'))

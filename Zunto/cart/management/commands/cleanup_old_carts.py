# cart/management/commands/cleanup_old_carts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartAbandonment


class Command(BaseCommand):
    help = 'Clean up old guest carts and track abandoned carts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete guest carts older than this many days'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find old guest carts (no user)
        old_guest_carts = Cart.objects.filter(
            user=None,
            updated_at__lt=cutoff_date
        )
        
        count = old_guest_carts.count()
        
        # Delete them
        old_guest_carts.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {count} old guest carts.')
        )
        
        # Track abandoned carts (carts not updated in 24 hours with items)
        abandonment_cutoff = timezone.now() - timedelta(hours=24)
        
        abandoned_carts = Cart.objects.filter(
            updated_at__lt=abandonment_cutoff,
            items__isnull=False
        ).distinct()
        
        abandoned_count = 0
        for cart in abandoned_carts:
            # Check if not already tracked
            if not CartAbandonment.objects.filter(cart=cart, recovered=False).exists():
                CartAbandonment.objects.create(
                    cart=cart,
                    user=cart.user,
                    total_items=cart.total_items,
                    total_value=cart.subtotal
                )
                abandoned_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Tracked {abandoned_count} abandoned carts.')
        )
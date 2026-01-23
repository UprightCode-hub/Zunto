# cart/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Cart, CartAbandonment


@receiver(post_save, sender=Cart)
def check_cart_abandonment(sender, instance, created, **kwargs):
    """Check if cart should be marked as abandoned"""
    
    # Only check for carts with items
    if instance.items.exists():
        # Check if cart hasn't been updated in 24 hours
        abandonment_time = timezone.now() - timedelta(hours=24)
        
        if instance.updated_at < abandonment_time:
            # Check if not already tracked
            if not CartAbandonment.objects.filter(
                cart=instance, 
                recovered=False
            ).exists():
                # Create abandonment record
                CartAbandonment.objects.create(
                    cart=instance,
                    user=instance.user,
                    total_items=instance.total_items,
                    total_value=instance.subtotal
                )
                
                # TODO: Send reminder email
                # if instance.user:
                #     send_cart_reminder_email(instance.user, instance)
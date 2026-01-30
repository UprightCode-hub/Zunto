# cart/tasks.py
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from datetime import timedelta
from .models import Cart, CartAbandonment
import logging

logger = logging.getLogger(__name__)


@shared_task
def detect_abandoned_carts():
    threshold = timezone.now() - timedelta(hours=24)
    
    abandoned_carts = Cart.objects.filter(
        updated_at__lt=threshold
    ).exclude(
        items__isnull=True
    ).exclude(
        Q(abandonment_records__recovered=False) & 
        Q(abandonment_records__abandoned_at__gte=threshold)
    ).prefetch_related('items__product')
    
    created_count = 0
    error_count = 0
    
    for cart in abandoned_carts:
        try:
            with transaction.atomic():
                _, created = CartAbandonment.objects.get_or_create(
                    cart=cart,
                    abandoned_at__gte=threshold,
                    recovered=False,
                    defaults={
                        'user': cart.user,
                        'total_items': cart.total_items,
                        'total_value': cart.subtotal,
                    }
                )
                if created:
                    created_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to create abandonment record for cart {cart.id}: {e}")
            continue
    
    logger.info(f"Detected {created_count} abandoned carts ({error_count} errors)")
    return f"Detected {created_count} abandoned carts"


@shared_task
def send_abandonment_reminders():
    reminder_threshold = timezone.now() - timedelta(hours=48)
    
    abandonments = CartAbandonment.objects.filter(
        recovered=False,
        reminder_sent=False,
        abandoned_at__lt=reminder_threshold,
        user__isnull=False,
        user__email__isnull=False
    ).select_related('user', 'cart')
    
    to_update = []
    sent_count = 0
    error_count = 0
    now = timezone.now()
    
    for abandonment in abandonments:
        try:
            # TODO: Implement email sending logic
            # send_cart_reminder_email(abandonment.user, abandonment.cart)
            
            abandonment.reminder_sent = True
            abandonment.reminder_sent_at = now
            to_update.append(abandonment)
            sent_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to send reminder for abandonment {abandonment.id}: {e}")
            continue
    
    if to_update:
        CartAbandonment.objects.bulk_update(
            to_update, 
            ['reminder_sent', 'reminder_sent_at'],
            batch_size=500
        )
    
    logger.info(f"Sent {sent_count} reminder emails ({error_count} errors)")
    return f"Sent {sent_count} reminder emails"
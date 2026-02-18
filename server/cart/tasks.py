#server/cart/tasks.py
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
from datetime import timedelta
from .models import Cart, CartAbandonment, UserScore
from .scoring import calculate_all_scores
import logging

logger = logging.getLogger(__name__)


@shared_task
def detect_abandoned_carts():
    """Detect carts abandoned for 24+ hours"""
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
    """Send reminders for carts abandoned 48+ hours ago"""
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


@shared_task
def calculate_user_scores_bulk():
    """Calculate scores for all users with cart history (bulk optimized)"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    eligible_users = User.objects.filter(
        Q(cart__isnull=False) | Q(abandoned_carts__isnull=False)
    ).distinct()
    
    to_create = []
    to_update = []
    error_count = 0
    
    for user in eligible_users:
        try:
            scores = calculate_all_scores(user)
            
            try:
                user_score = UserScore.objects.get(user=user)
                user_score.abandonment_score = scores['abandonment_score']
                user_score.value_score = scores['value_score']
                user_score.conversion_score = scores['conversion_score']
                user_score.hesitation_score = scores['hesitation_score']
                user_score.composite_score = scores['composite_score']
                to_update.append(user_score)
            except UserScore.DoesNotExist:
                to_create.append(UserScore(
                    user=user,
                    abandonment_score=scores['abandonment_score'],
                    value_score=scores['value_score'],
                    conversion_score=scores['conversion_score'],
                    hesitation_score=scores['hesitation_score'],
                    composite_score=scores['composite_score']
                ))
                
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to calculate score for user {user.id}: {e}")
            continue
    
    created_count = 0
    updated_count = 0
    
    if to_create:
        UserScore.objects.bulk_create(to_create, batch_size=500)
        created_count = len(to_create)
    
    if to_update:
        UserScore.objects.bulk_update(
            to_update,
            ['abandonment_score', 'value_score', 'conversion_score', 
             'hesitation_score', 'composite_score'],
            batch_size=500
        )
        updated_count = len(to_update)
    
    logger.info(
        f"Bulk score calculation complete: {created_count} created, "
        f"{updated_count} updated, {error_count} errors"
    )
    
    return f"Scores calculated: {created_count} new, {updated_count} updated"


@shared_task
def cleanup_old_guest_carts(days=30):
    """Delete old guest carts without abandonment records (automated)"""
    cutoff_date = timezone.now() - timedelta(days=days)
    
    carts_with_abandonments = CartAbandonment.objects.values_list('cart_id', flat=True)
    
    old_guest_carts = Cart.objects.filter(
        user=None,
        updated_at__lt=cutoff_date
    ).exclude(
        id__in=carts_with_abandonments
    )
    
    count = old_guest_carts.count()
    
    if count > 0:
        old_guest_carts.delete()
        logger.info(f"Cleaned up {count} old guest carts (preserved carts with abandonment records)")
    else:
        logger.info("No old guest carts to clean up")
    
    return f"Deleted {count} old guest carts"

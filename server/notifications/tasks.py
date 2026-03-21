#server/notifications/tasks.py
from celery import shared_task
from .email_service import EmailService
import logging
import time
import json
from django.conf import settings

logger = logging.getLogger(__name__)



def _log_task_metric(task_name, started_at, success, extra=None):
    duration_ms = int((time.monotonic() - started_at) * 1000)
    payload = {
        'event': 'email_task_metric',
        'task': task_name,
        'duration_ms': duration_ms,
        'success': success,
    }
    if extra:
        payload.update(extra)

    warn_ms = getattr(settings, 'EMAIL_TASK_WARN_DURATION_MS', 2000)
    if not success:
        logger.error(json.dumps(payload, default=str))
    elif duration_ms >= warn_ms:
        logger.warning(json.dumps(payload, default=str))
    else:
        logger.info(json.dumps(payload, default=str))



@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_welcome_email_task(self, user_id):
    """Send welcome email asynchronously"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    started_at = time.monotonic()

    try:
        user = User.objects.get(id=user_id)
        sent = EmailService.send_welcome_email(user)
        _log_task_metric('send_welcome_email_task', started_at, bool(sent), {'user_id': str(user_id)})
        if sent:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.error(f"Welcome email failed for {user.email}")
    except User.DoesNotExist:
        _log_task_metric('send_welcome_email_task', started_at, False, {'user_id': str(user_id), 'error': 'user_not_found'})
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        _log_task_metric('send_welcome_email_task', started_at, False, {'user_id': str(user_id), 'error': str(e)})
        logger.error(f"Failed to send welcome email: {str(e)}")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_verification_email_task(self, user_id, code):
    """Send verification email asynchronously"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    started_at = time.monotonic()

    try:
        user = User.objects.get(id=user_id)
        sent = EmailService.send_verification_email(user, code)
        _log_task_metric('send_verification_email_task', started_at, bool(sent), {'user_id': str(user_id)})
        if sent:
            logger.info(f"Verification email sent to {user.email}")
        else:
            logger.error(f"Verification email failed for {user.email}")
    except User.DoesNotExist:
        _log_task_metric('send_verification_email_task', started_at, False, {'user_id': str(user_id), 'error': 'user_not_found'})
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        _log_task_metric('send_verification_email_task', started_at, False, {'user_id': str(user_id), 'error': str(e)})
        logger.error(f"Failed to send verification email: {str(e)}")




@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_verification_email_to_recipient_task(self, recipient_email, recipient_name, code):
    """Send verification email to a pending-registration recipient asynchronously."""
    started_at = time.monotonic()
    sent = EmailService.send_verification_email_to_recipient(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        code=code,
    )
    _log_task_metric('send_verification_email_to_recipient_task', started_at, bool(sent), {'recipient_email': recipient_email})
    if not sent:
        raise RuntimeError(f"Verification email failed for {recipient_email}")
    logger.info(f"Verification email sent to {recipient_email}")
    return True


@shared_task
def send_order_confirmation_email_task(order_id):
    """Send order confirmation email asynchronously"""
    from orders.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        EmailService.send_order_confirmation_email(order)
        logger.info(f"Order confirmation email sent for {order.order_number}")
    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {str(e)}")


@shared_task
def send_payment_success_email_task(order_id):
    """Send payment success email asynchronously"""
    from orders.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        EmailService.send_payment_success_email(order)
        logger.info(f"Payment success email sent for {order.order_number}")
    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to send payment success email: {str(e)}")


@shared_task
def send_order_shipped_email_task(order_id):
    """Send order shipped email asynchronously"""
    from orders.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        EmailService.send_order_shipped_email(order)
        logger.info(f"Order shipped email sent for {order.order_number}")
    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to send order shipped email: {str(e)}")


@shared_task
def send_order_delivered_email_task(order_id):
    """Send order delivered email asynchronously"""
    from orders.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        EmailService.send_order_delivered_email(order)
        logger.info(f"Order delivered email sent for {order.order_number}")
    except Order.DoesNotExist:
        logger.error(f"Order with id {order_id} not found")
    except Exception as e:
        logger.error(f"Failed to send order delivered email: {str(e)}")


@shared_task
def send_cart_abandonment_emails():
    """Send cart abandonment emails to users"""
    from cart.models import Cart
    from django.utils import timezone
    from datetime import timedelta
    
                                      
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    abandoned_carts = Cart.objects.filter(
        user__isnull=False,
        items__isnull=False,
        updated_at__lte=cutoff_time
    ).distinct()
    
    count = 0
    for cart in abandoned_carts:
        try:
            EmailService.send_cart_abandonment_email(cart)
            count += 1
        except Exception as e:
            logger.error(f"Failed to send cart abandonment email: {str(e)}")
    
    logger.info(f"Sent {count} cart abandonment emails")
    return count


@shared_task
def send_seller_new_order_email_task(order_item_id):
    """Send new order notification to seller asynchronously"""
    from orders.models import OrderItem
    
    try:
        order_item = OrderItem.objects.get(id=order_item_id)
        EmailService.send_seller_new_order_email(order_item)
        logger.info(f"New order email sent to seller for order {order_item.order.order_number}")
    except OrderItem.DoesNotExist:
        logger.error(f"OrderItem with id {order_item_id} not found")
    except Exception as e:
        logger.error(f"Failed to send seller new order email: {str(e)}")


@shared_task
def send_seller_review_email_task(review_id, review_type):
    """Send new review notification to seller asynchronously"""
    
    try:
        if review_type == 'product':
            from reviews.models import ProductReview
            review = ProductReview.objects.get(id=review_id)
        else:
            from reviews.models import SellerReview
            review = SellerReview.objects.get(id=review_id)
        
        EmailService.send_seller_review_email(review)
        logger.info(f"Review notification email sent to seller")
    except Exception as e:
        logger.error(f"Failed to send seller review email: {str(e)}")

# notifications/tasks.py
from celery import shared_task
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email_task(user_id):
    """Send welcome email asynchronously"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        sent = EmailService.send_welcome_email(user)
        if sent:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.error(f"Welcome email failed for {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")


@shared_task
def send_verification_email_task(user_id, code):
    """Send verification email asynchronously"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        sent = EmailService.send_verification_email(user, code)
        if sent:
            logger.info(f"Verification email sent to {user.email}")
        else:
            logger.error(f"Verification email failed for {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")


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
    
    # Get carts abandoned for 24 hours
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

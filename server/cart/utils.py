# cart/utils.py (NEW FILE)
from django.db import transaction
from .models import CartEvent
import logging

logger = logging.getLogger(__name__)


def log_cart_event(event_type, cart, user=None, data=None):
    """Log a cart-related event with exception handling"""
    try:
        with transaction.atomic():
            CartEvent.objects.create(
                event_type=event_type,
                user=user,
                cart_id=cart.id,
                data=data or {}
            )
    except Exception as e:
        logger.error(f"Failed to log cart event {event_type}: {e}") 
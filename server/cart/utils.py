#server/cart/utils.py
from django.db import transaction
from .models import CartEvent
from market.models import DemandEvent
from market.demand_signals import track_demand_event
import logging

logger = logging.getLogger(__name__)


def log_cart_event(event_type, cart, user=None, data=None, source='direct'):
    """Log a cart-related event with exception handling"""
    try:
        with transaction.atomic():
            CartEvent.objects.create(
                event_type=event_type,
                user=user,
                cart_id=cart.id,
                data={**(data or {}), 'source': source}
            )

            if event_type == 'cart_item_added':
                payload = data or {}
                track_demand_event(
                    DemandEvent.EVENT_CART_ADD,
                    product_id=payload.get('product_id'),
                    user=user,
                    source=source,
                )
    except Exception as e:
        logger.error(f"Failed to log cart event {event_type}: {e}") 

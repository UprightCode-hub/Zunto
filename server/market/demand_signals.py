import logging

from market.models import DemandEvent
from market.tasks import schedule_demand_event_processing

logger = logging.getLogger(__name__)


DEFAULT_SOURCE = 'direct'


def _clean_location_value(value):
    text = str(value or '').strip()
    return text[:100]


def _resolve_state_lga(*, request=None, product=None, state=None, lga=None):
    resolved_state = _clean_location_value(state)
    resolved_lga = _clean_location_value(lga)

    if request is not None:
        params = getattr(request, 'query_params', None) or getattr(request, 'GET', None)
        if params is not None:
            resolved_state = resolved_state or _clean_location_value(params.get('state'))
            resolved_lga = resolved_lga or _clean_location_value(params.get('lga'))

    location = getattr(product, 'location', None)
    if location is not None:
        resolved_state = resolved_state or _clean_location_value(getattr(location, 'state', ''))
        resolved_lga = resolved_lga or _clean_location_value(getattr(location, 'area', '') or getattr(location, 'city', ''))

    return resolved_state, resolved_lga


def track_demand_event(
    event_type,
    *,
    product=None,
    product_id=None,
    user=None,
    request=None,
    source=DEFAULT_SOURCE,
    state=None,
    lga=None,
):
    """Canonical lightweight event writer for marketplace demand signals."""
    try:
        resolved_state, resolved_lga = _resolve_state_lga(
            request=request,
            product=product,
            state=state,
            lga=lga,
        )

        event = DemandEvent.objects.create(
            product_id=product.id if product is not None else product_id,
            user=user if getattr(user, 'is_authenticated', False) else None,
            event_type=event_type,
            state=resolved_state,
            lga=resolved_lga,
            source=str(source or DEFAULT_SOURCE).strip()[:50],
        )
        schedule_demand_event_processing(event.id)
        return event
    except Exception:
        logger.exception('Failed to track demand event', extra={'event_type': event_type})
        return None

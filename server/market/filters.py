from decimal import Decimal, InvalidOperation

from django.db.models import Q


def _as_bool(value):
    if value is None:
        return False
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _as_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def apply_product_filters(queryset, request):
    """Apply centralized structured filters for product listing endpoints."""
    params = request.query_params

    category = (params.get('category') or '').strip()
    if category:
        queryset = queryset.filter(category__slug=category)

    min_price = _as_decimal(params.get('min_price'))
    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)

    max_price = _as_decimal(params.get('max_price'))
    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)

    condition = (params.get('condition') or '').strip()
    if condition:
        queryset = queryset.filter(condition=condition)

    verified_only = _as_bool(params.get('verified_only')) or _as_bool(params.get('verified_product'))
    if verified_only:
        queryset = queryset.filter(is_verified_product=True)

    seller_type = (params.get('seller_type') or '').strip().lower()
    if seller_type == 'verified' or _as_bool(params.get('verified_seller')):
        queryset = queryset.filter(
            Q(seller__seller_profile__is_verified_seller=True) |
            Q(seller__is_verified_seller=True)
        )
    elif seller_type == 'normal':
        queryset = queryset.filter(
            Q(seller__seller_profile__is_verified_seller=False) |
            Q(seller__seller_profile__isnull=True, seller__is_verified_seller=False)
        )

    state = (params.get('state') or '').strip()
    if state:
        queryset = queryset.filter(seller__seller_profile__active_location__state__iexact=state)

    lga = (params.get('lga') or params.get('area') or '').strip()
    if lga:
        queryset = queryset.filter(seller__seller_profile__active_location__area__iexact=lga)

    seller = (params.get('seller') or '').strip()
    if seller:
        queryset = queryset.filter(seller_id=seller)

    listing_type = (params.get('listing_type') or '').strip()
    if listing_type:
        queryset = queryset.filter(listing_type=listing_type)

    is_negotiable = params.get('is_negotiable')
    if is_negotiable is not None and str(is_negotiable).strip() != '':
        queryset = queryset.filter(negotiable=_as_bool(is_negotiable))

    location_id = (params.get('location') or '').strip()
    if location_id:
        queryset = queryset.filter(location_id=location_id)

    return queryset

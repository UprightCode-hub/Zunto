#server/orders/commerce.py
from collections import OrderedDict
from accounts.seller_utils import get_seller_profile


def seller_supports_managed_commerce(seller):
    """Return True when seller is verified and has opted into managed commerce."""
    if not seller:
        return False
    profile = get_seller_profile(seller)
    if profile is None:
        return bool(
            getattr(seller, 'role', None) == 'seller'
            and getattr(seller, 'seller_commerce_mode', 'direct') == 'managed'
            and getattr(seller, 'is_verified', False)
        )
    return bool(
        profile is not None
        and profile.status == 'approved'
        and profile.is_verified_seller
        and profile.seller_commerce_mode == 'managed'
    )


def get_ineligible_sellers_for_items(items):
    """Collect unique sellers that cannot use managed payment/shipping/refund."""
    blocked = OrderedDict()
    for item in items:
        seller = getattr(getattr(item, 'product', None), 'seller', None) or getattr(item, 'seller', None)
        if seller_supports_managed_commerce(seller):
            continue
        if seller and str(seller.id) not in blocked:
            profile = get_seller_profile(seller)
            blocked[str(seller.id)] = {
                'seller_id': str(seller.id),
                'seller_name': seller.get_full_name() or seller.email,
                'mode': profile.seller_commerce_mode if profile is not None else 'direct',
                'is_verified_seller': bool(profile.is_verified_seller) if profile is not None else False,
                'is_verified': bool(profile.is_verified_seller) if profile is not None else False,
                'seller_status': profile.status if profile is not None else 'missing_profile',
            }
    return list(blocked.values())


def is_managed_order(order):
    """An order is managed if all item sellers support managed commerce."""
    items = order.items.select_related('seller').all()
    if not items:
        return False
    return all(seller_supports_managed_commerce(item.seller) for item in items)

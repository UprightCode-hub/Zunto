from collections import OrderedDict


def seller_supports_managed_commerce(seller):
    """Return True when seller is verified and has opted into managed commerce."""
    if not seller:
        return False
    return bool(
        getattr(seller, 'role', None) == 'seller'
        and getattr(seller, 'is_verified', False)
        and getattr(seller, 'seller_commerce_mode', 'direct') == 'managed'
    )


def get_ineligible_sellers_for_items(items):
    """Collect unique sellers that cannot use managed payment/shipping/refund."""
    blocked = OrderedDict()
    for item in items:
        seller = getattr(getattr(item, 'product', None), 'seller', None) or getattr(item, 'seller', None)
        if seller_supports_managed_commerce(seller):
            continue
        if seller and str(seller.id) not in blocked:
            blocked[str(seller.id)] = {
                'seller_id': str(seller.id),
                'seller_name': seller.get_full_name() or seller.email,
                'mode': getattr(seller, 'seller_commerce_mode', 'direct'),
                'is_verified': bool(getattr(seller, 'is_verified', False)),
            }
    return list(blocked.values())


def is_managed_order(order):
    """An order is managed if all item sellers support managed commerce."""
    items = order.items.select_related('seller').all()
    if not items:
        return False
    return all(seller_supports_managed_commerce(item.seller) for item in items)

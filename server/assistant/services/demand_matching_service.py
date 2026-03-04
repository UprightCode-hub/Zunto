from __future__ import annotations

from typing import Dict

from django.core.mail import send_mail
from django.db.models import QuerySet

from assistant.models import RecommendationDemandGap
from notifications.models import Notification, NotificationPreference


NON_STRUCTURED_DEMAND_KEYS = {
    'min_price',
    'max_price',
    'source',
    'raw_query',
    'location',
    'user_location',
    'category',
}



def _extract_numeric(value):
    try:
        if value in (None, ''):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None



def _product_location_text(product) -> str:
    if not getattr(product, 'location_id', None) or not product.location:
        return ''
    return str(product.location)



def _product_attributes(product) -> Dict[str, object]:
    attrs = {
        'condition': product.condition,
        'brand': product.brand,
        'listing_type': product.listing_type,
        'negotiable': product.negotiable,
        'is_verified_product': product.is_verified_product,
        'status': product.status,
    }
    return {key: value for key, value in attrs.items() if value not in (None, '', [])}



def _iter_demand_candidates(product) -> QuerySet[RecommendationDemandGap]:
    requested_category = ''
    if getattr(product, 'category_id', None) and product.category:
        requested_category = product.category.name

    return RecommendationDemandGap.objects.filter(requested_category=requested_category).select_related('user')



def _matches_price(demand: RecommendationDemandGap, product) -> bool:
    attrs = demand.requested_attributes or {}
    min_price = _extract_numeric(attrs.get('min_price'))
    max_price = _extract_numeric(attrs.get('max_price'))

    if min_price is not None and float(product.price) < min_price:
        return False
    if max_price is not None and float(product.price) > max_price:
        return False
    return True



def _matches_location(demand: RecommendationDemandGap, product) -> bool:
    if not demand.user_location:
        return True
    return demand.user_location == _product_location_text(product)



def _matches_structured_attributes(demand: RecommendationDemandGap, product) -> bool:
    demand_attrs = demand.requested_attributes or {}
    structured_demand_keys = {
        key
        for key in demand_attrs.keys()
        if key not in NON_STRUCTURED_DEMAND_KEYS
    }

    if not structured_demand_keys:
        return True

    product_attr_keys = set(_product_attributes(product).keys())
    return bool(structured_demand_keys & product_attr_keys)



def _should_notify_user(preferences: NotificationPreference | None) -> bool:
    if preferences is None:
        return True
    return preferences.email_promotional



def _send_email_if_enabled(user, product, preferences: NotificationPreference | None) -> None:
    if preferences is not None and not preferences.email_promotional:
        return
    if not user.email:
        return

    send_mail(
        subject='Product Now Available',
        message='A product matching your request is now available.',
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )



def _create_notification_once(user, product) -> bool:
    related_url = f"/products/{product.slug}/"
    already_notified = Notification.objects.filter(
        user=user,
        type='product',
        related_url=related_url,
        title='Product Now Available',
    ).exists()
    if already_notified:
        return False

    Notification.objects.create(
        user=user,
        type='product',
        title='Product Now Available',
        message='A product matching your request is now available.',
        related_url=related_url,
    )
    return True



def match_product_to_demand(product) -> int:
    """Match a newly-created product to existing demand gaps and notify matching users.

    Returns the number of new in-app notifications created.
    """
    if product is None:
        return 0

    notifications_created = 0
    demand_candidates = list(_iter_demand_candidates(product))

    preferences_by_user = {
        pref.user_id: pref
        for pref in NotificationPreference.objects.filter(
            user_id__in=[d.user_id for d in demand_candidates if d.user_id]
        )
    }

    notified_user_ids: set[int] = set()
    for demand in demand_candidates:
        if demand.user_id is None:
            continue
        if demand.user_id in notified_user_ids:
            continue

        if not _matches_price(demand, product):
            continue
        if not _matches_location(demand, product):
            continue
        if not _matches_structured_attributes(demand, product):
            continue

        preference = preferences_by_user.get(demand.user_id)
        if not _should_notify_user(preference):
            continue

        created = _create_notification_once(demand.user, product)
        if not created:
            notified_user_ids.add(demand.user_id)
            continue

        notifications_created += 1
        notified_user_ids.add(demand.user_id)
        _send_email_if_enabled(demand.user, product, preference)

    return notifications_created

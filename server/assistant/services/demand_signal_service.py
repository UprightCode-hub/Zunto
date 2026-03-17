from __future__ import annotations

import math
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from assistant.models import DemandCluster, RecommendationDemandGap
from market.models import Category, Location, Product
from notifications.models import Notification

DECAY_LAMBDA = 0.35
HOT_SCORE_THRESHOLD = 4.5
RANKING_MULTIPLIER = 1.25



def _resolve_category(gap: RecommendationDemandGap) -> Optional[Category]:
    category_text = (gap.requested_category or '').strip()
    if not category_text:
        return None
    category_slug = slugify(category_text)
    if not category_slug:
        return None

    category = Category.objects.filter(slug=category_slug).first()
    if category:
        return category
    return Category.objects.filter(name__iexact=category_text).first()



def _resolve_location(gap: RecommendationDemandGap) -> Optional[Location]:
    location_text = (gap.user_location or '').strip()
    if not location_text:
        return None

    parts = [p.strip() for p in location_text.split(',') if p.strip()]
    if len(parts) >= 3:
        area, city, state = parts[0], parts[-2], parts[-1]
        location = Location.objects.filter(state__iexact=state, city__iexact=city, area__iexact=area).first()
        if location:
            return location
    if len(parts) >= 2:
        city, state = parts[-2], parts[-1]
        location = Location.objects.filter(state__iexact=state, city__iexact=city).first()
        if location:
            return location

    return Location.objects.filter(state__iexact=location_text).first() or Location.objects.filter(city__iexact=location_text).first()



def _cluster_recent_gaps(cluster: DemandCluster, now):
    cutoff = now - timedelta(days=30)
    queryset = RecommendationDemandGap.objects.filter(
        requested_category=cluster.category.name,
        first_seen_at__gte=cutoff,
    )

    if cluster.location_id:
        queryset = queryset.filter(user_location=str(cluster.location))
    else:
        queryset = queryset.filter(user_location='')

    return queryset.only('user_id', 'first_seen_at').order_by('user_id', '-first_seen_at')



def _compute_time_weighted_hot_score(cluster: DemandCluster, now) -> float:
    score = 0.0
    last_counted_at_by_user = {}

    for gap in _cluster_recent_gaps(cluster, now):
        gap_time = gap.first_seen_at
        if not gap_time:
            continue

        if gap.user_id is not None:
            last_counted_at = last_counted_at_by_user.get(gap.user_id)
            if last_counted_at and (last_counted_at - gap_time) < timedelta(hours=24):
                continue
            last_counted_at_by_user[gap.user_id] = gap_time

        age_in_days = max((now - gap_time).total_seconds() / 86400.0, 0.0)
        score += math.exp(-DECAY_LAMBDA * age_in_days)

    return round(max(score, 0.0), 4)



def update_cluster_from_gap(gap: RecommendationDemandGap) -> Optional[DemandCluster]:
    category = _resolve_category(gap)
    if category is None:
        return None

    location = _resolve_location(gap)
    now = timezone.now()

    with transaction.atomic():
        cluster, _created = DemandCluster.objects.select_for_update().get_or_create(
            category=category,
            location=location,
            defaults={
                'demand_count': 0,
                'last_gap_at': now,
            },
        )

        previous_is_hot = cluster.is_hot
        cluster.demand_count += 1
        cluster.last_gap_at = now
        cluster.hot_score = _compute_time_weighted_hot_score(cluster, now)
        cluster.is_hot = cluster.hot_score >= HOT_SCORE_THRESHOLD
        cluster.save(update_fields=['demand_count', 'last_gap_at', 'hot_score', 'is_hot', 'updated_at'])

    cluster._transitioned_to_hot = bool(not previous_is_hot and cluster.is_hot)
    return cluster



def notify_sellers_for_hot_cluster(cluster: DemandCluster) -> int:
    if not cluster or not cluster.is_hot:
        return 0

    if not getattr(cluster, '_transitioned_to_hot', False):
        return 0

    sellers = Product.objects.filter(
        category=cluster.category,
        status='active',
    )
    if cluster.location_id:
        sellers = sellers.filter(location=cluster.location)

    seller_ids = sellers.values_list('seller_id', flat=True).distinct()

    location_text = str(cluster.location) if cluster.location_id else 'your area'
    related_url = f"/seller/dashboard?hot={cluster.category.slug}"
    message = f"Buyers are actively searching for {cluster.category.name} in {location_text}."

    created_count = 0
    for seller_id in seller_ids:
        exists = Notification.objects.filter(
            user_id=seller_id,
            type='hot_demand',
            related_url=related_url,
            title='🔥 High Buyer Demand Detected',
        ).exists()
        if exists:
            continue

        Notification.objects.create(
            user_id=seller_id,
            type='hot_demand',
            title='🔥 High Buyer Demand Detected',
            message=message,
            related_url=related_url,
        )
        created_count += 1

    return created_count

from __future__ import annotations

from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model

from assistant.models import RecommendationDemandGap

User = get_user_model()


def log_demand_gap(
    raw_query: str,
    structured_filters: Optional[Dict[str, Any]],
    user: Optional[User],
    source: str,
) -> RecommendationDemandGap:
    """Create or increment a demand-gap record without session/conversation dependencies."""
    payload = dict(structured_filters or {})

    requested_category = str(payload.get('category') or '')[:120]
    user_location = str(payload.get('location') or payload.get('user_location') or '')[:200]

    requested_attributes = {
        key: value
        for key, value in payload.items()
        if key not in {'category', 'location', 'user_location'}
    }

    if source:
        requested_attributes.setdefault('source', source)
    if raw_query:
        requested_attributes.setdefault('raw_query', raw_query)

    gap, created = RecommendationDemandGap.objects.get_or_create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        requested_category=requested_category,
        requested_attributes=requested_attributes,
        user_location=user_location,
        defaults={'frequency': 1},
    )

    if not created:
        gap.frequency += 1
        gap.save(update_fields=['frequency', 'last_seen_at'])

    return gap

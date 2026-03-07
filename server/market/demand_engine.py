from datetime import timedelta

from django.core.cache import cache
from django.db.models import Case, ExpressionWrapper, F, FloatField, Max, Sum, Value, When
from django.utils import timezone

from market.models import DemandEvent

TRENDING_CACHE_KEY = 'market:trending:product_ids:v1'
TRENDING_CACHE_TTL_SECONDS = 5 * 60
DEFAULT_WINDOW_DAYS = 7

EVENT_WEIGHTS = {
    DemandEvent.EVENT_VIEW: 1.0,
    DemandEvent.EVENT_FAVORITE: 3.0,
    DemandEvent.EVENT_CART_ADD: 5.0,
    DemandEvent.EVENT_PURCHASE: 10.0,
    DemandEvent.EVENT_SEARCH_INTEREST: 2.0,
}


def _event_weight_case():
    return Case(
        *[When(event_type=event_type, then=Value(weight)) for event_type, weight in EVENT_WEIGHTS.items()],
        default=Value(0.0),
        output_field=FloatField(),
    )


def _recency_decay_case(now):
    one_day_ago = now - timedelta(days=1)
    three_days_ago = now - timedelta(days=3)

    return Case(
        When(created_at__gte=one_day_ago, then=Value(1.0)),
        When(created_at__gte=three_days_ago, then=Value(0.75)),
        default=Value(0.5),
        output_field=FloatField(),
    )


def get_trending_products(limit=20, *, use_cache=True):
    limit = max(0, int(limit or 0))
    if limit == 0:
        return []

    cache_key = f'{TRENDING_CACHE_KEY}:{limit}'
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    now = timezone.now()
    window_start = now - timedelta(days=DEFAULT_WINDOW_DAYS)

    base_queryset = DemandEvent.objects.filter(
        created_at__gte=window_start,
        product_id__isnull=False,
        event_type__in=tuple(EVENT_WEIGHTS.keys()),
    )

    weighted_event_score = ExpressionWrapper(
        _event_weight_case() * _recency_decay_case(now),
        output_field=FloatField(),
    )

    ranked_rows = list(
        base_queryset
        .annotate(weighted_score=weighted_event_score)
        .values('product_id')
        .annotate(
            demand_score=Sum('weighted_score'),
            last_signal_at=Max('created_at'),
        )
        .order_by('-demand_score', '-last_signal_at')[:limit]
    )

    product_ids = [row['product_id'] for row in ranked_rows if row.get('product_id')]

    if use_cache:
        cache.set(cache_key, product_ids, TRENDING_CACHE_TTL_SECONDS)

    return product_ids

from django.db.models import (
    Avg,
    BooleanField,
    Case,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from market.filters import apply_product_filters
from market.models import DemandEvent, Favorite, Product, ProductImage, ProductView
from market.ranking import apply_location_priority, resolve_buyer_location
from market.search.embeddings import search_similar_products
from market.search.intent import detect_search_intent
from market.search.query_builder import build_search_query
from market.demand_signals import track_demand_event

_CHEAP_PRICE_THRESHOLD = 50_000


def _location_filter_from_intent(location_hint):
    if not location_hint:
        return Q()
    if location_hint in {'lagos', 'abuja', 'oyo'}:
        return Q(location__state__icontains=location_hint)
    if location_hint == 'ibadan':
        return Q(location__city__icontains='ibadan') | Q(location__area__icontains='ibadan')
    return Q(location__state__icontains=location_hint) | Q(location__city__icontains=location_hint)


def _apply_intent_guidance(queryset, parsed_query, intent):
    inferred = {
        'category_hint': intent.get('category'),
        'brand_hint': intent.get('brand'),
        'location_hint': intent.get('location_intent'),
        'condition_hint': None,
        'cheap_intent': intent.get('price_intent') == 'cheap',
    }

    price_intent = intent.get('price_intent')
    if not parsed_query.max_price and isinstance(price_intent, int):
        queryset = queryset.filter(price__lte=price_intent)

    if not parsed_query.condition and intent.get('condition'):
        condition_value = intent['condition']
        inferred['condition_hint'] = condition_value
        if condition_value == 'good':
            queryset = queryset.filter(condition__in=['like_new', 'good', 'fair'])
        else:
            queryset = queryset.filter(condition=condition_value)

    if not parsed_query.state and not parsed_query.lga and inferred['location_hint']:
        queryset = queryset.filter(_location_filter_from_intent(inferred['location_hint']))

    return queryset, inferred


def _optimized_product_list_queryset(request, queryset, apply_default_location_ordering=True):
    parsed = build_search_query(request)
    intent = detect_search_intent(parsed.query_text)

    intent_guided_queryset, inferred = _apply_intent_guidance(queryset, parsed, intent)
    filtered_queryset = apply_product_filters(intent_guided_queryset, request)

    semantic_score_map = {}
    if parsed.query_text:
        keyword_qs = filtered_queryset.filter(
            Q(title__icontains=parsed.query_text)
            | Q(description__icontains=parsed.query_text)
            | Q(brand__icontains=parsed.query_text)
        )
        keyword_ids = list(keyword_qs.values_list('id', flat=True)[:200])

        semantic_results = search_similar_products(parsed.query_text, filtered_queryset)
        semantic_ids = [product_id for product_id, _score in semantic_results]
        semantic_score_map = {product_id: float(score) for product_id, score in semantic_results}

        merged_ids = set(keyword_ids) | set(semantic_ids)
        if merged_ids:
            filtered_queryset = filtered_queryset.filter(id__in=merged_ids)

    buyer_location = resolve_buyer_location(request)
    ranked_queryset = apply_location_priority(filtered_queryset, buyer_location)

    image_queryset = ProductImage.objects.only('id', 'product_id', 'image', 'is_primary').order_by('-is_primary', 'id')

    category_hint = inferred.get('category_hint')
    brand_hint = inferred.get('brand_hint')
    condition_hint = inferred.get('condition_hint')
    location_hint = inferred.get('location_hint')

    category_match_condition = (
        Q(category__name__icontains=category_hint)
        | Q(title__icontains=category_hint)
        | Q(description__icontains=category_hint)
    ) if category_hint else Q(pk__isnull=True)

    brand_match_condition = (
        Q(brand__icontains=brand_hint)
        | Q(title__icontains=brand_hint)
        | Q(description__icontains=brand_hint)
    ) if brand_hint else Q(pk__isnull=True)

    condition_match_condition = Q(condition=condition_hint) if condition_hint else Q(pk__isnull=True)
    location_match_condition = _location_filter_from_intent(location_hint) if location_hint else Q(pk__isnull=True)

    cheap_match_condition = Q(price__lte=_CHEAP_PRICE_THRESHOLD) if inferred.get('cheap_intent') else Q(pk__isnull=True)

    optimized_queryset = ranked_queryset.annotate(
        avg_rating=Coalesce(Avg('reviews__rating', filter=Q(reviews__is_approved=True)), Value(0.0)),
        approved_review_count=Count('reviews', filter=Q(reviews__is_approved=True), distinct=True),
        reviews_count=Count('reviews', filter=Q(reviews__is_approved=True), distinct=True),
        view_count=Coalesce(F('views_count'), Value(0), output_field=IntegerField()),
        favorite_count=Coalesce(F('favorites_count'), Value(0), output_field=IntegerField()),
        boost_score=Case(When(is_boosted=True, then=Value(1)), default=Value(0), output_field=IntegerField()),
        semantic_score=Case(
            *[When(id=product_id, then=Value(score)) for product_id, score in semantic_score_map.items()],
            default=Value(0.0),
            output_field=FloatField(),
        ),
        category_intent_score=Case(
            When(category_match_condition, then=Value(1.5)),
            default=Value(0.0),
            output_field=FloatField(),
        ),
        brand_intent_score=Case(
            When(brand_match_condition, then=Value(1.5)),
            default=Value(0.0),
            output_field=FloatField(),
        ),
        condition_intent_score=Case(
            When(condition_match_condition, then=Value(0.8)),
            default=Value(0.0),
            output_field=FloatField(),
        ),
        location_intent_score=Case(
            When(location_match_condition, then=Value(0.8)),
            default=Value(0.0),
            output_field=FloatField(),
        ),
        cheap_intent_score=Case(
            When(cheap_match_condition, then=Value(0.6)),
            default=Value(0.0),
            output_field=FloatField(),
        ),
        popularity_score=ExpressionWrapper(
            F('view_count')
            + (F('favorite_count') * Value(3))
            + (F('reviews_count') * Value(4))
            + (F('boost_score') * Value(5)),
            output_field=FloatField(),
        ),
        is_favorited=Value(False, output_field=BooleanField()),
    ).annotate(
        intent_match_score=ExpressionWrapper(
            F('category_intent_score')
            + F('brand_intent_score')
            + F('condition_intent_score')
            + F('location_intent_score')
            + F('cheap_intent_score'),
            output_field=FloatField(),
        )
    ).select_related('category', 'location', 'seller').prefetch_related(
        Prefetch('images', queryset=image_queryset, to_attr='prefetched_images')
    )

    if request.user.is_authenticated:
        user_favorites = Favorite.objects.filter(user=request.user, product=OuterRef('pk'))
        optimized_queryset = optimized_queryset.annotate(is_favorited=Exists(user_favorites))

    if apply_default_location_ordering:
        return optimized_queryset.order_by(
            'location_priority',
            '-intent_match_score',
            '-semantic_score',
            '-popularity_score',
            '-created_at',
        )

    return optimized_queryset.order_by('-created_at')


def search_products(request, base_queryset=None):
    queryset = base_queryset if base_queryset is not None else Product.objects.filter(status='active')
    parsed = build_search_query(request)

    if parsed.query_text:
        source = str(request.query_params.get('source') or ProductView.SOURCE_NORMAL_SEARCH).strip().lower()
        track_demand_event(
            DemandEvent.EVENT_SEARCH_INTEREST,
            user=request.user,
            request=request,
            source=source,
        )

    return _optimized_product_list_queryset(
        request,
        queryset,
        apply_default_location_ordering=not bool(parsed.ordering),
    )

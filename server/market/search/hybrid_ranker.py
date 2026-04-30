import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional

from django.utils import timezone


_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class HybridRankingWeights:
    dense_similarity: float = 1.2
    keyword_match: float = 1.1
    product_family_match: float = 1.4
    price_fit: float = 1.35
    location_fit: float = 0.75
    seller_trust: float = 0.75
    verified_product: float = 0.65
    stock_freshness: float = 0.4
    popularity: float = 0.35
    favorites: float = 0.35
    recency: float = 0.35


DEFAULT_RANKING_WEIGHTS = HybridRankingWeights()


def _tokens(value: Any) -> List[str]:
    return _TOKEN_RE.findall(str(value or "").lower())


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            flattened = _flatten(value[key])
            if flattened:
                parts.append(f"{key} {flattened}")
        return " ".join(parts)
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    if value in (None, ""):
        return ""
    return str(value).strip()


def product_search_text(product) -> str:
    category_name = ""
    if getattr(product, "category_id", None) and getattr(product, "category", None):
        category_name = getattr(product.category, "name", "") or ""

    location_text = ""
    if getattr(product, "location_id", None) and getattr(product, "location", None):
        location_text = " ".join(
            part
            for part in (
                getattr(product.location, "area", "") or "",
                getattr(product.location, "city", "") or "",
                getattr(product.location, "state", "") or "",
            )
            if part
        )

    search_tags = getattr(product, "search_tags", None)
    product_family_text = ""
    product_family = getattr(product, "product_family", None)
    if getattr(product, "product_family_id", None) and product_family:
        product_family_text = _flatten(
            {
                "name": getattr(product_family, "name", "") or "",
                "aliases": getattr(product_family, "aliases", None) or [],
                "keywords": getattr(product_family, "keywords", None) or [],
            }
        )
    return " ".join(
        part
        for part in (
            getattr(product, "title", "") or "",
            getattr(product, "description", "") or "",
            getattr(product, "brand", "") or "",
            getattr(product, "condition", "") or "",
            category_name,
            product_family_text,
            location_text,
            _flatten(getattr(product, "attributes", None)),
            _flatten(search_tags),
        )
        if part
    )


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _normalize(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, float(value) / maximum))


def _keyword_scores(products: Iterable[Any], query: str) -> Dict[Any, float]:
    products = list(products)
    query_tokens = [token for token in _tokens(query) if len(token) > 1]
    if not products or not query_tokens:
        return {getattr(product, "id", product): 0.0 for product in products}

    docs = []
    document_frequencies = Counter()
    for product in products:
        doc_tokens = _tokens(product_search_text(product))
        docs.append((product, doc_tokens, Counter(doc_tokens)))
        for token in set(doc_tokens):
            document_frequencies[token] += 1

    avg_doc_len = sum(len(doc_tokens) for _, doc_tokens, _ in docs) / max(len(docs), 1)
    avg_doc_len = max(avg_doc_len, 1.0)
    k1 = 1.4
    b = 0.75
    raw_scores: Dict[Any, float] = {}
    doc_count = len(docs)

    for product, doc_tokens, token_counts in docs:
        doc_len = max(len(doc_tokens), 1)
        score = 0.0
        for token in query_tokens:
            tf = token_counts.get(token, 0)
            if not tf:
                continue
            idf = math.log(1 + (doc_count - document_frequencies[token] + 0.5) / (document_frequencies[token] + 0.5))
            denominator = tf + k1 * (1 - b + b * doc_len / avg_doc_len)
            score += idf * ((tf * (k1 + 1)) / denominator)
        raw_scores[getattr(product, "id", product)] = score

    max_score = max(raw_scores.values() or [0.0])
    if max_score <= 0:
        return {key: 0.0 for key in raw_scores}
    return {key: round(_normalize(value, max_score), 4) for key, value in raw_scores.items()}


def _product_family_score(product, slots: Mapping[str, Any]) -> float:
    family = str(slots.get("product_type") or slots.get("category") or "").strip().lower()
    if not family:
        return 0.5
    family_tokens = set(_tokens(family))
    text_tokens = set(_tokens(product_search_text(product)))
    if not family_tokens:
        return 0.5
    if family in product_search_text(product).lower():
        return 1.0
    overlap = len(family_tokens.intersection(text_tokens)) / max(len(family_tokens), 1)
    return round(max(0.0, min(1.0, overlap)), 4)


def _price_fit(product, slots: Mapping[str, Any], *, min_price_seen: Decimal, max_price_seen: Decimal) -> float:
    price = _safe_decimal(getattr(product, "price", None))
    if price is None:
        return 0.0

    price_min = _safe_decimal(slots.get("price_min"))
    price_max = _safe_decimal(slots.get("price_max"))
    price_intent = str(slots.get("price_intent") or "").strip().lower()

    if price_min is not None and price < price_min:
        return 0.0
    if price_max is not None and price > price_max:
        return 0.0

    spread = max_price_seen - min_price_seen
    price_position = Decimal("0.5") if spread <= 0 else (price - min_price_seen) / spread
    price_position_float = max(0.0, min(1.0, float(price_position)))

    if price_intent == "premium" or (price_min is not None and price_max is None):
        return round(price_position_float, 4)

    if price_intent == "cheap" or price_max is not None:
        if price_max and price_max > 0:
            budget_ratio = max(0.0, min(1.0, float(price / price_max)))
            return round(1.0 - (budget_ratio * 0.65), 4)
        return round(1.0 - price_position_float, 4)

    return 0.65


def _location_fit(product, slots: Mapping[str, Any]) -> float:
    wanted = str(slots.get("location") or "").strip().lower()
    if not wanted:
        return 0.5
    location = getattr(product, "location", None)
    if not location:
        return 0.0
    state = str(getattr(location, "state", "") or "").strip().lower()
    city = str(getattr(location, "city", "") or "").strip().lower()
    area = str(getattr(location, "area", "") or "").strip().lower()
    if wanted in {state, city, area}:
        return 1.0
    if wanted and (wanted in state or wanted in city or wanted in area):
        return 0.8
    return 0.0


def _seller_trust(product) -> float:
    seller = getattr(product, "seller", None)
    if seller is None:
        return 0.0

    score = 0.0
    if bool(getattr(seller, "is_verified_seller", False)):
        score += 0.35
    if bool(getattr(seller, "is_verified", False)):
        score += 0.15

    try:
        profile = seller.seller_profile
    except Exception:
        profile = None

    if profile is not None:
        if bool(getattr(profile, "is_verified_seller", False)) or bool(getattr(profile, "verified", False)):
            score += 0.3
        if str(getattr(profile, "status", "") or "").lower() == "approved":
            score += 0.1
        rating = float(getattr(profile, "rating", 0) or 0)
        review_count = float(getattr(profile, "total_reviews", 0) or 0)
        score += min(rating / 5.0, 1.0) * 0.15
        score += min(math.log1p(review_count) / math.log(51), 1.0) * 0.1

    return round(max(0.0, min(1.0, score)), 4)


def _stock_freshness(product) -> float:
    quantity = float(getattr(product, "quantity", 0) or 0)
    if quantity <= 0:
        return 0.0
    return round(min(math.log1p(quantity) / math.log(21), 1.0), 4)


def _recency(product) -> float:
    created_at = getattr(product, "created_at", None)
    if not created_at:
        return 0.5
    age = timezone.now() - created_at
    if age < timedelta(seconds=0):
        return 1.0
    return round(max(0.0, min(1.0, 1.0 - (age.days / 90.0))), 4)


def _match_reasons(product, components: Mapping[str, float]) -> List[str]:
    reasons = []
    if components.get("product_family_match", 0) >= 0.8:
        reasons.append("matches requested product family")
    if components.get("keyword_match", 0) >= 0.6:
        reasons.append("shares important query keywords")
    if components.get("dense_similarity", 0) >= 0.55:
        reasons.append("semantically similar to the request")
    if components.get("price_fit", 0) >= 0.7:
        reasons.append("fits the budget signal")
    if components.get("location_fit", 0) >= 0.8:
        reasons.append("matches requested location")
    if components.get("verified_product", 0) >= 1.0:
        reasons.append("verified product")
    if components.get("seller_trust", 0) >= 0.65:
        reasons.append("trusted seller signal")
    if components.get("stock_freshness", 0) >= 0.6:
        reasons.append("healthy available stock")
    if not reasons:
        reasons.append("best available catalog match after filters")
    return reasons


def rank_products_hybrid(
    products: Iterable[Any],
    *,
    slots: Mapping[str, Any],
    semantic_scores: Optional[Mapping[Any, float]] = None,
    weights: HybridRankingWeights = DEFAULT_RANKING_WEIGHTS,
) -> List[Any]:
    products = list(products)
    if not products:
        return []

    semantic_scores = semantic_scores or {}
    query = " ".join(
        str(value)
        for value in (
            slots.get("raw_query"),
            slots.get("product_type"),
            slots.get("category"),
            slots.get("brand"),
            _flatten(slots.get("attributes") or {}),
        )
        if value
    )
    keyword_scores = _keyword_scores(products, query)
    max_views = max(float(getattr(product, "views_count", 0) or 0) for product in products)
    max_favorites = max(float(getattr(product, "favorites_count", 0) or 0) for product in products)
    prices = [_safe_decimal(getattr(product, "price", None)) for product in products]
    prices = [price for price in prices if price is not None]
    min_price_seen = min(prices) if prices else Decimal("0")
    max_price_seen = max(prices) if prices else Decimal("0")

    price_weight = weights.price_fit
    if slots.get("price_max") is not None or slots.get("price_intent") in {"cheap", "premium"}:
        price_weight = 1.75

    weighted_fields = {
        "dense_similarity": weights.dense_similarity,
        "keyword_match": weights.keyword_match,
        "product_family_match": weights.product_family_match,
        "price_fit": price_weight,
        "location_fit": weights.location_fit,
        "seller_trust": weights.seller_trust,
        "verified_product": weights.verified_product,
        "stock_freshness": weights.stock_freshness,
        "popularity": weights.popularity,
        "favorites": weights.favorites,
        "recency": weights.recency,
    }

    ranked = []
    for product in products:
        product_id = getattr(product, "id", product)
        components = {
            "dense_similarity": round(float(semantic_scores.get(product_id, semantic_scores.get(str(product_id), 0.0)) or 0.0), 4),
            "keyword_match": keyword_scores.get(product_id, 0.0),
            "product_family_match": _product_family_score(product, slots),
            "price_fit": _price_fit(product, slots, min_price_seen=min_price_seen, max_price_seen=max_price_seen),
            "location_fit": _location_fit(product, slots),
            "seller_trust": _seller_trust(product),
            "verified_product": 1.0 if bool(getattr(product, "is_verified_product", False) or getattr(product, "is_verified", False)) else 0.0,
            "stock_freshness": _stock_freshness(product),
            "popularity": round(_normalize(math.log1p(float(getattr(product, "views_count", 0) or 0)), math.log1p(max_views)), 4) if max_views else 0.0,
            "favorites": round(_normalize(math.log1p(float(getattr(product, "favorites_count", 0) or 0)), math.log1p(max_favorites)), 4) if max_favorites else 0.0,
            "recency": _recency(product),
        }
        total_score = round(
            sum(components[field] * weight for field, weight in weighted_fields.items()),
            4,
        )
        product.recommendation_score = total_score
        product.recommendation_score_components = components
        product.recommendation_score_weights = weighted_fields
        product.recommendation_match_reasons = _match_reasons(product, components)
        ranked.append(product)

    ranked.sort(
        key=lambda product: (
            getattr(product, "recommendation_score", 0.0),
            _safe_decimal(getattr(product, "price", None)) or Decimal("0"),
            getattr(product, "created_at", timezone.now()),
        ),
        reverse=True,
    )
    return ranked

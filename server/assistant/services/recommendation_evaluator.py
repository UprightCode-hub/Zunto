# Deprecated: this evaluates the legacy RecommendationService pipeline.
# Live homepage recommendations are handled by
# assistant.services.gigi_agent.GigiRecommendationAgent; keep this only for
# historical comparison until a Gigi-specific evaluator replaces it.

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional

from assistant.services.recommendation_service import RecommendationService


@dataclass(frozen=True)
class HomepageRecoEvalCase:
    name: str
    prompts: List[str]
    slots: Dict[str, Any]
    expected_family: str
    expected_location: str = ''
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    expect_no_result: bool = False
    expected_terms: List[str] = field(default_factory=list)


DEFAULT_HOMEPAGE_RECO_EVAL_CASES: List[HomepageRecoEvalCase] = []


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _product_text(product) -> str:
    pieces = [
        getattr(product, 'title', ''),
        getattr(product, 'description', ''),
        getattr(product, 'brand', ''),
        getattr(getattr(product, 'category', None), 'name', ''),
        json.dumps(getattr(product, 'attributes', {}) or {}, sort_keys=True, default=str),
        json.dumps(getattr(product, 'search_tags', []) or [], sort_keys=True, default=str),
    ]
    return ' '.join(str(piece or '').lower() for piece in pieces)


def _matches_family(product, expected_family: str, expected_terms: Iterable[str]) -> bool:
    text = _product_text(product)
    family = str(expected_family or '').strip().lower()
    terms = [str(term).strip().lower() for term in expected_terms if str(term).strip()]
    if family and family in text:
        return True
    return bool(terms and any(term in text for term in terms))


def _matches_location(product, expected_location: str) -> bool:
    expected = str(expected_location or '').strip().lower()
    if not expected:
        return True
    location = getattr(product, 'location', None)
    if not location:
        return False
    values = [
        getattr(location, 'state', ''),
        getattr(location, 'city', ''),
        getattr(location, 'area', ''),
    ]
    return any(expected in str(value or '').lower() for value in values)


def _matches_price(product, price_min: Optional[float], price_max: Optional[float]) -> bool:
    price = _safe_decimal(getattr(product, 'price', None))
    if price is None:
        return False
    min_value = _safe_decimal(price_min)
    max_value = _safe_decimal(price_max)
    if min_value is not None and price < min_value:
        return False
    if max_value is not None and price > max_value:
        return False
    return True


def _explanation_ok(product) -> bool:
    components = getattr(product, 'recommendation_score_components', {}) or {}
    reasons = getattr(product, 'recommendation_match_reasons', []) or []
    required_components = {'product_family_match', 'price_fit', 'location_fit', 'keyword_match'}
    return bool(required_components.issubset(set(components.keys())) and len(reasons) >= 1)


def _score_case(case: HomepageRecoEvalCase, products: List[Any]) -> Dict[str, Any]:
    top3 = products[:3]
    if case.expect_no_result:
        no_result_honesty = 1.0 if not top3 else 0.0
        return {
            'product_family_accuracy': no_result_honesty,
            'price_adherence': no_result_honesty,
            'location_adherence': no_result_honesty,
            'no_result_honesty': no_result_honesty,
            'top3_relevance': no_result_honesty,
            'explanation_quality': no_result_honesty,
        }

    denominator = max(len(top3), 1)
    family_hits = sum(1 for product in top3 if _matches_family(product, case.expected_family, case.expected_terms))
    price_hits = sum(1 for product in top3 if _matches_price(product, case.price_min, case.price_max))
    location_hits = sum(1 for product in top3 if _matches_location(product, case.expected_location))
    relevant_hits = sum(
        1
        for product in top3
        if (
            _matches_family(product, case.expected_family, case.expected_terms)
            and _matches_price(product, case.price_min, case.price_max)
            and _matches_location(product, case.expected_location)
        )
    )
    explanation_hits = sum(1 for product in top3 if _explanation_ok(product))

    return {
        'product_family_accuracy': round(family_hits / denominator, 4) if top3 else 0.0,
        'price_adherence': round(price_hits / denominator, 4) if top3 else 0.0,
        'location_adherence': round(location_hits / denominator, 4) if top3 else 0.0,
        'no_result_honesty': 1.0 if top3 else 0.0,
        'top3_relevance': round(relevant_hits / min(3, denominator), 4) if top3 else 0.0,
        'explanation_quality': round(explanation_hits / denominator, 4) if top3 else 0.0,
    }


def _serialize_product(product) -> Dict[str, Any]:
    return {
        'id': str(getattr(product, 'id', '')),
        'title': getattr(product, 'title', ''),
        'price': str(getattr(product, 'price', '')),
        'location': str(getattr(product, 'location', '') or ''),
        'score': float(getattr(product, 'recommendation_score', 0.0) or 0.0),
        'score_components': getattr(product, 'recommendation_score_components', {}) or {},
        'match_reasons': getattr(product, 'recommendation_match_reasons', []) or [],
    }


def run_homepage_recommender_evaluation(
    cases: Optional[List[HomepageRecoEvalCase]] = None,
    *,
    top_k: int = 5,
) -> Dict[str, Any]:
    cases = cases or DEFAULT_HOMEPAGE_RECO_EVAL_CASES
    results = []

    for case in cases:
        products = RecommendationService._find_products(case.slots, top_k=top_k)
        metrics = _score_case(case, products)
        average_score = round(sum(metrics.values()) / len(metrics), 4) if metrics else 0.0
        passed = all(score >= 1.0 for score in metrics.values())
        results.append({
            'name': case.name,
            'prompts': case.prompts,
            'expected_family': case.expected_family,
            'expected_location': case.expected_location,
            'price_min': case.price_min,
            'price_max': case.price_max,
            'expect_no_result': case.expect_no_result,
            'metrics': metrics,
            'average_score': average_score,
            'passed': passed,
            'top_results': [_serialize_product(product) for product in products[:top_k]],
        })

    total = len(results)
    passed_count = sum(1 for result in results if result['passed'])
    metric_names = [
        'product_family_accuracy',
        'price_adherence',
        'location_adherence',
        'no_result_honesty',
        'top3_relevance',
        'explanation_quality',
    ]
    aggregate_metrics = {
        metric: round(sum(result['metrics'][metric] for result in results) / total, 4) if total else 0.0
        for metric in metric_names
    }

    return {
        'suite': 'homepage_recommender_eval',
        'total': total,
        'passed': passed_count,
        'failed': total - passed_count,
        'pass_rate_percent': round((passed_count / total) * 100, 2) if total else 0.0,
        'metrics': aggregate_metrics,
        'results': results,
    }


def dumps_pretty(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)

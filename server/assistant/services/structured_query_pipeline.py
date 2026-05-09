# Deprecated: the live homepage recommendation path now uses
# assistant.services.gigi_agent.GigiRecommendationAgent tool arguments.
# This structured-query pipeline is retained for legacy recommender tests and
# evaluation utilities; do not import it from active request code.

import json
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from market.search.attribute_normalizer import normalize_structured_query, normalize_text
from market.search.variant_extractor import apply_deterministic_parsing


FINAL_TOP_LEVEL_KEYS = [
    "product_type",
    "attributes",
    "numeric_filters",
    "preferences",
    "intent",
    "strictness",
    "raw_query",
    "confidence",
]
LLM_TOP_LEVEL_KEYS = {
    "product_type",
    "attributes",
    "numeric_filters",
    "preferences",
    "intent",
    "strictness",
}
INTENTS = {"buy", "browse", "compare", "budget", "premium", "gift", "replacement", "unknown"}
STRICTNESS = {"low", "medium", "high"}
MATCH_TYPES = {"text", "numeric", "categorical", "boolean", "range", "unknown"}
IMPORTANCE = {"low", "medium", "high"}
ATTRIBUTE_KEYS_TO_DROP = {
    "",
    "misc",
    "other",
    "stuff",
    "thing",
    "things",
    "item",
    "items",
    "unknown",
    "none",
    "null",
    "na",
    "n_a",
}
EMPTY_VALUES = (None, "", [], {})

NORMALIZATION_MAPS = {
    "price_intent": {
        "budget": {"cheap", "affordable", "budget", "low cost", "inexpensive", "low price"},
        "premium": {"best", "top", "high quality", "premium", "high end", "high-end"},
    },
    "quality": {
        "high": {"quality", "durable", "reliable", "strong", "heavy duty", "high quality"},
    },
    "recency_intent": {
        "latest": {"latest", "newest", "recent", "new model", "current version"},
    },
}

SNAKE_RE = re.compile(r"[^a-z0-9]+")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _empty_query(raw_query: str = "") -> Dict[str, Any]:
    return {
        "product_type": None,
        "attributes": {},
        "numeric_filters": {},
        "preferences": {},
        "intent": "unknown",
        "strictness": "low",
        "raw_query": raw_query or "",
        "confidence": {
            "product_type_confidence": 0.0,
            "attributes_confidence": 0.0,
            "numeric_confidence": 0.0,
            "overall_confidence": 0.0,
        },
    }


def parse_llm_json(raw_output: Any) -> Dict[str, Any]:
    if isinstance(raw_output, dict):
        return raw_output

    text = str(raw_output or "").strip()
    if not text:
        return {}

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def snake_case(value: Any) -> str:
    text = normalize_text(value)
    return SNAKE_RE.sub("_", text).strip("_")[:80]


def _normalize_enum(value: Any, allowed: Iterable[str], default: str) -> str:
    normalized = snake_case(value)
    return normalized if normalized in allowed else default


def _candidate_texts(value: Any) -> List[str]:
    if isinstance(value, dict):
        if "value" in value:
            return _candidate_texts(value.get("value"))
        texts: List[str] = []
        for nested in value.values():
            texts.extend(_candidate_texts(nested))
        return texts
    if isinstance(value, (list, tuple, set)):
        texts = []
        for item in value:
            texts.extend(_candidate_texts(item))
        return texts
    if value in EMPTY_VALUES:
        return []
    return [normalize_text(value)]


def _has_evidence(raw_query: str, value: Any) -> bool:
    raw_text = normalize_text(raw_query)
    if not raw_text:
        return False

    for candidate in _candidate_texts(value):
        if not candidate:
            continue
        if candidate in raw_text:
            return True
        tokens = TOKEN_RE.findall(candidate)
        if tokens and all(token in raw_text for token in tokens):
            return True
    return False


def _normalization_sources(raw_query: str) -> Dict[str, Any]:
    text = normalize_text(raw_query)
    preferences: Dict[str, Any] = {}
    attributes: Dict[str, Any] = {}

    for group, mappings in NORMALIZATION_MAPS.items():
        for canonical, phrases in mappings.items():
            if not any(normalize_text(phrase) in text for phrase in phrases):
                continue
            if group in {"price_intent", "recency_intent"}:
                preferences[group] = canonical
            else:
                attributes[group] = {
                    "value": canonical,
                    "match_type": "categorical",
                    "importance": "medium",
                    "source": "normalization_map",
                }

    return {"preferences": preferences, "attributes": attributes}


def _allowed_source(payload: Dict[str, Any]) -> str:
    source = normalize_text(payload.get("source") or "llm")
    if source in {"normalization_map", "deterministic_parser", "prior_context", "llm"}:
        return source
    return "llm"


def _clean_attribute(raw_query: str, key: Any, value: Any) -> Optional[Dict[str, Any]]:
    attr_key = snake_case(key)
    if attr_key in ATTRIBUTE_KEYS_TO_DROP:
        return None

    payload = deepcopy(value) if isinstance(value, dict) else {"value": value}
    if payload.get("value") in EMPTY_VALUES:
        return None

    source = _allowed_source(payload)
    if source == "llm" and not _has_evidence(raw_query, payload.get("value")):
        return None

    payload["match_type"] = _normalize_enum(payload.get("match_type"), MATCH_TYPES, "unknown")
    payload["importance"] = _normalize_enum(payload.get("importance"), IMPORTANCE, "medium")
    payload["source"] = source
    return payload


def _clean_attributes(raw_query: str, attributes: Any) -> Dict[str, Any]:
    if not isinstance(attributes, dict):
        return {}

    cleaned = {}
    for key, value in attributes.items():
        attr_key = snake_case(key)
        payload = _clean_attribute(raw_query, key, value)
        if attr_key and payload:
            cleaned[attr_key] = payload
    return cleaned


def _clean_preferences(raw_query: str, preferences: Any) -> Dict[str, Any]:
    if not isinstance(preferences, dict):
        return {}

    cleaned = {}
    for key, value in preferences.items():
        pref_key = snake_case(key)
        if not pref_key or value in EMPTY_VALUES:
            continue
        if _has_evidence(raw_query, value):
            cleaned[pref_key] = value
    return cleaned


def _numeric_filter_has_evidence(raw_query: str, value: Any) -> bool:
    if not isinstance(value, dict):
        return _has_evidence(raw_query, value)
    for numeric_key in ("min", "max", "target", "value"):
        if value.get(numeric_key) not in EMPTY_VALUES and _has_evidence(raw_query, value[numeric_key]):
            return True
    return False


def _clean_numeric_filters(raw_query: str, numeric_filters: Any) -> Dict[str, Any]:
    if not isinstance(numeric_filters, dict):
        return {}

    cleaned = {}
    for key, value in numeric_filters.items():
        filter_key = snake_case(key)
        if not filter_key or value in EMPTY_VALUES:
            continue
        source = _allowed_source(value) if isinstance(value, dict) else "llm"
        if source == "llm" and not _numeric_filter_has_evidence(raw_query, value):
            continue
        payload = deepcopy(value) if isinstance(value, dict) else {"target": value}
        payload["source"] = source
        cleaned[filter_key] = payload
    return cleaned


def _validated_base(raw_query: str, llm_output: Any) -> Dict[str, Any]:
    raw_payload = parse_llm_json(llm_output)
    payload = {key: value for key, value in raw_payload.items() if key in LLM_TOP_LEVEL_KEYS}
    query = _empty_query(raw_query)

    product_type = payload.get("product_type")
    if product_type not in EMPTY_VALUES and _has_evidence(raw_query, product_type):
        query["product_type"] = product_type

    query["attributes"] = _clean_attributes(raw_query, payload.get("attributes"))
    query["numeric_filters"] = _clean_numeric_filters(raw_query, payload.get("numeric_filters"))
    query["preferences"] = _clean_preferences(raw_query, payload.get("preferences"))
    query["intent"] = _normalize_enum(payload.get("intent"), INTENTS, "unknown")
    query["strictness"] = _normalize_enum(payload.get("strictness"), STRICTNESS, "medium")
    return query


def _merge_normalization(raw_query: str, query: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(query)
    normalized = _normalization_sources(raw_query)
    merged.setdefault("preferences", {}).update(normalized["preferences"])
    for key, value in normalized["attributes"].items():
        merged.setdefault("attributes", {}).setdefault(key, value)

    price_intent = merged.get("preferences", {}).get("price_intent")
    if price_intent in {"budget", "premium"} and merged.get("intent") == "unknown":
        merged["intent"] = price_intent
    return merged


def _merge_prior_context(query: Dict[str, Any], prior_slots: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(prior_slots, dict) or not prior_slots:
        return query

    merged = deepcopy(query)
    if not merged.get("product_type"):
        merged["product_type"] = prior_slots.get("product_type") or prior_slots.get("category")

    preferences = merged.setdefault("preferences", {})
    for key in ("brand", "condition", "location", "price_intent", "recency_intent", "use_case"):
        value = prior_slots.get(key)
        if key not in preferences and value not in EMPTY_VALUES:
            preferences[key] = value

    price = merged.setdefault("numeric_filters", {}).setdefault("price", {})
    if "min" not in price and prior_slots.get("price_min") is not None:
        price["min"] = prior_slots["price_min"]
        price.setdefault("currency", "NGN")
        price.setdefault("source", "prior_context")
    if "max" not in price and prior_slots.get("price_max") is not None:
        price["max"] = prior_slots["price_max"]
        price.setdefault("currency", "NGN")
        price.setdefault("source", "prior_context")
    if not price:
        merged["numeric_filters"].pop("price", None)

    attributes = merged.setdefault("attributes", {})
    for key, value in (prior_slots.get("attributes") or {}).items():
        attr_key = snake_case(key)
        if attr_key and attr_key not in attributes and value not in EMPTY_VALUES:
            payload = value if isinstance(value, dict) else {"value": value}
            payload = deepcopy(payload)
            payload.setdefault("match_type", "unknown")
            payload.setdefault("importance", "medium")
            payload["source"] = "prior_context"
            attributes[attr_key] = payload

    return merged


def _confidence(raw_query: str, query: Dict[str, Any]) -> Dict[str, float]:
    product_type = query.get("product_type")
    if not product_type:
        product_confidence = 0.0
    elif _has_evidence(raw_query, product_type):
        product_confidence = 1.0
    else:
        product_confidence = 0.75

    attr_scores = []
    for payload in (query.get("attributes") or {}).values():
        source = payload.get("source") if isinstance(payload, dict) else ""
        value = payload.get("value") if isinstance(payload, dict) else payload
        if source == "deterministic_parser":
            attr_scores.append(1.0)
        elif source == "normalization_map":
            attr_scores.append(0.85)
        elif source == "prior_context":
            attr_scores.append(0.7)
        elif _has_evidence(raw_query, value):
            attr_scores.append(0.95)
    attributes_confidence = sum(attr_scores) / len(attr_scores) if attr_scores else 0.5

    numeric_scores = []
    for payload in (query.get("numeric_filters") or {}).values():
        source = payload.get("source") if isinstance(payload, dict) else ""
        if source == "deterministic_parser":
            numeric_scores.append(1.0)
        elif source == "prior_context":
            numeric_scores.append(0.7)
        elif _numeric_filter_has_evidence(raw_query, payload):
            numeric_scores.append(0.9)
    numeric_confidence = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0.5

    overall = (0.35 * product_confidence) + (0.3 * attributes_confidence) + (0.2 * numeric_confidence) + 0.15
    return {
        "product_type_confidence": round(product_confidence, 4),
        "attributes_confidence": round(attributes_confidence, 4),
        "numeric_confidence": round(numeric_confidence, 4),
        "overall_confidence": round(max(0.0, min(1.0, overall)), 4),
    }


def finalize_structured_query(raw_query: str, query: Dict[str, Any]) -> Dict[str, Any]:
    final_query = normalize_structured_query(query)
    final_query["raw_query"] = raw_query or ""
    final_query["confidence"] = _confidence(raw_query, final_query)

    if not final_query.get("product_type") or final_query["confidence"]["overall_confidence"] < 0.65:
        final_query["strictness"] = "low"
    elif final_query.get("strictness") not in STRICTNESS:
        final_query["strictness"] = "medium"

    empty = _empty_query(raw_query)
    return {key: final_query.get(key, empty.get(key)) for key in FINAL_TOP_LEVEL_KEYS}


def build_structured_query(
    raw_query: str,
    llm_output: Any,
    prior_slots: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    query = _validated_base(raw_query, llm_output)
    query = _merge_normalization(raw_query, query)
    query = normalize_structured_query(query)
    query = apply_deterministic_parsing(raw_query, query)
    query = normalize_structured_query(query)
    query = _merge_prior_context(query, prior_slots)
    return finalize_structured_query(raw_query, query)


def _attribute_value(attribute: Any) -> Any:
    if isinstance(attribute, dict):
        return attribute.get("value")
    return attribute


def structured_query_to_slots(structured_query: Dict[str, Any]) -> Dict[str, Any]:
    query = structured_query or {}
    preferences = query.get("preferences") or {}
    price = (query.get("numeric_filters") or {}).get("price") or {}
    attributes = query.get("attributes") or {}

    color = _attribute_value(attributes.get("color"))
    slots = {
        "product_type": query.get("product_type"),
        "category": None,
        "price_min": price.get("min"),
        "price_max": price.get("max"),
        "location": preferences.get("location"),
        "condition": preferences.get("condition"),
        "brand": preferences.get("brand"),
        "price_intent": preferences.get("price_intent"),
        "color": color,
        "use_case": preferences.get("use_case"),
        "attributes": attributes,
        "rating": None,
        "raw_query": query.get("raw_query") or "",
        "budget_range": {"min": price.get("min"), "max": price.get("max")} if price else {},
        "product_intent": query.get("intent") or "unknown",
        "structured_query": query,
    }
    return {key: value for key, value in slots.items() if value not in EMPTY_VALUES or key in {"category", "rating"}}


def _flatten_for_query(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            flattened = _flatten_for_query(value[key])
            if flattened:
                parts.append(f"{key} {flattened}")
        return " ".join(parts)
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    if value in EMPTY_VALUES:
        return ""
    return str(value).strip()


def build_retrieval_query(structured_query: Dict[str, Any]) -> str:
    query = structured_query or {}
    parts = [
        query.get("raw_query"),
        query.get("product_type"),
        _flatten_for_query(query.get("preferences") or {}),
        _flatten_for_query(query.get("attributes") or {}),
        _flatten_for_query(query.get("numeric_filters") or {}),
    ]
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())

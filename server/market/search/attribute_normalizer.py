import re
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple


UNIT_GROUPS = {
    "storage": {
        "canonical_unit": "GB",
        "units": {"MB": Decimal("0.0009765625"), "GB": Decimal("1"), "TB": Decimal("1024")},
    },
    "weight": {
        "canonical_unit": "G",
        "units": {"G": Decimal("1"), "KG": Decimal("1000")},
    },
    "length": {
        "canonical_unit": "MM",
        "units": {"MM": Decimal("1"), "CM": Decimal("10"), "M": Decimal("1000"), "IN": Decimal("25.4"), "FT": Decimal("304.8")},
    },
    "battery": {
        "canonical_unit": "MAH",
        "units": {"MAH": Decimal("1"), "AH": Decimal("1000")},
    },
}

UNIT_TO_GROUP = {
    unit.lower(): group
    for group, spec in UNIT_GROUPS.items()
    for unit in spec["units"]
}

NUMBER_UNIT_RE = re.compile(
    r"^\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>mb|gb|tb|g|kg|mm|cm|m|in|ft|mah|ah)\s*$",
    re.IGNORECASE,
)

GENERIC_TEXT_SYNONYMS = {
    "black": {"black", "jet black", "matte black", "dark black"},
    "white": {"white", "off white", "off-white", "cream white"},
    "gray": {"gray", "grey"},
    "red": {"red", "wine red", "dark red"},
    "blue": {"blue", "navy blue", "dark blue"},
    "high": {"high", "fast", "powerful", "strong", "heavy duty", "high performance"},
    "budget": {"budget", "cheap", "affordable", "low cost", "inexpensive"},
    "premium": {"premium", "best", "top", "high quality", "high end"},
    "latest": {"latest", "newest", "recent", "new model", "current version"},
}

SYNONYM_LOOKUP = {
    phrase: canonical
    for canonical, phrases in GENERIC_TEXT_SYNONYMS.items()
    for phrase in phrases
}

PUNCTUATION_RE = re.compile(r"[^\w\s.+-]")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = PUNCTUATION_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return SYNONYM_LOOKUP.get(text, text)


def coerce_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def normalize_unit_value(number: Any, unit: str) -> Optional[Tuple[float, str, str]]:
    group = UNIT_TO_GROUP.get(str(unit or "").lower())
    if not group:
        return None

    numeric = coerce_number(number)
    if numeric is None:
        return None

    spec = UNIT_GROUPS[group]
    multiplier = spec["units"][str(unit).upper()]
    normalized = Decimal(str(numeric)) * multiplier
    value = int(normalized) if normalized == normalized.to_integral_value() else float(normalized)
    return value, spec["canonical_unit"], group


def parse_number_unit(value: Any) -> Optional[Tuple[float, str, str]]:
    match = NUMBER_UNIT_RE.match(str(value or ""))
    if not match:
        return None
    return normalize_unit_value(match.group("number"), match.group("unit"))


def _normalize_list(values):
    normalized = []
    for value in values:
        item = normalize_text(value)
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def normalize_attribute_value(key: str, attribute: Any) -> Optional[Dict[str, Any]]:
    if isinstance(attribute, dict):
        payload = deepcopy(attribute)
    else:
        payload = {"value": attribute}

    value = payload.get("value")
    if value in (None, "", [], {}):
        return None

    if isinstance(value, str):
        parsed = parse_number_unit(value)
        if parsed:
            number, unit, group = parsed
            payload.update({"value": number, "unit": unit, "unit_group": group, "match_type": "numeric"})
        else:
            payload["value"] = normalize_text(value)
            payload["match_type"] = payload.get("match_type") or "text"
    elif isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        payload["value"] = coerce_number(value)
        payload["match_type"] = "numeric"
    elif isinstance(value, list):
        payload["value"] = _normalize_list(value)
        payload["match_type"] = payload.get("match_type") or "categorical"
    elif isinstance(value, bool):
        payload["match_type"] = "boolean"
    else:
        payload["value"] = normalize_text(value)
        payload["match_type"] = payload.get("match_type") or "text"

    if payload.get("unit"):
        normalized = normalize_unit_value(payload.get("value"), payload.get("unit"))
        if normalized:
            number, unit, group = normalized
            payload.update({"value": number, "unit": unit, "unit_group": group, "match_type": "numeric"})
        else:
            payload["unit"] = str(payload["unit"]).upper()

    payload["importance"] = str(payload.get("importance") or "medium").lower()
    payload["match_type"] = str(payload.get("match_type") or "unknown").lower()
    payload.setdefault("source", "normalized")
    return payload


def _normalize_numeric_filter(numeric_filter: Any) -> Dict[str, Any]:
    if not isinstance(numeric_filter, dict):
        parsed = parse_number_unit(numeric_filter)
        if not parsed:
            number = coerce_number(numeric_filter)
            return {"target": number} if number is not None and number >= 0 else {}
        value, unit, group = parsed
        return {"target": value, "unit": unit, "unit_group": group}

    cleaned = {}
    for key in ("min", "max", "target", "value"):
        raw_value = numeric_filter.get(key)
        parsed = parse_number_unit(raw_value)
        if parsed:
            number, unit, group = parsed
            cleaned[key] = number
            cleaned.setdefault("unit", unit)
            cleaned.setdefault("unit_group", group)
            continue

        number = coerce_number(raw_value)
        if number is not None and number >= 0:
            cleaned[key] = number

    if "min" in cleaned and "max" in cleaned and cleaned["min"] > cleaned["max"]:
        cleaned["min"], cleaned["max"] = cleaned["max"], cleaned["min"]

    unit = numeric_filter.get("unit")
    if unit:
        for key in ("min", "max", "target", "value"):
            if key not in cleaned:
                continue
            normalized = normalize_unit_value(cleaned[key], str(unit))
            if normalized:
                number, canonical_unit, group = normalized
                cleaned[key] = number
                cleaned["unit"] = canonical_unit
                cleaned["unit_group"] = group
        cleaned.setdefault("unit", str(unit).upper())

    currency = numeric_filter.get("currency")
    if currency:
        cleaned["currency"] = normalize_text(currency).upper()
    elif cleaned and "unit" not in cleaned:
        cleaned["currency"] = "NGN"

    if cleaned:
        cleaned["importance"] = normalize_text(numeric_filter.get("importance") or "medium")
        source = numeric_filter.get("source")
        if source:
            cleaned["source"] = normalize_text(source)
    return cleaned


def normalize_structured_query(structured_query: Dict[str, Any]) -> Dict[str, Any]:
    query = deepcopy(structured_query or {})
    query["product_type"] = normalize_text(query.get("product_type")) or None
    query["intent"] = normalize_text(query.get("intent") or "unknown")
    query["strictness"] = normalize_text(query.get("strictness") or "low")

    attributes = {}
    for key, value in (query.get("attributes") or {}).items():
        normalized = normalize_attribute_value(key, value)
        if normalized:
            attributes[key] = normalized
    query["attributes"] = attributes

    normalized_filters = {}
    numeric_filters = query.get("numeric_filters") if isinstance(query.get("numeric_filters"), dict) else {}
    for key, value in numeric_filters.items():
        normalized = _normalize_numeric_filter(value)
        if normalized:
            normalized_filters[key] = normalized
    query["numeric_filters"] = normalized_filters

    preferences = {}
    for key, value in (query.get("preferences") or {}).items():
        if value not in (None, "", [], {}):
            preferences[key] = normalize_text(value) if isinstance(value, str) else value
    query["preferences"] = preferences
    return query

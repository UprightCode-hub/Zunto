import re
from typing import Any, Dict

from market.search.attribute_normalizer import coerce_number, normalize_text, normalize_unit_value


NUMBER_UNIT_RE = re.compile(
    r"(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>mb|gb|tb|g|kg|mm|cm|m|in|ft|mah|ah)\b",
    re.IGNORECASE,
)
DIMENSION_RE = re.compile(
    r"\b(?P<a>\d+(?:\.\d+)?)\s*[xX]\s*(?P<b>\d+(?:\.\d+)?)(?:\s*[xX]\s*(?P<c>\d+(?:\.\d+)?))?\s*(?P<unit>mm|cm|m|in|ft)\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(?P<year>19\d{2}|20\d{2})\b")
SIZE_RE = re.compile(
    r"\b(?:size|sizes|uk|us|eu)\s*[:#-]?\s*(?P<size>[a-z]{1,4}|\d{1,3}(?:\.\d+)?)\b",
    re.IGNORECASE,
)
LETTER_SIZE_RE = re.compile(r"\b(?P<size>xxxl|xxl|xl|xs|s|m|l)\b", re.IGNORECASE)
VERSION_RE = re.compile(r"\b(?P<version>v\d+(?:\.\d+)?|gen(?:eration)?\s*\d+|mark\s+[ivx0-9]+|series\s+\d+)\b", re.IGNORECASE)
VARIANT_RE = re.compile(
    r"\b(?P<variant>(?:pro\s+max)|(?:pro\s+plus)|pro|max|plus|mini|ultra|lite|air|se)\b",
    re.IGNORECASE,
)
PRICE_AMOUNT_RE = re.compile(
    r"(?P<prefix>\b(?:ngn|n)\s*|\u20a6\s*)?"
    r"(?P<number>\d[\d,.]*)\s*"
    r"(?P<multiplier>million|thousand|m|k)?\s*"
    r"(?P<suffix>naira|ngn)?",
    re.IGNORECASE,
)
PRICE_CONTEXT_RE = re.compile(
    r"\b(?:price|cost|budget|under|below|less\s+than|max|maximum|at\s+most|"
    r"not\s+more\s+than|above|over|more\s+than|min|minimum|at\s+least|from|"
    r"between|around|about|approximately|cheap|affordable|premium|expensive)\b|"
    r"\u20a6|\bngn\b|\bnaira\b",
    re.IGNORECASE,
)
NON_PRICE_UNIT_RE = re.compile(
    r"^\s*(?:mb|gb|tb|g|kg|mm|cm|m|in|ft|mah|ah)\b",
    re.IGNORECASE,
)

UNIT_ATTRIBUTE_KEYS = {
    "storage": "storage",
    "weight": "weight",
    "length": "length",
    "battery": "capacity",
}


def _attribute(value: Any, *, match_type: str, importance: str = "medium", unit: str = None, source: str = "deterministic_parser") -> Dict[str, Any]:
    payload = {
        "value": value,
        "match_type": match_type,
        "importance": importance,
        "source": source,
    }
    if unit:
        payload["unit"] = unit
    return payload


def _put_attribute(attributes: Dict[str, Any], key: str, payload: Dict[str, Any]) -> None:
    if key not in attributes:
        attributes[key] = payload
        return
    existing = attributes[key]
    existing_source = str(existing.get("source") or "") if isinstance(existing, dict) else ""
    if existing_source != "deterministic_parser":
        attributes[key] = payload


def _parse_price_amount(match: re.Match) -> Any:
    number = coerce_number(match.group("number"))
    if number is None:
        return None
    multiplier = normalize_text(match.group("multiplier"))
    if multiplier in {"k", "thousand"}:
        number *= 1000
    elif multiplier in {"m", "million"}:
        number *= 1000000
    return int(number) if float(number).is_integer() else number


def _has_price_context(raw_query: str, match: re.Match) -> bool:
    if match.group("prefix") or match.group("suffix"):
        return True
    window = raw_query[max(0, match.start() - 40): match.end() + 40]
    return bool(PRICE_CONTEXT_RE.search(window))


def extract_numeric_attributes(raw_query: str) -> Dict[str, Any]:
    text = raw_query or ""
    attributes: Dict[str, Any] = {}

    dimension_match = DIMENSION_RE.search(text)
    if dimension_match:
        unit = dimension_match.group("unit")
        values = [
            float(dimension_match.group(name))
            for name in ("a", "b", "c")
            if dimension_match.group(name) is not None
        ]
        normalized_values = []
        normalized_unit = None
        for value in values:
            normalized = normalize_unit_value(value, unit)
            if normalized:
                number, normalized_unit, _group = normalized
                normalized_values.append(number)
        if normalized_values and normalized_unit:
            attributes["dimensions"] = _attribute(
                normalized_values,
                unit=normalized_unit,
                match_type="numeric",
                importance="high",
            )

    for match in NUMBER_UNIT_RE.finditer(text):
        normalized = normalize_unit_value(match.group("number"), match.group("unit"))
        if not normalized:
            continue
        value, unit, group = normalized
        key = UNIT_ATTRIBUTE_KEYS.get(group, group)
        _put_attribute(
            attributes,
            key,
            _attribute(value, unit=unit, match_type="numeric", importance="high"),
        )

    size_match = SIZE_RE.search(text)
    if size_match:
        size = normalize_text(size_match.group("size")).upper()
        _put_attribute(attributes, "size", _attribute(size, match_type="categorical", importance="high"))
    elif re.search(r"\bsize\b", text, re.IGNORECASE):
        letter_match = LETTER_SIZE_RE.search(text)
        if letter_match:
            _put_attribute(
                attributes,
                "size",
                _attribute(normalize_text(letter_match.group("size")).upper(), match_type="categorical", importance="high"),
            )

    year_match = YEAR_RE.search(text)
    if year_match:
        _put_attribute(attributes, "year", _attribute(int(year_match.group("year")), match_type="numeric", importance="medium"))

    version_match = VERSION_RE.search(text)
    if version_match:
        _put_attribute(
            attributes,
            "version",
            _attribute(normalize_text(version_match.group("version")), match_type="text", importance="high"),
        )

    return attributes


def extract_variants(raw_query: str) -> Dict[str, Any]:
    text = raw_query or ""
    variants = []
    for regex in (VARIANT_RE, VERSION_RE):
        for match in regex.finditer(text):
            phrase = normalize_text(match.group(0))
            if phrase and phrase not in variants:
                variants.append(phrase)

    if not variants:
        return {}

    return {
        "variant": _attribute(
            variants,
            match_type="categorical",
            importance="high",
        )
    }


def extract_numeric_filters(raw_query: str) -> Dict[str, Any]:
    text = raw_query or ""
    matches = []
    for match in PRICE_AMOUNT_RE.finditer(text):
        following = text[match.end(): match.end() + 10]
        if NON_PRICE_UNIT_RE.match(following):
            continue
        if not _has_price_context(text, match):
            continue
        amount = _parse_price_amount(match)
        if amount is None:
            continue
        matches.append((match, amount))

    if not matches:
        return {}

    lower = text.lower()
    amounts = [amount for _match, amount in matches]
    price_filter = {"currency": "NGN", "source": "deterministic_parser", "importance": "high"}

    if len(amounts) >= 2 and re.search(r"\b(?:between|from)\b", lower):
        price_filter["min"] = min(amounts[:2])
        price_filter["max"] = max(amounts[:2])
    elif re.search(r"\b(?:under|below|less\s+than|max|maximum|at\s+most|not\s+more\s+than)\b", lower):
        price_filter["max"] = amounts[0]
    elif re.search(r"\b(?:above|over|more\s+than|min|minimum|at\s+least|from)\b", lower):
        price_filter["min"] = amounts[0]
    elif re.search(r"\b(?:around|about|approximately)\b", lower):
        price_filter["target"] = amounts[0]
    else:
        price_filter["target"] = amounts[0]

    return {"price": price_filter}


def apply_deterministic_parsing(raw_query: str, structured_query: Dict[str, Any]) -> Dict[str, Any]:
    query = dict(structured_query or {})
    attributes = dict(query.get("attributes") or {})
    for key, value in extract_numeric_attributes(raw_query).items():
        _put_attribute(attributes, key, value)
    for key, value in extract_variants(raw_query).items():
        _put_attribute(attributes, key, value)
    query["attributes"] = attributes

    numeric_filters = dict(query.get("numeric_filters") or {})
    for key, value in extract_numeric_filters(raw_query).items():
        numeric_filters.setdefault(key, value)
    query["numeric_filters"] = numeric_filters
    return query

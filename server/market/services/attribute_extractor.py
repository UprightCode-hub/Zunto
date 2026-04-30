import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from market.models import Category, ProductAttributeSchema, ProductFamily


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    'and', 'or', 'the', 'a', 'an', 'for', 'with', 'without', 'in', 'on', 'of',
    'to', 'from', 'by', 'new', 'used', 'good', 'clean', 'original', 'quality',
    'available', 'sale', 'sell', 'buy', 'product', 'item', 'pack',
}
_COLORS = {
    'black', 'white', 'blue', 'red', 'green', 'yellow', 'gold', 'silver',
    'grey', 'gray', 'brown', 'pink', 'purple', 'orange', 'cream', 'beige',
    'navy', 'midnight', 'starlight',
}
_MATERIALS = {
    'steel', 'stainless steel', 'iron', 'aluminium', 'aluminum', 'plastic',
    'wood', 'leather', 'cotton', 'polyester', 'rubber', 'glass', 'ceramic',
    'galvanized', 'copper', 'brass',
}


def _tokens(value: Any) -> List[str]:
    return _TOKEN_RE.findall(str(value or '').lower())


def _dedupe(values: Iterable[Any], *, limit: int = 30) -> List[str]:
    seen = set()
    cleaned = []
    for raw in values:
        value = str(raw or '').strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value[:60])
        if len(cleaned) >= limit:
            break
    return cleaned


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ''):
        return []
    return [str(value).strip()]


def _resolve_category(category: Optional[Any]) -> Optional[Category]:
    if isinstance(category, Category):
        return category
    if not category:
        return None
    try:
        return Category.objects.filter(id=category).first()
    except Exception:
        return Category.objects.filter(slug=str(category)).first() or Category.objects.filter(
            name__iexact=str(category)
        ).first()


def _family_terms(family: ProductFamily) -> List[str]:
    return _dedupe(
        [
            family.name,
            *(_coerce_list(family.aliases)),
            *(_coerce_list(family.keywords)),
        ],
        limit=80,
    )


def infer_product_family(
    text: str,
    *,
    category: Optional[Any] = None,
    product_family: Optional[Any] = None,
) -> Optional[ProductFamily]:
    if isinstance(product_family, ProductFamily):
        return product_family
    if product_family:
        family = (
            ProductFamily.objects.filter(id=product_family).first()
            or ProductFamily.objects.filter(slug=str(product_family)).first()
            or ProductFamily.objects.filter(name__iexact=str(product_family)).first()
        )
        if family:
            return family

    category_obj = _resolve_category(category)
    qs = ProductFamily.objects.filter(is_active=True).select_related('top_category', 'subcategory')
    if category_obj:
        qs = qs.filter(top_category=category_obj) | qs.filter(subcategory=category_obj)

    text_tokens = Counter(_tokens(text))
    text_lower = str(text or '').lower()
    best: Tuple[int, Optional[ProductFamily]] = (0, None)
    for family in qs[:2500]:
        score = 0
        for term in _family_terms(family):
            term_lower = term.lower()
            if not term_lower:
                continue
            if term_lower in text_lower:
                score += 8 + len(term_lower.split())
            else:
                score += sum(text_tokens.get(token, 0) for token in _tokens(term_lower))
        if score > best[0]:
            best = (score, family)
    return best[1] if best[0] > 0 else None


def _first_match(pattern: str, text: str, flags=re.I) -> Optional[str]:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return ' '.join(group for group in match.groups() if group).strip()


def _extract_known_value(key: str, text: str) -> Optional[Any]:
    key = key.lower().strip()
    lower = text.lower()

    if key in {'storage', 'capacity'}:
        return _first_match(r'\b(\d{2,4}\s?(?:gb|tb))\b', text)
    if key == 'ram':
        return _first_match(r'\b(\d{1,3}\s?gb)\s*(?:ram|memory)\b|\bram\s*(\d{1,3}\s?gb)\b', text)
    if key in {'battery_health', 'battery'}:
        return _first_match(r'\b(?:battery health|bh|battery)\s*[:\-]?\s*(\d{2,3}\s?%)', text)
    if key == 'network':
        if 'unlocked' in lower:
            return 'unlocked'
        if 'locked' in lower:
            return 'locked'
    if key in {'size', 'shoe_size', 'clothing_size'}:
        return _first_match(r'\b(?:size|sz)\s*[:\-]?\s*([a-z]{1,4}|\d{1,3}(?:\.\d)?)\b', text)
    if key in {'weight', 'pack_weight'}:
        return _first_match(r'\b(\d+(?:\.\d+)?\s?(?:kg|g|grams|tonnes?|tons?))\b', text)
    if key in {'volume', 'size_volume'}:
        return _first_match(r'\b(\d+(?:\.\d+)?\s?(?:ml|l|litres?|liters?))\b', text)
    if key == 'spf':
        return _first_match(r'\bspf\s*([0-9]{2,3})\b', text)
    if key in {'length', 'nail_length', 'cable_length'}:
        return _first_match(r'\b(\d+(?:\.\d+)?\s?(?:inch|inches|in|mm|cm|m))\b', text)
    if key in {'quantity_per_pack', 'pack_size'}:
        return _first_match(r'\b(?:pack of|x|qty|quantity)\s*([0-9]{1,6})\b', text)
    if key == 'color' or key == 'colour':
        for color in _COLORS:
            if re.search(rf'\b{re.escape(color)}\b', lower):
                return color
    if key == 'material':
        for material in sorted(_MATERIALS, key=len, reverse=True):
            if re.search(rf'\b{re.escape(material)}\b', lower):
                return material
    if key == 'condition':
        for condition in ('brand new', 'like new', 'fairly used', 'used', 'new', 'good', 'fair'):
            if condition in lower:
                return condition

    label = key.replace('_', ' ')
    return _first_match(rf'\b{re.escape(label)}\s*[:\-]\s*([a-z0-9 /.,+-]+)', text)


def _extract_attributes(text: str, family: Optional[ProductFamily]) -> Dict[str, Any]:
    schemas = []
    if family:
        schemas = list(
            ProductAttributeSchema.objects.filter(
                product_family=family,
                is_active=True,
            ).order_by('order', 'key')
        )

    attrs: Dict[str, Any] = {}
    keys = [schema.key for schema in schemas] or [
        'model', 'storage', 'ram', 'battery_health', 'network', 'size',
        'weight', 'volume', 'spf', 'length', 'material', 'color',
        'quantity_per_pack',
    ]
    for key in keys:
        value = _extract_known_value(key, text)
        if value not in (None, '', [], {}):
            attrs[key] = str(value).strip()
    return attrs


def suggest_product_metadata(
    *,
    title: str,
    description: str = '',
    category: Optional[Any] = None,
    product_family: Optional[Any] = None,
    brand: str = '',
) -> Dict[str, Any]:
    """Suggest structured attributes and search tags from seller text.

    This is deterministic and safe to run during upload. A future LLM call can
    enrich this output, but the seller/admin should still confirm attributes.
    """

    text = ' '.join(part for part in [title, description, brand] if part)
    family = infer_product_family(text, category=category, product_family=product_family)
    category_obj = _resolve_category(category)
    if family:
        category_obj = family.subcategory or family.top_category

    attributes = _extract_attributes(text, family)
    if family:
        attributes.setdefault('product_family', family.name.lower())

    required = []
    if family:
        required = list(
            ProductAttributeSchema.objects.filter(
                product_family=family,
                required=True,
                is_active=True,
            ).values_list('key', flat=True)
        )
    missing_required = [key for key in required if key not in attributes]

    tag_parts: List[str] = []
    if category_obj:
        tag_parts.extend([category_obj.name, category_obj.slug])
        if category_obj.parent_id:
            tag_parts.append(category_obj.parent.name)
    if family:
        tag_parts.extend(_family_terms(family))
    tag_parts.extend([brand])
    tag_parts.extend(str(value) for value in attributes.values())
    tag_parts.extend(
        token
        for token in _tokens(text)
        if len(token) > 2 and token not in _STOPWORDS
    )

    confidence = 0.35
    if family:
        confidence += 0.25
    if attributes:
        confidence += min(0.25, len(attributes) * 0.04)
    if required and not missing_required:
        confidence += 0.15

    return {
        'source': 'deterministic_attribute_extractor_v1',
        'product_family': {
            'id': str(family.id),
            'name': family.name,
            'slug': family.slug,
            'full_path': family.get_full_path(),
        } if family else None,
        'attributes': attributes,
        'search_tags': _dedupe(tag_parts, limit=30),
        'missing_required': missing_required,
        'confidence': round(min(confidence, 0.98), 2),
    }

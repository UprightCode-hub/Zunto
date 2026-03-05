import re

_CATEGORY_HINTS = {
    'phone': 'phones',
    'smartphone': 'phones',
    'laptop': 'laptops',
    'notebook': 'laptops',
    'sneakers': 'sneakers',
    'sneaker': 'sneakers',
    'shoes': 'shoes',
    'tablet': 'tablets',
    'ps5': 'gaming',
    'controller': 'controllers',
    'headphones': 'headphones',
    'earbuds': 'headphones',
}

_BRANDS = [
    'nike', 'adidas', 'apple', 'samsung', 'hp', 'dell', 'lenovo', 'sony'
]

_LOCATION_HINTS = ['lagos', 'abuja', 'ibadan', 'oyo']


def _parse_amount(raw_amount):
    cleaned = str(raw_amount or '').strip().lower().replace(',', '')
    if not cleaned:
        return None

    multiplier = 1
    if cleaned.endswith('k'):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith('m'):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]

    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
        return None


def detect_search_intent(query: str) -> dict:
    lower = (query or '').strip().lower()

    intent = {
        'category': None,
        'brand': None,
        'price_intent': None,
        'location_intent': None,
        'condition': None,
    }

    if not lower:
        return intent

    for token, category_hint in _CATEGORY_HINTS.items():
        if token in lower:
            intent['category'] = category_hint
            break

    for brand in _BRANDS:
        if re.search(rf'\b{re.escape(brand)}\b', lower):
            intent['brand'] = brand
            break

    price_match = re.search(r'(?:under|below)\s*(\d+[\d,]*(?:\.\d+)?[km]?)', lower)
    if price_match:
        parsed_amount = _parse_amount(price_match.group(1))
        if parsed_amount:
            intent['price_intent'] = parsed_amount
    elif any(token in lower for token in ['cheap', 'budget', 'affordable']):
        intent['price_intent'] = 'cheap'

    for location in _LOCATION_HINTS:
        if re.search(rf'\b{re.escape(location)}\b', lower):
            intent['location_intent'] = location
            break

    if 'brand new' in lower:
        intent['condition'] = 'new'
    elif re.search(r'\bnew\b', lower):
        intent['condition'] = 'new'
    elif 'fairly used' in lower:
        intent['condition'] = 'fair'
    elif re.search(r'\bused\b', lower):
        intent['condition'] = 'good'

    return intent

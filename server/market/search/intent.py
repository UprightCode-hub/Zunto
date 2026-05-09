import re


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

    price_match = re.search(r'(?:under|below|less\s+than|max(?:imum)?)\s*(\d+[\d,]*(?:\.\d+)?[km]?)', lower)
    if price_match:
        parsed_amount = _parse_amount(price_match.group(1))
        if parsed_amount:
            intent['price_intent'] = parsed_amount
    elif re.search(r'\b(?:cheap|budget|affordable|low[-\s]?cost|inexpensive)\b', lower):
        intent['price_intent'] = 'cheap'
    elif re.search(r'\b(?:premium|expensive|high[-\s]?end|top quality|best quality)\b', lower):
        intent['price_intent'] = 'premium'

    if re.search(r'\b(?:brand[-\s]?new|new)\b', lower):
        intent['condition'] = 'new'
    elif re.search(r'\b(?:used|second[-\s]?hand|pre[-\s]?owned|fairly used)\b', lower):
        intent['condition'] = 'used'

    return intent

import logging
import re
import threading
import time
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_GREETING_WORDS = frozenset([
    'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola',
    'how', 'ok', 'okay', 'sure', 'yep', 'yes', 'no', 'nope',
    'thanks', 'thank', 'bye', 'goodbye', 'lol', 'hmm', 'um', 'uh',
    'cool', 'nice', 'great', 'good', 'wow', 'oh', 'ah',
])

_SUPPORT_KEYWORDS = frozenset([
    'refund', 'dispute', 'complaint', 'return', 'track', 'order', 'delivery',
    'payment', 'scam', 'fraud', 'cancel', 'support', 'issue',
])

_LOCATION_KEYWORDS: Dict[str, str] = {
    'port harcourt': 'Port Harcourt',
    'benin city': 'Benin City',
    'lagos': 'Lagos',
    'abuja': 'Abuja',
    'kano': 'Kano',
    'ibadan': 'Ibadan',
    'oyo': 'Oyo',
    'enugu': 'Enugu',
    'benin': 'Benin City',
    'calabar': 'Calabar',
    'warri': 'Warri',
    'jos': 'Jos',
    'owerri': 'Owerri',
    'uyo': 'Uyo',
    'ilorin': 'Ilorin',
    'abeokuta': 'Abeokuta',
    'akure': 'Akure',
    'delta': 'Delta',
    'asaba': 'Asaba',
    'kaduna': 'Kaduna',
    'maiduguri': 'Maiduguri',
    'ph': 'Port Harcourt',
}

_CONDITION_MAP: Dict[str, str] = {
    'brand new': 'new',
    'brand-new': 'new',
    'new': 'new',
    'tokunbo': 'fair',
    'fairly used': 'fair',
    'fairly-used': 'fair',
    'uk used': 'fair',
    'uk-used': 'fair',
    'second hand': 'used',
    'second-hand': 'used',
    'secondhand': 'used',
    'used': 'used',
    'old': 'used',
    'like new': 'like_new',
    'good': 'good',
    'poor': 'poor',
}

_COLORS = {
    'red', 'blue', 'green', 'black', 'white', 'yellow', 'orange', 'purple',
    'pink', 'brown', 'grey', 'gray', 'silver', 'gold', 'navy', 'cream',
    'beige', 'maroon', 'violet', 'indigo', 'cyan', 'magenta', 'rose',
    'ash', 'charcoal', 'turquoise', 'wine',
}

_KNOWN_BRANDS = {
    'samsung', 'apple', 'iphone', 'nokia', 'tecno', 'infinix', 'itel',
    'xiaomi', 'realme', 'oppo', 'vivo', 'huawei', 'lg', 'sony', 'hp',
    'dell', 'lenovo', 'acer', 'asus', 'toshiba', 'hisense', 'haier',
    'nike', 'adidas', 'puma', 'reebok', 'converse', 'vans', 'new balance',
    'gucci', 'louis vuitton', 'zara', 'h&m',
    'thermocool', 'nexus', 'binatone', 'bruhm', 'scanfrost', 'polystar',
    'miyako', 'midea',
    'toyota', 'honda', 'hyundai', 'kia', 'mercedes', 'bmw', 'lexus',
    'ford', 'suzuki', 'nissan',
}

_USE_CASE_MAP: Dict[str, List[str]] = {
    'jogging': ['sneakers', 'running shoes', 'sportswear'],
    'running': ['sneakers', 'running shoes'],
    'gym': ['sportswear', 'sneakers', 'activewear'],
    'office': ['laptop', 'bag', 'formal shoes', 'shirt'],
    'work': ['laptop', 'bag', 'office chair'],
    'school': ['bag', 'laptop', 'stationery'],
    'gaming': ['gaming laptop', 'console', 'headphone'],
    'cooking': ['blender', 'pot', 'microwave', 'gas cooker'],
    'music': ['headphone', 'speaker', 'earphone'],
    'photography': ['camera', 'tripod', 'lens'],
    'travel': ['bag', 'suitcase', 'luggage'],
    'wedding': ['dress', 'suit', 'shoes', 'jewelry', 'bag'],
    'birthday': ['gift', 'watch', 'perfume', 'jewelry'],
    'watching tv': ['tv', 'television', 'remote'],
    'sleeping': ['mattress', 'bed', 'pillow', 'bedsheet'],
    'driving': ['car', 'tyre', 'car accessories'],
    'farming': ['generator', 'pump', 'equipment'],
    'church': ['dress', 'suit', 'heels'],
    'beach': ['swimwear', 'sandals', 'sunglasses'],
    'baby': ['baby clothes', 'diaper', 'baby food', 'stroller'],
}

_PRODUCT_TERMS = [
    'washing machine', 'air conditioner',
    'phone', 'smartphone', 'laptop', 'tablet', 'ipad', 'computer', 'pc',
    'tv', 'television', 'fridge', 'freezer', 'microwave', 'blender', 'fan', 'ac', 'generator',
    'sneaker', 'shoe', 'heel', 'sandal', 'boot', 'slipper',
    'shirt', 'dress', 'trouser', 'jean', 'skirt', 'suit', 'jacket',
    'bag', 'handbag', 'backpack', 'wallet', 'purse',
    'watch', 'perfume', 'jewelry', 'ring', 'necklace', 'bracelet',
    'car', 'motorcycle', 'bicycle',
    'sofa', 'chair', 'table', 'bed', 'mattress', 'wardrobe',
    'headphone', 'earphone', 'earbuds', 'speaker',
    'camera', 'tripod', 'lens',
    'baby', 'diaper', 'book', 'textbook',
    'game', 'console', 'playstation', 'xbox',
    'basmati rice', 'rice', 'beans', 'maize', 'tomatoes', 'catfish', 'palm oil',
    'sunscreen', 'shea butter', 'hair growth oil', 'vitamin c serum', 'multivitamin',
    'barbing kit',
]


class SlotExtractor:
    _category_cache: dict = {}
    _category_cache_lock = threading.Lock()
    _CATEGORY_CACHE_TTL = 300
    _SIZE_KEYWORDS = frozenset({
        'size', 'uk', 'eu', 'us', 'eu size', 'uk size',
        'us size', 'cm', 'inch', 'inches', 'ft', 'feet',
    })
    _SIZE_NUMBER_MAX = 59
    _NON_PRICE_SUFFIX_RE = re.compile(
        r'^\s*(?:gb|tb|mb|mhz|ghz|hz|mah|mp|inch|inches|cm|mm|ft|feet|kg|kgs|g|gram|grams|litre|litres|liter|liters|ml)\b'
    )

    @classmethod
    def _get_category_map(cls, force_refresh: bool = False) -> dict:
        now = time.monotonic()
        if (
            not force_refresh
            and cls._category_cache
            and now - cls._category_cache.get('_ts', 0) < cls._CATEGORY_CACHE_TTL
        ):
            return cls._category_cache['data']

        with cls._category_cache_lock:
            if (
                not force_refresh
                and cls._category_cache
                and now - cls._category_cache.get('_ts', 0) < cls._CATEGORY_CACHE_TTL
            ):
                return cls._category_cache['data']

            from market.models import Category
            data = {
                c.name.lower(): c.name
                for c in Category.objects.filter(is_active=True).only('name')[:400]
            }
            cls._category_cache = {'data': data, '_ts': now}
            return data

    @classmethod
    def _resolve_category(cls, text: str, product_type: Optional[str]) -> Optional[str]:
        probe_terms = [product_type or '', text or '']
        for force_refresh in (False, True):
            category_map = cls._get_category_map(force_refresh=force_refresh)
            for probe in probe_terms:
                probe = probe.lower().strip()
                if not probe:
                    continue
                if probe in category_map:
                    return category_map[probe]
                for key, value in category_map.items():
                    if key in probe:
                        return value
                    if len(probe) >= 4 and probe in key:
                        return value
        return None

    @staticmethod
    def _extract_budget(lower: str) -> Optional[Dict]:
        matches = re.findall(
            r"(?:₦|ngn\s*|n\s*)?(\d[\d,.]*)(?:\s*(million|m|k|thousand)\b)?",
            lower,
        )
        if not matches:
            return None

        values = []
        for raw, mult in matches[:2]:
            try:
                amount = Decimal(raw.replace(',', ''))
                if mult in {'million', 'm'}:
                    amount *= Decimal('1000000')
                elif mult in {'k', 'thousand'}:
                    amount *= Decimal('1000')
                values.append(float(amount))
            except (InvalidOperation, ValueError):
                continue

        if not values:
            return None

        values = sorted(values)
        if len(values) == 1:
            if re.search(r"\b(?:under|below|less\s+than|max|at\s+most|not\s+more\s+than)\b", lower):
                return {'min': None, 'max': values[0]}
            if re.search(r"\b(?:above|over|more\s+than|min|at\s+least|from)\b", lower):
                return {'min': values[0], 'max': None}
            return {'min': None, 'max': values[0]}

        return {'min': values[0], 'max': values[-1]}

    @staticmethod
    def _is_size_not_price(value: float, preceding_text: str) -> bool:
        """
        Return True if this number is likely a product size rather than a price.
        Numbers 1-59 immediately following size keywords are treated as sizes.
        """
        if value > SlotExtractor._SIZE_NUMBER_MAX:
            return False
        preceding = (preceding_text or '').lower().strip()
        last_words = preceding.split()[-3:]
        return any(
            keyword in last_words or keyword in preceding
            for keyword in SlotExtractor._SIZE_KEYWORDS
        )

    @classmethod
    def _extract_budget_details(cls, lower: str) -> Tuple[Optional[Dict], Dict[str, str]]:
        pattern = re.compile(
            r"(?<![a-z])(?:\u20a6|ngn\s*|n\s*)?(\d[\d,.]*)(?:\s*(million|m|k|thousand)\b)?"
        )
        matches = list(pattern.finditer(lower))
        if not matches:
            return None, {}

        values = []
        attributes: Dict[str, str] = {}
        for match in matches[:2]:
            raw = match.group(1)
            mult = match.group(2)
            try:
                amount = Decimal(raw.replace(',', ''))
                if mult in {'million', 'm'}:
                    amount *= Decimal('1000000')
                elif mult in {'k', 'thousand'}:
                    amount *= Decimal('1000')
                numeric_value = float(amount)
            except (InvalidOperation, ValueError):
                continue

            preceding_text = lower[max(0, match.start() - 40):match.start()]
            following_text = lower[match.end():match.end() + 12]

            if cls._is_size_not_price(numeric_value, preceding_text):
                attributes['size'] = (
                    str(int(numeric_value))
                    if numeric_value.is_integer()
                    else str(numeric_value)
                )
                continue

            if mult is None and cls._NON_PRICE_SUFFIX_RE.match(following_text):
                continue

            values.append(numeric_value)

        if not values:
            return None, attributes

        values = sorted(values)
        if len(values) == 1:
            if re.search(r"\b(?:under|below|less\s+than|max|at\s+most|not\s+more\s+than)\b", lower):
                return {'min': None, 'max': values[0]}, attributes
            if re.search(r"\b(?:above|over|more\s+than|min|at\s+least|from)\b", lower):
                return {'min': values[0], 'max': None}, attributes
            return {'min': None, 'max': values[0]}, attributes

        return {'min': values[0], 'max': values[-1]}, attributes

    @staticmethod
    def _extract_location(lower: str) -> Optional[str]:
        for key in sorted(_LOCATION_KEYWORDS, key=len, reverse=True):
            if re.search(rf'\b{re.escape(key)}\b', lower):
                return _LOCATION_KEYWORDS[key]
        return None

    @staticmethod
    def _extract_condition(lower: str) -> Optional[str]:
        for key in sorted(_CONDITION_MAP, key=len, reverse=True):
            if key in lower:
                return _CONDITION_MAP[key]
        return None

    @staticmethod
    def _extract_color(lower: str) -> Optional[str]:
        for color in _COLORS:
            if re.search(rf'\b{re.escape(color)}\b', lower):
                return color
        return None

    @staticmethod
    def _extract_brand(text: str) -> Optional[str]:
        lower = text.lower()
        for brand in sorted(_KNOWN_BRANDS, key=len, reverse=True):
            match = re.search(rf'\b{re.escape(brand)}\b', lower)
            if match:
                return text[match.start(): match.end()].title()
        return None

    @staticmethod
    def _extract_price_intent(lower: str) -> Optional[str]:
        if re.search(r'\b(?:premium|high[-\s]?end|flagship|luxury|best quality|top quality|expensive)\b', lower):
            return 'premium'
        if re.search(r'\b(?:cheap|budget|affordable|low[-\s]?cost|inexpensive|cheaper|lowest price)\b', lower):
            return 'cheap'
        return None

    @staticmethod
    def _extract_use_case(lower: str) -> Tuple[Optional[str], Optional[str]]:
        for use_case, hints in _USE_CASE_MAP.items():
            if use_case in lower:
                return use_case, hints[0]
        return None, None

    @staticmethod
    def _extract_product_type(lower: str) -> Optional[str]:
        for term in sorted(_PRODUCT_TERMS, key=len, reverse=True):
            suffix = 's?' if ' ' not in term and not term.endswith('s') else ''
            if re.search(rf'\b{re.escape(term)}{suffix}\b', lower):
                return term
        return None

    @classmethod
    def extract(cls, message: str, prior: Optional[Dict] = None) -> Dict:
        prior = prior or {}
        text = (message or '').strip()
        lower = text.lower()

        use_case, use_case_hint = cls._extract_use_case(lower)
        product_type = cls._extract_product_type(lower) or use_case_hint
        category = cls._resolve_category(lower, product_type)
        budget, derived_attributes = cls._extract_budget_details(lower)
        attributes = (
            dict(prior.get('attributes') or {})
            if isinstance(prior.get('attributes'), dict)
            else {}
        )
        attributes.update(derived_attributes)

        slots = {
            'product_type': product_type if product_type is not None else prior.get('product_type'),
            'category': category if category is not None else prior.get('category'),
            'price_min': budget.get('min') if budget else prior.get('price_min'),
            'price_max': budget.get('max') if budget else prior.get('price_max'),
            'location': cls._extract_location(lower) or prior.get('location'),
            'condition': cls._extract_condition(lower) or prior.get('condition'),
            'brand': cls._extract_brand(text) or prior.get('brand'),
            'price_intent': cls._extract_price_intent(lower) or prior.get('price_intent'),
            'color': cls._extract_color(lower) or prior.get('color'),
            'use_case': use_case if use_case is not None else prior.get('use_case'),
            'attributes': attributes,
            'rating': prior.get('rating'),
            'raw_query': text,
        }

        slots['budget_range'] = (
            {'min': slots.get('price_min'), 'max': slots.get('price_max')}
            if slots.get('price_min') is not None or slots.get('price_max') is not None
            else {}
        )
        slots['product_intent'] = 'purchase'
        return slots

    @staticmethod
    def has_product_intent(message: str, slots: Dict) -> bool:
        if slots.get('product_type') or slots.get('category'):
            return True
        if slots.get('price_min') is not None or slots.get('price_max') is not None:
            return True

        raw = (message or '').strip().lower()
        if not raw or raw in _GREETING_WORDS:
            return False
        if any(k in raw for k in _SUPPORT_KEYWORDS):
            return False
        if all(t in _GREETING_WORDS for t in raw.split()):
            return False

        product_signals = [
            'buy', 'purchase', 'need', 'want', 'find', 'looking', 'available',
            'price', 'cost', 'cheap', 'affordable', 'get me', 'show me', 'do you have',
        ]
        return any(sig in raw for sig in product_signals) or len(raw) >= 8

    @staticmethod
    def build_semantic_query(slots: Dict) -> str:
        parts = []
        for key in ('use_case', 'product_type', 'category', 'brand', 'color'):
            if slots.get(key):
                parts.append(str(slots[key]))

        attributes = slots.get('attributes') or {}
        if isinstance(attributes, dict):
            for key in sorted(attributes):
                value = attributes.get(key)
                if value not in (None, '', [], {}):
                    parts.append(f"{key} {value}")

        if slots.get('price_intent') == 'premium':
            parts.append('premium high end')
        elif slots.get('price_intent') == 'cheap':
            parts.append('budget affordable')

        if slots.get('condition') == 'new':
            parts.append('brand new')
        elif slots.get('condition') in {'fair', 'used', 'like_new', 'good', 'poor'}:
            parts.append('used')

        if slots.get('raw_query'):
            parts.append(str(slots['raw_query']))

        return ' '.join(parts).strip()


class SlotStateMachine:
    MAX_CLARIFICATIONS = 3
    CONFIRM_TOKENS = frozenset({
        'yes', 'y', 'yep', 'yeah', 'sure', 'ok', 'okay', 'go ahead',
        'show me', 'show', 'proceed', 'search', 'find', 'go', 'alright',
    })
    DECLINE_TOKENS = frozenset({'no', 'n', 'not yet', 'wait', 'change'})

    @classmethod
    def is_confirmation(cls, message: str) -> bool:
        return (message or '').lower().strip() in cls.CONFIRM_TOKENS

    @classmethod
    def is_decline(cls, message: str) -> bool:
        return (message or '').lower().strip() in cls.DECLINE_TOKENS

    @classmethod
    def get_next_clarification(cls, slots: Dict, intent_state: Dict) -> Optional[str]:
        count = int(intent_state.get('clarification_count', 0) or 0)
        if count >= cls.MAX_CLARIFICATIONS:
            return None

        if not slots.get('product_type'):
            return "What are you looking for? 🛍️ (e.g. Nike sneakers, Samsung phone, fairly used laptop)"

        if slots.get('price_max') is None:
            product = slots.get('product_type') or 'it'
            return f"What's your budget for {product}? 💰 (e.g. under ₦50,000 or around 200k)"

        if slots.get('condition') is None:
            return "New or fairly used (tokunbo)? 🔍"

        return None

    @staticmethod
    def build_confirmation_prompt(slots: Dict) -> str:
        product = slots.get('product_type') or slots.get('category') or 'product'
        details = []

        if slots.get('brand'):
            details.append(str(slots['brand']))

        if slots.get('condition'):
            label = {
                'new': 'brand new',
                'fair': 'fairly used',
                'used': 'used',
                'like_new': 'like new',
                'good': 'good condition',
                'poor': 'poor condition',
            }.get(str(slots['condition']), str(slots['condition']))
            details.append(label)

        if slots.get('price_max') is not None:
            details.append(f"under ₦{slots['price_max']:,.0f}")
        elif slots.get('price_min') is not None:
            details.append(f"from ₦{slots['price_min']:,.0f}")

        if slots.get('location'):
            details.append(f"in {slots['location']}")

        if slots.get('color'):
            details.append(str(slots['color']))

        suffix = f" — {', '.join(details)}" if details else ''
        return f"Got it! 👍 Looking for **{product}**{suffix}. Shall I show you what’s available? ✅"

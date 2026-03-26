"""
server/assistant/services/recommendation_service.py

Fixes applied (v2):
  1. _infer_category() was firing a fresh DB query on every single message.
     Now uses a 5-minute in-memory cache (thread-safe).
  2. _find_products() called the full search_products() pipeline which
     triggers semantic encoding of 200 products. Replaced with a direct
     ORM query — category filter + popularity ranking + price filter.
  3. NEW: _has_product_intent() gates evaluate_recommendation_message().
     Conversational messages ("hi", "yo", "hello", "how") now get a
     friendly prompt instead of a broken product lookup.
  4. FIXED: raw_query fallback in _find_products() now requires minimum
     query length and rejects known greeting words, preventing "yo"
     matching "Toyota" via icontains.
"""
import logging
import re
import threading
import time
import uuid
from decimal import Decimal
from typing import Dict, Optional

from django.db import transaction
from django.utils import timezone

from assistant.models import ConversationSession
from assistant.services.demand_gap_service import log_demand_gap

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Greeting / filler words that should never be used as product search terms
# ---------------------------------------------------------------------------
_GREETING_WORDS = frozenset([
    'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola',
    'how', 'ok', 'okay', 'sure', 'yep', 'yes', 'no', 'nope',
    'thanks', 'thank', 'bye', 'goodbye', 'lol', 'hmm', 'um', 'uh',
    'cool', 'nice', 'great', 'good', 'wow', 'oh', 'ah',
])

# Minimum meaningful query length for raw-text product search
_MIN_QUERY_LENGTH = 4


class RecommendationService:
    """Deterministic recommendation context management and constraint extraction."""

    SWITCH_CONFIRM_TOKENS = {'yes', 'y', 'confirm', 'switch', 'go ahead', 'sure', 'okay'}

    # -----------------------------------------------------------------------
    # Category cache — replaces per-message DB query
    # -----------------------------------------------------------------------
    _category_cache: dict = {}
    _category_cache_lock = threading.Lock()
    _CATEGORY_CACHE_TTL = 300  # seconds

    @classmethod
    def _get_category_map(cls) -> dict:
        """
        Return {lower_name: display_name} for all active categories.
        Cached for 5 minutes — eliminates the DB hit on every message turn.
        """
        now = time.monotonic()
        cache = cls._category_cache

        if cache and now - cache.get('_ts', 0) < cls._CATEGORY_CACHE_TTL:
            return cache['data']

        with cls._category_cache_lock:
            if cache and now - cache.get('_ts', 0) < cls._CATEGORY_CACHE_TTL:
                return cache['data']

            from market.models import Category
            data = {
                c.name.lower(): c.name
                for c in Category.objects.filter(is_active=True).only('name')[:300]
            }
            cls._category_cache = {'data': data, '_ts': now}
            logger.debug(f"Category cache refreshed: {len(data)} categories loaded")
            return data

    # -----------------------------------------------------------------------
    # Context lifecycle
    # -----------------------------------------------------------------------

    @classmethod
    def initialize_context(cls, session: ConversationSession) -> None:
        updates = []
        if session.context_type != ConversationSession.CONTEXT_TYPE_RECOMMENDATION:
            session.context_type = ConversationSession.CONTEXT_TYPE_RECOMMENDATION
            updates.append('context_type')
        if not isinstance(session.constraint_state, dict):
            session.constraint_state = {}
            updates.append('constraint_state')
        if not isinstance(session.intent_state, dict):
            session.intent_state = {}
            updates.append('intent_state')
        if updates:
            updates.append('updated_at')
            session.save(update_fields=updates)

    # -----------------------------------------------------------------------
    # Intent gate — NEW
    # -----------------------------------------------------------------------

    @classmethod
    def _has_product_intent(cls, message: str, constraints: Dict) -> bool:
        """
        Return True only when the message actually contains product-discovery
        or shopping intent.

        Blocks pure greetings / conversational fillers from triggering the
        product lookup pipeline, which previously caused:
          - "hi"  → random sneaker recommendation
          - "yo"  → Toyota Camry (icontains matched "To*yo*ta")
          - "how" → "couldn't find a matching product"
        """
        # If we extracted a real category or budget, there's intent
        if constraints.get('category'):
            return True
        if constraints.get('budget_range'):
            return True

        raw = (constraints.get('raw_query') or '').strip().lower()

        # Too short or a known greeting word → no intent
        if not raw or raw in _GREETING_WORDS or len(raw) < _MIN_QUERY_LENGTH:
            return False

        # All tokens are greeting words → no intent
        tokens = raw.split()
        if all(t in _GREETING_WORDS for t in tokens):
            return False

        # Explicit shopping signals
        PRODUCT_SIGNALS = [
            'buy', 'purchase', 'need', 'want', 'find', 'looking',
            'available', 'price', 'cost', 'cheap', 'affordable',
            'phone', 'laptop', 'sneaker', 'shoe', 'shirt', 'dress',
            'bag', 'watch', 'perfume', 'furniture', 'car', 'tablet',
            'headphone', 'earphone', 'earbuds', 'tv', 'fridge',
            'generator', 'AC', 'air conditioner', 'bicycle',
        ]
        if any(sig in raw for sig in PRODUCT_SIGNALS):
            return True

        # Raw query is long enough to be a real search term (e.g. "red high heels")
        if len(raw) >= 8:
            return True

        return False

    # -----------------------------------------------------------------------
    # Conversational reply when no product intent detected
    # -----------------------------------------------------------------------

    @staticmethod
    def _conversational_reply(message: str) -> str:
        """
        Return a natural, context-appropriate response for conversational
        messages that have no product intent.
        """
        lower = message.lower().strip()

        greetings = {'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola'}
        if lower in greetings or (len(lower.split()) == 1 and lower in greetings):
            return (
                "Hi there! 👋 I'm here to help you find great products. "
                "What are you shopping for today?"
            )

        acknowledgements = {'ok', 'okay', 'sure', 'cool', 'nice', 'great', 'good', 'wow'}
        if lower in acknowledgements:
            return "Great! What product are you looking for? I can help you find it. 🛍️"

        thanks = {'thanks', 'thank you', 'thank', 'ty'}
        if lower in thanks:
            return "You're welcome! Is there anything else you'd like to find? 😊"

        question_words = {'how', 'what', 'when', 'where', 'why', 'who'}
        if lower in question_words or lower.rstrip('?') in question_words:
            return (
                "I'm your shopping assistant — I can help you find products on Zunto. "
                "What are you looking for? Try something like "
                "'sneakers under ₦30,000' or 'Samsung phone'."
            )

        # Generic fallback for short unrecognised messages
        return (
            "I'm best at helping you find products! 🛒 "
            "Try telling me what you're looking for — e.g. "
            "'affordable laptops' or 'Nike sneakers in Lagos'."
        )

    # -----------------------------------------------------------------------
    # Constraint extraction
    # -----------------------------------------------------------------------

    @classmethod
    def extract_constraints(cls, message: str, prior: Optional[Dict] = None) -> Dict:
        text = (message or '').strip()
        lower = text.lower()
        prior = prior or {}

        category = cls._infer_category(lower) or prior.get('category')
        budget = cls._extract_budget(lower) or prior.get('budget_range')

        attributes = (
            prior.get('attributes', {}).copy()
            if isinstance(prior.get('attributes'), dict)
            else {}
        )
        for key in ['size', 'color']:
            m = re.search(rf"\b{key}\s*[:=]\s*([a-z0-9\- ]+)", lower)
            if m:
                attributes[key] = m.group(1).strip()

        location = None
        for token in ['in lagos', 'in abuja', 'in port harcourt', 'in kano']:
            if token in lower:
                location = token.replace('in ', '').title()
                break

        product_intent = 'browse'
        if any(k in lower for k in ['buy', 'purchase', 'need', 'looking for']):
            product_intent = 'purchase'

        return {
            'category': category,
            'sub_category': prior.get('sub_category'),
            'attributes': attributes,
            'budget_range': budget,
            'location': location or prior.get('location'),
            'product_intent': product_intent,
            'raw_query': text,
        }

    # -----------------------------------------------------------------------
    # Main evaluation entry point
    # -----------------------------------------------------------------------

    @classmethod
    def evaluate_recommendation_message(cls, session: ConversationSession, message: str) -> Dict:
        cls.initialize_context(session)

        existing = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        extracted = cls.extract_constraints(message, existing)

        # ── INTENT GATE ────────────────────────────────────────────────────
        # If the message has no product intent, respond conversationally
        # instead of running a product lookup that will either return a
        # random result or the "couldn't find" failure message.
        if not cls._has_product_intent(message, extracted):
            logger.debug(f"No product intent detected for: {message[:50]!r} — returning conversational reply")
            return {
                'reply': cls._conversational_reply(message),
                'drift_detected': False,
                'new_session_id': None,
            }
        # ───────────────────────────────────────────────────────────────────

        old_category = (existing.get('category') or '').lower().strip()
        new_category = (extracted.get('category') or '').lower().strip()

        pending = (
            session.intent_state.get('pending_category_switch')
            if isinstance(session.intent_state, dict)
            else None
        )
        if pending and message.lower().strip() in cls.SWITCH_CONFIRM_TOKENS:
            return cls._switch_conversation(session, pending)

        if old_category and new_category and old_category != new_category:
            session.drift_flag = True
            intent_state = session.intent_state if isinstance(session.intent_state, dict) else {}
            intent_state['pending_category_switch'] = extracted
            session.intent_state = intent_state
            session.save(update_fields=['drift_flag', 'intent_state', 'updated_at'])
            return {
                'reply': (
                    f"I noticed your request changed from **{old_category}** to **{new_category}**. "
                    "Reply 'yes' to start a new recommendation thread for this product."
                ),
                'drift_detected': True,
                'new_session_id': None,
            }

        session.constraint_state = extracted
        session.intent_state = {
            **(session.intent_state if isinstance(session.intent_state, dict) else {}),
            'last_intent': extracted.get('product_intent', 'browse'),
            'pending_category_switch': None,
        }
        session.drift_flag = False
        session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])

        products = cls._find_products(extracted)
        if not products:
            cls.log_demand_gap(session, extracted)
            return {
                'reply': (
                    "I couldn't find a matching product right now. "
                    "I've logged your request so our inventory can improve. "
                    "Try broadening your search — e.g. drop the price limit or try a different category."
                ),
                'drift_detected': False,
                'new_session_id': None,
            }

        top = products[0]
        session.active_product = top
        session.save(update_fields=['active_product', 'updated_at'])
        return {
            'reply': (
                f"Top recommendation: **{top.title}** — ₦{top.price:,}. "
                "Would you like more options in this category?"
            ),
            'drift_detected': False,
            'new_session_id': None,
        }

    # -----------------------------------------------------------------------
    # Session switching
    # -----------------------------------------------------------------------

    @classmethod
    def _switch_conversation(cls, session: ConversationSession, pending_constraints: Dict) -> Dict:
        with transaction.atomic():
            now = timezone.now()
            session.completed_at = now
            session.current_state = 'closed'
            session.drift_flag = False
            session.save(update_fields=['completed_at', 'current_state', 'drift_flag', 'updated_at'])

            new_session = ConversationSession.objects.create(
                session_id=str(uuid.uuid4()),
                user=session.user,
                user_name=session.user_name,
                assistant_lane=session.assistant_lane,
                assistant_mode=session.assistant_mode,
                is_persistent=session.is_persistent,
                current_state='chat_mode',
                context=session.context,
                context_data=session.context_data,
                context_type=ConversationSession.CONTEXT_TYPE_RECOMMENDATION,
                constraint_state=pending_constraints,
                intent_state={'last_intent': pending_constraints.get('product_intent', 'browse')},
                conversation_history=[],
            )
        return {
            'reply': 'Got it — I started a new recommendation thread for this product category.',
            'drift_detected': False,
            'new_session_id': new_session.session_id,
        }

    # -----------------------------------------------------------------------
    # Demand gap logging
    # -----------------------------------------------------------------------

    @classmethod
    def log_demand_gap(cls, session: ConversationSession, constraints: Dict) -> None:
        payload = {
            'category': constraints.get('category') or '',
            'location': constraints.get('location') or '',
            **(constraints.get('attributes') or {}),
        }
        log_demand_gap(
            raw_query='',
            structured_filters=payload,
            user=session.user,
            source='',
        )

    # -----------------------------------------------------------------------
    # Category inference — uses cache, no per-call DB query
    # -----------------------------------------------------------------------

    @classmethod
    def _infer_category(cls, lower: str) -> Optional[str]:
        """Infer category from message using cached map — zero DB queries per call."""
        category_map = cls._get_category_map()
        for key, name in category_map.items():
            if key in lower:
                return name

        FALLBACK = [
            'phone', 'laptop', 'sneaker', 'shoe', 'shirt', 'dress',
            'bag', 'watch', 'perfume', 'furniture', 'car',
        ]
        for f in FALLBACK:
            if f in lower:
                return f.title()
        return None

    # -----------------------------------------------------------------------
    # Budget extraction
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_budget(lower: str) -> Optional[Dict]:
        matches = re.findall(r"(?:₦|ngn|n)?\s*(\d{2,9})", lower)
        if not matches:
            return None
        nums = sorted(Decimal(m) for m in matches[:2])
        if len(nums) == 1:
            return {'min': float(nums[0]), 'max': float(nums[0])}
        return {'min': float(nums[0]), 'max': float(nums[1])}

    # -----------------------------------------------------------------------
    # Product lookup — direct ORM, bypasses full search pipeline
    # -----------------------------------------------------------------------

    @staticmethod
    def _find_products(constraints: Dict):
        """
        Lightweight product lookup for the AI recommendation path.

        Uses direct ORM filtering + popularity ordering instead of going
        through the full search_products() pipeline (which triggers semantic
        encoding of up to 200 products on every message).

        Fast path: category filter → price filter → popularity sort → top 5.

        Safety: raw_query fallback is only used when:
          - the query is at least _MIN_QUERY_LENGTH characters long
          - the query is not a greeting/filler word
        This prevents short words like "yo" matching product titles via
        icontains (e.g. "yo" matching "Toyota").
        """
        from market.models import Product
        from django.db.models import F, FloatField, ExpressionWrapper, Value, Q
        from django.db.models.functions import Coalesce

        raw_query = (constraints.get('raw_query') or '').strip()
        category = constraints.get('category')
        budget = constraints.get('budget_range') or {}
        location = (constraints.get('location') or '').strip()

        # Short-circuit: nothing useful to search on
        if not category and not raw_query:
            return []

        # Safety: don't use raw_query as a search term if it's a greeting
        # or too short — this prevents accidental substring matches like
        # "yo" → "Toyota", "hi" → any product with "hi" in the title
        safe_raw_query = ''
        if raw_query:
            lower_raw = raw_query.lower().strip()
            is_greeting = lower_raw in _GREETING_WORDS
            is_too_short = len(lower_raw) < _MIN_QUERY_LENGTH
            all_greetings = all(t in _GREETING_WORDS for t in lower_raw.split())
            if not is_greeting and not is_too_short and not all_greetings:
                safe_raw_query = raw_query

        # If we have no category AND no safe query, bail out
        if not category and not safe_raw_query:
            return []

        qs = Product.objects.filter(status='active').select_related('category', 'location')

        if category:
            qs = qs.filter(category__name__icontains=category)
        elif safe_raw_query:
            qs = qs.filter(
                Q(title__icontains=safe_raw_query)
                | Q(description__icontains=safe_raw_query)
                | Q(category__name__icontains=safe_raw_query)
            )

        if isinstance(budget, dict):
            if budget.get('min') is not None:
                qs = qs.filter(price__gte=budget['min'])
            if budget.get('max') is not None:
                qs = qs.filter(price__lte=budget['max'])

        if location:
            qs = qs.filter(
                Q(location__state__icontains=location)
                | Q(location__city__icontains=location)
            )

        qs = qs.annotate(
            pop_score=ExpressionWrapper(
                Coalesce(F('views_count'), Value(0))
                + Coalesce(F('favorites_count'), Value(0)) * 3,
                output_field=FloatField(),
            )
        ).order_by('-pop_score', '-created_at')

        return list(qs[:5])
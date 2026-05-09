# Deprecated: live homepage recommendations are now handled by
# assistant.services.gigi_agent.GigiRecommendationAgent.
# This module is retained for legacy tests, seed scripts, and historical
# evaluation utilities; do not import it from active request code.

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import Case, ExpressionWrapper, F, FloatField, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from assistant.models import ConversationSession
from assistant.processors.local_model import LocalModelAdapter
from assistant.services.demand_gap_service import log_demand_gap
from assistant.services.llm_slot_enricher import enrich_slots
from assistant.services.slot_extractor import SlotStateMachine
from assistant.services.structured_query_pipeline import (
    build_retrieval_query,
    build_structured_query,
    structured_query_to_slots,
)
from market.search.embeddings import search_similar_products
from market.search.hybrid_ranker import product_search_text, rank_products_hybrid

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecommendationTurnDecision:
    turn_type: str
    active_context: bool
    clarification_key: str = ''


@dataclass(frozen=True)
class RecommendationContextShift:
    action: str
    reason: str = ''
    confidence: float = 0.0
    source: str = 'fallback'


class RecommendationTurnClassifier:
    TURN_NEW_QUERY = 'new_query'
    TURN_CLARIFICATION_ANSWER = 'clarification_answer'
    TURN_REFINEMENT = 'refinement'
    TURN_REJECTION = 'rejection'
    OUTCOME_RESULTS = 'results'
    OUTCOME_NO_RESULTS = 'no_results'

    _FOLLOW_UP_REFINEMENT_TOKENS = frozenset({
        'different options', 'something else', 'show me more', 'more options',
        'another one', 'another', 'different', 'else', 'something cheaper',
        'cheaper', 'less expensive', 'show another', 'show me something cheaper',
    })
    _NON_CLARIFICATION_TOKENS = frozenset({
        'yes', 'y', 'no', 'n', 'ok', 'okay', 'sure', 'nah', 'nope', 'wait',
    })

    @classmethod
    def classify(
        cls,
        *,
        message: str,
        prior_slots: Dict[str, Any],
        raw_slots: Dict[str, Any],
        slots: Dict[str, Any],
        raw_has_product_intent: bool,
        has_constraint_updates: bool,
        short_follow_up_constraint_turn: bool,
        rejection_detected: bool,
    ) -> RecommendationTurnDecision:
        raw = (message or '').strip().lower()
        clarification_key = str(prior_slots.get('_last_clarification_key') or '').strip()
        active_context = bool(
            prior_slots.get('product_type')
            or prior_slots.get('category')
            or prior_slots.get('_shown_product_ids')
            or clarification_key
        )

        if active_context and rejection_detected:
            return RecommendationTurnDecision(turn_type=cls.TURN_REJECTION, active_context=True)

        if active_context and clarification_key and cls._is_clarification_answer(
            message=message,
            raw_slots=raw_slots,
            raw_has_product_intent=raw_has_product_intent,
            has_constraint_updates=has_constraint_updates,
        ):
            return RecommendationTurnDecision(
                turn_type=cls.TURN_CLARIFICATION_ANSWER,
                active_context=True,
                clarification_key=clarification_key,
            )

        if active_context and cls._is_new_query(
            prior_slots=prior_slots,
            raw_slots=raw_slots,
            slots=slots,
            raw_has_product_intent=raw_has_product_intent,
        ):
            return RecommendationTurnDecision(turn_type=cls.TURN_NEW_QUERY, active_context=True)

        if active_context and cls._is_refinement_turn(
            raw=raw,
            has_constraint_updates=has_constraint_updates,
            short_follow_up_constraint_turn=short_follow_up_constraint_turn,
        ):
            return RecommendationTurnDecision(turn_type=cls.TURN_REFINEMENT, active_context=True)

        return RecommendationTurnDecision(turn_type=cls.TURN_NEW_QUERY, active_context=active_context)

    @classmethod
    def _is_clarification_answer(
        cls,
        *,
        message: str,
        raw_slots: Dict[str, Any],
        raw_has_product_intent: bool,
        has_constraint_updates: bool,
    ) -> bool:
        raw = (message or '').strip().lower()
        if not raw or raw in cls._NON_CLARIFICATION_TOKENS:
            return False
        if raw.endswith('?'):
            return False
        if SlotStateMachine.is_confirmation(raw) or SlotStateMachine.is_decline(raw):
            return False
        if has_constraint_updates and not raw_has_product_intent:
            return True
        if raw_slots.get('attributes') and len(raw.split()) <= 4:
            return True
        return len(raw.split()) <= 3 and not raw_has_product_intent

    @classmethod
    def _is_refinement_turn(
        cls,
        *,
        raw: str,
        has_constraint_updates: bool,
        short_follow_up_constraint_turn: bool,
    ) -> bool:
        if has_constraint_updates or short_follow_up_constraint_turn:
            return True
        if raw in cls._FOLLOW_UP_REFINEMENT_TOKENS:
            return True
        return any(token in raw for token in cls._FOLLOW_UP_REFINEMENT_TOKENS)

    @staticmethod
    def _is_new_query(
        *,
        prior_slots: Dict[str, Any],
        raw_slots: Dict[str, Any],
        slots: Dict[str, Any],
        raw_has_product_intent: bool,
    ) -> bool:
        if not raw_has_product_intent:
            return False

        prior_product = str(
            prior_slots.get('product_type')
            or prior_slots.get('category')
            or ''
        ).strip().lower()
        current_product = str(
            raw_slots.get('product_type')
            or raw_slots.get('category')
            or slots.get('product_type')
            or slots.get('category')
            or ''
        ).strip().lower()

        if not current_product:
            return False
        if not prior_product:
            return True
        return current_product != prior_product


class RecommendationService:
    """Conversational catalog-semantic product recommender for homepage_reco."""

    UPDATE_SLOT_KEYS = (
        'product_type',
        'category',
        'price_min',
        'price_max',
        'price_intent',
        'condition',
        'location',
        'brand',
        'color',
        'use_case',
        'attributes',
    )
    FOCUSED_FOLLOWUP_FAMILIES = {
        'phone',
        'phones',
        'smartphone',
        'smartphones',
        'mobile phone',
        'mobile phones',
    }

    @staticmethod
    def _build_response(
        *,
        reply: str,
        source: str,
        session: ConversationSession,
        confidence: float = 0.8,
        drift_detected: bool = False,
        new_session_id: str = None,
        metadata: Dict = None,
    ) -> Dict:
        base_metadata = {
            'assistant_mode': session.assistant_mode,
            'assistant_lane': session.assistant_lane,
            'intent': 'product_search',
            'knowledge_lane': 'homepage_reco_catalog',
            'retrieval_system': 'catalog_semantic_search',
            'retrieval_source': 'market.Product',
        }
        if isinstance(metadata, dict):
            base_metadata.update(metadata)
        return {
            'reply': reply,
            'confidence': float(confidence),
            'source': source,
            'metadata': base_metadata,
            'drift_detected': drift_detected,
            'new_session_id': new_session_id,
        }

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

    @staticmethod
    def _stray_reply_keywords(message: str) -> str:
        lower = (message or '').lower()
        support_keywords = {'refund', 'dispute', 'complaint', 'return', 'track', 'order', 'delivery', 'payment', 'scam', 'fraud'}
        if any(k in lower for k in support_keywords):
            return "😅 I'm here to help with product recommendations only. For support issues, please use the AI inbox."

        greetings = {'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola'}
        if lower.strip() in greetings:
            return "👋 Hey! I'm Gigi, your shopping assistant. What product are you looking for today?"

        if any(t in lower for t in ['😂', 'haha', 'lol', 'joke']):
            return "😄 Haha! Now let's find something great for you — what are you shopping for?"
        return "I can help you find products fast. Tell me what you want, including budget, location, or preferences if they matter."

    @classmethod
    def _stray_reply(cls, message: str) -> str:
        lower = (message or '').lower().strip()

        greetings = {'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola'}
        if lower in greetings:
            return "👋 Hey! I'm Gigi, your shopping assistant. Tell me what product you're hunting for."

        support_keywords = {'refund', 'dispute', 'complaint', 'return', 'track', 'order', 'delivery', 'payment', 'scam', 'fraud'}
        if any(k in lower for k in support_keywords):
            return "I can handle product recommendations only here. Please use the AI inbox for support issues."

        nonsense_tokens = {'asdf', 'qwerty', 'zxczxc', '123123', '???'}
        if lower in nonsense_tokens:
            return "😅 I didn't catch that one. Tell me the product you want and I'll jump in."

        adapter = LocalModelAdapter.get_instance()
        if not adapter.is_available():
            logger.info("Recommendation stray detector: local adapter unavailable, using keyword fallback")
            return cls._stray_reply_keywords(message)

        llm_output = adapter.generate(
            prompt=message,
            system_prompt=(
                "You are a drift detector for a product recommendation AI..."
            ),
            max_tokens=20,
            temperature=0.1,
        )
        label = (llm_output.get('response', '') if isinstance(llm_output, dict) else str(llm_output)).strip().upper()
        if label in {'```PRODUCT_SEARCH```', '```SUPPORT_ISSUE```', '```CASUAL_CHAT```', '```NONSENSE```'}:
            label = label.strip('`').strip()

        if label == 'PRODUCT_SEARCH':
            logger.debug("Recommendation stray detector allowed product search path")
            return None
        if label == 'SUPPORT_ISSUE':
            return "I can only handle product recommendations here. Please use the AI inbox for support issues."
        if label == 'CASUAL_CHAT':
            return "😄 I'm in shopping mode — tell me what product you want and I'll find options."
        if label == 'NONSENSE':
            return "🤖 My Naija brain buffer just overflowed 😅 — tell me what item you want to buy."

        return cls._stray_reply_keywords(message)

    @classmethod
    def _has_prior_product_context(cls, slots: Dict) -> bool:
        return bool(slots.get('product_type') or slots.get('category'))

    @staticmethod
    def _get_prior_search_slots(user) -> Dict[str, Any]:
        """
        Retrieve the last meaningful homepage_reco slots for an authenticated user.
        ConversationSession remains the source of truth; failures stay silent.
        """
        try:
            if not user or not getattr(user, 'is_authenticated', False):
                return {}

            prior_session = (
                ConversationSession.objects.filter(
                    user=user,
                    assistant_mode='homepage_reco',
                )
                .exclude(constraint_state={})
                .exclude(constraint_state__isnull=True)
                .order_by('-last_activity')
                .first()
            )
            if not prior_session:
                return {}

            slots = prior_session.constraint_state or {}
            if not isinstance(slots, dict):
                return {}
            if not (slots.get('product_type') or slots.get('category')):
                return {}

            return {
                key: value
                for key, value in slots.items()
                if not str(key).startswith('_')
                and value not in (None, '', [], {})
            }
        except Exception as exc:
            logger.warning("Prior search load failed: %s", exc)
            return {}

    @staticmethod
    def _build_memory_greeting(prior_slots: Dict[str, Any]) -> str:
        """Build a returning-buyer greeting from prior search slots."""
        product = (
            prior_slots.get('product_type')
            or prior_slots.get('category')
            or 'products'
        )
        parts = [f"Welcome back! Last time you searched for **{product}**"]

        location = prior_slots.get('location')
        if location:
            parts.append(f"in {str(location).title()}")

        price_max = prior_slots.get('price_max')
        if price_max:
            try:
                parts.append(f"under ₦{int(float(price_max)):,}")
            except (TypeError, ValueError):
                pass

        condition = prior_slots.get('condition')
        if condition:
            parts.append(f"({condition} condition)")

        return (
            ' '.join(parts) + '.\n\n'
            'Shall I pick up where we left off, or are you looking for something different today?'
        )

    @staticmethod
    def _clean_intent_state(intent_state: Dict, **overrides) -> Dict:
        cleaned = {
            key: value
            for key, value in (intent_state or {}).items()
            if key not in {'confirmed', 'confirmation_pending'}
        }
        cleaned.update(overrides)
        return cleaned

    @classmethod
    def _has_constraint_updates(cls, raw_slots: Dict, prior_slots: Dict) -> bool:
        for key in cls.UPDATE_SLOT_KEYS:
            current = raw_slots.get(key)
            if current is None:
                continue
            if current != prior_slots.get(key):
                return True
        return False

    @classmethod
    def _is_short_follow_up_constraint_turn(cls, message: str, raw_slots: Dict, prior_slots: Dict) -> bool:
        if not cls._has_prior_product_context(prior_slots):
            return False

        raw = (message or '').strip().lower()
        if not raw:
            return False

        if cls._has_constraint_updates(raw_slots, prior_slots):
            return True

        if SlotStateMachine.is_confirmation(raw) or SlotStateMachine.is_decline(raw):
            return True

        return raw in {'yes', 'no', 'y', 'n', 'ok', 'okay', 'wait'}

    @staticmethod
    def _normalize_context_value(value: Any) -> str:
        return re.sub(r'\s+', ' ', str(value or '').strip().lower())

    @classmethod
    def _context_family_signature(cls, slots: Optional[Dict[str, Any]]) -> str:
        slots = slots or {}
        for key in ('product_type', 'category'):
            value = cls._normalize_context_value(slots.get(key))
            if value and value != 'products':
                return value
        brand = cls._normalize_context_value(slots.get('brand'))
        return brand

    @staticmethod
    def _explicit_new_search_signal(message: str) -> bool:
        raw = (message or '').lower()
        return bool(re.search(
            r'\b(?:now|actually|instead|new search|start over|start fresh|change to|switch to|'
            r'i want|i need|looking for|show me|find me|get me)\b',
            raw,
        ))

    @staticmethod
    def _sanitize_new_context_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {
            key: value
            for key, value in dict(slots or {}).items()
            if not str(key).startswith('_')
            and key not in {'rating'}
            and value not in (None, '', [], {})
        }
        if not isinstance(cleaned.get('attributes'), dict):
            cleaned.pop('attributes', None)
        return cleaned

    @classmethod
    def _detect_context_shift_fallback(
        cls,
        *,
        message: str,
        prior_slots: Dict[str, Any],
        raw_slots: Dict[str, Any],
        slots: Dict[str, Any],
        raw_has_product_intent: bool,
        has_constraint_updates: bool,
        short_follow_up_constraint_turn: bool,
    ) -> RecommendationContextShift:
        if not cls._has_prior_product_context(prior_slots):
            return RecommendationContextShift(action='continue', reason='no_prior_context', confidence=1.0)
        if not raw_has_product_intent:
            return RecommendationContextShift(action='continue', reason='no_new_product_intent', confidence=0.85)
        if short_follow_up_constraint_turn and not cls._context_family_signature(raw_slots):
            return RecommendationContextShift(action='continue', reason='short_refinement', confidence=0.8)

        prior_family = cls._context_family_signature(prior_slots)
        raw_family = cls._context_family_signature(raw_slots)
        new_family = raw_family or cls._context_family_signature(slots)

        if prior_family and new_family and prior_family != new_family:
            return RecommendationContextShift(
                action='reset',
                reason='product_family_changed',
                confidence=0.92,
            )

        if (
            has_constraint_updates
            and cls._explicit_new_search_signal(message)
            and any(raw_slots.get(key) is not None for key in ('price_min', 'price_max', 'location', 'condition', 'brand'))
        ):
            return RecommendationContextShift(
                action='reset',
                reason='fresh_constraints_for_same_family',
                confidence=0.76,
            )

        return RecommendationContextShift(action='continue', reason='same_context', confidence=0.8)

    @classmethod
    def _detect_context_shift_llm(
        cls,
        *,
        message: str,
        prior_slots: Dict[str, Any],
        raw_slots: Dict[str, Any],
        slots: Dict[str, Any],
    ) -> Optional[RecommendationContextShift]:
        try:
            adapter = LocalModelAdapter.get_instance()
            if not adapter.is_available():
                return None

            prompt = f"""Decide whether a marketplace shopper's newest message continues the current product search
or resets the current search with new constraints inside the same conversation.

Current search slots:
{json.dumps(cls._sanitize_new_context_slots(prior_slots), ensure_ascii=False)}

Newest message:
{message}

Fresh slots extracted only from the newest message:
{json.dumps(cls._sanitize_new_context_slots(raw_slots), ensure_ascii=False)}

Merged slots that would be used if context continued:
{json.dumps(cls._sanitize_new_context_slots(slots), ensure_ascii=False)}

Return only JSON:
{{"action":"continue|reset","reason":"short reason","confidence":0.0}}

Use "reset" when the shopper asks for a different product family or requests a fresh search.
Use "continue" for short answers, clarifications, cheaper/different-options requests, or refinements inside the same search.
"""
            output = adapter.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a context-state classifier for a product recommender. "
                    "Use language understanding and product context. Return only valid JSON."
                ),
                max_tokens=120,
                temperature=0.0,
            )
            raw = output.get('response', '') if isinstance(output, dict) else str(output)
            raw = raw.strip()
            if raw.startswith('```'):
                raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
                raw = re.sub(r'\s*```$', '', raw)
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                raw = match.group(0)
            parsed = json.loads(raw)
            action = str(parsed.get('action') or '').strip().lower()
            if action not in {'continue', 'reset'}:
                return None
            confidence = float(parsed.get('confidence') or 0.0)
            return RecommendationContextShift(
                action=action,
                reason=str(parsed.get('reason') or 'llm_context_shift').strip(),
                confidence=max(0.0, min(confidence, 1.0)),
                source='llm',
            )
        except Exception as exc:
            logger.warning("LLM context shift detection failed; using fallback: %s", exc)
            return None

    @classmethod
    def _detect_context_shift(
        cls,
        *,
        message: str,
        prior_slots: Dict[str, Any],
        raw_slots: Dict[str, Any],
        slots: Dict[str, Any],
        raw_has_product_intent: bool,
        has_constraint_updates: bool,
        short_follow_up_constraint_turn: bool,
    ) -> RecommendationContextShift:
        fallback = cls._detect_context_shift_fallback(
            message=message,
            prior_slots=prior_slots,
            raw_slots=raw_slots,
            slots=slots,
            raw_has_product_intent=raw_has_product_intent,
            has_constraint_updates=has_constraint_updates,
            short_follow_up_constraint_turn=short_follow_up_constraint_turn,
        )
        llm_decision = cls._detect_context_shift_llm(
            message=message,
            prior_slots=prior_slots,
            raw_slots=raw_slots,
            slots=slots,
        )
        if not llm_decision:
            return fallback
        if fallback.action == 'reset' and fallback.reason == 'product_family_changed' and llm_decision.action == 'continue':
            return fallback
        if llm_decision.confidence >= 0.65:
            return llm_decision
        return fallback

    @staticmethod
    def _with_turn_metadata(
        metadata: Optional[Dict[str, Any]] = None,
        *,
        turn_type: Optional[str] = None,
        turn_outcome: Optional[str] = None,
    ) -> Dict[str, Any]:
        merged = dict(metadata or {})
        if turn_type is not None:
            merged['turn_type'] = turn_type
        if turn_outcome is not None:
            merged['turn_outcome'] = turn_outcome
        return merged

    @classmethod
    def _build_turn_response(
        cls,
        *,
        reply: str,
        source: str,
        session: ConversationSession,
        turn_type: str,
        turn_outcome: Optional[str] = None,
        confidence: float = 0.8,
        drift_detected: bool = False,
        new_session_id: str = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return cls._build_response(
            reply=reply,
            source=source,
            session=session,
            confidence=confidence,
            drift_detected=drift_detected,
            new_session_id=new_session_id,
            metadata=cls._with_turn_metadata(
                metadata,
                turn_type=turn_type,
                turn_outcome=turn_outcome,
            ),
        )

    @classmethod
    def _compose_turn_intent_state(
        cls,
        intent_state: Dict[str, Any],
        *,
        turn_type: str,
        turn_outcome: Optional[str] = None,
        **overrides,
    ) -> Dict[str, Any]:
        return cls._clean_intent_state(
            intent_state,
            last_intent='product_search',
            last_turn_type=turn_type,
            last_turn_outcome=turn_outcome,
            **overrides,
        )

    @staticmethod
    def _active_product_label(slots: Dict[str, Any]) -> str:
        product = str(
            slots.get('product_type')
            or slots.get('category')
            or 'products'
        ).strip()
        return product or 'products'

    @classmethod
    def _normalized_product_family(cls, slots: Dict[str, Any]) -> str:
        family = cls._active_product_label(slots).lower().strip()
        family = re.sub(r'\s+', ' ', family)
        if family.endswith('s') and len(family) > 4:
            family = family[:-1]
        return family

    @classmethod
    def _has_meaningful_shopping_constraint(cls, slots: Dict[str, Any]) -> bool:
        if slots.get('price_min') is not None or slots.get('price_max') is not None:
            return True
        for key in ('brand', 'condition', 'location', 'color', 'use_case', 'price_intent'):
            if slots.get(key) not in (None, '', {}, []):
                return True
        attributes = slots.get('attributes')
        if isinstance(attributes, dict):
            return any(value not in (None, '', {}, []) for value in attributes.values())
        return False

    @classmethod
    def _focused_followup_for_vague_request(cls, slots: Dict[str, Any]) -> Optional[Dict[str, str]]:
        family = cls._normalized_product_family(slots)
        if family not in cls.FOCUSED_FOLLOWUP_FAMILIES:
            return None
        if cls._has_meaningful_shopping_constraint(slots):
            return None
        return {
            'question': "What's your budget for the phone?",
            'attribute_key': 'price_max',
        }

    @classmethod
    def _is_distinct_product_request(
        cls,
        prior_slots: Dict[str, Any],
        raw_slots: Dict[str, Any],
    ) -> bool:
        prior_product = cls._active_product_label(prior_slots or {}).lower()
        raw_product = cls._active_product_label(raw_slots or {}).lower()
        if prior_product == 'products' or raw_product == 'products':
            return False
        return prior_product != raw_product

    @staticmethod
    def _has_searchable_exact_context(slots: Dict[str, Any]) -> bool:
        has_product = bool(
            slots.get('product_type')
            or slots.get('category')
            or slots.get('brand')
        )
        if not has_product:
            return False
        if slots.get('price_min') is not None or slots.get('price_max') is not None:
            return True
        if slots.get('location') or slots.get('condition') or slots.get('brand'):
            return True
        attributes = slots.get('attributes')
        return isinstance(attributes, dict) and bool(attributes)

    @staticmethod
    def _product_primary_image_url(product) -> Optional[str]:
        return getattr(product, 'image_url', None)

    @classmethod
    def _serialize_product_suggestions(
        cls,
        products,
        slots: Optional[Dict[str, Any]] = None,
        *,
        match_type: str = 'match',
    ) -> List[Dict[str, Any]]:
        suggestions = []
        for product in list(products or [])[:5]:
            location = ''
            if getattr(product, 'location_id', None) and getattr(product, 'location', None):
                location = str(product.location)

            seller = getattr(product, 'seller', None)
            seller_name = ''
            if seller:
                try:
                    seller_name = seller.get_full_name() or getattr(seller, 'email', '') or ''
                except Exception:
                    seller_name = getattr(seller, 'email', '') or ''

            category_name = ''
            if getattr(product, 'category_id', None) and getattr(product, 'category', None):
                category_name = getattr(product.category, 'name', '') or ''

            suggestions.append({
                'id': str(product.id),
                'title': product.title,
                'slug': product.slug,
                'product_url': f"/product/{product.slug}",
                'price': str(product.price),
                'condition': getattr(product, 'condition', '') or '',
                'brand': getattr(product, 'brand', '') or '',
                'location': location,
                'category': category_name,
                'seller_name': seller_name,
                'primary_image': cls._product_primary_image_url(product),
                'match_type': match_type,
                'is_verified': bool(getattr(product, 'is_verified', False)),
                'is_verified_product': bool(getattr(product, 'is_verified_product', False)),
                'ranking': {
                    'total_score': float(getattr(product, 'recommendation_score', 0.0) or 0.0),
                    'components': getattr(product, 'recommendation_score_components', {}) or {},
                    'weights': getattr(product, 'recommendation_score_weights', {}) or {},
                },
                'match_reasons': getattr(product, 'recommendation_match_reasons', []) or [],
            })
        return suggestions

    @classmethod
    def _product_suggestion_metadata(
        cls,
        products,
        slots: Optional[Dict[str, Any]] = None,
        *,
        match_type: str = 'match',
    ) -> Dict[str, Any]:
        suggestions = cls._serialize_product_suggestions(
            products,
            slots,
            match_type=match_type,
        )
        return {
            'suggested_products': suggestions,
            'suggested_product_count': len(suggestions),
            'active_product_family': cls._active_product_label(slots or {}),
            'suggestion_match_type': match_type,
        }

    @staticmethod
    def _hard_constraint_snapshot(slots: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        slots = slots or {}
        constraints = {'stock': 'active_quantity_gt_0'}
        for key in (
            'product_type',
            'category',
            'brand',
            'condition',
            'location',
            'price_min',
            'price_max',
            'color',
        ):
            value = slots.get(key)
            if value not in (None, '', {}, []):
                constraints[key] = value
        attributes = slots.get('attributes')
        if isinstance(attributes, dict) and attributes:
            constraints['attributes'] = attributes
        return constraints

    @classmethod
    def _exact_match_metadata(
        cls,
        products,
        slots: Optional[Dict[str, Any]] = None,
        *,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = {
            'exact_match_found': True,
            'no_exact_match': False,
            'match_contract': 'deterministic_filtered_active_inventory',
            'hard_constraints': cls._hard_constraint_snapshot(slots),
            **cls._product_suggestion_metadata(products, slots, match_type='match'),
        }
        if extra:
            metadata.update(extra)
        return metadata

    @classmethod
    def _no_exact_match_metadata(
        cls,
        alternatives,
        slots: Optional[Dict[str, Any]] = None,
        *,
        reason: str = 'ranked_inventory_no_close_match',
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = {
            'exact_match_found': False,
            'no_exact_match': True,
            'match_contract': 'ranked_active_inventory_with_labeled_alternatives',
            'no_exact_match_reason': reason,
            'hard_constraints': cls._hard_constraint_snapshot(slots),
            'alternatives_labeled': True,
            **cls._product_suggestion_metadata(
                alternatives,
                slots,
                match_type='alternative',
            ),
        }
        if extra:
            metadata.update(extra)
        return metadata

    @classmethod
    def _merge_active_refinement_slots(
        cls,
        prior_slots: Dict[str, Any],
        constraint_update: Dict[str, Any],
        message: str,
    ) -> Dict[str, Any]:
        updated_slots = dict(prior_slots or {})
        for key, value in (constraint_update or {}).items():
            if key == '_shown_product_ids':
                continue
            if value in (None, '', {}, []):
                continue
            updated_slots[key] = value
        updated_slots['raw_query'] = message
        updated_slots.pop('structured_query', None)
        return updated_slots

    @staticmethod
    def _has_product_intent(message: str, slots: Dict[str, Any]) -> bool:
        raw = (message or '').strip().lower()
        if not raw:
            return False

        non_search_tokens = {
            'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola',
            'yes', 'y', 'no', 'n', 'ok', 'okay', 'sure', 'thanks', 'thank you',
        }
        if raw in non_search_tokens:
            return False

        support_keywords = {
            'refund', 'dispute', 'complaint', 'return', 'track', 'order',
            'delivery', 'payment', 'scam', 'fraud', 'cancel', 'support',
        }
        if any(keyword in raw for keyword in support_keywords):
            return False

        structured = slots.get('structured_query') if isinstance(slots, dict) else {}
        has_extracted_signal = bool(
            slots.get('product_type')
            or (structured or {}).get('product_type')
            or slots.get('attributes')
            or (structured or {}).get('attributes')
            or slots.get('price_min') is not None
            or slots.get('price_max') is not None
            or ((structured or {}).get('numeric_filters') or {})
        )
        if has_extracted_signal:
            return True

        request_signals = {
            'buy', 'purchase', 'need', 'want', 'find', 'looking', 'search',
            'available', 'price', 'cost', 'cheap', 'affordable', 'show me',
            'do you have', 'recommend', 'compare',
        }
        return any(signal in raw for signal in request_signals)

    @classmethod
    def _format_refinement_no_results_reply(
        cls,
        *,
        acknowledgement: str,
        slots: Dict[str, Any],
        alternatives: List[Any],
    ) -> str:
        product = cls._active_product_label(slots)
        prefix = f"{acknowledgement} " if acknowledgement else ""
        if alternatives:
            alt_lines = [f"- Alternative: **{item.title}** - \u20A6{item.price:,.0f}" for item in alternatives]
            return (
                f"{prefix}I couldn't find an exact refreshed match for **{product}** "
                "with that change. Alternatives below are not exact matches:\n"
                + "\n".join(alt_lines)
                + "\nI've also logged this preference so sellers can respond with closer stock."
            )
        return (
            f"{prefix}I couldn't find a closer **{product}** match with that refinement right now. "
            "I've kept your search context and logged the preference so we can surface new matches when they appear."
        )

    @classmethod
    def _format_no_exact_match_reply(
        cls,
        slots: Dict[str, Any],
        alternatives: List[Any],
    ) -> str:
        product = cls._active_product_label(slots)
        if alternatives:
            alt_lines = [
                f"- Alternative: **{item.title}** - \u20A6{item.price:,.0f}"
                for item in alternatives
            ]
            return (
                f"No exact match: I couldn't find **{product}** that satisfies every requested constraint right now.\n"
                "Alternatives (not exact matches):\n"
                + "\n".join(alt_lines)
                + "\nI've logged the exact demand so sellers can respond with closer stock."
            )
        return (
            f"No exact match: I couldn't find **{product}** that satisfies every requested constraint right now. "
            "I've logged the exact demand so sellers can respond when matching stock appears."
        )

    @classmethod
    def _refresh_active_recommendation_context(
        cls,
        *,
        session: ConversationSession,
        prior_slots: Dict[str, Any],
        intent_state: Dict[str, Any],
        message: str,
        rejection: Dict[str, Any],
        turn_type: str,
    ) -> Dict[str, Any]:
        constraint_update = dict(rejection.get('constraint_update') or {})
        acknowledgement = str(rejection.get('acknowledgement') or '').strip()
        if not acknowledgement:
            acknowledgement = "Let me refresh the options inside this search."

        general_refresh = (
            not constraint_update
            or set(constraint_update.keys()) == {'_shown_product_ids'}
        )
        prior_shown_ids = [
            str(product_id)
            for product_id in (prior_slots.get('_shown_product_ids') or [])
        ]
        updated_slots = cls._merge_active_refinement_slots(
            prior_slots,
            constraint_update,
            message,
        )
        updated_slots['_shown_product_ids'] = prior_shown_ids if general_refresh else []

        session.constraint_state = updated_slots
        session.intent_state = cls._compose_turn_intent_state(
            intent_state,
            turn_type=turn_type,
            pending_category_switch=None,
        )
        session.drift_flag = False
        session.save(update_fields=[
            'constraint_state',
            'intent_state',
            'drift_flag',
            'updated_at',
        ])

        try:
            products = cls._find_products(updated_slots)
        except Exception as exc:
            logger.warning("Recommendation refinement refresh failed: %s", exc, exc_info=True)
            return cls._build_turn_response(
                reply=(
                    f"{acknowledgement} "
                    f"I hit a snag refreshing {cls._active_product_label(updated_slots)} options just now. "
                    "Please try again in a moment."
                ),
                source='recommendation_rejection_retry',
                session=session,
                turn_type=turn_type,
                confidence=0.6,
            )

        if general_refresh and prior_shown_ids:
            shown_ids = set(prior_shown_ids)
            # FIX: cast p.id to str for correct comparison against string shown_ids
            products = [product for product in products if str(product.id) not in shown_ids]

        if products:
            new_shown_ids = [
                str(product.id) for product in products
                if str(product.id) not in prior_shown_ids
            ]
            updated_slots['_shown_product_ids'] = (
                prior_shown_ids + new_shown_ids
                if general_refresh
                else new_shown_ids
            )
            session.constraint_state = updated_slots
            session.active_product = products[0]
            session.intent_state = cls._compose_turn_intent_state(
                intent_state,
                turn_type=turn_type,
                turn_outcome=RecommendationTurnClassifier.OUTCOME_RESULTS,
                pending_category_switch=None,
            )
            session.save(update_fields=[
                'constraint_state',
                'active_product',
                'intent_state',
                'updated_at',
            ])

            rejection_type = 'general' if general_refresh else 'constraint'
            if 'condition' in constraint_update:
                rejection_type = 'condition'
            elif (
                'price_max' in constraint_update
                or constraint_update.get('price_intent')
            ):
                rejection_type = 'price'

            return cls._build_turn_response(
                reply=f"{acknowledgement}\n\n{cls._format_results_reply(products, updated_slots)}",
                source='recommendation_rejection_refined',
                session=session,
                turn_type=turn_type,
                turn_outcome=RecommendationTurnClassifier.OUTCOME_RESULTS,
                confidence=0.88,
                metadata=cls._exact_match_metadata(products, updated_slots, extra={
                    'rejection_type': rejection_type,
                    'updated_constraints': list(constraint_update.keys()),
                }),
            )

        cls.log_demand_gap(session, updated_slots)
        alternatives = cls._find_alternatives(updated_slots)
        if general_refresh and prior_shown_ids:
            shown_ids = set(prior_shown_ids)
            # FIX: cast p.id to str
            alternatives = [product for product in alternatives if str(product.id) not in shown_ids]
        if alternatives:
            updated_slots['_shown_product_ids'] = (
                prior_shown_ids + [
                    str(product.id) for product in alternatives
                    if str(product.id) not in prior_shown_ids
                ]
            )
            session.constraint_state = updated_slots

        session.intent_state = cls._compose_turn_intent_state(
            intent_state,
            turn_type=turn_type,
            turn_outcome=RecommendationTurnClassifier.OUTCOME_NO_RESULTS,
            pending_category_switch=None,
        )
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        return cls._build_turn_response(
            reply=cls._format_refinement_no_results_reply(
                acknowledgement=acknowledgement,
                slots=updated_slots,
                alternatives=alternatives,
            ),
            source='recommendation_rejection_no_results',
            session=session,
            turn_type=turn_type,
            turn_outcome=RecommendationTurnClassifier.OUTCOME_NO_RESULTS,
            confidence=0.75,
            metadata=cls._no_exact_match_metadata(
                alternatives,
                updated_slots,
                reason='refinement_ranked_inventory_no_close_match',
                extra={
                    'updated_constraints': list(constraint_update.keys()),
                },
            ),
        )

    @classmethod
    def _prepare_turn_payload(cls, message: str, prior_slots: Dict[str, Any]) -> Dict[str, Any]:
        msg_lower = (message or '').lower().strip()

        try:
            llm_enriched = enrich_slots(message, prior_slots)
            logger.info("LLM raw extraction completed for recommendation flow")
        except Exception as exc:
            logger.warning("LLM raw extraction failed, using empty extraction: %s", exc)
            llm_enriched = {}

        raw_structured_query = build_structured_query(message, llm_enriched, None)
        raw_slots = structured_query_to_slots(raw_structured_query)
        distinct_product_request = cls._is_distinct_product_request(prior_slots, raw_slots)
        structured_query = build_structured_query(
            message,
            llm_enriched,
            {} if distinct_product_request else prior_slots,
        )
        slots = structured_query_to_slots(structured_query)
        if not isinstance(raw_slots, dict):
            logger.warning("raw_slots was not a dict; coercing to empty dict")
            raw_slots = {}
        if not isinstance(slots, dict):
            logger.warning("slots was not a dict; coercing to empty dict")
            slots = {}

        if not distinct_product_request and prior_slots.get('_last_clarification_key'):
            slots['_last_clarification_key'] = str(prior_slots.get('_last_clarification_key') or '').strip()

        last_attr_key = str(prior_slots.get('_last_clarification_key') or '').strip()
        if last_attr_key and message.strip() and not distinct_product_request:
            current_attrs = dict(slots.get('attributes') or {})
            current_attrs[last_attr_key] = {
                'value': message.strip(),
                'match_type': 'text',
                'importance': 'high',
                'source': 'deterministic_parser',
            }
            slots['attributes'] = current_attrs
            slots['_last_clarification_key'] = ''
            slots['price_min'] = prior_slots.get('price_min')
            slots['price_max'] = prior_slots.get('price_max')
            slots['budget_range'] = (
                prior_slots.get('budget_range')
                if isinstance(prior_slots.get('budget_range'), dict)
                else {}
            )
            structured = dict(slots.get('structured_query') or structured_query)
            structured_attrs = dict(structured.get('attributes') or {})
            structured_attrs[last_attr_key] = current_attrs[last_attr_key]
            structured['attributes'] = structured_attrs
            slots['structured_query'] = structured

            raw_slots['attributes'] = {last_attr_key: current_attrs[last_attr_key]}
            raw_slots['price_min'] = prior_slots.get('price_min')
            raw_slots['price_max'] = prior_slots.get('price_max')
            raw_slots['budget_range'] = (
                prior_slots.get('budget_range')
                if isinstance(prior_slots.get('budget_range'), dict)
                else {}
            )

        slots['raw_query'] = message
        mandatory_missing = [
            slot_name for slot_name in ('product_type',)
            if slots.get(slot_name) is None
        ]
        force_signals = [
            'just show me',
            'show me anything',
            'just search',
            'i dont care',
            'whatever',
            'abeg just find',
            'any one',
        ]
        has_force_signal = any(signal in msg_lower for signal in force_signals)
        forced_search = has_force_signal and bool(mandatory_missing)

        # FIX: replaced mojibake characters with correct Unicode
        forced_prefix = (
            "⚠️ Fair warning — I'm searching without all the details, "
            "so I'm basically throwing darts in the dark 🎯 "
            "Results may not be exactly what you need, "
            "but here goes!\n\n"
        ) if forced_search else ""

        location_warning = (
            "\n\n📍 *Tip: You didn't mention a location — "
            "some of these might be so far away it'd take a full moon "
            "spin around the earth to get delivered! 🌍 "
            "Reply with your city to narrow it down.*"
        ) if slots.get('location') is None else ""

        forced_prefix = (
            "Fair warning: I am searching with limited product detail, "
            "so results may be broad.\n\n"
        ) if forced_search else ""
        location_warning = ""

        return {
            'llm_enriched': llm_enriched,
            'raw_slots': raw_slots,
            'slots': slots,
            'forced_search': forced_search,
            'forced_prefix': forced_prefix,
            'location_warning': location_warning,
        }

    @classmethod
    def _evaluate_classified_turn(
        cls,
        *,
        session: ConversationSession,
        message: str,
        prior_slots: Dict[str, Any],
        intent_state: Dict[str, Any],
    ) -> Dict:
        turn_payload = cls._prepare_turn_payload(message, prior_slots)
        raw_slots = turn_payload['raw_slots']
        slots = turn_payload['slots']
        forced_search = turn_payload['forced_search']
        forced_prefix = turn_payload['forced_prefix']
        location_warning = turn_payload['location_warning']

        raw_has_product_intent = cls._has_product_intent(message, raw_slots)
        has_constraint_updates = cls._has_constraint_updates(raw_slots, prior_slots)
        short_follow_up_constraint_turn = cls._is_short_follow_up_constraint_turn(
            message,
            raw_slots,
            prior_slots,
        )
        context_shift = cls._detect_context_shift(
            message=message,
            prior_slots=prior_slots,
            raw_slots=raw_slots,
            slots=slots,
            raw_has_product_intent=raw_has_product_intent,
            has_constraint_updates=has_constraint_updates,
            short_follow_up_constraint_turn=short_follow_up_constraint_turn,
        )
        fresh_slots = cls._sanitize_new_context_slots({**raw_slots, 'raw_query': message})
        if fresh_slots.get('price_min') is not None or fresh_slots.get('price_max') is not None:
            fresh_slots['budget_range'] = {
                'min': fresh_slots.get('price_min'),
                'max': fresh_slots.get('price_max'),
            }
        fresh_slots['product_intent'] = 'purchase'

        if context_shift.action in {'branch', 'reset'}:
            prior_slots = {}
            intent_state = cls._clean_intent_state(
                intent_state,
                clarification_count=0,
                pending_category_switch=None,
                context_shift_action=context_shift.action,
                context_shift_reason=context_shift.reason,
                context_shift_source=context_shift.source,
            )
            slots = fresh_slots or slots
            has_constraint_updates = False
            short_follow_up_constraint_turn = False

        rejection = {
            'is_rejection': False,
            'constraint_update': {},
            'acknowledgement': '',
        }
        if cls._has_prior_product_context(prior_slots):
            rejection = cls._detect_rejection_llm(message, prior_slots)

        turn_decision = RecommendationTurnClassifier.classify(
            message=message,
            prior_slots=prior_slots,
            raw_slots=raw_slots,
            slots=slots,
            raw_has_product_intent=raw_has_product_intent,
            has_constraint_updates=has_constraint_updates,
            short_follow_up_constraint_turn=short_follow_up_constraint_turn,
            rejection_detected=rejection['is_rejection'],
        )
        turn_type = turn_decision.turn_type

        context_data = dict(session.context_data or {})
        context_data['last_structured_query'] = slots.get('structured_query') or {}
        context_data['last_turn_classification'] = turn_type
        context_data['last_context_shift'] = {
            'action': context_shift.action,
            'reason': context_shift.reason,
            'confidence': context_shift.confidence,
            'source': context_shift.source,
        }
        session.context_data = context_data
        session.save(update_fields=['context_data', 'updated_at'])

        explicit_refresh = (
            turn_type == RecommendationTurnClassifier.TURN_REFINEMENT
            and not has_constraint_updates
            and not short_follow_up_constraint_turn
        )
        if (
            turn_type == RecommendationTurnClassifier.TURN_REJECTION
            and rejection['is_rejection']
        ) or explicit_refresh:
            if not rejection['is_rejection']:
                rejection = cls._detect_rejection(message, prior_slots)
            if not rejection['is_rejection']:
                rejection = {
                    'is_rejection': True,
                    'constraint_update': {'_shown_product_ids': []},
                    'acknowledgement': 'Let me try different options inside this search.',
                }
            return cls._refresh_active_recommendation_context(
                session=session,
                prior_slots=prior_slots,
                intent_state=intent_state,
                message=message,
                rejection=rejection,
                turn_type=turn_type,
            )

        if (
            turn_type == RecommendationTurnClassifier.TURN_NEW_QUERY
            and not raw_has_product_intent
            and not short_follow_up_constraint_turn
        ):
            stray_reply = cls._stray_reply(message)
            if stray_reply is not None:
                session.intent_state = cls._compose_turn_intent_state(
                    intent_state,
                    turn_type=turn_type,
                    pending_category_switch=None,
                )
                session.save(update_fields=['intent_state', 'updated_at'])
                return cls._build_turn_response(
                    reply=stray_reply,
                    source='recommendation_stray',
                    session=session,
                    turn_type=turn_type,
                    confidence=0.7,
                    metadata={'intent': 'stray'},
                )

        clarification = None
        llm_decision = None
        conversation_history = session.conversation_history if isinstance(session.conversation_history, list) else []
        clarification_limit_reached = int(intent_state.get('clarification_count', 0) or 0) >= SlotStateMachine.MAX_CLARIFICATIONS
        focused_followup = cls._focused_followup_for_vague_request(slots)
        if focused_followup and not clarification_limit_reached:
            clarification = focused_followup['question']
            llm_decision = {
                'action': 'clarify',
                'question': focused_followup['question'],
                'attribute_key': focused_followup['attribute_key'],
                'reasoning': 'vague_high-variance_product_request',
            }
        elif not forced_search and not clarification_limit_reached:
            try:
                llm_decision = cls.generate_clarification_question(message, slots, conversation_history)
                if llm_decision.get('action') == 'clarify':
                    clarification = llm_decision.get('question')
            except Exception as exc:
                logger.warning(
                    "LLM clarification generation failed; falling back to SlotStateMachine: %s",
                    exc,
                )
                clarification = SlotStateMachine.get_next_clarification(slots, intent_state)

        if clarification:
            slots['_last_clarification_key'] = ''
            if isinstance(llm_decision, dict) and llm_decision.get('action') == 'clarify':
                slots['_last_clarification_key'] = str(
                    llm_decision.get('attribute_key') or ''
                ).strip()

            clarification_count = int(intent_state.get('clarification_count', 0) or 0) + 1
            already_shown = set(str(pid) for pid in (prior_slots.get('_shown_product_ids') or []))
            broad_products = [] if focused_followup else cls._find_products_broad(slots, top_k=3)
            # FIX: cast p.id to str for correct comparison against string set
            broad_products = [
                p for p in broad_products
                if str(p.id) not in already_shown
            ][:3]

            if broad_products:
                slots['_shown_product_ids'] = list(already_shown) + [
                    str(p.id) for p in broad_products  # FIX: cast to str
                ]
                reply_text = cls._format_interleaved_reply(
                    broad_products,
                    slots,
                    clarification,
                )
                reply_source = 'recommendation_interleaved'
                reply_confidence = 0.85
                turn_outcome = RecommendationTurnClassifier.OUTCOME_RESULTS
            elif cls._has_searchable_exact_context(slots):
                cls.log_demand_gap(session, slots)
                alternatives = cls._find_alternatives(slots)
                # FIX: cast p.id to str
                alternatives = [
                    p for p in alternatives
                    if str(p.id) not in already_shown
                ][:3]
                slots['_shown_product_ids'] = list(already_shown) + [
                    str(p.id) for p in alternatives  # FIX: cast to str
                ]
                session.constraint_state = slots
                session.intent_state = cls._compose_turn_intent_state(
                    intent_state,
                    turn_type=turn_type,
                    turn_outcome=RecommendationTurnClassifier.OUTCOME_NO_RESULTS,
                    pending_category_switch=None,
                    clarification_count=clarification_count,
                )
                session.drift_flag = False
                session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])
                return cls._build_turn_response(
                    reply=cls._format_no_exact_match_reply(slots, alternatives),
                    source='recommendation_results_alternatives',
                    session=session,
                    turn_type=turn_type,
                    turn_outcome=RecommendationTurnClassifier.OUTCOME_NO_RESULTS,
                    confidence=0.75,
                    metadata=cls._no_exact_match_metadata(
                        alternatives,
                        slots,
                        reason='clarification_ranked_inventory_no_close_match',
                    ),
                )
            else:
                slots['_shown_product_ids'] = list(already_shown)
                reply_text = clarification
                reply_source = 'recommendation_clarification'
                reply_confidence = 0.85
                turn_outcome = None

            session.constraint_state = slots
            session.intent_state = cls._compose_turn_intent_state(
                intent_state,
                turn_type=turn_type,
                turn_outcome=turn_outcome,
                pending_category_switch=None,
                clarification_count=clarification_count,
            )
            session.drift_flag = False
            session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])
            return cls._build_turn_response(
                reply=reply_text,
                source=reply_source,
                session=session,
                turn_type=turn_type,
                turn_outcome=turn_outcome,
                confidence=reply_confidence,
                metadata=cls._product_suggestion_metadata(broad_products, slots) if broad_products else None,
            )

        slots['_last_clarification_key'] = str(slots.get('_last_clarification_key') or '').strip()
        already_shown = list(str(pid) for pid in (prior_slots.get('_shown_product_ids') or []))
        if already_shown:
            slots['_shown_product_ids'] = list(already_shown)

        session.constraint_state = slots
        session.intent_state = cls._compose_turn_intent_state(
            intent_state,
            turn_type=turn_type,
            pending_category_switch=None,
        )
        session.drift_flag = False
        session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])

        products = cls._find_products(slots)
        if already_shown:
            shown_ids = set(already_shown)
            # FIX: cast p.id to str
            products = [p for p in products if str(p.id) not in shown_ids]

        if not products:
            cls.log_demand_gap(session, slots)
            alternatives = cls._find_alternatives(slots)
            if already_shown:
                shown_ids = set(already_shown)
                # FIX: cast p.id to str
                alternatives = [p for p in alternatives if str(p.id) not in shown_ids]
            if alternatives:
                slots['_shown_product_ids'] = already_shown + [
                    str(p.id) for p in alternatives  # FIX: cast to str
                    if str(p.id) not in already_shown
                ]
                session.constraint_state = slots

            session.intent_state = cls._compose_turn_intent_state(
                intent_state,
                turn_type=turn_type,
                turn_outcome=RecommendationTurnClassifier.OUTCOME_NO_RESULTS,
                pending_category_switch=None,
            )
            session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

            results_reply = cls._format_no_exact_match_reply(slots, alternatives)
            final_reply = forced_prefix + results_reply + location_warning
            return cls._build_turn_response(
                reply=final_reply,
                source='recommendation_results_alternatives',
                session=session,
                turn_type=turn_type,
                turn_outcome=RecommendationTurnClassifier.OUTCOME_NO_RESULTS,
                confidence=0.75,
                metadata=cls._no_exact_match_metadata(
                    alternatives,
                    slots,
                    reason='ranked_inventory_no_close_match',
                    extra={
                        'forced_search': forced_search,
                        'location_missing': slots.get('location') is None,
                    },
                ),
            )

        slots['_shown_product_ids'] = already_shown + [
            str(p.id) for p in products  # FIX: cast to str
            if str(p.id) not in already_shown
        ]
        session.constraint_state = slots
        session.active_product = products[0]
        session.intent_state = cls._compose_turn_intent_state(
            intent_state,
            turn_type=turn_type,
            turn_outcome=RecommendationTurnClassifier.OUTCOME_RESULTS,
            pending_category_switch=None,
        )
        session.save(update_fields=['constraint_state', 'active_product', 'intent_state', 'updated_at'])
        results_reply = cls._format_results_reply(products, slots)
        final_reply = forced_prefix + results_reply + location_warning
        return cls._build_turn_response(
            reply=final_reply,
            source='recommendation_results',
            session=session,
            turn_type=turn_type,
            turn_outcome=RecommendationTurnClassifier.OUTCOME_RESULTS,
            confidence=0.9,
            metadata=cls._exact_match_metadata(
                products,
                slots,
                extra={
                    'forced_search': forced_search,
                    'location_missing': slots.get('location') is None,
                },
            ),
        )

    @classmethod
    def _detect_rejection(cls, message: str, prior_slots: Dict) -> Dict[str, Any]:
        """
        Rule-based rejection detection.
        Fallback for when LLM is unavailable or the call fails.
        Called by _detect_rejection_llm() automatically.
        """
        lower = (message or '').lower().strip()
        result = {
            'is_rejection': False,
            'constraint_update': {},
            'acknowledgement': '',
        }

        price_too_high = any(token in lower for token in [
            'too expensive', 'too costly', 'costly', 'cheaper', 'less expensive',
            'lower price', 'lower budget', 'reduce price', 'more affordable',
            'budget option', 'something cheaper', 'cheaper option', 'cut the price',
            'too much', 'way too high', 'out of my budget',
        ])
        price_too_low = any(token in lower for token in [
            'too cheap', 'low quality', 'something better', 'higher quality',
            'premium option', 'more expensive', 'upgrade', 'better quality',
        ])
        wants_new = any(token in lower for token in [
            'brand new', 'only new', 'new only', 'not used', 'not fairly used', 'fresh',
        ])
        wants_used = any(token in lower for token in [
            'fairly used', 'second hand', 'tokunbo', 'used is fine', 'used okay', 'pre-owned',
        ])
        general_rejection = any(token in lower for token in [
            'not what i wanted', 'not what i need', 'not this one', 'not this',
            'not this item', 'wrong', "that's not it", 'not right',
            'show me something else', 'different', 'other options',
            'none of these', 'not interested', 'try again',
        ])

        if price_too_high:
            result['is_rejection'] = True
            current_max = prior_slots.get('price_max')
            if current_max is not None:
                try:
                    new_max = int(float(current_max) * 0.70)
                    result['constraint_update']['price_max'] = new_max
                    result['acknowledgement'] = f"Got it - looking for something under \u20A6{new_max:,} now."
                except (TypeError, ValueError):
                    result['constraint_update']['price_intent'] = 'cheap'
                    result['acknowledgement'] = "Understood - let me find more affordable options."
            else:
                result['constraint_update']['price_intent'] = 'cheap'
                result['acknowledgement'] = "Got it - looking for more affordable options."
        elif price_too_low:
            result['is_rejection'] = True
            current_max = prior_slots.get('price_max')
            if current_max is not None:
                try:
                    new_max = int(float(current_max) * 1.50)
                    result['constraint_update']['price_max'] = new_max
                    result['acknowledgement'] = "Understood - let me show you better quality options."
                except (TypeError, ValueError):
                    result['constraint_update']['price_intent'] = 'premium'
                    result['acknowledgement'] = "Got it - looking for premium options."
            else:
                result['constraint_update']['price_intent'] = 'premium'
                result['acknowledgement'] = "Let me find higher quality options for you."
        elif wants_new:
            result['is_rejection'] = True
            result['constraint_update']['condition'] = 'new'
            result['acknowledgement'] = "Sure - showing brand new listings only."
        elif wants_used:
            result['is_rejection'] = True
            result['constraint_update']['condition'] = 'fair'
            result['acknowledgement'] = "Got it - including fairly used options."
        elif general_rejection:
            result['is_rejection'] = True
            result['constraint_update']['_shown_product_ids'] = []
            result['acknowledgement'] = "Let me try different options for you."

        return result

    @classmethod
    def _detect_rejection_llm(cls, message: str, prior_slots: Dict) -> Dict[str, Any]:
        """
        Use the local LLM to detect rejection intent and infer which
        constraint should be updated before re-running search.

        Returns the same shape as _detect_rejection() and falls back
        to that rule-based method on any failure.
        """
        try:
            adapter = LocalModelAdapter.get_instance()
            if not adapter.is_available():
                return cls._detect_rejection(message, prior_slots)

            product = (
                prior_slots.get('product_type')
                or prior_slots.get('category')
                or 'product'
            )
            current_price_max = prior_slots.get('price_max')
            current_condition = str(prior_slots.get('condition') or '').strip()
            price_text = 'not set'
            if current_price_max is not None:
                try:
                    price_text = f"\u20A6{int(float(current_price_max)):,}"
                except (TypeError, ValueError):
                    price_text = str(current_price_max)

            prompt = f"""A user is shopping for {product} on a Nigerian marketplace called Zunto.

Current search constraints:
- Max price: {price_text}
- Condition: {current_condition or 'not set'}

The user just said: "{message}"

Determine if this is a rejection of the current results and what they want changed.
The user may be speaking English, Nigerian Pidgin, or a mix.

Common rejection patterns include but are not limited to:
- Price too high: "too expensive", "e don cost", "abeg find cheaper", "the price steep", "out of my budget", "too much"
- Price too low / wants better: "too cheap", "want something better", "premium", "higher quality", "upgrade"
- Wrong condition: "I want new", "brand new only", "fairly used is fine"
- General rejection: "not what I want", "show something else", "try again", "this no be am"

Respond ONLY with valid JSON, no other text:
{{
  "is_rejection": true or false,
  "rejection_type": "price_high" | "price_low" | "condition_new" | "condition_used" | "general" | "none",
  "acknowledgement": "friendly 1-sentence response in same tone as user",
  "reasoning": "brief internal note"
}}

If not a rejection, return:
{{"is_rejection": false, "rejection_type": "none", "acknowledgement": "", "reasoning": "..."}}
"""

            llm_output = adapter.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a rejection intent classifier for a "
                    "Nigerian marketplace AI. Respond only with valid JSON."
                ),
                max_tokens=120,
                temperature=0.1,
            )
            if isinstance(llm_output, dict) and llm_output.get('error'):
                raise RuntimeError(str(llm_output.get('error')))

            raw = (
                llm_output.get('response', '')
                if isinstance(llm_output, dict)
                else str(llm_output)
            ).strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
                raw = re.sub(r'\s*```$', '', raw)
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                raw = match.group(0)

            parsed = json.loads(raw)
            is_rejection = parsed.get('is_rejection')
            if isinstance(is_rejection, str):
                is_rejection = is_rejection.strip().lower() == 'true'
            if not is_rejection:
                return {
                    'is_rejection': False,
                    'constraint_update': {},
                    'acknowledgement': '',
                }

            rejection_type = str(parsed.get('rejection_type') or 'general').strip().lower()
            acknowledgement = str(parsed.get('acknowledgement') or '').strip()
            constraint_update: Dict[str, Any] = {}

            if rejection_type == 'price_high':
                current_max = prior_slots.get('price_max')
                if current_max is not None:
                    try:
                        new_max = int(float(current_max) * 0.70)
                        constraint_update['price_max'] = new_max
                        if not acknowledgement:
                            acknowledgement = f"Got it - looking under \u20A6{new_max:,} now."
                    except (TypeError, ValueError):
                        constraint_update['price_intent'] = 'cheap'
                else:
                    constraint_update['price_intent'] = 'cheap'
            elif rejection_type == 'price_low':
                current_max = prior_slots.get('price_max')
                if current_max is not None:
                    try:
                        new_max = int(float(current_max) * 1.50)
                        constraint_update['price_max'] = new_max
                        if not acknowledgement:
                            acknowledgement = "Let me find better quality options."
                    except (TypeError, ValueError):
                        constraint_update['price_intent'] = 'premium'
                else:
                    constraint_update['price_intent'] = 'premium'
            elif rejection_type == 'condition_new':
                constraint_update['condition'] = 'new'
                if not acknowledgement:
                    acknowledgement = "Showing brand new only."
            elif rejection_type == 'condition_used':
                constraint_update['condition'] = 'fair'
                if not acknowledgement:
                    acknowledgement = "Including fairly used options."
            else:
                constraint_update['_shown_product_ids'] = []
                if not acknowledgement:
                    acknowledgement = "Let me find different options for you."

            return {
                'is_rejection': True,
                'constraint_update': constraint_update,
                'acknowledgement': acknowledgement,
            }
        except Exception as exc:
            logger.warning(
                "LLM rejection detection failed, falling back to rules: %s",
                exc,
            )
            return cls._detect_rejection(message, prior_slots)

    @staticmethod
    def _is_decline_phrase(message: str) -> bool:
        raw = (message or '').lower().strip()
        if SlotStateMachine.is_decline(raw):
            return True
        return bool(re.match(r'^(no|nope|nah|wait|hold on)\b', raw))

    @staticmethod
    def _recent_conversation_turns(conversation_history: Any, limit: int = 3) -> List[Dict[str, str]]:
        if not isinstance(conversation_history, list):
            return []

        turns: List[Dict[str, str]] = []
        for entry in conversation_history[-limit:]:
            if not isinstance(entry, dict):
                continue
            role = str(entry.get('role') or '').strip().lower()
            content = str(entry.get('content') or '').strip()
            if not role or not content:
                continue
            turns.append({'role': role, 'content': content})
        return turns

    @classmethod
    def _infer_product_type_hint(cls, slots: Dict) -> str:
        product_type = (
            str(slots.get('product_type') or slots.get('category') or '')
            .lower()
            .strip()
        )
        return product_type

    @classmethod
    def _get_attribute_profile_for_llm(cls, slots: Dict) -> str:
        """
        Query real verified product attributes from DB to build
        a context-rich profile for the LLM clarification decision.
        Only uses attributes from admin-verified products.
        """
        product_type = cls._infer_product_type_hint(slots)

        if not product_type:
            return "No product type known yet. Ask what product they want."

        try:
            from market.models import Product

            base_qs = Product.objects.filter(status='active', quantity__gt=0)
            total_count = base_qs.count()

            inventory_sample = list(
                base_qs.values('attributes', 'attributes_verified', 'brand', 'condition', 'price')[:300]
            )
            verified_products = [
                product for product in inventory_sample
                if product.get('attributes_verified') and product.get('attributes')
            ][:150]
            verified_count = len(verified_products)

            attribute_map: Dict[str, set] = {}
            brands = set()
            conditions = set()
            prices = []

            for product in verified_products:
                attrs = product.get('attributes') or {}
                if not isinstance(attrs, dict):
                    continue
                for key, value in attrs.items():
                    attr_key = str(key).strip()
                    if not attr_key:
                        continue
                    attribute_map.setdefault(attr_key, set())
                    if isinstance(value, list):
                        for item in value:
                            item_text = str(item).strip()
                            if item_text:
                                attribute_map[attr_key].add(item_text)
                    else:
                        value_text = str(value).strip()
                        if value_text:
                            attribute_map[attr_key].add(value_text)
                if product.get('brand'):
                    brands.add(str(product['brand']).strip())
                if product.get('condition'):
                    conditions.add(str(product['condition']).strip())
                if product.get('price') is not None:
                    prices.append(float(product['price']))

            profile_lines = [
                f"Requested product text: {product_type}",
                f"Total active listings: {total_count}",
                f"Listings with verified attributes: {verified_count}",
            ]

            if brands:
                profile_lines.append(f"Available brands: {', '.join(sorted(brands)[:8])}")
            if conditions:
                profile_lines.append(f"Available conditions: {', '.join(sorted(conditions))}")
            if prices:
                profile_lines.append(f"Price range in DB: N{min(prices):,.0f} - N{max(prices):,.0f}")

            if attribute_map:
                profile_lines.append("Common attributes in verified listings:")
                for attr_key, attr_values in sorted(attribute_map.items()):
                    if not attr_values:
                        continue
                    sample_values = ', '.join(sorted(attr_values)[:6])
                    profile_lines.append(
                        f"  - {attr_key} ({len(attr_values)} distinct values): {sample_values}"
                    )
            else:
                profile_lines.append("No verified structured attributes are available yet for this product type.")

            return '\n'.join(profile_lines)

        except Exception as exc:
            logger.warning("Attribute profile query failed: %s", exc)
            return f"Product type: {product_type}. Ask about budget and condition."

    @staticmethod
    def _parse_clarification_json(raw_response: Any) -> Dict[str, Any]:
        if isinstance(raw_response, dict) and 'action' in raw_response:
            payload = raw_response
        else:
            text = str(raw_response or '').strip()
            if not text:
                raise ValueError("LLM clarification response was empty")
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
                text = re.sub(r'\s*```$', '', text)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
            payload = json.loads(text)

        if not isinstance(payload, dict):
            raise ValueError("LLM clarification response was not a JSON object")

        action = str(payload.get('action') or '').strip().lower()
        if action not in {'search', 'clarify'}:
            raise ValueError(f"Unsupported clarification action: {action!r}")

        normalized = {
            'action': action,
            'reasoning': str(payload.get('reasoning') or '').strip(),
        }
        if action == 'clarify':
            question = str(payload.get('question') or '').strip()
            attribute_key = str(payload.get('attribute_key') or '').strip()
            if not question:
                raise ValueError("Clarification action missing question")
            if not attribute_key:
                raise ValueError("Clarification action missing attribute_key")
            normalized['question'] = question
            normalized['attribute_key'] = attribute_key
        return normalized

    @classmethod
    def generate_clarification_question(
        cls,
        message: str,
        slots: Dict,
        conversation_history: Any,
    ) -> Dict[str, Any]:
        adapter = LocalModelAdapter.get_instance()
        if not adapter.is_available():
            raise RuntimeError("Local model adapter unavailable for clarification generation")

        product_type = cls._infer_product_type_hint(slots) or 'unknown'
        attribute_profile = cls._get_attribute_profile_for_llm(slots)
        recent_history = cls._recent_conversation_turns(conversation_history, limit=3)
        prompt = """
You are Gigi, a personal shopping assistant for Zunto, a Nigerian marketplace.

A user is looking for a product. Based on their message and what you already know,
decide whether you have enough information to search, or whether ONE clarifying
question would meaningfully improve the results.

Known information: {slots}
User's message: {message}
Recent conversation: {history}

REAL INVENTORY CONTEXT:
{attribute_profile}

Based on this REAL data from the Zunto database, decide what ONE
question - if any - would help narrow down to the best match.

Only ask about attributes that:
1. Actually exist in the verified listings above
2. Have multiple distinct values so the answer changes results
3. Are not already known from the conversation

If the user's request already matches the available attributes
closely enough to return good results, choose action: "search".

Examples of good questions based on real inventory:
- If one verified attribute has multiple values, ask which value they prefer.
- If several numeric capacities exist, ask which capacity range they want.
- If multiple delivery or meetup areas exist in inventory, ask which area they prefer.

Never ask about an attribute that doesn't appear in the inventory data.

Inference rules:
- Words like "expensive", "premium", or "high-end" imply a high budget, so do not ask for price
- Words like "affordable", "cheap", or "budget" imply a lower price range, so do not ask for price
- "Affordable", "cheap", or "budget" can also imply fair or good condition for second-hand-friendly categories
- Condition phrases like "brand new", "fairly used", "second hand", or "Tokunbo" should be respected without asking again
- If location is already mentioned, do not ask for location again
- If brand is already mentioned, do not ask for brand again
- Never ask for information that is already present in the message, the known slots, or the recent conversation
- Default to search when the request already has enough detail to return broadly relevant results
- If the user already gave a product type plus two meaningful constraints, prefer search over another question
- If no product type is known yet, ask what product they want using attribute_key "product_type"
- Ask only ONE question, and only if that question would materially improve the matches

If you have enough to do a useful search, return:
{{"action": "search", "reasoning": "..."}}

If ONE question would significantly improve results, return:
{{"action": "clarify", "question": "...", "attribute_key": "...", "reasoning": "..."}}

The question must sound natural and conversational, not like a form field.
Example good question: "Do you prefer one of the available capacity options?"
Example bad question: "What model generation do you require?"
Decision guidance:
- Prefer search when the structured query already has a product type plus useful ranking signals.
- Ask about an attribute only when real inventory shows multiple meaningful values.
- Do not ask about budget when the query already expresses budget or premium intent.

Respond ONLY with valid JSON, no other text.
""".format(
            slots=json.dumps(slots or {}, ensure_ascii=True, sort_keys=True),
            message=message or '',
            history=json.dumps(recent_history, ensure_ascii=True),
            product_type=product_type,
            attribute_profile=attribute_profile,
        )

        llm_output = adapter.generate(
            prompt=prompt,
            system_prompt="You are Gigi. Reply with strict JSON only.",
            max_tokens=180,
            temperature=0.1,
        )
        if not isinstance(llm_output, dict):
            raise ValueError("Clarification generation returned a non-dict result")
        if llm_output.get('error'):
            raise RuntimeError(str(llm_output.get('error')))

        parsed = cls._parse_clarification_json(llm_output.get('response'))
        logger.info(
            "LLM clarification decision resolved action=%s profile=%s",
            parsed.get('action'),
            product_type,
        )
        return parsed

    @classmethod
    def _safe_number(cls, value):
        if value in (None, ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalized_tokens(value: Any) -> List[str]:
        tokens = re.findall(r"[a-z0-9]+", str(value or "").lower())
        normalized = []
        for token in tokens:
            if len(token) > 3 and token.endswith('s'):
                token = token[:-1]
            if token:
                normalized.append(token)
        return normalized

    @classmethod
    def _text_contains_constraint(cls, text: str, value: Any, *, require_all: bool = True) -> bool:
        wanted = cls._normalized_tokens(value)
        if not wanted:
            return True
        text_tokens = set(cls._normalized_tokens(text))
        if not text_tokens:
            return False
        if require_all:
            return all(token in text_tokens for token in wanted)
        return any(token in text_tokens for token in wanted)

    @classmethod
    def _product_type_matches(cls, product, product_type: Any) -> bool:
        product_type_text = str(product_type or '').strip()
        if not product_type_text:
            return True
        search_text = product_search_text(product)
        wanted_tokens = cls._normalized_tokens(product_type_text)
        if not wanted_tokens:
            return True

        pattern = r"(^|[^a-z0-9])" + r"[^a-z0-9]+".join(
            re.escape(token) for token in wanted_tokens
        ) + r"s?([^a-z0-9]|$)"
        if re.search(pattern, search_text.lower()):
            return True

        return cls._text_contains_constraint(search_text, product_type_text, require_all=True)

    @classmethod
    def _location_matches(cls, product, wanted_location: Any) -> bool:
        wanted = str(wanted_location or '').strip()
        if not wanted:
            return True
        location = getattr(product, 'location', None)
        if location is None:
            return False
        location_text = ' '.join(
            str(part or '')
            for part in (
                getattr(location, 'area', ''),
                getattr(location, 'city', ''),
                getattr(location, 'state', ''),
            )
        )
        return cls._text_contains_constraint(location_text, wanted, require_all=True)

    @classmethod
    def _attribute_matches(cls, product, key: str, attribute: Any) -> bool:
        if key in {'misc', 'other', 'unknown'}:
            return True
        value = attribute.get('value') if isinstance(attribute, dict) else attribute
        if value in (None, '', {}, []):
            return True

        search_text = product_search_text(product)
        match_type = str(attribute.get('match_type') if isinstance(attribute, dict) else '').lower()
        if match_type in {'numeric', 'range'}:
            return cls._text_contains_constraint(search_text, value, require_all=False)
        return cls._text_contains_constraint(search_text, value, require_all=True)

    @classmethod
    def _product_satisfies_hard_constraints(cls, product, slots: Dict[str, Any]) -> bool:
        if str(getattr(product, 'status', '') or '').lower() != 'active':
            return False
        if int(getattr(product, 'quantity', 0) or 0) <= 0:
            return False

        price = cls._safe_number(getattr(product, 'price', None))
        price_min = cls._safe_number(slots.get('price_min'))
        price_max = cls._safe_number(slots.get('price_max'))
        if price is None:
            return False
        if price_min is not None and price < price_min:
            return False
        if price_max is not None and price > price_max:
            return False

        product_type = slots.get('product_type') or slots.get('category')
        if product_type and not cls._product_type_matches(product, product_type):
            return False

        brand = slots.get('brand')
        if brand and not cls._text_contains_constraint(
            f"{getattr(product, 'brand', '')} {getattr(product, 'title', '')}",
            brand,
            require_all=True,
        ):
            return False

        condition = str(slots.get('condition') or '').strip().lower()
        if condition and condition not in {'any', 'unknown'}:
            product_condition = str(getattr(product, 'condition', '') or '').lower()
            if condition == 'used':
                if product_condition not in {'like_new', 'good', 'fair', 'poor', 'used'}:
                    return False
            elif condition != product_condition:
                return False

        if slots.get('location') and not cls._location_matches(product, slots.get('location')):
            return False

        if slots.get('color') and not cls._attribute_matches(product, 'color', slots.get('color')):
            return False

        attributes = slots.get('attributes') or {}
        if isinstance(attributes, dict):
            for key, attribute in attributes.items():
                if key == 'color' and slots.get('color'):
                    continue
                if not cls._attribute_matches(product, str(key), attribute):
                    return False

        return True

    @classmethod
    def _apply_database_hard_filters(cls, queryset, slots: Dict[str, Any]):
        price_min = cls._safe_number(slots.get('price_min'))
        price_max = cls._safe_number(slots.get('price_max'))
        if price_min is not None:
            queryset = queryset.filter(price__gte=price_min)
        if price_max is not None:
            queryset = queryset.filter(price__lte=price_max)

        location = str(slots.get('location') or '').strip()
        if location:
            queryset = queryset.filter(
                Q(location__area__icontains=location)
                | Q(location__city__icontains=location)
                | Q(location__state__icontains=location)
            )

        product_type = str(slots.get('product_type') or slots.get('category') or '').strip()
        if product_type:
            queryset = cls._apply_product_family_filter(queryset, product_type)

        brand = str(slots.get('brand') or '').strip()
        if brand:
            queryset = queryset.filter(Q(brand__icontains=brand) | Q(title__icontains=brand))

        condition = str(slots.get('condition') or '').strip().lower()
        if condition and condition not in {'any', 'unknown'}:
            if condition == 'used':
                queryset = queryset.filter(condition__in=['like_new', 'good', 'fair', 'poor', 'used'])
            else:
                queryset = queryset.filter(condition__iexact=condition)

        return queryset

    @staticmethod
    def _apply_product_family_filter(queryset, product_type: str):
        model = getattr(queryset, 'model', None)
        meta = getattr(model, '_meta', None)
        if meta is None:
            return queryset.filter(product_family__icontains=product_type)

        try:
            field = meta.get_field('product_family')
        except Exception:
            return queryset.filter(product_family__icontains=product_type)

        if not getattr(field, 'is_relation', False):
            return queryset.filter(product_family__icontains=product_type)

        related_meta = getattr(getattr(field, 'related_model', None), '_meta', None)
        product_family_query = Q()
        for related_field in ('name', 'title', 'label', 'slug'):
            try:
                related_meta.get_field(related_field)
            except Exception:
                continue
            product_family_query |= Q(**{f'product_family__{related_field}__icontains': product_type})

        if not product_family_query:
            return queryset.filter(product_family__icontains=product_type)
        return queryset.filter(product_family_query)

    @staticmethod
    def _merge_hard_filter_slots(extracted_slots: Dict[str, Any], ranking_slots: Dict[str, Any]) -> Dict[str, Any]:
        hard_filter_slots = dict(extracted_slots or {})
        for key, value in (ranking_slots or {}).items():
            if value not in (None, '', [], {}):
                hard_filter_slots[key] = value
        return hard_filter_slots

    @classmethod
    def _filter_hard_constraint_candidates(cls, products, slots: Dict[str, Any]):
        return [
            product
            for product in products
            if cls._product_satisfies_hard_constraints(product, slots)
        ]

    @classmethod
    def _build_semantic_queryset(cls, slots: Dict, base_queryset=None):
        from market.models import Product

        base_qs = base_queryset if base_queryset is not None else Product.objects.all()
        return base_qs.filter(status='active', quantity__gt=0)

    @classmethod
    def _find_products(cls, slots: Dict, top_k: int = 5, base_queryset=None):
        structured_query = (slots or {}).get('structured_query')
        if not isinstance(structured_query, dict):
            structured_query = build_structured_query(
                str((slots or {}).get('raw_query') or ''),
                {},
                slots or {},
            )
        ranking_slots = structured_query_to_slots(structured_query)
        hard_filter_slots = cls._merge_hard_filter_slots(slots or {}, ranking_slots)

        qs = cls._apply_database_hard_filters(
            cls._build_semantic_queryset(hard_filter_slots, base_queryset=base_queryset),
            hard_filter_slots,
        )
        query = build_retrieval_query(structured_query)
        candidate_limit = int(getattr(settings, 'PRODUCT_RECOMMENDER_CANDIDATE_LIMIT', 1000) or 1000)

        semantic_results = search_similar_products(
            query,
            qs,
            candidate_limit=candidate_limit,
            top_k=max(80, min(candidate_limit, 1000)),
        ) if query else []
        semantic_scores = {pid: float(score) for pid, score in semantic_results}

        candidate_ids = [product_id for product_id, _score in semantic_results]
        candidates_qs = qs.select_related('category', 'location', 'seller', 'product_family')
        if candidate_ids:
            semantic_id_set = {str(product_id) for product_id in candidate_ids}
            candidates = list(candidates_qs.filter(id__in=candidate_ids))
            missing_limit = max(0, min(candidate_limit, top_k * 20) - len(candidates))
            if missing_limit:
                candidates.extend(
                    list(
                        candidates_qs.exclude(id__in=semantic_id_set)
                        .order_by('-is_verified_product', '-views_count', '-favorites_count', '-created_at')[:missing_limit]
                    )
                )
        else:
            candidates = list(
                candidates_qs.order_by('-is_verified_product', '-views_count', '-favorites_count', '-created_at')[:candidate_limit]
            )

        candidates = cls._filter_hard_constraint_candidates(candidates, hard_filter_slots)
        if len(candidates) < top_k:
            seen_ids = {str(getattr(product, 'id', '')) for product in candidates}
            fallback_pool = list(
                candidates_qs.exclude(id__in=seen_ids)
                .order_by('-is_verified_product', '-views_count', '-favorites_count', '-created_at')[:candidate_limit]
            )
            candidates.extend(
                product
                for product in cls._filter_hard_constraint_candidates(fallback_pool, hard_filter_slots)
                if str(getattr(product, 'id', '')) not in seen_ids
            )

        ranked = rank_products_hybrid(
            candidates,
            slots=ranking_slots,
            semantic_scores=semantic_scores,
        )
        return ranked[:top_k]

    @classmethod
    def _find_products_broad(cls, slots: Dict, top_k: int = 3, base_queryset=None):
        try:
            return cls._find_products(slots, top_k=top_k, base_queryset=base_queryset)
        except Exception as exc:
            logger.warning("_find_products_broad failed: %s", exc)
            return []

    @classmethod
    def _find_alternatives(cls, slots: Dict, top_k: int = 3, base_queryset=None):
        alternative_price_intent = slots.get('price_intent')
        if alternative_price_intent != 'premium' and slots.get('price_max') is not None:
            alternative_price_intent = 'cheap'

        relaxed = {
            **slots,
            'price_min': None,
            'price_max': None,
            'price_intent': alternative_price_intent,
            'location': None,
            'condition': None,
            'attributes': {},
        }
        relaxed.pop('structured_query', None)
        return cls._find_products(relaxed, top_k=top_k, base_queryset=base_queryset)

    @staticmethod
    def _format_results_reply(products, slots: Dict) -> str:
        product = slots.get('product_type') or slots.get('category') or 'products'
        lines = [f"🔥 Here are top {len(products)} {product} options I found:"]
        medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
        for idx, p in enumerate(products):
            location = ''
            if getattr(p, 'location_id', None) and p.location:
                location = p.location.city or p.location.state or ''
            loc_text = f" · 📍 {location}" if location else ''
            lines.append(f"{medals[idx] if idx < len(medals) else f'{idx + 1}.'} **{p.title}** · ₦{p.price:,.0f}{loc_text}")
        lines.append("Want me to narrow this by brand, budget, condition, or location?")
        return '\n'.join(lines)

    @staticmethod
    def _format_interleaved_reply(
        products,
        slots: Dict,
        clarification_question: str,
    ) -> str:
        product_label = (
            slots.get('product_type')
            or slots.get('category')
            or 'products'
        )
        medals = ['🥇', '🥈', '🥉']
        lines = [f"Here are some **{product_label}** options to start:"]
        for idx, p in enumerate(products):
            location = ''
            if getattr(p, 'location_id', None) and p.location:
                location = p.location.city or p.location.state or ''
            loc_text = f" · 📍 {location}" if location else ''
            medal = medals[idx] if idx < len(medals) else f"{idx + 1}."
            lines.append(
                f"{medal} **{p.title}** · ₦{p.price:,.0f}{loc_text}"
            )
        lines.append('')
        lines.append(clarification_question)
        return '\n'.join(lines)

    @classmethod
    def log_demand_gap(cls, session: ConversationSession, constraints: Dict) -> None:
        payload = {
            'category': constraints.get('category') or constraints.get('product_type') or '',
            'location': constraints.get('location') or '',
            'min_price': constraints.get('price_min'),
            'max_price': constraints.get('price_max'),
            'condition': constraints.get('condition'),
            'brand': constraints.get('brand'),
            'color': constraints.get('color'),
            'use_case': constraints.get('use_case'),
            'product_type': constraints.get('product_type'),
        }
        payload = {k: v for k, v in payload.items() if v not in (None, '', {})}

        log_demand_gap(
            raw_query=str(constraints.get('raw_query') or ''),
            structured_filters=payload,
            user=session.user,
            source='homepage_reco',
        )

    @classmethod
    def evaluate_recommendation_message(cls, session: ConversationSession, message: str) -> Dict:
        cls.initialize_context(session)

        prior_slots = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        intent_state = session.intent_state if isinstance(session.intent_state, dict) else {}
        intent_state = cls._clean_intent_state(intent_state)
        if not isinstance(session.context_data, dict):
            session.context_data = {}

        context_data = dict(session.context_data or {})
        stale_keys = {'pending_memory_resume', 'memory_greeting_sent'}
        if any(key in context_data for key in stale_keys) or intent_state.get('pending_category_switch'):
            for key in stale_keys:
                context_data.pop(key, None)
            intent_state = cls._clean_intent_state(intent_state, pending_category_switch=None)
            session.context_data = context_data
            session.intent_state = intent_state
            session.save(update_fields=['context_data', 'intent_state', 'updated_at'])

        prior_slots = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        intent_state = session.intent_state if isinstance(session.intent_state, dict) else {}
        intent_state = cls._clean_intent_state(intent_state)
        return cls._evaluate_classified_turn(
            session=session,
            message=message,
            prior_slots=prior_slots,
            intent_state=intent_state,
        )

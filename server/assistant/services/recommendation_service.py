import logging
import re
import uuid
from typing import Dict

from django.db import transaction
from django.db.models import Case, ExpressionWrapper, F, FloatField, Q, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from assistant.models import ConversationSession
from assistant.processors.local_model import LocalModelAdapter
from assistant.services.demand_gap_service import log_demand_gap
from assistant.services.llm_slot_enricher import enrich_slots
from assistant.services.slot_extractor import SlotExtractor, SlotStateMachine
from market.search.embeddings import search_similar_products

logger = logging.getLogger(__name__)


class RecommendationService:
    """Conversational FAISS-backed product recommender for homepage_reco."""

    SWITCH_CONFIRM_TOKENS = {'yes', 'y', 'confirm', 'switch', 'go ahead', 'sure', 'okay', 'ok'}
    UPDATE_SLOT_KEYS = ('price_min', 'price_max', 'condition', 'location', 'brand', 'color', 'use_case')

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
            return "😅 I’m here to help with product recommendations only. For support issues, please use the AI inbox."

        greetings = {'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola'}
        if lower.strip() in greetings:
            return "👋 Hey! I’m Gigi, your shopping assistant. What product are you looking for today?"

        if any(t in lower for t in ['😂', 'haha', 'lol', 'joke']):
            return "😄 Haha! Now let’s find something great for you — what are you shopping for?"

        return "🛍️ I can help you find products fast. Tell me what you want, e.g. 'Samsung phone under ₦200k in Lagos'."

    @classmethod
    def _stray_reply(cls, message: str) -> str:
        lower = (message or '').lower().strip()

        greetings = {'hi', 'hey', 'hello', 'yo', 'sup', 'howdy', 'hiya', 'hola'}
        if lower in greetings:
            return "👋 Hey! I’m Gigi, your shopping assistant. Tell me what product you’re hunting for."

        support_keywords = {'refund', 'dispute', 'complaint', 'return', 'track', 'order', 'delivery', 'payment', 'scam', 'fraud'}
        if any(k in lower for k in support_keywords):
            return "I can handle product recommendations only here. Please use the AI inbox for support issues."

        nonsense_tokens = {'asdf', 'qwerty', 'zxczxc', '123123', '???'}
        if lower in nonsense_tokens:
            return "😅 I didn’t catch that one. Tell me the product you want and I’ll jump in."

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
            return "😄 I’m in shopping mode — tell me what product you want and I’ll find options."
        if label == 'NONSENSE':
            return "🤖 My Naija brain buffer just overflowed 😅 — tell me what item you want to buy."

        return cls._stray_reply_keywords(message)

    @classmethod
    def _has_prior_product_context(cls, slots: Dict) -> bool:
        return bool(slots.get('product_type') or slots.get('category'))

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
    def _is_decline_phrase(message: str) -> bool:
        raw = (message or '').lower().strip()
        if SlotStateMachine.is_decline(raw):
            return True
        return bool(re.match(r'^(no|nope|nah|wait|hold on)\b', raw))

    @classmethod
    def _build_semantic_queryset(cls, slots: Dict):
        from market.models import Product

        base_qs = Product.objects.filter(status='active', quantity__gt=0)

        if slots.get('category'):
            base_qs = base_qs.filter(Q(category__name__icontains=slots['category']) | Q(title__icontains=slots['category']))

        if slots.get('brand'):
            base_qs = base_qs.filter(Q(brand__icontains=slots['brand']) | Q(title__icontains=slots['brand']))

        if slots.get('price_min') is not None:
            base_qs = base_qs.filter(price__gte=slots['price_min'])

        if slots.get('price_max') is not None:
            base_qs = base_qs.filter(price__lte=slots['price_max'])

        if slots.get('condition'):
            cond = str(slots['condition']).lower()
            if cond in {'fair', 'used'}:
                base_qs = base_qs.filter(condition__in=['fair', 'good', 'like_new'])
            else:
                base_qs = base_qs.filter(condition__iexact=cond)

        if slots.get('location'):
            base_qs = base_qs.filter(Q(location__state__icontains=slots['location']) | Q(location__city__icontains=slots['location']))

        if slots.get('color'):
            base_qs = base_qs.filter(Q(title__icontains=slots['color']) | Q(description__icontains=slots['color']))

        return base_qs

    @classmethod
    def _find_products(cls, slots: Dict, top_k: int = 5):
        qs = cls._build_semantic_queryset(slots)
        query = SlotExtractor.build_semantic_query(slots)

        semantic_results = search_similar_products(query, qs, candidate_limit=250, top_k=80) if query else []
        semantic_ids = [pid for pid, score in semantic_results if float(score) >= 0.15]
        semantic_scores = {pid: float(score) for pid, score in semantic_results}

        if semantic_ids:
            qs = qs.filter(id__in=semantic_ids)

        qs = qs.annotate(
            semantic_score=Case(
                *[When(id=pid, then=Value(score)) for pid, score in semantic_scores.items()],
                default=Value(0.0),
                output_field=FloatField(),
            ),
            pop_score=ExpressionWrapper(
                Coalesce(F('views_count'), Value(0)) + Coalesce(F('favorites_count'), Value(0)) * 3,
                output_field=FloatField(),
            ),
        ).order_by('-semantic_score', '-pop_score', '-created_at')

        return list(qs[:top_k])

    @classmethod
    def _find_alternatives(cls, slots: Dict):
        relaxed = {**slots, 'price_min': None, 'price_max': None, 'location': None, 'condition': None}
        return cls._find_products(relaxed, top_k=3)

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
                intent_state={
                    'confirmed': False,
                    'confirmation_pending': False,
                    'clarification_count': 0,
                    'last_intent': 'product_search',
                },
                conversation_history=[],
            )
        return cls._build_response(
            reply="Got it — I started a new recommendation thread for this product category.",
            source='recommendation_switch',
            confidence=0.9,
            drift_detected=False,
            new_session_id=new_session.session_id,
            session=session,
            metadata={'pending_category_switch': False},
        )

    @classmethod
    def evaluate_recommendation_message(cls, session: ConversationSession, message: str) -> Dict:
        cls.initialize_context(session)

        prior_slots = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        intent_state = session.intent_state if isinstance(session.intent_state, dict) else {}
        msg_lower = (message or '').lower().strip()

        pending = intent_state.get('pending_category_switch')
        if pending and msg_lower in cls.SWITCH_CONFIRM_TOKENS:
            return cls._switch_conversation(session, pending)

        if not isinstance(session.context_data, dict):
            session.context_data = {}
        try:
            llm_enriched = enrich_slots(message, prior_slots)
            logger.info("LLM slot enrichment completed for recommendation flow")
        except Exception as exc:
            logger.warning("LLM slot enrichment failed, using empty enrichment: %s", exc)
            llm_enriched = {}

        hint_parts = []

        if llm_enriched.get('product_type'):
            hint_parts.append(llm_enriched['product_type'])

        if llm_enriched.get('occasion'):
            hint_parts.append(llm_enriched['occasion'])

        if llm_enriched.get('recipient'):
            hint_parts.append(f"for {llm_enriched['recipient']}")

        if hint_parts:
            hint_context = message + " " + " ".join(hint_parts)
        else:
            hint_context = message

        raw_slots = SlotExtractor.extract(hint_context, {})
        slots = SlotExtractor.extract(hint_context, prior_slots)
        # ARCHITECTURE GUARD (Phase 9): slot flow depends on dict-shaped slots.
        if not isinstance(raw_slots, dict):
            logger.warning("raw_slots was not a dict; coercing to empty dict")
            raw_slots = {}
        if not isinstance(slots, dict):
            logger.warning("slots was not a dict; coercing to empty dict")
            slots = {}

        for key in llm_enriched:
            if key not in slots or slots.get(key) is None:
                slots[key] = llm_enriched[key]

        slots['raw_query'] = message
        mandatory_missing = [
            slot_name for slot_name in ('product_type', 'price_max', 'condition')
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
        if forced_search:
            logger.info("Forced search activated with missing slots: %s", mandatory_missing)
        session.context_data['last_llm_enrichment'] = llm_enriched
        session.save(update_fields=['context_data', 'updated_at'])

        raw_has_product_intent = SlotExtractor.has_product_intent(message, raw_slots)
        allow_short_follow_up = cls._is_short_follow_up_constraint_turn(message, raw_slots, prior_slots)
        if not raw_has_product_intent and not allow_short_follow_up:
            stray_reply = cls._stray_reply(message)
            if stray_reply is not None:
                return cls._build_response(
                    reply=stray_reply,
                    source='recommendation_stray',
                    confidence=0.7,
                    drift_detected=False,
                    new_session_id=None,
                    session=session,
                    metadata={'intent': 'stray'},
                )

        if intent_state.get('confirmation_pending'):
            has_constraint_updates = cls._has_constraint_updates(raw_slots, prior_slots)
            if cls._is_decline_phrase(message):
                intent_state['confirmation_pending'] = False
                if has_constraint_updates:
                    intent_state['confirmed'] = False
                else:
                    session.intent_state = intent_state
                    session.save(update_fields=['intent_state', 'updated_at'])
                    return cls._build_response(
                        reply="No problem 👍 Tell me what to change (budget, brand, condition, or location).",
                        source='recommendation_confirmation',
                        confidence=0.8,
                        drift_detected=False,
                        new_session_id=None,
                        session=session,
                    )
            elif SlotStateMachine.is_confirmation(message):
                intent_state['confirmation_pending'] = False
                intent_state['confirmed'] = True
            elif has_constraint_updates:
                intent_state['confirmation_pending'] = False
                intent_state['confirmed'] = False
            else:
                return cls._build_response(
                    reply="Should I proceed and show options now? Reply 'yes' to continue.",
                    source='recommendation_confirmation',
                    confidence=0.8,
                    drift_detected=False,
                    new_session_id=None,
                    session=session,
                )

        if not raw_has_product_intent and not allow_short_follow_up:
            stray_reply = cls._stray_reply(message)
            if stray_reply is not None:
                return cls._build_response(
                    reply=stray_reply,
                    source='recommendation_stray',
                    confidence=0.7,
                    drift_detected=False,
                    new_session_id=None,
                    session=session,
                    metadata={'intent': 'stray'},
                )

        old_category = (prior_slots.get('category') or '').lower().strip()
        new_category = (slots.get('category') or '').lower().strip()
        if old_category and new_category and old_category != new_category:
            session.drift_flag = True
            intent_state['pending_category_switch'] = slots
            session.intent_state = intent_state
            session.save(update_fields=['drift_flag', 'intent_state', 'updated_at'])
            return cls._build_response(
                reply=(
                    f"I noticed your request changed from **{old_category}** to **{new_category}**. "
                    "Reply 'yes' to start a new recommendation thread for this product."
                ),
                source='recommendation_drift_detected',
                confidence=0.9,
                drift_detected=True,
                new_session_id=None,
                session=session,
            )

        clarification = None if forced_search else SlotStateMachine.get_next_clarification(slots, intent_state)
        if clarification:
            intent_state['clarification_count'] = int(intent_state.get('clarification_count', 0) or 0) + 1
            session.constraint_state = slots
            session.intent_state = {**intent_state, 'last_intent': 'product_search', 'pending_category_switch': None}
            session.drift_flag = False
            session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])
            return cls._build_response(
                reply=clarification,
                source='recommendation_clarification',
                confidence=0.85,
                drift_detected=False,
                new_session_id=None,
                session=session,
            )

        if not intent_state.get('confirmed') and not forced_search:
            intent_state['confirmation_pending'] = True
            session.constraint_state = slots
            session.intent_state = {**intent_state, 'last_intent': 'product_search', 'pending_category_switch': None}
            session.drift_flag = False
            session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])
            return cls._build_response(
                reply=SlotStateMachine.build_confirmation_prompt(slots),
                source='recommendation_confirmation',
                confidence=0.85,
                drift_detected=False,
                new_session_id=None,
                session=session,
            )

        session.constraint_state = slots
        session.intent_state = {**intent_state, 'last_intent': 'product_search', 'pending_category_switch': None}
        session.drift_flag = False
        session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])

        products = cls._find_products(slots)
        if not products:
            cls.log_demand_gap(session, slots)
            alternatives = cls._find_alternatives(slots)
            if alternatives:
                alt_lines = [f"- **{item.title}** — ₦{item.price:,.0f}" for item in alternatives]
                results_reply = (
                    "We don’t currently have that exact product 😅. Here are similar options:\n"
                    + "\n".join(alt_lines)
                    + "\nI’ve logged your request so sellers can respond, and we’ll notify you when a closer match appears."
                )
            else:
                results_reply = (
                    "I couldn’t find an exact match right now 😅. "
                    "I’ve logged your request so sellers are notified and we can alert you when stock appears."
                )
            final_reply = forced_prefix + results_reply + location_warning
            return cls._build_response(
                reply=final_reply,
                source='recommendation_results_alternatives',
                confidence=0.75,
                drift_detected=False,
                new_session_id=None,
                session=session,
                metadata={'forced_search': forced_search, 'location_missing': slots.get('location') is None},
            )

        session.active_product = products[0]
        session.save(update_fields=['active_product', 'updated_at'])
        results_reply = cls._format_results_reply(products, slots)
        final_reply = forced_prefix + results_reply + location_warning
        return cls._build_response(
            reply=final_reply,
            source='recommendation_results',
            confidence=0.9,
            drift_detected=False,
            new_session_id=None,
            session=session,
            metadata={'forced_search': forced_search, 'location_missing': slots.get('location') is None},
        )

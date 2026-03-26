import logging
import uuid
from typing import Dict

from django.db import transaction
from django.db.models import Case, ExpressionWrapper, F, FloatField, Q, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from assistant.models import ConversationSession
from assistant.services.demand_gap_service import log_demand_gap
from assistant.services.slot_extractor import SlotExtractor, SlotStateMachine
from market.search.embeddings import search_similar_products

logger = logging.getLogger(__name__)


class RecommendationService:
    """Conversational FAISS-backed product recommender for homepage_reco."""

    SWITCH_CONFIRM_TOKENS = {'yes', 'y', 'confirm', 'switch', 'go ahead', 'sure', 'okay', 'ok'}

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
    def _stray_reply(message: str) -> str:
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
        return {
            'reply': "Got it — I started a new recommendation thread for this product category.",
            'drift_detected': False,
            'new_session_id': new_session.session_id,
        }

    @classmethod
    def evaluate_recommendation_message(cls, session: ConversationSession, message: str) -> Dict:
        cls.initialize_context(session)

        prior_slots = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        intent_state = session.intent_state if isinstance(session.intent_state, dict) else {}
        msg_lower = (message or '').lower().strip()

        pending = intent_state.get('pending_category_switch')
        if pending and msg_lower in cls.SWITCH_CONFIRM_TOKENS:
            return cls._switch_conversation(session, pending)

        slots = SlotExtractor.extract(message, prior_slots)

        if not SlotExtractor.has_product_intent(message, slots):
            return {'reply': cls._stray_reply(message), 'drift_detected': False, 'new_session_id': None}

        old_category = (prior_slots.get('category') or '').lower().strip()
        new_category = (slots.get('category') or '').lower().strip()
        if old_category and new_category and old_category != new_category:
            session.drift_flag = True
            intent_state['pending_category_switch'] = slots
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

        if intent_state.get('confirmation_pending'):
            if SlotStateMachine.is_decline(message):
                intent_state['confirmation_pending'] = False
                session.intent_state = intent_state
                session.save(update_fields=['intent_state', 'updated_at'])
                return {
                    'reply': "No problem 👍 Tell me what to change (budget, brand, condition, or location).",
                    'drift_detected': False,
                    'new_session_id': None,
                }
            if SlotStateMachine.is_confirmation(message):
                intent_state['confirmation_pending'] = False
                intent_state['confirmed'] = True
            else:
                return {
                    'reply': "Should I proceed and show options now? Reply 'yes' to continue.",
                    'drift_detected': False,
                    'new_session_id': None,
                }

        clarification = SlotStateMachine.get_next_clarification(slots, intent_state)
        if clarification:
            intent_state['clarification_count'] = int(intent_state.get('clarification_count', 0) or 0) + 1
            session.constraint_state = slots
            session.intent_state = {**intent_state, 'last_intent': 'product_search', 'pending_category_switch': None}
            session.drift_flag = False
            session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])
            return {'reply': clarification, 'drift_detected': False, 'new_session_id': None}

        if not intent_state.get('confirmed'):
            intent_state['confirmation_pending'] = True
            session.constraint_state = slots
            session.intent_state = {**intent_state, 'last_intent': 'product_search', 'pending_category_switch': None}
            session.drift_flag = False
            session.save(update_fields=['constraint_state', 'intent_state', 'drift_flag', 'updated_at'])
            return {'reply': SlotStateMachine.build_confirmation_prompt(slots), 'drift_detected': False, 'new_session_id': None}

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
                reply = (
                    "We don’t currently have that exact product 😅. Here are similar options:\n"
                    + "\n".join(alt_lines)
                    + "\nI’ve logged your request so sellers can respond, and we’ll notify you when a closer match appears."
                )
            else:
                reply = (
                    "I couldn’t find an exact match right now 😅. "
                    "I’ve logged your request so sellers are notified and we can alert you when stock appears."
                )
            return {'reply': reply, 'drift_detected': False, 'new_session_id': None}

        session.active_product = products[0]
        session.save(update_fields=['active_product', 'updated_at'])
        return {
            'reply': cls._format_results_reply(products, slots),
            'drift_detected': False,
            'new_session_id': None,
        }

import logging
import re
import uuid
from decimal import Decimal
from typing import Dict, Optional

from django.db import transaction
from django.utils import timezone

from assistant.models import ConversationSession, RecommendationDemandGap
from market.models import Category, Product

logger = logging.getLogger(__name__)


class RecommendationService:
    """Deterministic recommendation context management and constraint extraction."""

    SWITCH_CONFIRM_TOKENS = {'yes', 'y', 'confirm', 'switch', 'go ahead', 'sure', 'okay'}

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

    @classmethod
    def extract_constraints(cls, message: str, prior: Optional[Dict] = None) -> Dict:
        text = (message or '').strip()
        lower = text.lower()
        prior = prior or {}

        category = cls._infer_category(lower) or prior.get('category')
        budget = cls._extract_budget(lower) or prior.get('budget_range')
        attributes = prior.get('attributes', {}).copy() if isinstance(prior.get('attributes'), dict) else {}

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

    @classmethod
    def evaluate_recommendation_message(cls, session: ConversationSession, message: str) -> Dict:
        cls.initialize_context(session)

        existing = session.constraint_state if isinstance(session.constraint_state, dict) else {}
        extracted = cls.extract_constraints(message, existing)

        old_category = (existing.get('category') or '').lower().strip()
        new_category = (extracted.get('category') or '').lower().strip()

        pending = session.intent_state.get('pending_category_switch') if isinstance(session.intent_state, dict) else None
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
                    f"I noticed your request changed from {old_category} to {new_category}. "
                    "Reply 'yes' to start a new recommendation thread for this new product journey."
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
                'reply': "I could not find a matching product right now. I have logged your request so inventory can improve.",
                'drift_detected': False,
                'new_session_id': None,
            }

        top = products[0]
        session.active_product = top
        session.save(update_fields=['active_product', 'updated_at'])
        return {
            'reply': f"Top recommendation: {top.title} — ₦{top.price}. Would you like more options in this category?",
            'drift_detected': False,
            'new_session_id': None,
        }

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
            'reply': 'Great — I started a new recommendation thread for the new product category.',
            'drift_detected': False,
            'new_session_id': new_session.session_id,
        }

    @classmethod
    def log_demand_gap(cls, session: ConversationSession, constraints: Dict) -> None:
        category = constraints.get('category') or ''
        attrs = constraints.get('attributes') or {}
        location = constraints.get('location') or ''
        gap, created = RecommendationDemandGap.objects.get_or_create(
            user=session.user,
            requested_category=category[:120],
            requested_attributes=attrs,
            user_location=location[:200],
            defaults={'frequency': 1},
        )
        if not created:
            gap.frequency += 1
            gap.save(update_fields=['frequency', 'last_seen_at'])

    @staticmethod
    def _infer_category(lower: str) -> Optional[str]:
        category_map = {c.name.lower(): c.name for c in Category.objects.filter(is_active=True).only('name')[:300]}
        for key, name in category_map.items():
            if key in lower:
                return name
        fallback = ['phone', 'laptop', 'shoe', 'shirt', 'car', 'house', 'furniture']
        for f in fallback:
            if f in lower:
                return f.title()
        return None

    @staticmethod
    def _extract_budget(lower: str) -> Optional[Dict]:
        matches = re.findall(r"(?:₦|ngn|n)?\s*(\d{2,9})", lower)
        if not matches:
            return None
        nums = sorted(Decimal(m) for m in matches[:2])
        if len(nums) == 1:
            return {'min': float(nums[0]), 'max': float(nums[0])}
        return {'min': float(nums[0]), 'max': float(nums[1])}

    @staticmethod
    def _find_products(constraints: Dict):
        qs = Product.objects.filter(status='active').select_related('category').order_by('-created_at')
        category = constraints.get('category')
        if category:
            qs = qs.filter(category__name__icontains=category)
        budget = constraints.get('budget_range') or {}
        if isinstance(budget, dict):
            if budget.get('min') is not None:
                qs = qs.filter(price__gte=budget['min'])
            if budget.get('max') is not None:
                qs = qs.filter(price__lte=budget['max'])
        return list(qs[:5])

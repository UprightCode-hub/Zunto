"""
server/assistant/processors/conversation_manager.py

Fix applied:
  Greeting state hijacks first user message entirely — the message was
  thrown away and a generic welcome returned regardless of what the user asked.

  Added _should_bypass_greeting() which detects product/support intent in the
  first message and routes directly to STATE_CHAT_MODE, skipping the welcome
  flow. Short bare greetings ("hi", "hello") still go through greeting flow.
  homepage_reco mode always bypasses greeting.

Change (this session):
  assistant_mode is now forwarded to QueryProcessor.process() so the LLM
  receives a mode-aware system prompt (inbox_general vs customer_service vs
  homepage_reco scoping).
"""
import logging
from typing import Dict, Tuple, Optional
import gc
import re
import uuid

from django.conf import settings

from assistant.models import ConversationSession
from assistant.processors.query_processor import QueryProcessor
from assistant.processors.local_model import LocalModelAdapter
from assistant.services.gigi_agent import GigiRecommendationAgent
from assistant.services.customer_service_agent import CustomerServiceAgent

from assistant.ai import (
    classify_intent,
    ContextManager,
    ResponsePersonalizer
)

from assistant.flows import (
    GreetingFlow,
    FAQFlow,
    DisputeFlow,
    FeedbackFlow
)

from assistant.utils.constants import (
    STATE_GREETING,
    STATE_MENU,
    STATE_FAQ_MODE,
    STATE_DISPUTE_MODE,
    STATE_FEEDBACK_MODE,
    STATE_CHAT_MODE,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM
)
from assistant.utils.validators import (
    validate_message,
    sanitize_message,
    is_spam_message
)
from assistant.utils.formatters import (
    clean_message
)
from assistant.utils.assistant_modes import (
    resolve_legacy_lane,
    mode_gate_response,
    ASSISTANT_MODE_CUSTOMER_SERVICE,
    ASSISTANT_MODE_INBOX_GENERAL,
    ASSISTANT_MODE_HOMEPAGE_RECO,
)

logger = logging.getLogger(__name__)


PRODUCT_TYPE_ALIASES = (
    ('rice', ('bag of rice', 'bags of rice', 'rice')),
    ('air conditioner', ('air conditioner', 'air conditioners', 'air conditioning', 'split ac', 'split unit', 'a/c', 'ac', 'acs')),
    ('phone', ('mobile phone', 'mobile phones', 'smartphone', 'smartphones', 'iphone', 'android phone', 'phone', 'phones')),
    ('laptop', ('laptop computer', 'laptop computers', 'notebook computer', 'laptop', 'laptops')),
    ('shoe', ('sneakers', 'trainer', 'trainers', 'shoe', 'shoes')),
    ('shirt', ('shirt', 'shirts', 't-shirt', 't-shirts', 'tee shirt', 'tee shirts')),
    ('dress', ('dress', 'dresses')),
    ('generator', ('generator', 'generators')),
    ('television', ('television', 'televisions', 'smart tv', 'tv', 'tvs')),
    ('refrigerator', ('refrigerator', 'refrigerators', 'fridge', 'fridges')),
    ('fan', ('standing fan', 'ceiling fan', 'fan', 'fans')),
    ('bag', ('handbag', 'handbags', 'school bag', 'school bags', 'bag', 'bags')),
    ('watch', ('smart watch', 'smartwatch', 'wristwatch', 'watch', 'watches')),
    ('camera', ('camera', 'cameras')),
    ('speaker', ('bluetooth speaker', 'speaker', 'speakers')),
    ('chair', ('chair', 'chairs')),
    ('table', ('table', 'tables')),
    ('bed', ('bed frame', 'bed', 'beds')),
    ('mattress', ('mattress', 'mattresses')),
    ('perfume', ('perfume', 'perfumes', 'fragrance', 'fragrances')),
)

PRODUCT_CONTEXT_KEYS = {
    'activeproduct',
    'category',
    'categoryname',
    'categoryslug',
    'itemtype',
    'lastcategory',
    'lastproduct',
    'lastproducttype',
    'normalizedproducttype',
    'product',
    'productcategory',
    'productname',
    'productslug',
    'producttitle',
    'producttype',
    'requestedcategory',
    'requestedproduct',
    'requestedproducttype',
    'searchcategory',
}


def _normalize_context_key(value) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def _normalize_product_text(value) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower()).strip()


def _detect_product_type_from_text(value) -> str:
    if isinstance(value, dict):
        for nested in value.values():
            detected = _detect_product_type_from_text(nested)
            if detected:
                return detected
        return ''

    if isinstance(value, (list, tuple, set)):
        for nested in value:
            detected = _detect_product_type_from_text(nested)
            if detected:
                return detected
        return ''

    normalized = _normalize_product_text(value)
    if not normalized:
        return ''

    padded = f' {normalized} '
    for canonical, aliases in PRODUCT_TYPE_ALIASES:
        for alias in aliases:
            normalized_alias = _normalize_product_text(alias)
            if normalized_alias and f' {normalized_alias} ' in padded:
                return canonical
    return ''


def _iter_product_context_values(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if _normalize_context_key(key) in PRODUCT_CONTEXT_KEYS:
                yield value
            if isinstance(value, (dict, list, tuple)):
                yield from _iter_product_context_values(value)
    elif isinstance(data, (list, tuple)):
        for item in data:
            yield from _iter_product_context_values(item)


class ConversationManager:

    def __init__(self, session_id: str, user_id: int = None, assistant_mode: str = ASSISTANT_MODE_INBOX_GENERAL):
        self.session_id = session_id
        self.user_id = user_id
        self.assistant_mode = assistant_mode
        self.assistant_lane = resolve_legacy_lane(assistant_mode)
        self.session = self._get_or_create_session()

        self.query_processor = QueryProcessor()
        self.llm = LocalModelAdapter.get_instance()

        self.context_mgr = ContextManager(self.session)
        self.personalizer = ResponsePersonalizer(self.session)
        self.last_ai_result = None

        self.greeting_flow = GreetingFlow(self.session, self.context_mgr)
        self.faq_flow = FAQFlow(self.session, self.query_processor, self.context_mgr)
        self.dispute_flow = DisputeFlow(self.session, self.llm, self.context_mgr, query_processor=self.query_processor)
        self.feedback_flow = FeedbackFlow(self.session, self.context_mgr, intent_classifier=True)

        self._message_intent_cache = {}

        gc.collect()
        logger.info(f"ConversationManager initialized for session {session_id[:8]}")

    # -----------------------------------------------------------------------
    # Session management
    # -----------------------------------------------------------------------

    def _get_or_create_session(self) -> ConversationSession:
        try:
            initial_state = STATE_GREETING
            if self.assistant_mode == ASSISTANT_MODE_HOMEPAGE_RECO:
                initial_state = STATE_CHAT_MODE
            elif self.assistant_lane == 'customer_service':
                initial_state = STATE_CHAT_MODE

            session, created = ConversationSession.objects.get_or_create(
                session_id=self.session_id,
                defaults={
                    'user_id': self.user_id,
                    'assistant_lane': self.assistant_lane,
                    'assistant_mode': self.assistant_mode,
                    'is_persistent': True,
                    'current_state': initial_state,
                    'context': {}
                }
            )

            if created:
                logger.info(f"New session created: {self.session_id}")

            if not created:
                if self.user_id and session.user_id and session.user_id != self.user_id:
                    raise PermissionError('Session does not belong to the authenticated user')

                if self.user_id and session.user_id is None:
                    logger.info(
                        "Ignoring anonymous session %s for authenticated user %s; creating a fresh session",
                        session.session_id[:8],
                        self.user_id,
                    )
                    self.session_id = str(uuid.uuid4())
                    session = ConversationSession.objects.create(
                        session_id=self.session_id,
                        user_id=self.user_id,
                        assistant_lane=self.assistant_lane,
                        assistant_mode=self.assistant_mode,
                        is_persistent=True,
                        current_state=initial_state,
                        context={},
                        context_data={},
                        conversation_history=[],
                        context_type=(
                            ConversationSession.CONTEXT_TYPE_RECOMMENDATION
                            if self.assistant_mode == ASSISTANT_MODE_HOMEPAGE_RECO
                            else ConversationSession.CONTEXT_TYPE_SUPPORT
                        ),
                        constraint_state={},
                        intent_state={},
                    )
                    return session

                if (
                    self.assistant_mode == ASSISTANT_MODE_HOMEPAGE_RECO
                    and session.assistant_mode != ASSISTANT_MODE_HOMEPAGE_RECO
                ):
                    logger.info(
                        "Rotating homepage_reco request away from %s session %s",
                        session.assistant_mode,
                        session.session_id[:8],
                    )
                    self.session_id = str(uuid.uuid4())
                    session = ConversationSession.objects.create(
                        session_id=self.session_id,
                        user_id=self.user_id,
                        assistant_lane=self.assistant_lane,
                        assistant_mode=self.assistant_mode,
                        is_persistent=True,
                        current_state=initial_state,
                        context={},
                        context_data={},
                        conversation_history=[],
                        context_type=ConversationSession.CONTEXT_TYPE_RECOMMENDATION,
                        constraint_state={},
                        intent_state={},
                    )
                    return session

                updates = []
                persisted_mode = getattr(session, 'assistant_mode', None)
                if persisted_mode:
                    self.assistant_mode = persisted_mode
                    self.assistant_lane = resolve_legacy_lane(persisted_mode)
                else:
                    session.assistant_mode = self.assistant_mode
                    updates.append('assistant_mode')

                if session.assistant_lane != self.assistant_lane:
                    session.assistant_lane = self.assistant_lane
                    updates.append('assistant_lane')

                if self.assistant_mode == ASSISTANT_MODE_HOMEPAGE_RECO and session.current_state != STATE_CHAT_MODE:
                    session.current_state = STATE_CHAT_MODE
                    updates.append('current_state')

                if updates:
                    updates.append('updated_at')
                    session.save(update_fields=updates)

            return session
        except Exception as e:
            logger.error(f"Session creation error: {e}", exc_info=True)
            raise

    def _ensure_conversation_title(self, message: str):
        if self.session.conversation_title:
            return

        trimmed = (message or '').strip()
        title = trimmed[:80].strip()

        if len(title) < 8:
            product_name = (
                self.session.context.get('product_name')
                or self.session.context_data.get('product_name')
                or 'support'
            )
            title = f"Conversation about {product_name}"

        self.session.conversation_title = title
        from django.utils import timezone
        self.session.title_generated_at = timezone.now()
        self.session.save(update_fields=['conversation_title', 'title_generated_at', 'updated_at'])

    # -----------------------------------------------------------------------
    # Main message entry point
    # -----------------------------------------------------------------------

    def process_message(self, message: str) -> str:
        try:
            self.last_ai_result = None
            is_valid, error = validate_message(message)
            if not is_valid:
                logger.warning(f"Invalid message: {error}")
                return f"⚠️ {error}"

            if is_spam_message(message):
                logger.warning(f"Spam detected: {message[:50]}...")
                return "I'm sorry, but your message appears to be spam. Please try again with a genuine question."

            message = sanitize_message(message)
            message = clean_message(message)

            current_state = self.session.current_state

            if self.assistant_mode == ASSISTANT_MODE_HOMEPAGE_RECO:
                GigiRecommendationAgent.initialize_context(self.session)
                return self._handle_homepage_reco_mode(message)

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and current_state != STATE_CHAT_MODE:
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])
                current_state = STATE_CHAT_MODE

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and current_state == STATE_DISPUTE_MODE:
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])
                current_state = STATE_CHAT_MODE

            # ── KEY FIX: bypass greeting when user has clear intent ────────
            if current_state == STATE_GREETING and self._should_bypass_greeting(message):
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])
                current_state = STATE_CHAT_MODE
                logger.info(f"Greeting bypassed — routing directly to chat for: {message[:50]}")
            # ─────────────────────────────────────────────────────────────

            logger.info(f"Processing message in state '{current_state}': {message[:50]}...")

            if current_state == STATE_GREETING:
                return self._handle_greeting()
            elif current_state == STATE_MENU:
                return self._handle_menu_selection(message)
            elif current_state == STATE_FAQ_MODE:
                return self._handle_faq_mode(message)
            elif current_state == STATE_DISPUTE_MODE:
                return self._handle_dispute_mode(message)
            elif current_state == STATE_FEEDBACK_MODE:
                return self._handle_feedback_mode(message)
            elif current_state == STATE_CHAT_MODE:
                return self._handle_chat_mode(message)
            else:
                logger.warning(f"Unknown state '{current_state}', falling back to query processor")
                return self._handle_chat_mode(message)

        except Exception as e:
            logger.error(f"ConversationManager error: {e}", exc_info=True)
            return (
                "I apologize, but I encountered an error processing your message. "
                "Please try again or contact our support team for assistance."
            )

    # -----------------------------------------------------------------------
    # Greeting bypass detection
    # -----------------------------------------------------------------------

    def _should_bypass_greeting(self, message: str) -> bool:
        """
        Return True when the user's first message already contains actionable
        intent and we should skip the welcome/menu flow.

        Always bypasses for homepage_reco mode.
        Bypasses for product queries, support questions, and messages longer
        than a bare greeting.
        Short greetings ("hi", "hello") still go through greeting flow.
        """
        # Reco mode: every message is a product query
        if self.assistant_mode == ASSISTANT_MODE_HOMEPAGE_RECO:
            return True

        msg = message.lower().strip()

        # Very short bare greetings → keep greeting flow
        if len(msg.split()) <= 2 and not any(
            kw in msg for kw in ['buy', 'get', 'find', 'need', 'want', 'order', 'help']
        ):
            return False

        INTENT_SIGNALS = [
            # product discovery
            'is there', 'do you have', 'find me', 'looking for', 'available',
            'sneakers', 'shoes', 'phone', 'laptop', 'shirt', 'dress', 'bag',
            'buy', 'purchase', 'price', 'cost', 'how much', 'cheap',
            # support
            'track', 'order', 'delivery', 'refund', 'return', 'payment',
            'dispute', 'problem', 'issue', 'complaint', 'cancel',
            # faq
            'how do i', 'how to', 'can i', 'what is', 'when will', 'where is',
        ]
        return any(signal in msg for signal in INTENT_SIGNALS)

    # -----------------------------------------------------------------------
    # Intent classification (cached per conversation turn)
    # -----------------------------------------------------------------------

    def _get_or_classify_intent(self, message: str):
        use_caching = getattr(settings, 'PHASE1_INTENT_CACHING', True)

        if not use_caching:
            intent, confidence, metadata = classify_intent(message, self.session.context)
            return intent, confidence, metadata

        if message not in self._message_intent_cache:
            try:
                intent, confidence, metadata = classify_intent(message, self.session.context)
                self._message_intent_cache[message] = (intent, confidence, metadata)
            except Exception as e:
                logger.error(f"Intent classification error: {e}", exc_info=True)
                from assistant.ai.intent_classifier import Intent
                return Intent.UNKNOWN, 0.0, {'emotion': 'neutral'}

        return self._message_intent_cache[message]

    # -----------------------------------------------------------------------
    # Mode gate helpers
    # -----------------------------------------------------------------------

    def _customer_service_redirect_message(self) -> str:
        return (
            "For dispute resolution, please use the Customer Service button "
            "(top-right or Settings). This assistant lane handles normal conversations only."
        )

    def _is_dispute_request(self, message: str, intent_value: str = '') -> bool:
        if intent_value in {'dispute', 'complaint', 'issue'}:
            return True
        text = (message or '').lower()
        dispute_terms = {
            'dispute', 'chargeback', 'formal complaint', 'scam', 'fraud',
            'counterfeit', 'fake product', 'wrong item', 'damaged',
            'not delivered', 'did not receive', 'never arrived', 'evidence',
            'proof', 'mediation', 'escalate', 'report seller', 'report buyer',
        }
        return any(term in text for term in dispute_terms)

    def _apply_mode_gate(self, message: str) -> Optional[str]:
        return mode_gate_response(self.assistant_mode, message)

    # -----------------------------------------------------------------------
    # Recommendation context hygiene
    # -----------------------------------------------------------------------

    def _loaded_recommendation_product_type(self) -> str:
        for data in (
            self.session.intent_state,
            self.session.constraint_state,
            self.session.context,
            self.session.context_data,
        ):
            for value in _iter_product_context_values(data):
                detected = _detect_product_type_from_text(value)
                if detected:
                    return detected

        detected = _detect_product_type_from_text(self.session.conversation_title)
        if detected:
            return detected

        active_product = getattr(self.session, 'active_product', None)
        if active_product:
            for value in (
                getattr(active_product, 'title', ''),
                getattr(active_product, 'name', ''),
                getattr(getattr(active_product, 'category', None), 'name', ''),
                getattr(getattr(active_product, 'category', None), 'slug', ''),
            ):
                detected = _detect_product_type_from_text(value)
                if detected:
                    return detected

        return ''

    def _reset_recommendation_context(self, stale_product_type: str, incoming_product_type: str):
        self.session.context = {}
        self.session.context_data = {}
        self.session.conversation_history = []
        self.session.constraint_state = {}
        self.session.intent_state = {}
        self.session.active_product = None
        self.session.context_type = ConversationSession.CONTEXT_TYPE_RECOMMENDATION
        self.session.current_state = STATE_CHAT_MODE
        self.session.conversation_title = ''
        self.session.title_generated_at = None
        self.session.message_count = 0
        self.session.sentiment_score = 0.5
        self.session.satisfaction_score = 0.5
        self.session.escalation_level = 0
        self.session.is_escalated = False
        self.session.drift_flag = False
        self.session.completed_at = None
        self.session.closed_at = None
        self.session.save(update_fields=[
            'context',
            'context_data',
            'conversation_history',
            'constraint_state',
            'intent_state',
            'active_product',
            'context_type',
            'current_state',
            'conversation_title',
            'title_generated_at',
            'message_count',
            'sentiment_score',
            'satisfaction_score',
            'escalation_level',
            'is_escalated',
            'drift_flag',
            'completed_at',
            'closed_at',
            'updated_at',
        ])
        self.context_mgr = ContextManager(self.session)
        self.personalizer = ResponsePersonalizer(self.session)
        self._message_intent_cache.clear()
        logger.info(
            "Discarded stale homepage_reco context for session %s: %s -> %s",
            self.session.session_id[:8],
            stale_product_type,
            incoming_product_type,
        )

    def _discard_stale_recommendation_context(self, message: str):
        incoming_product_type = _detect_product_type_from_text(message)
        if not incoming_product_type:
            return

        stale_product_type = self._loaded_recommendation_product_type()
        if stale_product_type and stale_product_type != incoming_product_type:
            self._reset_recommendation_context(stale_product_type, incoming_product_type)

    # -----------------------------------------------------------------------
    # State handlers
    # -----------------------------------------------------------------------

    def _handle_greeting(self) -> str:
        try:
            return self.greeting_flow.start_conversation()
        except Exception as e:
            logger.error(f"Greeting flow error: {e}", exc_info=True)
            return "Hello! I'm your Zunto support assistant. How can I help you today?"

    def _handle_name_input(self, message: str) -> str:
        logger.info("Name input state is deprecated; routing to menu selection")
        self.session.current_state = STATE_MENU
        self.session.save(update_fields=['current_state', 'updated_at'])
        return self._handle_menu_selection(message)

    def _handle_menu_selection(self, message: str) -> str:
        try:
            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE:
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])
                return self._handle_customer_service_mode(message)

            message_lower = message.lower().strip()

            if message_lower in ['1', 'faq', 'question', 'questions', 'ask']:
                intro = self.faq_flow.enter_faq_mode()
                self.context_mgr.add_message('assistant', intro, confidence=1.0)
                return intro
            elif message_lower in ['2', 'dispute', 'report', 'problem', 'issue']:
                if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE:
                    return self._customer_service_redirect_message()
                intro = self.dispute_flow.enter_dispute_mode()
                self.context_mgr.add_message('assistant', intro, confidence=1.0)
                return intro
            elif message_lower in ['3', 'feedback', 'suggest', 'suggestion']:
                intro = self.feedback_flow.enter_feedback_mode()
                self.context_mgr.add_message('assistant', intro, confidence=1.0)
                return intro
            else:
                intent, confidence, metadata = self._get_or_classify_intent(message)
                emotion = metadata.get('emotion', 'neutral')

                logger.info(f"Menu selection: intent={intent.value}, emotion={emotion}")

                if intent.value in ['dispute', 'complaint', 'issue']:
                    if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE:
                        return self._customer_service_redirect_message()
                    return self.dispute_flow.enter_dispute_mode()
                elif intent.value in ['faq', 'question']:
                    return self.faq_flow.enter_faq_mode()
                elif intent.value in ['feedback', 'suggestion', 'praise']:
                    return self.feedback_flow.enter_feedback_mode()
                else:
                    self.session.current_state = STATE_CHAT_MODE
                    self.session.save()
                    return self._handle_chat_mode(message)

        except Exception as e:
            logger.error(f"Menu selection error: {e}", exc_info=True)
            return "Please select an option (1-3) or describe what you need help with."

    def _handle_faq_mode(self, message: str) -> str:
        try:
            gate_reply = self._apply_mode_gate(message)
            if gate_reply:
                return gate_reply

            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and self._is_dispute_request(message, intent.value):
                return self._customer_service_redirect_message()

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, faq_metadata = self.faq_flow.handle_faq_query(message)
            self.last_ai_result = {'metadata': faq_metadata, 'source': 'faq_flow'}

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)

            if use_personalization and self._needs_personalization(reply):
                final_reply = self.personalizer.personalize(
                    base_response=reply,
                    confidence=faq_metadata.get('confidence', 0.5),
                    emotion=emotion
                )
            else:
                final_reply = reply

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=faq_metadata.get('confidence', 0.5)
            )
            return final_reply

        except Exception as e:
            logger.error(f"FAQ mode error: {e}", exc_info=True)
            return "I encountered an issue processing your question. Could you try rephrasing it?"

    def _handle_dispute_mode(self, message: str) -> str:
        try:
            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE:
                return self._customer_service_redirect_message()

            return self._handle_customer_service_mode(message)

            gate_reply = self._apply_mode_gate(message)
            if gate_reply:
                return gate_reply

            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and not self._is_dispute_request(message, intent.value):
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])
                return self._handle_chat_mode(message)

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, dispute_metadata = self.dispute_flow.handle_dispute_message(message)
            self.last_ai_result = {'metadata': dispute_metadata, 'source': 'dispute_flow'}

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)

            if use_personalization and self._needs_personalization(reply):
                final_reply = self.personalizer.personalize(
                    base_response=reply,
                    confidence=0.9,
                    emotion=emotion,
                    formality='formal'
                )
            else:
                final_reply = reply

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=0.9
            )

            if dispute_metadata.get('complete'):
                self.context_mgr.mark_resolution(success=True)

            return final_reply

        except Exception as e:
            logger.error(f"Dispute mode error: {e}", exc_info=True)
            return "I encountered an issue. Please describe your dispute and I'll help you report it."

    def _handle_feedback_mode(self, message: str) -> str:
        try:
            gate_reply = self._apply_mode_gate(message)
            if gate_reply:
                return gate_reply

            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and self._is_dispute_request(message, intent.value):
                return self._customer_service_redirect_message()

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, feedback_metadata = self.feedback_flow.handle_feedback_message(message, emotion=emotion)

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)

            if use_personalization and self._needs_personalization(reply):
                final_reply = self.personalizer.personalize(
                    base_response=reply,
                    confidence=0.85,
                    emotion=emotion
                )
            else:
                final_reply = reply

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=0.85
            )

            if feedback_metadata.get('complete'):
                self.context_mgr.mark_resolution(
                    success=feedback_metadata.get('sentiment') != 'negative'
                )

            return final_reply

        except Exception as e:
            logger.error(f"Feedback mode error: {e}", exc_info=True)
            return "Thank you for your feedback! Type 'menu' to return to main options."

    def _handle_homepage_reco_mode(self, message: str) -> str:
        try:
            if self.session.current_state != STATE_CHAT_MODE:
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent='product_search',
                emotion='neutral',
            )

            agent = GigiRecommendationAgent()
            history = (
                self.session.conversation_history
                if isinstance(self.session.conversation_history, list)
                else []
            )
            recommendation = agent.run(
                conversation_history=history,
                user_message=message,
                session=self.session,
            )
            self.last_ai_result = recommendation
            final_reply = recommendation['reply']
            assistant_confidence = float(recommendation.get('confidence', 0.8) or 0.8)

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=assistant_confidence,
                metadata={
                    'source': recommendation.get('source', 'recommendation_service'),
                    **(recommendation.get('metadata') if isinstance(recommendation.get('metadata'), dict) else {}),
                },
            )

            new_session_id = recommendation.get('new_session_id')
            if new_session_id:
                self.session = ConversationSession.objects.get(session_id=new_session_id)
                self.context_mgr = ContextManager(self.session)

            return final_reply

        except Exception as e:
            logger.error(f"Homepage recommendation mode error: {e}", exc_info=True)
            return "I hit a snag while fetching recommendations. Please try again."

    def _handle_chat_mode(self, message: str) -> str:
        try:
            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE:
                return self._handle_customer_service_mode(message)

            gate_reply = self._apply_mode_gate(message)
            if gate_reply:
                return gate_reply

            message_lower = message.lower()

            if message_lower in ['menu', 'main menu', 'options', 'back', 'go back']:
                self.session.current_state = STATE_MENU
                self.session.save()
                return self.greeting_flow._build_unified_menu(self.get_user_name())

            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and self._is_dispute_request(message, intent.value):
                return self._customer_service_redirect_message()

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and self._is_dispute_request(message, intent.value):
                self.dispute_flow.enter_dispute_mode()
                return self._handle_dispute_mode(message)

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            use_context = getattr(settings, 'PHASE1_CONTEXT_INTEGRATION', True)

            # ── assistant_mode forwarded so LLM gets mode-scoped system prompt ──
            result = self.query_processor.process(
                message=message,
                user_name=self.get_user_name(),
                context=self.session.context if use_context else {},
                assistant_mode=self.assistant_mode,
            )
            self.last_ai_result = result

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)

            if use_personalization and self._needs_personalization(result['reply']):
                hints = self.context_mgr.get_personalization_hints()
                formality = ResponsePersonalizer.detect_formality_preference(message)

                final_reply = self.personalizer.personalize(
                    base_response=result['reply'],
                    confidence=result['confidence'],
                    emotion=emotion,
                    formality=hints.get('formality', formality),
                    add_greeting=True,
                    add_emoji=True
                )
            else:
                final_reply = result['reply']

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=result['confidence']
            )

            if result['confidence'] >= CONFIDENCE_HIGH:
                self.context_mgr.mark_resolution(success=True)

            if 'last_topic' in self.session.context:
                self.session.context['last_topic'] = None
                self.session.save()

            return final_reply

        except Exception as e:
            logger.error(f"Chat mode error: {e}", exc_info=True)
            return "I encountered an issue. Could you rephrase your question?"

    def _handle_customer_service_mode(self, message: str) -> str:
        try:
            self.context_mgr.add_message(
                role='user',
                content=message,
                intent='customer_service',
                emotion='neutral',
            )

            agent = CustomerServiceAgent(self.session)
            result = agent.run(message)
            self.last_ai_result = result
            final_reply = result.get('reply') or "I could not process that support request. Please try again."
            metadata = result.get('metadata') if isinstance(result.get('metadata'), dict) else {}
            confidence = float(result.get('confidence', 0.85) or 0.85)

            self.session.current_state = STATE_CHAT_MODE
            self.session.context_type = ConversationSession.CONTEXT_TYPE_SUPPORT
            self.session.save(update_fields=['current_state', 'context_type', 'updated_at'])

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=confidence,
                metadata=metadata,
            )
            return final_reply

        except Exception as e:
            logger.error("Customer service mode error: %s", e, exc_info=True)
            return "I hit an issue while checking your account records. Please try again in a moment."

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    def _needs_personalization(self, response: str) -> bool:
        try:
            has_greeting = any(
                g in response.lower()[:50]
                for g in ['hi ', 'hello', 'hey', 'good morning', 'good afternoon']
            )
            has_emoji = any(ord(c) > 0x1F300 for c in response)
            return not (has_greeting and has_emoji)
        except Exception as e:
            logger.warning(f"Personalization check failed: {e}")
            return False

    def get_current_state(self) -> str:
        return self.session.current_state

    def get_user_name(self) -> str:
        user = getattr(self.session, 'user', None)
        if user:
            full_name = user.get_full_name().strip()
            if full_name:
                return full_name
            first_name = getattr(user, 'first_name', '').strip()
            if first_name:
                return first_name
        return "there"

    def get_conversation_summary(self) -> Dict:
        try:
            return self.context_mgr.get_conversation_summary()
        except Exception as e:
            logger.error(f"Conversation summary error: {e}", exc_info=True)
            return {}

    def reset_session(self):
        try:
            self.session.current_state = STATE_GREETING
            self.session.context = {}
            self.session.save()
            self.context_mgr.reset()
            self._message_intent_cache.clear()
            logger.info(f"Session reset: {self.session_id}")
        except Exception as e:
            logger.error(f"Session reset error: {e}", exc_info=True)

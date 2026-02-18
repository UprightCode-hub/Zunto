#server/assistant/processors/conversation_manager.py
import logging
from typing import Dict, Tuple, Optional
import gc

from django.conf import settings

from assistant.models import ConversationSession
from assistant.processors.query_processor import QueryProcessor
from assistant.processors.local_model import LocalModelAdapter

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

        self.greeting_flow = GreetingFlow(self.session, self.context_mgr)
        self.faq_flow = FAQFlow(self.session, self.query_processor, self.context_mgr)
        self.dispute_flow = DisputeFlow(self.session, self.llm, self.context_mgr)
        self.feedback_flow = FeedbackFlow(self.session, self.context_mgr, intent_classifier=True)

        self._message_intent_cache = {}

        gc.collect()
        logger.info(f"ConversationManager initialized for session {session_id[:8]}")

    def _get_or_create_session(self) -> ConversationSession:
        try:
            session, created = ConversationSession.objects.get_or_create(
                session_id=self.session_id,
                defaults={
                    'user_id': self.user_id,
                    'assistant_lane': self.assistant_lane,
                    'assistant_mode': self.assistant_mode,
                    'is_persistent': True,
                    'current_state': STATE_DISPUTE_MODE if self.assistant_lane == 'customer_service' else STATE_GREETING,
                    'context': {}
                }
            )

            if created:
                logger.info(f"New session created: {self.session_id}")

            if not created:
                if self.user_id and session.user_id and session.user_id != self.user_id:
                    raise PermissionError('Session does not belong to the authenticated user')

                updates = []
                if self.user_id and session.user_id is None:
                    session.user_id = self.user_id
                    updates.append('user')

                persisted_mode = getattr(session, 'assistant_mode', None)
                if persisted_mode:
                    # Preserve session origin mode once created; do not mutate by caller context.
                    self.assistant_mode = persisted_mode
                    self.assistant_lane = resolve_legacy_lane(persisted_mode)
                else:
                    session.assistant_mode = self.assistant_mode
                    updates.append('assistant_mode')

                if session.assistant_lane != self.assistant_lane:
                    session.assistant_lane = self.assistant_lane
                    updates.append('assistant_lane')

                if updates:
                    updates.append('updated_at')
                    session.save(update_fields=updates)

            return session
        except Exception as e:
            logger.error(f"Session creation error: {e}", exc_info=True)
            raise

    def _ensure_conversation_title(self, message: str):
        """Set deterministic title once using first user message snippet."""
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

    def process_message(self, message: str) -> str:
        try:
            is_valid, error = validate_message(message)
            if not is_valid:
                logger.warning(f"Invalid message: {error}")
                return f"⚠️ {error}"

            if is_spam_message(message):
                logger.warning(f"Spam detected: {message[:50]}...")
                return "I'm sorry, but your message appears to be spam. Please try again with a genuine question."

            message = sanitize_message(message)
            message = clean_message(message)
            self._ensure_conversation_title(message)

            current_state = self.session.current_state

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and current_state != STATE_DISPUTE_MODE:
                self.dispute_flow.enter_dispute_mode()
                current_state = self.session.current_state

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and current_state == STATE_DISPUTE_MODE:
                self.session.current_state = STATE_CHAT_MODE
                self.session.save(update_fields=['current_state', 'updated_at'])
                current_state = STATE_CHAT_MODE

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

    def _get_or_classify_intent(self, message: str):
        use_caching = getattr(settings, 'PHASE1_INTENT_CACHING', True)
        
        if not use_caching:
            intent, confidence, metadata = classify_intent(message, self.session.context)
            logger.debug(f"Intent classified without cache: {intent.value} ({confidence:.2f})")
            return intent, confidence, metadata
        
        if message not in self._message_intent_cache:
            try:
                intent, confidence, metadata = classify_intent(message, self.session.context)
                self._message_intent_cache[message] = (intent, confidence, metadata)
                logger.debug(f"Intent classified and cached: {intent.value} ({confidence:.2f})")
            except Exception as e:
                logger.error(f"Intent classification error: {e}", exc_info=True)
                from assistant.ai.intent_classifier import Intent
                return Intent.UNKNOWN, 0.0, {'emotion': 'neutral'}
        else:
            logger.debug(f"Intent retrieved from cache")
        
        return self._message_intent_cache[message]

    def _customer_service_redirect_message(self) -> str:
        return (
            "For dispute resolution, please use the Customer Service button "
            "(top-right or Settings). This assistant lane handles normal conversations only."
        )

    def _is_dispute_request(self, message: str, intent_value: str = '') -> bool:
        if intent_value in {'dispute', 'complaint', 'issue'}:
            return True
        return mode_gate_response(ASSISTANT_MODE_CUSTOMER_SERVICE, message) is None

    def _apply_mode_gate(self, message: str) -> Optional[str]:
        return mode_gate_response(self.assistant_mode, message)

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
                    intro = self.dispute_flow.enter_dispute_mode()
                    return intro

                elif intent.value in ['faq', 'question']:
                    intro = self.faq_flow.enter_faq_mode()
                    return intro

                elif intent.value in ['feedback', 'suggestion', 'praise']:
                    intro = self.feedback_flow.enter_feedback_mode()
                    return intro

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

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and not self._is_dispute_request(message, intent.value):
                return (
                    "Customer Service mode is dedicated to dispute handling. "
                    "Please describe the dispute, product/order affected, and timeline."
                )

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and self._is_dispute_request(message, intent.value):
                return self._customer_service_redirect_message()

            reply, faq_metadata = self.faq_flow.handle_faq_query(message)

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

            gate_reply = self._apply_mode_gate(message)
            if gate_reply:
                return gate_reply

            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            if self.assistant_mode != ASSISTANT_MODE_CUSTOMER_SERVICE and self._is_dispute_request(message, intent.value):
                return self._customer_service_redirect_message()

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and not self._is_dispute_request(message, intent.value):
                return (
                    "Customer Service mode is dedicated to dispute handling. "
                    "Please describe the dispute, product/order affected, and timeline."
                )

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, dispute_metadata = self.dispute_flow.handle_dispute_message(message)

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

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and not self._is_dispute_request(message, intent.value):
                return (
                    "Customer Service mode is dedicated to dispute handling. "
                    "Please describe the dispute, product/order affected, and timeline."
                )

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

    def _handle_chat_mode(self, message: str) -> str:
        try:
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

            if self.assistant_mode == ASSISTANT_MODE_CUSTOMER_SERVICE and not self._is_dispute_request(message, intent.value):
                return (
                    "Customer Service mode is dedicated to dispute handling. "
                    "Please describe the dispute, product/order affected, and timeline."
                )

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            use_context = getattr(settings, 'PHASE1_CONTEXT_INTEGRATION', True)
            
            result = self.query_processor.process(
                message=message,
                user_name=self.get_user_name(),
                context=self.session.context if use_context else {}
            )

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

    def _needs_personalization(self, response: str) -> bool:
        try:
            has_greeting = any(g in response.lower()[:50] for g in ['hi ', 'hello', 'hey', 'good morning', 'good afternoon'])
            has_emoji = any(ord(c) > 0x1F300 for c in response)
            has_markdown = '**' in response or '#' in response
            
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

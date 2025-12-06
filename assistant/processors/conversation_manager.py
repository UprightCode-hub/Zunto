"""
Conversation Manager - REFACTORED with premium AI modules.
Orchestrates multi-turn conversations using modular flow handlers.

NEW FEATURES:
- Premium name detection (multi-language, typo correction)
- Intent classification with emotion detection
- Context tracking and learning
- Response personalization
- Modular flow handlers (greeting, FAQ, dispute, feedback)
- Smart escalation detection

BACKWARD COMPATIBLE: All existing functionality preserved.
"""
import logging
from typing import Dict, Tuple, Optional

from assistant.models import ConversationSession
from assistant.processors.query_processor import QueryProcessor
from assistant.processors.local_model import LocalModelAdapter

# Import AI components
from assistant.ai import (
    detect_name,
    classify_intent,
    ContextManager,
    ResponsePersonalizer
)

# Import flow handlers
from assistant.flows import (
    GreetingFlow,
    FAQFlow,
    DisputeFlow,
    FeedbackFlow
)

# NEW: Import utils
from assistant.utils.constants import (
    STATE_GREETING,
    STATE_AWAITING_NAME,
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
    format_greeting,
    format_menu,
    clean_message
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Premium conversation orchestrator with modular AI system.
    Handles: greeting → name → menu → [FAQ | Dispute | Feedback]
    """
    
    def __init__(self, session_id: str, user_id: int = None):
        """
        Initialize conversation manager with premium modules.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional authenticated user ID
        """
        self.session_id = session_id
        self.user_id = user_id
        self.session = self._get_or_create_session()
        
        # Initialize core processors
        self.query_processor = QueryProcessor()
        self.llm = LocalModelAdapter.get_instance()
        
        # Initialize AI components
        self.context_mgr = ContextManager(self.session)
        self.personalizer = ResponsePersonalizer(self.session)
        
        # Initialize flow handlers
        self.greeting_flow = GreetingFlow(self.session, self.context_mgr)
        self.faq_flow = FAQFlow(self.session, self.query_processor, self.context_mgr)
        self.dispute_flow = DisputeFlow(self.session, self.llm, self.context_mgr)
        self.feedback_flow = FeedbackFlow(self.session, self.context_mgr, intent_classifier=True)
        
        logger.info(f"ConversationManager initialized for session {session_id[:8]}")
    
    def _get_or_create_session(self) -> ConversationSession:
        """Get existing session or create new one with greeting state."""
        session, created = ConversationSession.objects.get_or_create(
            session_id=self.session_id,
            defaults={
                'user_id': self.user_id,
                'current_state': STATE_GREETING,
                'context': {}
            }
        )
        
        if created:
            logger.info(f"New session created: {self.session_id}")
        
        return session
    
    def process_message(self, message: str) -> str:
        """
        Main entry point: process user message and return response.
        
        Args:
            message: User's input message
        
        Returns:
            str: Assistant's response
        """
        # NEW: Validate and sanitize message
        is_valid, error = validate_message(message)
        if not is_valid:
            logger.warning(f"Invalid message: {error}")
            return f"⚠️ {error}"
        
        # NEW: Check for spam
        if is_spam_message(message):
            logger.warning(f"Spam detected: {message[:50]}...")
            return "I'm sorry, but your message appears to be spam. Please try again with a genuine question."
        
        # NEW: Sanitize message
        message = sanitize_message(message)
        message = clean_message(message)
        
        current_state = self.session.current_state
        
        logger.info(f"Processing message in state '{current_state}': {message[:50]}...")
        
        # Route to appropriate handler based on state
        if current_state == STATE_GREETING:
            return self._handle_greeting()
        
        elif current_state == STATE_AWAITING_NAME:
            return self._handle_name_input(message)
        
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
            # Fallback: treat as general query
            logger.warning(f"Unknown state '{current_state}', falling back to query processor")
            return self._handle_chat_mode(message)
    
    def _handle_greeting(self) -> str:
        """
        Handle initial greeting state.
        Uses GreetingFlow for premium welcome experience.
        """
        return self.greeting_flow.start_conversation()
    
    def _handle_name_input(self, message: str) -> str:
        """
        Handle name collection with PREMIUM name detection.
        Replaces old basic capitalization with multi-language detection.
        """
        # Use GreetingFlow
        response, metadata = self.greeting_flow.handle_name_input(message)
        
        # Add to context manager
        if metadata.get('name_detected'):
            self.context_mgr.add_message(
                role='user',
                content=message,
                intent='greeting',
                emotion='neutral'
            )
            
            self.context_mgr.add_message(
                role='assistant',
                content=response,
                confidence=metadata['confidence']
            )
        
        return response
    
    def _handle_menu_selection(self, message: str) -> str:
        """
        Handle menu selection with SMART intent detection.
        
        Logic: Classify intent, then route to appropriate flow.
        Keywords override numbers if present.
        """
        # Classify intent with emotion detection
        intent, confidence, metadata = classify_intent(message, self.session.context)
        emotion = metadata.get('emotion', 'neutral')
        
        logger.info(f"Menu selection: intent={intent.value}, emotion={emotion}, confidence={confidence:.2f}")
        
        # Add user message to context
        self.context_mgr.add_message(
            role='user',
            content=message,
            intent=intent.value,
            emotion=emotion
        )
        
        # Route based on intent
        if intent.value in ['dispute', 'complaint', 'issue']:
            intro = self.dispute_flow.enter_dispute_mode()
            self.context_mgr.add_message('assistant', intro, confidence=1.0)
            return intro
        
        elif intent.value in ['faq', 'question']:
            intro = self.faq_flow.enter_faq_mode()
            self.context_mgr.add_message('assistant', intro, confidence=1.0)
            return intro
        
        elif intent.value in ['feedback', 'suggestion', 'praise']:
            intro = self.feedback_flow.enter_feedback_mode()
            self.context_mgr.add_message('assistant', intro, confidence=1.0)
            return intro
        
        else:
            # User didn't select a menu option - treat as direct query
            self.session.current_state = STATE_CHAT_MODE
            self.session.save()
            return self._handle_chat_mode(message)
    
    def _handle_faq_mode(self, message: str) -> str:
        """
        Handle FAQ queries with 3-tier confidence system.
        Uses FAQFlow with RAG integration (0.03s queries!).
        """
        # Classify intent for emotion tracking
        intent, conf, metadata = classify_intent(message, self.session.context)
        emotion = metadata.get('emotion', 'neutral')
        
        # Add user message to context
        self.context_mgr.add_message(
            role='user',
            content=message,
            intent=intent.value,
            emotion=emotion
        )
        
        # Process through FAQ flow
        reply, faq_metadata = self.faq_flow.handle_faq_query(message)
        
        # Personalize response
        final_reply = self.personalizer.personalize(
            base_response=reply,
            confidence=faq_metadata.get('confidence', 0.5),
            emotion=emotion
        )
        
        # Add assistant response to context
        self.context_mgr.add_message(
            role='assistant',
            content=final_reply,
            confidence=faq_metadata.get('confidence', 0.5)
        )
        
        # Check for escalation
        if self.context_mgr.is_escalated():
            logger.warning("🚨 User escalated in FAQ mode - consider human handoff")
        
        return final_reply
    
    def _handle_dispute_mode(self, message: str) -> str:
        """
        Handle multi-step dispute reporting.
        Uses DisputeFlow with AI draft generation.
        """
        # Classify intent for emotion tracking
        intent, conf, metadata = classify_intent(message, self.session.context)
        emotion = metadata.get('emotion', 'neutral')
        
        # Add user message to context
        self.context_mgr.add_message(
            role='user',
            content=message,
            intent=intent.value,
            emotion=emotion
        )
        
        # Process through dispute flow
        reply, dispute_metadata = self.dispute_flow.handle_dispute_message(message)
        
        # Personalize response (tone: empathetic for disputes)
        final_reply = self.personalizer.personalize(
            base_response=reply,
            confidence=0.9,  # High confidence for templated flow
            emotion=emotion,
            formality='formal'  # Professional tone for disputes
        )
        
        # Add assistant response to context
        self.context_mgr.add_message(
            role='assistant',
            content=final_reply,
            confidence=0.9
        )
        
        # Mark resolution if complete
        if dispute_metadata.get('complete'):
            self.context_mgr.mark_resolution(success=True)
            logger.info(f"Dispute completed: Report #{dispute_metadata.get('report_id')}")
        
        return final_reply
    
    def _handle_feedback_mode(self, message: str) -> str:
        """
        Handle feedback collection with sentiment analysis.
        Uses FeedbackFlow with smart escalation.
        """
        # Classify intent for emotion tracking
        intent, conf, metadata = classify_intent(message, self.session.context)
        emotion = metadata.get('emotion', 'neutral')
        
        # Add user message to context
        self.context_mgr.add_message(
            role='user',
            content=message,
            intent=intent.value,
            emotion=emotion
        )
        
        # Process through feedback flow
        reply, feedback_metadata = self.feedback_flow.handle_feedback_message(message)
        
        # Personalize response (match user's emotion)
        final_reply = self.personalizer.personalize(
            base_response=reply,
            confidence=0.85,
            emotion=emotion
        )
        
        # Add assistant response to context
        self.context_mgr.add_message(
            role='assistant',
            content=final_reply,
            confidence=0.85
        )
        
        # Handle escalation to dispute
        if feedback_metadata.get('action') == 'escalated_to_dispute':
            logger.info("Feedback escalated to dispute mode")
        
        # Mark resolution if complete
        if feedback_metadata.get('complete'):
            self.context_mgr.mark_resolution(
                success=feedback_metadata.get('sentiment') != 'negative'
            )
        
        return final_reply
    
    def _handle_chat_mode(self, message: str) -> str:
        """
        Handle general chat/query mode.
        Uses QueryProcessor with personalization.
        """
        # Classify intent for context
        intent, conf, metadata = classify_intent(message, self.session.context)
        emotion = metadata.get('emotion', 'neutral')
        
        # Add user message to context
        self.context_mgr.add_message(
            role='user',
            content=message,
            intent=intent.value,
            emotion=emotion
        )
        
        # Process through query processor (RAG + LLM)
        result = self.query_processor.process(message)
        
        # Personalize response
        hints = self.context_mgr.get_personalization_hints()
        
        final_reply = self.personalizer.personalize(
            base_response=result['reply'],
            confidence=result['confidence'],
            emotion=emotion,
            formality=hints.get('formality', 'neutral'),
            emoji_level=hints.get('emoji_level', 'moderate')
        )
        
        # Add assistant response to context
        self.context_mgr.add_message(
            role='assistant',
            content=final_reply,
            confidence=result['confidence']
        )
        
        # Mark resolution based on confidence
        if result['confidence'] >= CONFIDENCE_HIGH:
            self.context_mgr.mark_resolution(success=True)
        elif result['confidence'] < CONFIDENCE_MEDIUM:
            self.context_mgr.mark_resolution(success=False)
        
        return final_reply
    
    def get_current_state(self) -> str:
        """Get current conversation state."""
        return self.session.current_state
    
    def get_user_name(self) -> str:
        """Get user's name or default."""
        return self.session.user_name or "there"
    
    def get_conversation_summary(self) -> Dict:
        """
        Get conversation summary for analytics.
        Uses ContextManager for rich insights.
        """
        return self.context_mgr.get_conversation_summary()
    
    def reset_session(self):
        """Reset session to initial greeting state."""
        self.session.current_state = STATE_GREETING
        self.session.user_name = ''
        self.session.context = {}
        self.session.save()
        
        # Reset context manager
        self.context_mgr.reset()
        
        logger.info(f"Session reset: {self.session_id}")


# BACKWARD COMPATIBILITY: Keep old class structure for gradual migration
class LegacyConversationManager(ConversationManager):
    """
    Legacy wrapper for backward compatibility.
    Use ConversationManager directly for new code.
    """
    
    def get_greeting(self) -> Tuple[str, str]:
        """Legacy method - use process_message() instead."""
        message = self._handle_greeting()
        return message, STATE_AWAITING_NAME
    
    def handle_name_input(self, message: str) -> Tuple[str, str]:
        """Legacy method - use process_message() instead."""
        response = self._handle_name_input(message)
        return response, STATE_MENU
    
    def handle_menu_selection(self, message: str) -> Tuple[Optional[str], str, str]:
        """Legacy method - use process_message() instead."""
        response = self._handle_menu_selection(message)
        state = self.session.current_state
        
        # Determine mode from state
        mode_map = {
            STATE_FAQ_MODE: 'faq',
            STATE_DISPUTE_MODE: 'dispute',
            STATE_FEEDBACK_MODE: 'feedback',
            STATE_CHAT_MODE: 'direct_query'
        }
        mode = mode_map.get(state, 'direct_query')
        
        return response, state, mode
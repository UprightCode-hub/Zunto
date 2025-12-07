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
- Portfolio Demo Mode support
- Creator context tracking with follow-ups

BACKWARD COMPATIBLE: All existing functionality preserved.

FIXES (Dec 7, 2024):
- ✅ Fixed detect_name() unpacking error (returns 2 values, not 4)
- ✅ Fixed ConversationLog UUID error (handled in query_processor.py)
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
    
    NEW: Portfolio Demo Mode - Showcases creator skills on LinkedIn
    
    Architecture:
    - Modular AI components (name detection, intent classification, context tracking)
    - Flow-based handlers (greeting, FAQ, dispute, feedback)
    - Smart state management with context awareness
    - Personalized responses based on emotion and conversation history
    """
    
    def __init__(self, session_id: str, user_id: int = None):
        """
        Initialize conversation manager with premium modules.
        
        Args:
            session_id: Unique session identifier (UUID string)
            user_id: Optional authenticated user ID for personalization
        
        Components initialized:
        - QueryProcessor: Handles RAG-based FAQ queries
        - LocalModelAdapter: LLM for dispute drafts
        - ContextManager: Tracks conversation history and emotions
        - ResponsePersonalizer: Adjusts tone and formality
        - Flow Handlers: Greeting, FAQ, Dispute, Feedback
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
        """
        Get existing session or create new one with greeting state.
        
        Returns:
            ConversationSession: Django model instance
        
        Note: New sessions always start in STATE_GREETING
        """
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
            message: User's input message (raw text)
        
        Returns:
            str: Assistant's response (formatted markdown)
        
        Flow:
        1. Validate & sanitize input
        2. Check for spam
        3. Route to state-specific handler
        4. Return personalized response
        
        Validation includes:
        - Length checks (1-2000 chars)
        - Content filtering (profanity, spam)
        - HTML sanitization
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
        
        NEW: Supports Portfolio Mode for LinkedIn demos.
        
        Returns:
            str: Greeting message + name prompt
        
        State transition: GREETING → AWAITING_NAME
        """
        # Check if portfolio mode is enabled
        try:
            from assistant.portfolio_config import is_portfolio_mode, get_portfolio_greeting
            if is_portfolio_mode():
                self.session.current_state = STATE_AWAITING_NAME
                self.session.save()
                return get_portfolio_greeting()
        except ImportError:
            pass  # portfolio_config not available, use standard flow
        
        return self.greeting_flow.start_conversation()
    
    def _handle_name_input(self, message: str) -> str:
        """
        Handle name collection with PREMIUM name detection.
        Replaces old basic capitalization with multi-language detection.
        
        NEW: Supports Portfolio Mode menu.
        
        Args:
            message: User's name input (e.g. "John", "María", "李明")
        
        Returns:
            str: Personalized greeting + menu OR retry prompt
        
        State transition: AWAITING_NAME → MENU (if name detected)
        
        FIXED (Dec 7, 2024):
        - detect_name() now correctly unpacks 2 values instead of 4
        - Old: name, confidence, metadata, extra = detect_name(message)
        - New: name, confidence = detect_name(message)
        """
        # FIXED: detect_name returns (name, confidence) - 2 values only
        name, confidence = detect_name(message)
        
        if name:
            self.session.user_name = name
            self.session.current_state = STATE_MENU
            self.session.save()
            
            # Check for portfolio mode
            try:
                from assistant.portfolio_config import is_portfolio_mode, get_portfolio_menu
                if is_portfolio_mode():
                    response = get_portfolio_menu(name)
                else:
                    response, metadata = self.greeting_flow.handle_name_input(message)
            except ImportError:
                response, metadata = self.greeting_flow.handle_name_input(message)
            
            # Add to context manager for conversation tracking
            self.context_mgr.add_message(
                role='user',
                content=message,
                intent='greeting',
                emotion='neutral'
            )
            
            self.context_mgr.add_message(
                role='assistant',
                content=response,
                confidence=confidence
            )
            
            return response
        
        else:
            # Name not detected - ask again with helpful hint
            return (
                "I didn't quite catch that. Could you please share your name? "
                "(Just your first name is fine!)"
            )
    
    def _handle_menu_selection(self, message: str) -> str:
        """
        Handle menu selection with SMART intent detection.
        
        Logic: 
        1. Check for creator questions FIRST (bypass intent classification)
        2. Classify intent with emotion detection
        3. Route to appropriate flow based on intent
        
        Keywords override numbers if present.
        Example: "I have a problem with my order" → dispute flow (even if user typed "1")
        
        Args:
            message: User's menu choice (number, keyword, or direct query)
        
        Returns:
            str: Flow introduction message OR direct query response
        
        State transitions:
        - MENU → FAQ_MODE (questions, "how do I", etc.)
        - MENU → DISPUTE_MODE (complaints, issues)
        - MENU → FEEDBACK_MODE (suggestions, praise)
        - MENU → CHAT_MODE (creator questions, direct queries)
        """
        # Check for creator/developer questions FIRST (before intent classification)
        from assistant.ai.creator_info import should_mention_creator
        if should_mention_creator(message):
            self.session.current_state = STATE_CHAT_MODE
            self.session.save()
            return self._handle_chat_mode(message)
        
        # Classify intent with emotion detection
        intent, confidence, metadata = classify_intent(message, self.session.context)
        emotion = metadata.get('emotion', 'neutral')
        
        logger.info(f"Menu selection: intent={intent.value}, emotion={emotion}, confidence={confidence:.2f}")
        
        # Add user message to context for tracking
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
        
        Confidence tiers:
        - HIGH (0.8+): Direct answer with source
        - MEDIUM (0.5-0.8): Answer + suggestion to contact support
        - LOW (<0.5): "I don't know" + escalation offer
        
        Args:
            message: User's FAQ question
        
        Returns:
            str: Personalized answer + confidence-based additions
        
        Features:
        - Semantic similarity search
        - Multi-FAQ synthesis
        - Smart escalation detection
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
        
        # Personalize response based on emotion and confidence
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
        
        # Check for escalation (repeated low-confidence queries)
        if self.context_mgr.is_escalated():
            logger.warning("🚨 User escalated in FAQ mode - consider human handoff")
        
        return final_reply
    
    def _handle_dispute_mode(self, message: str) -> str:
        """
        Handle multi-step dispute reporting.
        Uses DisputeFlow with AI draft generation.
        
        Multi-step flow:
        1. Ask for order details
        2. Ask for issue description
        3. Generate professional email draft
        4. Create dispute record
        
        Args:
            message: User's input for current dispute step
        
        Returns:
            str: Next question OR final draft + confirmation
        
        Features:
        - AI-powered email drafting (using LocalModel)
        - Formal tone adjustment
        - Auto-save to database
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
        
        # Personalize response (tone: empathetic + formal for disputes)
        final_reply = self.personalizer.personalize(
            base_response=reply,
            confidence=0.9,
            emotion=emotion,
            formality='formal'
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
        
        Sentiment detection:
        - Positive → Thank + encourage more feedback
        - Neutral → Thank + ask for details
        - Negative → Empathize + offer dispute escalation
        
        Args:
            message: User's feedback message
        
        Returns:
            str: Acknowledgment + next action
        
        Features:
        - Real-time sentiment analysis
        - Auto-escalation to dispute if angry
        - Feedback categorization (bug, feature, praise)
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
        
        NEW: Enhanced creator detection with follow-up tracking.
        
        Args:
            message: User's general question or chat
        
        Returns:
            str: Personalized response with emoji + greeting (if appropriate)
        
        Features:
        - Creator info detection (answers "who made this?")
        - Follow-up question tracking
        - RAG-based knowledge retrieval
        - Confidence-based response styling
        
        Flow:
        1. Check if asking about creator → special response
        2. Classify intent + detect emotion
        3. Query RAG system
        4. Personalize based on conversation history
        5. Track resolution for analytics
        """
        # Check for creator questions FIRST
        from assistant.ai.creator_info import should_mention_creator, get_detailed_creator_response
        
        # Check if asking about creator OR following up on creator topic
        is_creator_query = should_mention_creator(message)
        is_followup = self._is_creator_followup(message)
        
        if is_creator_query or is_followup:
            logger.info(f"🎨 Creator question detected! Responding with Wisdom's info...")
            
            # Determine detail level from query or followup context
            if is_followup:
                detail_level = 'detailed'  # Give more info on followup
            else:
                detail_level = 'balanced'
            
            # Get creator response
            from assistant.ai.creator_info import get_creator_bio, format_creator_card, get_creator_achievements
            
            if 'more' in message.lower() or 'tell me about' in message.lower() or is_followup:
                # Detailed response with achievements
                response = get_creator_bio('detailed', self.session.user_name)
                achievements = get_creator_achievements()
                response += f"\n\n🏆 **Key Achievements:**\n" + "\n".join(f"• {a}" for a in achievements[:3])
            elif 'brief' in message.lower() or 'quick' in message.lower():
                response = get_creator_bio('brief', self.session.user_name)
            else:
                response = get_detailed_creator_response(message, self.session.user_name)
            
            # Mark that we talked about creator (for followup detection)
            self.session.context['last_topic'] = 'creator'
            self.session.context['creator_detail_level'] = detail_level
            self.session.save()
            
            return response
        
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
        
        # Process through query processor WITH user_name for personalization
        result = self.query_processor.process(
            message=message,
            user_name=self.session.user_name or None
        )
        
        # Personalize response
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
        
        # Clear last_topic if we moved to different topic
        if 'last_topic' in self.session.context:
            self.session.context['last_topic'] = None
            self.session.save()
        
        return final_reply
    
    def _is_creator_followup(self, message: str) -> bool:
        """
        Detect if user is following up on creator conversation.
        
        Examples of followup questions:
        - "tell me more"
        - "what else"
        - "his background"
        - "his achievements"
        - "more about him"
        
        Args:
            message: User's message
        
        Returns:
            bool: True if this is a followup on creator topic
        
        Logic:
        - Only returns True if we JUST talked about creator
        - Checks session.context['last_topic'] == 'creator'
        - Matches common followup patterns
        """
        # Only consider followup if we just talked about creator
        last_topic = self.session.context.get('last_topic')
        if last_topic != 'creator':
            return False
        
        message_lower = message.lower()
        
        followup_patterns = [
            'tell me more',
            'more about',
            'what else',
            'his background',
            'his experience',
            'his achievements',
            'his projects',
            'more info',
            'continue',
            'go on',
            'elaborate',
            'details',
            'more details',
        ]
        
        return any(pattern in message_lower for pattern in followup_patterns)
    
    def get_current_state(self) -> str:
        """
        Get current conversation state.
        
        Returns:
            str: One of STATE_* constants
        """
        return self.session.current_state
    
    def get_user_name(self) -> str:
        """
        Get user's name or default.
        
        Returns:
            str: User's name or "there" if not collected yet
        """
        return self.session.user_name or "there"
    
    def get_conversation_summary(self) -> Dict:
        """
        Get conversation summary for analytics.
        Uses ContextManager for rich insights.
        
        Returns:
            Dict with keys:
            - message_count: Total messages exchanged
            - avg_confidence: Average response confidence
            - emotions: List of detected emotions
            - intents: List of detected intents
            - escalated: Whether user needed escalation
            - resolved: Whether query was resolved
            - duration: Conversation duration in seconds
        """
        return self.context_mgr.get_conversation_summary()
    
    def reset_session(self):
        """
        Reset session to initial greeting state.
        Clears all conversation history and context.
        
        Use cases:
        - User wants to start over
        - Testing/debugging
        - Session timeout cleanup
        """
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
    
    This class exists to support old code that uses the legacy API:
    - get_greeting()
    - handle_name_input()
    - handle_menu_selection()
    
    New code should use:
    - process_message() for everything
    """
    
    def get_greeting(self) -> Tuple[str, str]:
        """
        Legacy method - use process_message() instead.
        
        Returns:
            Tuple[str, str]: (greeting_message, next_state)
        """
        message = self._handle_greeting()
        return message, STATE_AWAITING_NAME
    
    def handle_name_input(self, message: str) -> Tuple[str, str]:
        """
        Legacy method - use process_message() instead.
        
        Args:
            message: User's name input
        
        Returns:
            Tuple[str, str]: (response_message, next_state)
        """
        response = self._handle_name_input(message)
        return response, STATE_MENU
    
    def handle_menu_selection(self, message: str) -> Tuple[Optional[str], str, str]:
        """
        Legacy method - use process_message() instead.
        
        Args:
            message: User's menu selection
        
        Returns:
            Tuple[Optional[str], str, str]: (response, state, mode)
        """
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
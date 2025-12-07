"""
Greeting Flow - Premium greeting and name collection handler.
Replaces simple name extraction with intelligent detection and validation.
"""
import logging
from typing import Tuple, Dict, Optional
from assistant.models import ConversationSession
from assistant.ai.name_detector import detect_name
from assistant.ai.response_personalizer import ResponsePersonalizer

logger = logging.getLogger(__name__)


class GreetingFlow:
    """Handles initial greeting and intelligent name collection."""
    
    GREETING_MESSAGE = """Hello! Welcome to Zunto Marketplace! 🎉

I'm Gigi, your virtual assistant. I'm here to help you with anything related to buying, selling, or using our platform.

Before we begin, may I know your name?"""
    
    MENU_TEMPLATE = """Hi {name}! 😊 Great to meet you!

Here's how I can assist you today:

1️⃣ **Report a Dispute** - Report suspicious activity, scams, or problems with sellers/buyers
2️⃣ **Ask FAQ Questions** - Quick answers to common questions about orders, payments, refunds, and more
3️⃣ **Share Feedback** - Tell us about your experience or suggest improvements

Just type **1**, **2**, or **3**, or describe what you need help with!"""
    
    def __init__(self, session: ConversationSession, context_manager=None):
        """
        Initialize greeting flow.
        
        Args:
            session: ConversationSession instance
            context_manager: Optional ContextManager for tracking
        """
        self.session = session
        self.context_manager = context_manager
        self.personalizer = ResponsePersonalizer(session)
    
    def start_conversation(self) -> str:
        """
        Start a new conversation with greeting.
        
        Returns:
            Greeting message
        """
        # Update session state
        self.session.current_state = 'awaiting_name'
        self.session.save()
        
        # Track mode usage
        if self.context_manager:
            self.context_manager.mark_mode_used('greeting')
        
        logger.info(f"Session {self.session.session_id[:8]} - Initial greeting sent")
        
        return self.GREETING_MESSAGE
    
    def handle_initial_greeting(self) -> Tuple[str, str]:
        """
        Send initial greeting and transition to awaiting_name.
        
        Returns: (message, new_state)
        """
        message = self.start_conversation()
        return message, 'awaiting_name'
    
    def handle_name_input(self, message: str) -> Tuple[str, Dict]:
        """
        Premium name extraction with validation and personalization.
        
        Returns: (menu_message, metadata)
        """
        # Use premium name detector
        is_name, detected_name, metadata = detect_name(message, self.session.context)
        
        if is_name and detected_name:
            # Save validated name
            self.session.user_name = detected_name
            self.session.current_state = 'menu'
            
            # Store name metadata in context
            context = self.session.context or {}
            context['name_metadata'] = {
                'original_input': message,
                'detected_name': detected_name,
                'confidence': metadata.get('confidence', 0.0),
                'method': metadata.get('method', 'unknown')
            }
            self.session.context = context
            self.session.save()
            
            # Generate personalized menu
            menu_message = self.MENU_TEMPLATE.format(name=detected_name)
            
            logger.info(
                f"Session {self.session.session_id[:8]} - Name detected: '{detected_name}' "
                f"(confidence: {metadata.get('confidence', 0):.2f}, method: {metadata.get('method')})"
            )
            
            # Add success flag to metadata
            metadata['name_detected'] = True
            
            return menu_message, metadata
        
        else:
            # Name detection failed - ask for clarification
            clarification = self._generate_clarification(metadata)
            
            logger.warning(
                f"Session {self.session.session_id[:8]} - Name detection failed: {metadata.get('reason', 'unknown')}"
            )
            
            # Add failure flag to metadata
            metadata['name_detected'] = False
            
            return clarification, metadata
    
    def _generate_clarification(self, metadata: Dict) -> str:
        """Generate friendly clarification request based on failure reason."""
        reason = metadata.get('reason', 'invalid')
        
        clarifications = {
            'too_long': "That seems a bit long for a name! 😅 Could you share just your first name?",
            'common_word': "I want to make sure I get your name right! Could you tell me your actual name?",
            'no_alpha': "I didn't catch a name there. What should I call you?",
            'empty': "I didn't receive anything. What's your name?",
            'invalid': "I want to address you properly! Could you share your name?"
        }
        
        return clarifications.get(reason, clarifications['invalid'])
    
    def handle_nickname_request(self, message: str) -> Tuple[str, str]:
        """
        Handle "call me X" requests during conversation.
        
        Returns: (response, state)
        """
        # Patterns: "call me X", "my name is X", "I'm X"
        msg_lower = message.lower().strip()
        
        triggers = ['call me', 'my name is', "i'm ", 'im ']
        detected = False
        new_name = None
        
        for trigger in triggers:
            if trigger in msg_lower:
                # Extract name after trigger
                parts = msg_lower.split(trigger, 1)
                if len(parts) == 2:
                    potential_name = parts[1].strip().split()[0]  # First word after trigger
                    
                    # Validate
                    is_name, validated_name, _ = detect_name(potential_name, {})
                    if is_name:
                        new_name = validated_name
                        detected = True
                        break
        
        if detected and new_name:
            old_name = self.session.user_name or "there"
            self.session.user_name = new_name
            self.session.save()
            
            response = f"Got it! I'll call you {new_name} from now on. 😊"
            logger.info(f"Session {self.session.session_id[:8]} - Name updated: {old_name} → {new_name}")
            
            return response, self.session.current_state
        
        else:
            return "", self.session.current_state  # No change
    
    def personalize_greeting(self, emotion: str = 'neutral') -> str:
        """
        Generate personalized greeting based on context and emotion.
        
        Args:
            emotion: Detected emotion from intent classifier
        
        Returns:
            Personalized greeting message
        """
        return self.personalizer.personalize(
            base_response=self.GREETING_MESSAGE,
            confidence=1.0,
            emotion=emotion,
            add_greeting=False,
            add_emoji=True
        )
    
    @staticmethod
    def get_instance(session: ConversationSession, context_manager=None):
        """Factory method."""
        return GreetingFlow(session, context_manager)


# Integration Example
"""
# In conversation_manager.py:

from assistant.flows.greeting_flow import GreetingFlow

class ConversationManager:
    def __init__(self, session_id: str, user_id: int = None):
        self.session_id = session_id
        self.user_id = user_id
        self.session = self._get_or_create_session()
        self.context_mgr = ContextManager(self.session)
        self.greeting_flow = GreetingFlow(self.session, self.context_mgr)
    
    def get_greeting(self) -> Tuple[str, str]:
        return self.greeting_flow.handle_initial_greeting()
    
    def handle_name_input(self, message: str) -> Tuple[str, Dict]:
        menu_msg, metadata = self.greeting_flow.handle_name_input(message)
        return menu_msg, metadata
"""
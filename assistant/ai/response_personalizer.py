"""
Response Personalizer - Advanced response customization engine.
Adapts tone, formality, and content based on user context, emotion, and conversation history.

Features:
- Multi-dimensional tone adjustment (formal ↔ casual, technical ↔ simple)
- Emotion-aware responses (frustrated → empathetic, happy → enthusiastic)
- Context-based personalization (repeat user, first-time, escalation)
- Dynamic emoji usage based on user style
- Confidence-aware explanations (high → brief, low → detailed)
- Cultural/temporal awareness (greetings by time, regional preferences)
"""
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from assistant.models import ConversationSession

logger = logging.getLogger(__name__)


class ResponsePersonalizer:
    """
    Premium response personalization engine.
    Transforms generic responses into contextually appropriate, emotionally intelligent replies.
    """
    
    # Tone templates for different confidence tiers
    HIGH_CONFIDENCE_TEMPLATES = [
        "{greeting} {content}",
        "{content} {emoji}",
        "{greeting} {content} {closing}",
    ]
    
    MEDIUM_CONFIDENCE_TEMPLATES = [
        "{greeting} Based on our FAQs, {content} {clarification}",
        "{content} {emoji} {clarification}",
        "{greeting} {content} Let me know if you need more details!",
    ]
    
    LOW_CONFIDENCE_TEMPLATES = [
        "{greeting} {content} {disclaimer}",
        "{content} {disclaimer} Feel free to ask for clarification!",
        "{greeting} {content} If this doesn't fully answer your question, please let me know!",
    ]
    
    # Emotion-based response modifiers
    EMOTION_MODIFIERS = {
        'frustrated': {
            'prefix': ["I understand this can be frustrating.", "I hear your concern.", "I'm sorry you're experiencing this."],
            'tone': 'empathetic',
            'emoji_multiplier': 0.5,  # Fewer emojis
        },
        'angry': {
            'prefix': ["I sincerely apologize for this experience.", "I understand your frustration.", "This shouldn't have happened."],
            'tone': 'professional',
            'emoji_multiplier': 0.0,  # No emojis
        },
        'confused': {
            'prefix': ["Let me clarify this for you.", "I'll explain this step-by-step.", "Great question!"],
            'tone': 'educational',
            'emoji_multiplier': 0.7,
        },
        'happy': {
            'prefix': ["Glad to help!", "Great!", "Awesome!"],
            'tone': 'enthusiastic',
            'emoji_multiplier': 1.5,
        },
        'neutral': {
            'prefix': ["", "Sure!", "Of course!"],
            'tone': 'balanced',
            'emoji_multiplier': 1.0,
        },
        'urgent': {
            'prefix': ["I understand this is urgent.", "Let's address this quickly."],
            'tone': 'direct',
            'emoji_multiplier': 0.3,
        }
    }
    
    # Contextual greetings based on time and user history
    TIME_GREETINGS = {
        'morning': ["Good morning", "Morning", "Hey there", "Hi"],
        'afternoon': ["Good afternoon", "Afternoon", "Hey", "Hi"],
        'evening': ["Good evening", "Evening", "Hey", "Hi"],
        'night': ["Hello", "Hi", "Hey there"],
    }
    
    # User familiarity levels
    FAMILIARITY_STYLES = {
        'first_time': {
            'greeting': "Welcome to Zunto!",
            'tone': 'warm',
            'detail_level': 'high',
        },
        'returning': {
            'greeting': "Welcome back",
            'tone': 'friendly',
            'detail_level': 'medium',
        },
        'frequent': {
            'greeting': "Hey",
            'tone': 'casual',
            'detail_level': 'low',
        }
    }
    
    # Emoji library by category
    EMOJIS = {
        'positive': ['😊', '👍', '✅', '🎉', '💯', '🙌'],
        'helpful': ['💡', '📚', '🔍', '📝', '✨'],
        'warning': ['⚠️', '🚨', '⚡', '🛡️'],
        'thinking': ['🤔', '💭', '🧠'],
        'support': ['🤝', '💬', '📞', '💌'],
    }
    
    def __init__(self, session: Optional[ConversationSession] = None):
        """
        Initialize personalizer with optional session context.
        
        Args:
            session: ConversationSession for context-aware personalization
        """
        self.session = session
        self.user_name = session.user_name if session else None
        self.context = session.context if session else {}
        self.message_count = len(self.context.get('message_history', []))
    
    def personalize(
        self,
        base_response: str,
        confidence: float,
        emotion: str = 'neutral',
        add_greeting: bool = True,
        add_emoji: bool = True,
        formality: str = 'balanced'  # 'formal', 'balanced', 'casual'
    ) -> str:
        """
        Transform a base response into a personalized, contextually appropriate reply.
        
        Args:
            base_response: Raw response text
            confidence: Confidence score (0-1) from RAG/query processor
            emotion: Detected emotion (frustrated, happy, confused, etc.)
            add_greeting: Whether to add contextual greeting
            add_emoji: Whether to add appropriate emojis
            formality: Desired formality level
        
        Returns:
            Personalized response string
        """
        # Get emotion modifier
        emotion_mod = self.EMOTION_MODIFIERS.get(emotion, self.EMOTION_MODIFIERS['neutral'])
        
        # Build components
        greeting = self._build_greeting(add_greeting, formality) if add_greeting else ""
        content = self._adjust_content_tone(base_response, emotion_mod['tone'], formality)
        emoji = self._select_emoji(confidence, emotion, add_emoji, emotion_mod['emoji_multiplier'])
        clarification = self._build_clarification(confidence)
        disclaimer = self._build_disclaimer(confidence)
        closing = self._build_closing(confidence, emotion)
        
        # Select template based on confidence
        if confidence >= 0.65:
            template = random.choice(self.HIGH_CONFIDENCE_TEMPLATES)
        elif confidence >= 0.40:
            template = random.choice(self.MEDIUM_CONFIDENCE_TEMPLATES)
        else:
            template = random.choice(self.LOW_CONFIDENCE_TEMPLATES)
        
        # Add emotion prefix if applicable
        emotion_prefix = ""
        if emotion in ['frustrated', 'angry', 'urgent'] and emotion_mod['prefix']:
            emotion_prefix = random.choice(emotion_mod['prefix']) + " "
        
        # Format response
        response = template.format(
            greeting=greeting,
            content=content,
            emoji=emoji,
            clarification=clarification,
            disclaimer=disclaimer,
            closing=closing
        ).strip()
        
        # Add emotion prefix
        if emotion_prefix:
            response = emotion_prefix + response
        
        # Clean up extra spaces
        response = ' '.join(response.split())
        
        logger.info(f"Personalized response (confidence: {confidence:.2f}, emotion: {emotion}, formality: {formality})")
        
        return response
    
    def _build_greeting(self, add_greeting: bool, formality: str) -> str:
        """Build contextual greeting based on time and user familiarity."""
        if not add_greeting:
            return ""
        
        # Skip greeting if we just greeted them
        if self.message_count <= 2:
            return ""
        
        # Get time-based greeting
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_period = 'morning'
        elif 12 <= hour < 17:
            time_period = 'afternoon'
        elif 17 <= hour < 21:
            time_period = 'evening'
        else:
            time_period = 'night'
        
        base_greeting = random.choice(self.TIME_GREETINGS[time_period])
        
        # Add name if available
        if self.user_name and formality != 'formal':
            return f"{base_greeting} {self.user_name}!"
        
        return f"{base_greeting}!"
    
    def _adjust_content_tone(self, content: str, tone: str, formality: str) -> str:
        """
        Adjust content tone based on emotion and formality.
        
        Tones: empathetic, professional, educational, enthusiastic, balanced, direct
        """
        # Remove excessive punctuation
        content = content.replace('!!', '!').replace('..', '.')
        
        # Formality adjustments
        if formality == 'formal':
            # Remove casual contractions
            replacements = {
                "don't": "do not",
                "can't": "cannot",
                "won't": "will not",
                "it's": "it is",
                "you're": "you are",
                "we're": "we are",
            }
            for casual, formal in replacements.items():
                content = content.replace(casual, formal)
        
        elif formality == 'casual':
            # Add contractions if not present
            replacements = {
                "do not": "don't",
                "cannot": "can't",
                "will not": "won't",
                "it is": "it's",
                "you are": "you're",
                "we are": "we're",
            }
            for formal, casual in replacements.items():
                content = content.replace(formal, casual)
        
        # Tone-specific adjustments
        if tone == 'empathetic':
            # Soften language
            content = content.replace("You must", "You may want to")
            content = content.replace("You should", "I recommend")
        
        elif tone == 'enthusiastic':
            # Add energy (but don't go overboard)
            if not content.endswith(('!', '?')):
                content += "!"
        
        elif tone == 'direct':
            # Remove filler words
            fillers = [" really", " actually", " basically", " honestly", " literally"]
            for filler in fillers:
                content = content.replace(filler, "")
        
        return content
    
    def _select_emoji(self, confidence: float, emotion: str, add_emoji: bool, multiplier: float) -> str:
        """Select appropriate emoji based on context."""
        if not add_emoji or multiplier == 0.0:
            return ""
        
        # Determine if we should add emoji
        emoji_chance = confidence * multiplier
        if random.random() > emoji_chance:
            return ""
        
        # Select emoji category
        if emotion in ['happy', 'enthusiastic']:
            category = 'positive'
        elif emotion in ['confused', 'thinking']:
            category = 'thinking'
        elif emotion in ['frustrated', 'urgent']:
            category = 'support'
        elif confidence >= 0.65:
            category = 'positive'
        else:
            category = 'helpful'
        
        emoji_list = self.EMOJIS.get(category, self.EMOJIS['helpful'])
        return random.choice(emoji_list)
    
    def _build_clarification(self, confidence: float) -> str:
        """Build clarification text for medium confidence responses."""
        if confidence >= 0.65:
            return ""
        
        clarifications = [
            "Let me know if you need more details!",
            "Does this answer your question?",
            "Feel free to ask for clarification!",
            "Anything else you'd like to know?",
        ]
        
        return random.choice(clarifications)
    
    def _build_disclaimer(self, confidence: float) -> str:
        """Build disclaimer for low confidence responses."""
        if confidence >= 0.40:
            return ""
        
        disclaimers = [
            "However, I recommend contacting support for personalized assistance.",
            "For more specific details, please reach out to our support team.",
            "Our support team can provide more detailed guidance on this.",
        ]
        
        return random.choice(disclaimers)
    
    def _build_closing(self, confidence: float, emotion: str) -> str:
        """Build closing statement based on confidence and emotion."""
        if confidence < 0.50 or emotion in ['frustrated', 'angry', 'urgent']:
            return "Let me know how else I can help!"
        
        closings = [
            "Happy to help!",
            "Hope this helps!",
            "You're all set!",
            "Glad I could assist!",
        ]
        
        return random.choice(closings)
    
    def personalize_menu(self, base_menu: str, user_traits: Dict) -> str:
        """
        Personalize menu display based on user traits.
        
        Args:
            base_menu: Standard menu text
            user_traits: Dict with keys like 'previous_disputes', 'common_questions'
        
        Returns:
            Personalized menu with smart suggestions
        """
        # Add smart suggestions based on history
        suggestions = []
        
        if user_traits.get('previous_disputes', 0) > 0:
            suggestions.append("💡 *Quick tip:* I see you've reported issues before. Feel free to jump straight to option 1 if needed!")
        
        if user_traits.get('frequent_faqs', False):
            suggestions.append("📚 *Pro tip:* You ask great questions! Type 2 to explore our FAQ library.")
        
        if suggestions:
            suggestion_text = "\n\n" + random.choice(suggestions)
            return base_menu + suggestion_text
        
        return base_menu
    
    def personalize_error(self, error_type: str, user_name: Optional[str] = None) -> str:
        """
        Generate personalized error messages.
        
        Args:
            error_type: Type of error (timeout, no_results, system_error, etc.)
            user_name: User's name for personalization
        
        Returns:
            Friendly error message
        """
        name = user_name or self.user_name or "there"
        
        error_templates = {
            'timeout': [
                f"I'm sorry {name}, but that took longer than expected. Please try again!",
                f"Oops {name}! The request timed out. Let's give it another shot.",
            ],
            'no_results': [
                f"I couldn't find a direct answer to that, {name}. Could you rephrase your question?",
                f"Hmm {name}, I don't have info on that specific topic. Can you ask it differently?",
            ],
            'system_error': [
                f"I'm experiencing a technical hiccup, {name}. Please try again in a moment!",
                f"Apologies {name}! Something went wrong on my end. Let's try that again.",
            ],
            'invalid_input': [
                f"I didn't quite understand that, {name}. Could you try rephrasing?",
                f"{name}, I need a bit more info to help you. Can you clarify?",
            ]
        }
        
        templates = error_templates.get(error_type, error_templates['system_error'])
        return random.choice(templates)
    
    def add_context_hint(self, response: str, context_type: str) -> str:
        """
        Add contextual hints to guide user through flows.
        
        Args:
            response: Base response
            context_type: Type of hint (dispute_next, faq_more, feedback_thanks)
        
        Returns:
            Response with appended hint
        """
        hints = {
            'dispute_next': "\n\n💡 *Next:* I'll help you draft a professional message to send to support.",
            'faq_more': "\n\n💡 *Tip:* You can ask follow-up questions or type 'menu' to see other options.",
            'feedback_thanks': "\n\n🙏 *Thank you!* Your feedback helps us serve you better.",
            'back_to_menu': "\n\n🔙 Type 'menu' anytime to see all options.",
        }
        
        hint = hints.get(context_type, "")
        return response + hint
    
    @staticmethod
    def detect_formality_preference(message: str) -> str:
        """
        Detect user's preferred formality level from their message.
        
        Returns: 'formal', 'casual', or 'balanced'
        """
        formal_indicators = ['sir', 'madam', 'kindly', 'please assist', 'would like to', 'could you please']
        casual_indicators = ['hey', 'sup', 'yo', 'wanna', 'gonna', 'yeah', 'nah']
        
        msg_lower = message.lower()
        
        formal_score = sum(1 for indicator in formal_indicators if indicator in msg_lower)
        casual_score = sum(1 for indicator in casual_indicators if indicator in msg_lower)
        
        if formal_score > casual_score:
            return 'formal'
        elif casual_score > formal_score:
            return 'casual'
        else:
            return 'balanced'
    
    @staticmethod
    def get_instance(session: Optional[ConversationSession] = None):
        """Factory method for creating personalizer instance."""
        return ResponsePersonalizer(session)


# Integration Example
"""
# In views.py or conversation_manager.py:

from assistant.ai.response_personalizer import ResponsePersonalizer
from assistant.ai.intent_classifier import classify_intent

# Get response from query processor
result = query_processor.process(user_message)
base_response = result['reply']
confidence = result['confidence']

# Detect emotion from intent classifier
intent, _, metadata = classify_intent(user_message, session.context)
emotion = metadata.get('emotion', 'neutral')

# Detect formality preference
formality = ResponsePersonalizer.detect_formality_preference(user_message)

# Personalize response
personalizer = ResponsePersonalizer(session)
final_response = personalizer.personalize(
    base_response=base_response,
    confidence=confidence,
    emotion=emotion,
    formality=formality
)

# OR for menu personalization:
user_traits = {
    'previous_disputes': session.context.get('dispute_count', 0),
    'frequent_faqs': session.context.get('faq_queries', 0) > 5
}
personalized_menu = personalizer.personalize_menu(menu_text, user_traits)
"""
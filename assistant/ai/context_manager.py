"""
Context Manager - Premium conversation context tracking and learning.
Tracks message history, user traits, sentiment, and provides personalization hints.

Features:
- Message history tracking (with compression for long conversations)
- User trait learning (preferences, communication style, common issues)
- Sentiment tracking and shift detection
- Personalization hints for response_personalizer
- Escalation detection (frustration, urgency patterns)
- DB persistence via ConversationSession.context
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, deque

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Premium context manager for conversation state and user profiling.
    Syncs with ConversationSession.context for database persistence.
    """
    
    # Configuration
    MAX_HISTORY_MESSAGES = 20  # Keep last 20 messages in memory
    SENTIMENT_WINDOW = 5       # Track sentiment over last 5 messages
    ESCALATION_THRESHOLD = 3   # 3 negative messages = escalation
    
    # Sentiment keywords
    POSITIVE_KEYWORDS = {
        'thanks', 'thank', 'great', 'good', 'excellent', 'perfect', 'amazing',
        'helpful', 'appreciate', 'love', 'awesome', 'wonderful', '😊', '👍',
        '🙏', '❤️', 'happy', 'satisfied'
    }
    
    NEGATIVE_KEYWORDS = {
        'bad', 'terrible', 'worst', 'awful', 'horrible', 'hate', 'angry',
        'frustrated', 'annoying', 'useless', 'stupid', 'disappointed',
        'unhappy', 'dissatisfied', '😠', '😡', '👎', 'scam', 'fraud'
    }
    
    URGENCY_KEYWORDS = {
        'urgent', 'asap', 'immediately', 'now', 'emergency', 'critical',
        'help', 'please', 'quickly', 'hurry', 'fast'
    }
    
    def __init__(self, session):
        """
        Initialize context manager with session.
        
        Args:
            session: ConversationSession instance
        """
        self.session = session
        self.context = session.context or {}
        
        # Initialize context structure if new session
        if not self.context:
            self._initialize_context()
            self._save()
    
    def _initialize_context(self):
        """Initialize fresh context structure."""
        self.context = {
            # Message history (compressed for performance)
            'history': [],
            
            # User traits
            'traits': {
                'name': self.session.user_name or '',
                'formality_preference': 'neutral',  # formal, neutral, casual
                'emoji_preference': 'moderate',     # none, minimal, moderate, high
                'response_length_preference': 'medium',  # short, medium, long
                'common_topics': [],
                'common_intents': [],
                'language_hints': []  # Detected non-English words
            },
            
            # Sentiment tracking
            'sentiment': {
                'current': 'neutral',
                'history': [],  # List of (message_num, sentiment) tuples
                'shifts': [],   # List of sentiment shift events
                'overall_satisfaction': 0.5  # 0-1 scale
            },
            
            # Escalation tracking
            'escalation': {
                'level': 0,  # 0=calm, 1-2=concerned, 3+=escalated
                'negative_streak': 0,
                'last_escalation': None,
                'triggers': []
            },
            
            # Session metadata
            'metadata': {
                'message_count': 0,
                'session_start': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat(),
                'topics_discussed': [],
                'modes_used': [],  # faq_mode, dispute_mode, etc.
                'successful_resolutions': 0,
                'failed_queries': 0
            }
        }
    
    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        emotion: Optional[str] = None,
        confidence: float = 0.0
    ):
        """
        Add message to conversation history.
        
        Args:
            role: 'user' or 'assistant'
            content: Message text
            intent: Detected intent (from intent_classifier)
            emotion: Detected emotion (from intent_classifier)
            confidence: Response confidence score
        """
        message_num = self.context['metadata']['message_count'] + 1
        
        # Create message entry
        message = {
            'num': message_num,
            'role': role,
            'content': content[:500],  # Truncate for storage
            'timestamp': datetime.now().isoformat(),
            'intent': intent,
            'emotion': emotion,
            'confidence': confidence
        }
        
        # Add to history (rolling window)
        history = self.context.get('history', [])
        history.append(message)
        
        # Keep only last MAX_HISTORY_MESSAGES
        if len(history) > self.MAX_HISTORY_MESSAGES:
            history = history[-self.MAX_HISTORY_MESSAGES:]
        
        self.context['history'] = history
        self.context['metadata']['message_count'] = message_num
        self.context['metadata']['last_active'] = datetime.now().isoformat()
        
        # Update traits from user messages
        if role == 'user':
            self._update_traits(content, intent)
            self._track_sentiment(content, emotion, message_num)
        
        self._save()
        logger.info(f"Message {message_num} added ({role}): {content[:50]}...")
    
    def _update_traits(self, content: str, intent: Optional[str]):
        """Learn user traits from message."""
        traits = self.context['traits']
        
        # Update common intents
        if intent:
            intents = traits.get('common_intents', [])
            intents.append(intent)
            # Keep top 5 most common
            intent_counts = Counter(intents)
            traits['common_intents'] = [i for i, _ in intent_counts.most_common(5)]
        
        # Detect formality preference
        formal_indicators = ['please', 'could you', 'would you', 'may i']
        casual_indicators = ['hey', 'hi', 'sup', 'yeah', 'yep', 'cool']
        
        content_lower = content.lower()
        formal_score = sum(1 for ind in formal_indicators if ind in content_lower)
        casual_score = sum(1 for ind in casual_indicators if ind in content_lower)
        
        if formal_score > casual_score:
            traits['formality_preference'] = 'formal'
        elif casual_score > formal_score:
            traits['formality_preference'] = 'casual'
        
        # Detect emoji usage
        emoji_count = sum(1 for char in content if ord(char) > 0x1F300)
        msg_length = len(content.split())
        
        if emoji_count == 0:
            traits['emoji_preference'] = 'none'
        elif emoji_count / max(msg_length, 1) < 0.1:
            traits['emoji_preference'] = 'minimal'
        elif emoji_count / max(msg_length, 1) < 0.2:
            traits['emoji_preference'] = 'moderate'
        else:
            traits['emoji_preference'] = 'high'
        
        self.context['traits'] = traits
    
    def _track_sentiment(self, content: str, emotion: Optional[str], message_num: int):
        """Track sentiment and detect shifts."""
        content_lower = content.lower()
        words = set(content_lower.split())
        
        # Calculate sentiment score
        positive_count = len(words & self.POSITIVE_KEYWORDS)
        negative_count = len(words & self.NEGATIVE_KEYWORDS)
        urgency_count = len(words & self.URGENCY_KEYWORDS)
        
        # Determine sentiment
        if emotion in ['angry', 'frustrated']:
            sentiment = 'negative'
        elif emotion in ['happy', 'excited']:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        elif positive_count > negative_count:
            sentiment = 'positive'
        else:
            sentiment = 'neutral'
        
        # Add to history
        sentiment_data = self.context['sentiment']
        sentiment_data['current'] = sentiment
        
        history = sentiment_data.get('history', [])
        history.append((message_num, sentiment))
        
        # Keep only recent window
        if len(history) > self.SENTIMENT_WINDOW:
            history = history[-self.SENTIMENT_WINDOW:]
        
        sentiment_data['history'] = history
        
        # Update overall satisfaction
        recent_sentiments = [s for _, s in history]
        positive_ratio = recent_sentiments.count('positive') / len(recent_sentiments)
        negative_ratio = recent_sentiments.count('negative') / len(recent_sentiments)
        
        sentiment_data['overall_satisfaction'] = (
            positive_ratio * 1.0 + 
            (1 - negative_ratio - positive_ratio) * 0.5
        )
        
        # Detect sentiment shifts
        if len(recent_sentiments) >= 3:
            if recent_sentiments[-3] == 'positive' and sentiment == 'negative':
                sentiment_data['shifts'].append({
                    'message_num': message_num,
                    'from': 'positive',
                    'to': 'negative',
                    'timestamp': datetime.now().isoformat()
                })
                logger.warning(f"Sentiment shift detected: positive → negative at msg {message_num}")
        
        self.context['sentiment'] = sentiment_data
        
        # Update escalation tracking
        self._track_escalation(sentiment, urgency_count > 0, message_num)
    
    def _track_escalation(self, sentiment: str, is_urgent: bool, message_num: int):
        """Track escalation patterns."""
        escalation = self.context['escalation']
        
        # Update negative streak
        if sentiment == 'negative':
            escalation['negative_streak'] += 1
        else:
            escalation['negative_streak'] = 0
        
        # Calculate escalation level
        level = 0
        if escalation['negative_streak'] >= self.ESCALATION_THRESHOLD:
            level = 2
        elif escalation['negative_streak'] >= 2:
            level = 1
        
        if is_urgent:
            level += 1
        
        escalation['level'] = min(level, 3)
        
        # Record escalation events
        if level >= 2:
            escalation['last_escalation'] = datetime.now().isoformat()
            escalation['triggers'].append({
                'message_num': message_num,
                'level': level,
                'reason': f"negative_streak={escalation['negative_streak']}, urgent={is_urgent}",
                'timestamp': datetime.now().isoformat()
            })
            logger.warning(f"🚨 Escalation level {level} detected at message {message_num}")
        
        self.context['escalation'] = escalation
    
    def get_personalization_hints(self) -> Dict:
        """
        Get hints for response_personalizer.
        
        Returns:
            {
                'formality': str,
                'emoji_level': str,
                'tone_adjustments': dict,
                'context_cues': list
            }
        """
        traits = self.context['traits']
        sentiment = self.context['sentiment']
        escalation = self.context['escalation']
        
        hints = {
            'formality': traits.get('formality_preference', 'neutral'),
            'emoji_level': traits.get('emoji_preference', 'moderate'),
            'tone_adjustments': {},
            'context_cues': []
        }
        
        # Adjust tone based on sentiment
        if sentiment['current'] == 'negative':
            hints['tone_adjustments']['empathy'] = 'high'
            hints['tone_adjustments']['formality'] = 'increase'
        
        # Add escalation warnings
        if escalation['level'] >= 2:
            hints['context_cues'].append('user_escalated')
            hints['tone_adjustments']['urgency_acknowledgment'] = True
        
        # Add satisfaction cues
        if sentiment['overall_satisfaction'] < 0.4:
            hints['context_cues'].append('user_dissatisfied')
        
        # Add conversation length cues
        msg_count = self.context['metadata']['message_count']
        if msg_count > 10:
            hints['context_cues'].append('long_conversation')
        
        return hints
    
    def is_escalated(self) -> bool:
        """Check if user is escalated (frustrated/urgent)."""
        return self.context['escalation']['level'] >= 2
    
    def get_conversation_summary(self) -> Dict:
        """Get summary of conversation for admin dashboard."""
        return {
            'message_count': self.context['metadata']['message_count'],
            'duration_minutes': self._calculate_duration(),
            'user_name': self.context['traits']['name'],
            'current_state': self.session.current_state,
            'sentiment': self.context['sentiment']['current'],
            'satisfaction_score': self.context['sentiment']['overall_satisfaction'],
            'escalation_level': self.context['escalation']['level'],
            'common_intents': self.context['traits'].get('common_intents', []),
            'topics_discussed': self.context['metadata'].get('topics_discussed', [])
        }
    
    def _calculate_duration(self) -> int:
        """Calculate conversation duration in minutes."""
        try:
            start = datetime.fromisoformat(self.context['metadata']['session_start'])
            now = datetime.now()
            return int((now - start).total_seconds() / 60)
        except:
            return 0
    
    def mark_topic_discussed(self, topic: str):
        """Mark a topic as discussed (e.g., 'refund', 'shipping', 'dispute')."""
        topics = self.context['metadata'].get('topics_discussed', [])
        if topic not in topics:
            topics.append(topic)
            self.context['metadata']['topics_discussed'] = topics
            self._save()
    
    def mark_mode_used(self, mode: str):
        """Mark a mode as used (e.g., 'faq_mode', 'dispute_mode')."""
        modes = self.context['metadata'].get('modes_used', [])
        if mode not in modes:
            modes.append(mode)
            self.context['metadata']['modes_used'] = modes
            self._save()
    
    def mark_resolution(self, success: bool):
        """Mark query resolution as success or failure."""
        if success:
            self.context['metadata']['successful_resolutions'] += 1
        else:
            self.context['metadata']['failed_queries'] += 1
        self._save()
    
    def _save(self):
        """Persist context to session."""
        self.session.context = self.context
        self.session.save(update_fields=['context', 'updated_at'])
    
    def reset(self):
        """Reset context (for testing or manual reset)."""
        self._initialize_context()
        self._save()
        logger.info(f"Context reset for session {self.session.session_id}")


# Integration example
"""
# In conversation_manager.py or views.py:

from assistant.ai.context_manager import ContextManager
from assistant.ai.intent_classifier import classify_intent

# Initialize context manager
context_mgr = ContextManager(session)

# Add user message
intent, confidence, metadata = classify_intent(user_message, session.context)
emotion = metadata.get('emotion', 'neutral')

context_mgr.add_message(
    role='user',
    content=user_message,
    intent=intent,
    emotion=emotion
)

# Process query
result = query_processor.process(user_message)

# Add assistant response
context_mgr.add_message(
    role='assistant',
    content=result['reply'],
    confidence=result['confidence']
)

# Get personalization hints for response_personalizer
from assistant.ai.response_personalizer import ResponsePersonalizer
personalizer = ResponsePersonalizer(session)
hints = context_mgr.get_personalization_hints()

final_response = personalizer.personalize(
    base_response=result['reply'],
    confidence=result['confidence'],
    emotion=emotion,
    formality=hints['formality'],
    emoji_level=hints['emoji_level']
)

# Check for escalation
if context_mgr.is_escalated():
    logger.warning("🚨 User is escalated - consider human handoff")
    # Optional: Add escalation flag to response
"""
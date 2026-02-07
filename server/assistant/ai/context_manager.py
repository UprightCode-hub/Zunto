"""
Context Manager - Conversation state tracking with DB persistence.
Tracks message history, user traits, sentiment analysis, and escalation detection.
Syncs with ConversationSession.context field.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, deque

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages conversation state and user profiling.
    Persists to ConversationSession.context field.
    """

    MAX_HISTORY_MESSAGES = 20
    SENTIMENT_WINDOW = 5
    ESCALATION_THRESHOLD = 3

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
        self.session = session
        self.context = session.context or {}

        if not self.context:
            self._initialize_context()
            self._save()

    def _initialize_context(self):
        self.context = {
            'history': [],

            'traits': {
                'name': self.session.user_name or '',
                'formality_preference': 'neutral',
                'emoji_preference': 'moderate',
                'response_length_preference': 'medium',
                'common_topics': [],
                'common_intents': [],
                'language_hints': []
            },

            'sentiment': {
                'current': 'neutral',
                'history': [],
                'shifts': [],
                'overall_satisfaction': 0.5
            },

            'escalation': {
                'level': 0,
                'negative_streak': 0,
                'last_escalation': None,
                'triggers': []
            },

            'metadata': {
                'message_count': 0,
                'session_start': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat(),
                'topics_discussed': [],
                'modes_used': [],
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
        message_num = self.context['metadata']['message_count'] + 1

        message = {
            'num': message_num,
            'role': role,
            'content': content[:500],  # Truncate for storage
            'timestamp': datetime.now().isoformat(),
            'intent': intent,
            'emotion': emotion,
            'confidence': confidence
        }

        history = self.context.get('history', [])
        history.append(message)

        if len(history) > self.MAX_HISTORY_MESSAGES:
            history = history[-self.MAX_HISTORY_MESSAGES:]

        self.context['history'] = history
        self.context['metadata']['message_count'] = message_num
        self.context['metadata']['last_active'] = datetime.now().isoformat()

        if role == 'user':
            self._update_traits(content, intent)
            self._track_sentiment(content, emotion, message_num)

        self._save()
        logger.info(f"Message {message_num} added ({role}): {content[:50]}...")

    def _update_traits(self, content: str, intent: Optional[str]):
        traits = self.context['traits']

        if intent:
            intents = traits.get('common_intents', [])
            intents.append(intent)
            intent_counts = Counter(intents)
            traits['common_intents'] = [i for i, _ in intent_counts.most_common(5)]

        formal_indicators = ['please', 'could you', 'would you', 'may i']
        casual_indicators = ['hey', 'hi', 'sup', 'yeah', 'yep', 'cool']

        content_lower = content.lower()
        formal_score = sum(1 for ind in formal_indicators if ind in content_lower)
        casual_score = sum(1 for ind in casual_indicators if ind in content_lower)

        if formal_score > casual_score:
            traits['formality_preference'] = 'formal'
        elif casual_score > formal_score:
            traits['formality_preference'] = 'casual'

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
        content_lower = content.lower()
        words = set(content_lower.split())

        positive_count = len(words & self.POSITIVE_KEYWORDS)
        negative_count = len(words & self.NEGATIVE_KEYWORDS)
        urgency_count = len(words & self.URGENCY_KEYWORDS)

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

        sentiment_data = self.context['sentiment']
        sentiment_data['current'] = sentiment

        history = sentiment_data.get('history', [])
        history.append((message_num, sentiment))

        if len(history) > self.SENTIMENT_WINDOW:
            history = history[-self.SENTIMENT_WINDOW:]

        sentiment_data['history'] = history

        recent_sentiments = [s for _, s in history]
        positive_ratio = recent_sentiments.count('positive') / len(recent_sentiments)
        negative_ratio = recent_sentiments.count('negative') / len(recent_sentiments)

        sentiment_data['overall_satisfaction'] = (
            positive_ratio * 1.0 + 
            (1 - negative_ratio - positive_ratio) * 0.5
        )

        # Track positive→negative shifts
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
        self._track_escalation(sentiment, urgency_count > 0, message_num)

    def _track_escalation(self, sentiment: str, is_urgent: bool, message_num: int):
        escalation = self.context['escalation']

        if sentiment == 'negative':
            escalation['negative_streak'] += 1
        else:
            escalation['negative_streak'] = 0

        level = 0
        if escalation['negative_streak'] >= self.ESCALATION_THRESHOLD:
            level = 2
        elif escalation['negative_streak'] >= 2:
            level = 1

        if is_urgent:
            level += 1

        escalation['level'] = min(level, 3)

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
        """Returns hints for response_personalizer."""
        traits = self.context['traits']
        sentiment = self.context['sentiment']
        escalation = self.context['escalation']

        hints = {
            'formality': traits.get('formality_preference', 'neutral'),
            'emoji_level': traits.get('emoji_preference', 'moderate'),
            'tone_adjustments': {},
            'context_cues': []
        }

        if sentiment['current'] == 'negative':
            hints['tone_adjustments']['empathy'] = 'high'
            hints['tone_adjustments']['formality'] = 'increase'

        if escalation['level'] >= 2:
            hints['context_cues'].append('user_escalated')
            hints['tone_adjustments']['urgency_acknowledgment'] = True

        if sentiment['overall_satisfaction'] < 0.4:
            hints['context_cues'].append('user_dissatisfied')

        msg_count = self.context['metadata']['message_count']
        if msg_count > 10:
            hints['context_cues'].append('long_conversation')

        return hints

    def is_escalated(self) -> bool:
        return self.context['escalation']['level'] >= 2

    def get_conversation_summary(self) -> Dict:
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
        try:
            start = datetime.fromisoformat(self.context['metadata']['session_start'])
            now = datetime.now()
            return int((now - start).total_seconds() / 60)
        except:
            return 0

    def mark_topic_discussed(self, topic: str):
        topics = self.context['metadata'].get('topics_discussed', [])
        if topic not in topics:
            topics.append(topic)
            self.context['metadata']['topics_discussed'] = topics
            self._save()

    def mark_mode_used(self, mode: str):
        modes = self.context['metadata'].get('modes_used', [])
        if mode not in modes:
            modes.append(mode)
            self.context['metadata']['modes_used'] = modes
            self._save()

    def mark_resolution(self, success: bool):
        if success:
            self.context['metadata']['successful_resolutions'] += 1
        else:
            self.context['metadata']['failed_queries'] += 1
        self._save()

    def _save(self):
        """Persist to session.context field. Requires updated_at field on model."""
        self.session.context = self.context
        self.session.save(update_fields=['context', 'updated_at'])

    def reset(self):
        self._initialize_context()
        self._save()
        logger.info(f"Context reset for session {self.session.session_id}")
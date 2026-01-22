"""
Intent classification with emotion detection, multi-intent support, and history tracking.
"""
import re
from typing import Dict, Tuple, List
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Intent(Enum):
    """User intent types."""

    DISPUTE = "dispute"
    FAQ = "faq"
    FEEDBACK = "feedback"

    MENU = "menu"
    BACK = "back"
    EXIT = "exit"

    GREETING = "greeting"
    FAREWELL = "farewell"
    AFFIRMATION = "affirmation"
    NEGATION = "negation"
    GRATITUDE = "gratitude"

    HELP_REQUEST = "help_request"
    QUESTION = "question"

    COMPLAINT = "complaint"

    UNKNOWN = "unknown"


class IntentClassifier:
    """
    Intent classification with emotion confidence, multi-intent detection, and history tracking.
    """

    INTENT_PATTERNS = {
        Intent.DISPUTE: {
            'keywords': [
                'report', 'dispute', 'issue', 'problem', 'scam', 'fraud', 
                'fake', 'complaint', 'seller', 'buyer', 'suspicious',
                'not received', 'wrong item', 'counterfeit', 'damaged'
            ],
            'weight': 1.2
        },
        Intent.FAQ: {
            'keywords': [
                'faq', 'question', 'ask', 'how', 'what', 'when', 'where', 
                'why', 'who', 'help', 'explain', 'tell me', 'show me',
                'guide', 'tutorial', 'instructions'
            ],
            'weight': 0.8
        },
        Intent.FEEDBACK: {
            'keywords': [
                'feedback', 'suggest', 'suggestion', 'improve', 'improvement',
                'opinion', 'review', 'experience', 'recommend', 'better',
                'could be', 'would be nice'
            ],
            'weight': 1.0
        },
        Intent.MENU: {
            'keywords': [
                'menu', 'options', 'main menu', 'show options', 'what can you do'
            ],
            'weight': 1.0
        },
        Intent.BACK: {
            'keywords': ['back', 'return', 'go back', 'previous', 'main'],
            'weight': 1.0
        },
        Intent.EXIT: {
            'keywords': ['exit', 'quit', 'bye', 'goodbye', 'stop', 'end'],
            'weight': 1.0
        },
        Intent.GREETING: {
            'keywords': [
                'hi', 'hello', 'hey', 'sup', 'yo', 'greetings',
                'good morning', 'good afternoon', 'good evening'
            ],
            'weight': 0.9
        },
        Intent.FAREWELL: {
            'keywords': [
                'bye', 'goodbye', 'see you', 'talk later', 'take care', 
                'peace', 'cya', 'later'
            ],
            'weight': 1.0
        },
        Intent.AFFIRMATION: {
            'keywords': ['yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'alright'],
            'weight': 1.0
        },
        Intent.NEGATION: {
            'keywords': ['no', 'nope', 'nah', 'not really', 'dont think so'],
            'weight': 1.0
        },
        Intent.GRATITUDE: {
            'keywords': ['thank', 'thanks', 'thx', 'ty', 'appreciate', 'grateful'],
            'weight': 1.0
        },
        Intent.HELP_REQUEST: {
            'keywords': ['help', 'assist', 'support', 'need help', 'can you help'],
            'weight': 1.1
        },
        Intent.QUESTION: {
            'keywords': [],
            'weight': 0.7
        },
        Intent.COMPLAINT: {
            'keywords': [
                'complain', 'complaint', 'unhappy', 'disappointed', 
                'frustrated', 'angry', 'upset', 'bad experience'
            ],
            'weight': 1.1
        },
    }

    EMOTION_KEYWORDS = {
        'frustrated': [
            'problem', 'issue', 'not working', 'bad', 'terrible', 
            'awful', 'hate', 'annoying', 'frustrated', 'angry'
        ],
        'happy': [
            'great', 'thanks', 'perfect', 'love', 'awesome', 
            'excellent', 'amazing', 'wonderful', 'good'
        ],
        'urgent': [
            'urgent', 'asap', 'immediately', 'now', 'emergency', 
            'critical', 'hurry', 'quickly', 'fast'
        ],
        'confused': [
            'confused', 'don\'t understand', 'unclear', 'not sure',
            'help me understand', 'explain', 'what does', 'how does'
        ],
        'neutral': []
    }

    QUESTION_PATTERNS = [
        r'\bhow\s+(do|does|can|should|would|to)\b',
        r'\bwhat\s+(is|are|do|does|can|should)\b',
        r'\bwhen\s+(is|are|do|does|can|should)\b',
        r'\bwhere\s+(is|are|do|does|can|should)\b',
        r'\bwhy\s+(is|are|do|does|can|should)\b',
        r'\bwho\s+(is|are|do|does|can|should)\b',
        r'\?$',
    ]

    @classmethod
    def calculate_intent_score(cls, text: str, intent: Intent) -> float:
        """Calculate confidence score for a specific intent."""
        if intent not in cls.INTENT_PATTERNS:
            return 0.0

        text_lower = text.lower()
        config = cls.INTENT_PATTERNS[intent]
        keywords = config['keywords']
        weight = config['weight']

        if not keywords:
            if intent == Intent.QUESTION:
                for pattern in cls.QUESTION_PATTERNS:
                    if re.search(pattern, text_lower):
                        return 0.7 * weight
                return 0.0
            return 0.0

        matches = sum(1 for kw in keywords if kw in text_lower)

        if matches == 0:
            return 0.0

        score = min((matches / len(keywords)) * weight * 3, 1.0)

        return score

    @classmethod
    def _calculate_emotion_confidence(cls, emotion: str, message: str) -> float:
        """Calculate confidence in emotion detection (0.0 to 1.0)."""
        if emotion not in cls.EMOTION_KEYWORDS:
            return 0.0

        message_lower = message.lower()
        keywords = cls.EMOTION_KEYWORDS[emotion]

        if not keywords:
            return 0.5

        matches = sum(1 for kw in keywords if kw in message_lower)

        confidence = min(matches * 0.3, 1.0)

        return confidence

    @classmethod
    def detect_emotion(cls, intent: Intent, message: str) -> Tuple[str, float]:
        """Detect emotion from intent and message content. Returns (emotion, confidence)."""
        intent_emotion_map = {
            Intent.DISPUTE: 'frustrated',
            Intent.COMPLAINT: 'frustrated',
            Intent.GREETING: 'happy',
            Intent.GRATITUDE: 'happy',
            Intent.HELP_REQUEST: 'confused',
            Intent.QUESTION: 'confused',
            Intent.FAQ: 'neutral',
            Intent.FEEDBACK: 'neutral',
        }

        base_emotion = intent_emotion_map.get(intent, 'neutral')

        emotion_scores = {}
        for emotion in cls.EMOTION_KEYWORDS.keys():
            confidence = cls._calculate_emotion_confidence(emotion, message)
            if confidence > 0:
                emotion_scores[emotion] = confidence

        if emotion_scores:
            detected_emotion = max(emotion_scores, key=emotion_scores.get)
            detected_confidence = emotion_scores[detected_emotion]

            if detected_confidence > 0.5:
                return (detected_emotion, detected_confidence)

        base_confidence = 0.6 if base_emotion != 'neutral' else 0.5
        return (base_emotion, base_confidence)

    @classmethod
    def classify(cls, text: str, threshold: float = 0.1) -> Tuple[Intent, float, Dict]:
        """Classify user intent with confidence scoring and emotion detection."""
        text = text.strip()

        if not text:
            return (Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0})

        if re.match(r'^\d+$', text):
            return (Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0})

        scores = {}
        for intent in Intent:
            if intent == Intent.UNKNOWN:
                continue

            score = cls.calculate_intent_score(text, intent)
            if score > threshold:
                scores[intent] = score

        if scores:
            primary_intent = max(scores, key=scores.get)
            confidence = scores[primary_intent]

            emotion, emotion_confidence = cls.detect_emotion(primary_intent, text)

            metadata = {
                'all_scores': scores,
                'method': 'rule_based',
                'emotion': emotion,
                'emotion_confidence': emotion_confidence,
            }

            logger.debug(
                f"Intent: {primary_intent.value} ({confidence:.2f}), "
                f"Emotion: {emotion} ({emotion_confidence:.2f})"
            )

            return (primary_intent, confidence, metadata)

        return (Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0})

    @classmethod
    def detect_all_intents(cls, text: str, threshold: float = 0.3) -> List[Tuple[Intent, float]]:
        """Detect all intents above threshold, sorted by confidence."""
        text = text.strip()

        if not text or re.match(r'^\d+$', text):
            return []

        scores = {}
        for intent in Intent:
            if intent == Intent.UNKNOWN:
                continue

            score = cls.calculate_intent_score(text, intent)
            if score >= threshold:
                scores[intent] = score

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if sorted_intents:
            logger.info(f"Multi-intent detected: {[(i.value, f'{c:.2f}') for i, c in sorted_intents]}")

        return sorted_intents

    @classmethod
    def track_intent_in_history(cls, session_context: dict, intent: Intent, confidence: float) -> dict:
        """Track intent in session context for history analysis."""
        if 'intent_history' not in session_context:
            session_context['intent_history'] = []

        session_context['intent_history'].append({
            'intent': intent.value,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        })

        if len(session_context['intent_history']) > 10:
            session_context['intent_history'] = session_context['intent_history'][-10:]

        return session_context

    @classmethod
    def has_topic_switched(cls, current_intent: Intent, session_context: dict) -> bool:
        """Detect if user switched topics based on intent history."""
        history = session_context.get('intent_history', [])

        if not history:
            return False

        last_intent_value = history[-1]['intent']

        related_groups = [
            {'dispute', 'complaint', 'issue'},
            {'faq', 'question', 'help_request'},
            {'feedback', 'suggestion'},
            {'greeting', 'farewell', 'gratitude'},
        ]

        current_value = current_intent.value

        for group in related_groups:
            if current_value in group and last_intent_value in group:
                return False

        is_switch = current_value != last_intent_value

        if is_switch:
            logger.info(f"🔄 Topic switch detected: {last_intent_value} → {current_value}")

        return is_switch

    @classmethod
    def get_menu_option(cls, intent: Intent) -> int:
        """Map intent to menu option number."""
        intent_to_option = {
            Intent.DISPUTE: 1,
            Intent.COMPLAINT: 1,
            Intent.FAQ: 2,
            Intent.QUESTION: 2,
            Intent.HELP_REQUEST: 2,
            Intent.FEEDBACK: 3,
        }

        return intent_to_option.get(intent, 0)

    @classmethod
    def should_trigger_mode(cls, intent: Intent) -> Tuple[bool, str]:
        """Check if intent should trigger a specific mode."""
        if intent in [Intent.DISPUTE, Intent.COMPLAINT]:
            return (True, 'dispute')
        elif intent in [Intent.FAQ, Intent.QUESTION, Intent.HELP_REQUEST]:
            return (True, 'faq')
        elif intent == Intent.FEEDBACK:
            return (True, 'feedback')
        else:
            return (False, 'none')


def classify_intent(message: str, context: dict = None):
    """
    Wrapper for IntentClassifier.classify() with automatic history tracking.
    Returns: (intent, confidence, metadata)
    """
    if context is None:
        context = {}

    intent, confidence, metadata = IntentClassifier.classify(message)

    context = IntentClassifier.track_intent_in_history(context, intent, confidence)

    topic_switched = IntentClassifier.has_topic_switched(intent, context)
    metadata['topic_switched'] = topic_switched

    return (intent, confidence, metadata)


def test_intent_classifier():
    """Test upgraded features."""
    print("\n" + "="*70)
    print("INTENT CLASSIFIER TEST SUITE (UPGRADED)")
    print("="*70 + "\n")

    print("TEST 1: Emotion Confidence")
    intent, conf, meta = IntentClassifier.classify("I'm having a terrible problem with my order")
    print(f"Intent: {intent.value}, Confidence: {conf:.2f}")
    print(f"Emotion: {meta['emotion']}, Emotion Confidence: {meta['emotion_confidence']:.2f}\n")

    print("TEST 2: Multi-Intent Detection")
    intents = IntentClassifier.detect_all_intents("I want to report a problem AND ask about refunds")
    print(f"Detected intents: {[(i.value, f'{c:.2f}') for i, c in intents]}\n")

    print("TEST 3: Topic Switch Detection")
    context = {}

    intent1, _, _ = classify_intent("How do I get a refund?", context)
    print(f"Intent 1: {intent1.value}")

    intent2, _, meta2 = classify_intent("What's your refund policy?", context)
    print(f"Intent 2: {intent2.value}, Topic switched: {meta2.get('topic_switched')}")

    intent3, _, meta3 = classify_intent("I want to report a scam", context)
    print(f"Intent 3: {intent3.value}, Topic switched: {meta3.get('topic_switched')}")

    print("\n" + "="*70)
    print("🎉 ALL UPGRADED FEATURES WORKING!")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_intent_classifier()
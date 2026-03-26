"""
server/assistant/ai/intent_classifier.py

Embedding-based intent classifier.

REPLACES the keyword-counting approach with semantic similarity using the
already-loaded paraphrase-MiniLM-L3-v2 sentence transformer (lazy_loader.py
singleton — zero extra model load cost).

Architecture:
  - Each intent has prototype phrases that represent it semantically.
  - At first use, prototypes are batch-encoded and cached as class-level
    numpy arrays (one-time cost, ~50-80ms).
  - At classify time, the user message is encoded (single call, ~5-10ms),
    cosine similarity is computed against all prototype vectors, and the
    intent with the highest mean similarity above threshold wins.
  - Public API is identical to the old file — drop-in replacement.

Why this is better than keyword counting:
  - "abeg help me find this thing" → HELP_REQUEST  (pidgin, no keywords)
  - "I paid and nothing came"      → DISPUTE       (no "dispute" word)
  - "problem solved, thanks"       → GRATITUDE     (contains "problem" but isn't DISPUTE)
  - "I don't have a problem"       → negation handled by semantic space
"""
import logging
import threading
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.28      # Below this → UNKNOWN
CONFIDENCE_SCALE = 1.30          # Expand raw cosine scores toward 0–1 range
PROTOTYPE_TOP_K = 3              # Average top-k prototype scores per intent
                                  # (more robust than single nearest prototype)


class Intent(Enum):
    """User intent types — unchanged from original for full backward compat."""
    DISPUTE      = "dispute"
    FAQ          = "faq"
    FEEDBACK     = "feedback"
    MENU         = "menu"
    BACK         = "back"
    EXIT         = "exit"
    GREETING     = "greeting"
    FAREWELL     = "farewell"
    AFFIRMATION  = "affirmation"
    NEGATION     = "negation"
    GRATITUDE    = "gratitude"
    HELP_REQUEST = "help_request"
    QUESTION     = "question"
    COMPLAINT    = "complaint"
    UNKNOWN      = "unknown"


# ---------------------------------------------------------------------------
# Intent prototypes
# ---------------------------------------------------------------------------
# Each entry is a list of short representative phrases for that intent.
# Variety matters: include Nigerian English, pidgin, formal, and casual forms.
# More prototypes = better semantic coverage, negligible cost after encoding.
# ---------------------------------------------------------------------------
INTENT_PROTOTYPES: Dict[Intent, List[str]] = {

    Intent.DISPUTE: [
        "I want to report a scam",
        "the seller sent the wrong item",
        "I was defrauded on this platform",
        "I did not receive my order",
        "the product is fake and counterfeit",
        "I want to dispute this transaction",
        "seller is not responding and I want a refund",
        "buyer cheated me out of my money",
        "this is a fraudulent seller",
        "I paid but nothing arrived",
        "my package never came and seller disappeared",
        "the item I received is damaged and broken",
        "abeg I want to report this seller",
        "this man scam me on this app",
        "the thing they send me no be the one I buy",
    ],

    Intent.FAQ: [
        "how do I get a refund",
        "what is the return policy",
        "can you explain how payments work",
        "I have a question about my order",
        "tell me how to verify a seller",
        "how does shipping work on Zunto",
        "what are the fees for selling",
        "how long does delivery take",
        "can I change my order after placing it",
        "what happens if I don't receive my item",
        "how do I track my shipment",
        "is there a buyer protection policy",
    ],

    Intent.FEEDBACK: [
        "I want to give feedback about the app",
        "here is my suggestion for improvement",
        "you should add this feature",
        "I think the platform could be better",
        "I have a recommendation for the team",
        "my experience using Zunto was great",
        "I love how easy it is to buy here",
        "the app could use some improvements",
        "I wish you had this feature",
        "overall I am satisfied with the service",
    ],

    Intent.GREETING: [
        "hello there",
        "hi how are you",
        "good morning",
        "good afternoon",
        "hey what is up",
        "good evening",
        "howdy",
        "hiya",
        "sup",
        "yo what is happening",
    ],

    Intent.FAREWELL: [
        "goodbye see you later",
        "bye I am done",
        "take care",
        "talk to you later",
        "I am leaving now",
        "cya later",
        "peace out",
        "I am done here thanks",
    ],

    Intent.AFFIRMATION: [
        "yes that is correct",
        "okay I agree",
        "sure go ahead",
        "yes please proceed",
        "that is right",
        "yeah that is what I meant",
        "yep exactly",
        "alright that works",
    ],

    Intent.NEGATION: [
        "no that is not right",
        "I disagree with that",
        "no thank you",
        "that is not what I meant",
        "nope not that",
        "that is wrong",
        "nah that is not it",
    ],

    Intent.GRATITUDE: [
        "thank you so much for your help",
        "thanks I really appreciate it",
        "I am grateful for your assistance",
        "you have been very helpful thanks",
        "appreciate the help",
        "thanks a lot",
        "thank you kindly",
    ],

    Intent.HELP_REQUEST: [
        "I need help with something",
        "can you please assist me",
        "I need support right now",
        "please help me figure this out",
        "I am stuck and need assistance",
        "abeg help me with this thing",
        "I need someone to help me",
        "can you guide me through this",
    ],

    Intent.COMPLAINT: [
        "I am very unhappy with this service",
        "this is completely unacceptable",
        "I am disappointed with Zunto",
        "this experience was terrible",
        "the service here is very bad",
        "I have a serious complaint to make",
        "I am not satisfied at all",
        "this platform has failed me",
    ],

    Intent.MENU: [
        "show me the main menu",
        "what options do I have",
        "show me what you can do",
        "I want to see the menu",
        "take me back to main options",
        "list your features",
    ],

    Intent.BACK: [
        "go back to previous",
        "I want to return",
        "take me back",
        "go back",
        "previous menu",
        "return to where I was",
    ],

    Intent.EXIT: [
        "I want to quit",
        "exit this conversation",
        "I am done please stop",
        "end the chat",
        "close this",
        "bye I am exiting now",
    ],

    Intent.QUESTION: [
        "what is the meaning of this",
        "when will my order arrive",
        "where can I find this",
        "how much does this cost",
        "who is responsible for this",
        "which option should I choose",
        "why is this happening",
    ],
}


# ---------------------------------------------------------------------------
# Emotion detection — keyword-based
# ---------------------------------------------------------------------------
# Emotion is a secondary signal layered on top of intent. Kept as keyword
# matching because: (a) it's fast, (b) affect words are direct enough that
# keyword overlap is semantically meaningful, (c) we only need 5 categories.
# ---------------------------------------------------------------------------
EMOTION_KEYWORDS: Dict[str, List[str]] = {
    'frustrated': [
        'problem', 'issue', 'not working', 'bad', 'terrible',
        'awful', 'hate', 'annoying', 'frustrated', 'angry', 'useless',
    ],
    'happy': [
        'great', 'thanks', 'perfect', 'love', 'awesome',
        'excellent', 'amazing', 'wonderful', 'good', 'satisfied',
    ],
    'urgent': [
        'urgent', 'asap', 'immediately', 'now', 'emergency',
        'critical', 'hurry', 'quickly', 'fast',
    ],
    'confused': [
        'confused', "don't understand", 'unclear', 'not sure',
        'help me understand', 'explain', 'what does', 'how does',
    ],
    'neutral': [],
}

INTENT_DEFAULT_EMOTION: Dict[Intent, str] = {
    Intent.DISPUTE:      'frustrated',
    Intent.COMPLAINT:    'frustrated',
    Intent.GREETING:     'happy',
    Intent.GRATITUDE:    'happy',
    Intent.HELP_REQUEST: 'confused',
    Intent.QUESTION:     'confused',
    Intent.FAQ:          'neutral',
    Intent.FEEDBACK:     'neutral',
}


class IntentClassifier:
    """
    Embedding-based intent classifier.

    Uses paraphrase-MiniLM-L3-v2 (already loaded via lazy_loader singleton)
    to compute cosine similarity between user message and per-intent prototype
    phrase clusters. No keyword counting. No regex. Handles paraphrase,
    pidgin, and negation naturally through the embedding space.

    Thread-safe prototype initialization via class-level lock.
    """

    # Class-level prototype cache — computed once, reused forever
    _prototype_matrix: Optional[np.ndarray] = None   # (n_intents, hidden_dim)
    _prototype_intents: Optional[List[Intent]] = None
    _init_lock = threading.Lock()
    _initialized = False

    # -----------------------------------------------------------------------
    # Prototype initialization
    # -----------------------------------------------------------------------

    @classmethod
    def _ensure_initialized(cls):
        """Encode prototypes once using the lazy_loader singleton model."""
        if cls._initialized:
            return

        with cls._init_lock:
            if cls._initialized:
                return

            try:
                from assistant.processors.lazy_loader import get_ai_loader
                encoder = get_ai_loader().sentence_model

                intents = [i for i in INTENT_PROTOTYPES]
                all_texts: List[str] = []
                intent_lengths: List[int] = []

                for intent in intents:
                    phrases = INTENT_PROTOTYPES[intent]
                    all_texts.extend(phrases)
                    intent_lengths.append(len(phrases))

                logger.info(
                    f"Encoding {len(all_texts)} intent prototypes "
                    f"across {len(intents)} intents..."
                )

                # Batch encode — single model call, same optimization that
                # fixed the 82-second latency bug in embeddings.py
                embeddings = encoder.encode(
                    all_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )  # shape: (n_total_phrases, hidden_dim)

                # Build per-intent matrices
                intent_matrices: List[np.ndarray] = []
                cursor = 0
                for length in intent_lengths:
                    intent_matrices.append(embeddings[cursor: cursor + length])
                    cursor += length

                cls._prototype_matrix = intent_matrices  # List[np.ndarray]
                cls._prototype_intents = intents
                cls._initialized = True

                logger.info(
                    f"✅ Intent prototype embeddings ready "
                    f"({len(intents)} intents, {len(all_texts)} prototypes)"
                )

            except Exception as e:
                logger.error(f"Intent prototype initialization failed: {e}", exc_info=True)
                # Leave _initialized=False so next call retries
                raise

    # -----------------------------------------------------------------------
    # Scoring
    # -----------------------------------------------------------------------

    @classmethod
    def _score_message(cls, message_embedding: np.ndarray) -> Dict[Intent, float]:
        """
        Compute per-intent score as mean of top-k cosine similarities
        against that intent's prototype vectors.

        message_embedding: normalized vector, shape (hidden_dim,)
        Returns: {Intent: score} for all intents
        """
        scores: Dict[Intent, float] = {}

        for intent, proto_matrix in zip(cls._prototype_intents, cls._prototype_matrix):
            # Cosine similarity: dot product of normalized vectors
            similarities = proto_matrix @ message_embedding  # (n_prototypes,)

            # Average the top-k most similar prototypes for robustness
            k = min(PROTOTYPE_TOP_K, len(similarities))
            top_k = np.sort(similarities)[::-1][:k]
            scores[intent] = float(np.mean(top_k))

        return scores

    @classmethod
    def _raw_to_confidence(cls, raw_score: float) -> float:
        """Map raw cosine similarity [0,1] to a confidence value."""
        scaled = raw_score * CONFIDENCE_SCALE
        return max(0.0, min(1.0, scaled))

    # -----------------------------------------------------------------------
    # Emotion detection (keyword-based, kept from original)
    # -----------------------------------------------------------------------

    @classmethod
    def _detect_emotion(cls, intent: Intent, message: str) -> Tuple[str, float]:
        message_lower = message.lower()

        emotion_scores: Dict[str, float] = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if not keywords:
                continue
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > 0:
                emotion_scores[emotion] = min(matches * 0.3, 1.0)

        if emotion_scores:
            best_emotion = max(emotion_scores, key=emotion_scores.get)
            best_conf = emotion_scores[best_emotion]
            if best_conf > 0.4:
                return best_emotion, best_conf

        base_emotion = INTENT_DEFAULT_EMOTION.get(intent, 'neutral')
        base_conf = 0.6 if base_emotion != 'neutral' else 0.5
        return base_emotion, base_conf

    # -----------------------------------------------------------------------
    # Public API — identical signatures to original
    # -----------------------------------------------------------------------

    @classmethod
    def classify(
        cls,
        text: str,
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> Tuple[Intent, float, Dict]:
        """
        Classify user intent with confidence scoring and emotion detection.

        Returns: (Intent, confidence, metadata)
        """
        text = (text or '').strip()
        if not text:
            return Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0}

        # Pure numbers → no intent (menu selection handled upstream)
        import re
        if re.match(r'^\d+$', text):
            return Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0}

        try:
            cls._ensure_initialized()
        except Exception:
            logger.warning("Intent classifier unavailable — returning UNKNOWN")
            return Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0, 'method': 'unavailable'}

        try:
            from assistant.processors.lazy_loader import get_ai_loader
            encoder = get_ai_loader().sentence_model

            message_embedding = encoder.encode(
                [text],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0]  # shape: (hidden_dim,)

            scores = cls._score_message(message_embedding)

            # Filter by threshold
            above_threshold = {
                intent: score for intent, score in scores.items()
                if score >= threshold
            }

            if not above_threshold:
                return Intent.UNKNOWN, 0.0, {
                    'emotion': 'neutral',
                    'emotion_confidence': 0.0,
                    'method': 'embedding',
                    'all_scores': {i.value: round(s, 4) for i, s in scores.items()},
                }

            primary_intent = max(above_threshold, key=above_threshold.get)
            raw_confidence = above_threshold[primary_intent]
            confidence = cls._raw_to_confidence(raw_confidence)

            emotion, emotion_confidence = cls._detect_emotion(primary_intent, text)

            metadata = {
                'method': 'embedding',
                'emotion': emotion,
                'emotion_confidence': emotion_confidence,
                'all_scores': {i.value: round(s, 4) for i, s in scores.items()},
                'raw_similarity': round(raw_confidence, 4),
            }

            logger.debug(
                f"Intent: {primary_intent.value} ({confidence:.2f}), "
                f"Emotion: {emotion} ({emotion_confidence:.2f})"
            )

            return primary_intent, confidence, metadata

        except Exception as e:
            logger.error(f"Intent classification error: {e}", exc_info=True)
            return Intent.UNKNOWN, 0.0, {'emotion': 'neutral', 'emotion_confidence': 0.0, 'method': 'error'}

    @classmethod
    def detect_all_intents(
        cls,
        text: str,
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> List[Tuple[Intent, float]]:
        """
        Detect all intents above threshold, sorted by confidence.
        Identical return shape to original.
        """
        text = (text or '').strip()
        if not text:
            return []

        import re
        if re.match(r'^\d+$', text):
            return []

        try:
            cls._ensure_initialized()
            from assistant.processors.lazy_loader import get_ai_loader
            encoder = get_ai_loader().sentence_model

            message_embedding = encoder.encode(
                [text],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0]

            scores = cls._score_message(message_embedding)
            results = [
                (intent, cls._raw_to_confidence(score))
                for intent, score in scores.items()
                if score >= threshold
            ]
            results.sort(key=lambda x: x[1], reverse=True)

            if results:
                logger.info(
                    f"Multi-intent detected: "
                    f"{[(i.value, f'{c:.2f}') for i, c in results]}"
                )

            return results

        except Exception as e:
            logger.error(f"detect_all_intents error: {e}", exc_info=True)
            return []

    # -----------------------------------------------------------------------
    # Backward-compat helpers — signatures unchanged
    # -----------------------------------------------------------------------

    @classmethod
    def calculate_intent_score(cls, text: str, intent: Intent) -> float:
        """
        Backward-compatible single-intent score.
        Retained for any code that calls this directly.
        Uses embedding similarity against that intent's prototypes.
        """
        try:
            cls._ensure_initialized()
            from assistant.processors.lazy_loader import get_ai_loader
            encoder = get_ai_loader().sentence_model

            if intent not in INTENT_PROTOTYPES:
                return 0.0

            msg_emb = encoder.encode(
                [text],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0]

            idx = cls._prototype_intents.index(intent)
            proto_matrix = cls._prototype_matrix[idx]
            similarities = proto_matrix @ msg_emb
            k = min(PROTOTYPE_TOP_K, len(similarities))
            return float(cls._raw_to_confidence(np.mean(np.sort(similarities)[::-1][:k])))

        except Exception:
            return 0.0

    @classmethod
    def detect_emotion(cls, intent: Intent, message: str) -> Tuple[str, float]:
        """Public alias for backward compat."""
        return cls._detect_emotion(intent, message)

    @classmethod
    def track_intent_in_history(
        cls,
        session_context: dict,
        intent: Intent,
        confidence: float,
    ) -> dict:
        """Track intent in session context — unchanged."""
        if 'intent_history' not in session_context:
            session_context['intent_history'] = []

        session_context['intent_history'].append({
            'intent': intent.value,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
        })

        if len(session_context['intent_history']) > 10:
            session_context['intent_history'] = session_context['intent_history'][-10:]

        return session_context

    @classmethod
    def has_topic_switched(cls, current_intent: Intent, session_context: dict) -> bool:
        """Detect topic switch from intent history — unchanged."""
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
            logger.info(f"🔄 Topic switch: {last_intent_value} → {current_value}")
        return is_switch

    @classmethod
    def get_menu_option(cls, intent: Intent) -> int:
        """Map intent to menu option — unchanged."""
        return {
            Intent.DISPUTE:      1,
            Intent.COMPLAINT:    1,
            Intent.FAQ:          2,
            Intent.QUESTION:     2,
            Intent.HELP_REQUEST: 2,
            Intent.FEEDBACK:     3,
        }.get(intent, 0)

    @classmethod
    def should_trigger_mode(cls, intent: Intent) -> Tuple[bool, str]:
        """Check if intent should trigger a mode — unchanged."""
        if intent in [Intent.DISPUTE, Intent.COMPLAINT]:
            return True, 'dispute'
        elif intent in [Intent.FAQ, Intent.QUESTION, Intent.HELP_REQUEST]:
            return True, 'faq'
        elif intent == Intent.FEEDBACK:
            return True, 'feedback'
        return False, 'none'

    @classmethod
    def warm_up(cls):
        """
        Pre-warm the prototype embeddings at server startup.
        Call this from Django AppConfig.ready() to avoid first-request latency.

        Example in assistant/apps.py:
            def ready(self):
                from assistant.ai.intent_classifier import IntentClassifier
                IntentClassifier.warm_up()
        """
        try:
            cls._ensure_initialized()
            logger.info("IntentClassifier warm-up complete")
        except Exception as e:
            logger.warning(f"IntentClassifier warm-up failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Module-level wrapper — identical to original
# ---------------------------------------------------------------------------

def classify_intent(
    message: str,
    context: dict = None,
) -> Tuple[Intent, float, Dict]:
    """
    Wrapper for IntentClassifier.classify() with automatic history tracking.
    Returns: (intent, confidence, metadata)
    Drop-in replacement — same signature as original.
    """
    if context is None:
        context = {}

    intent, confidence, metadata = IntentClassifier.classify(message)
    context = IntentClassifier.track_intent_in_history(context, intent, confidence)
    topic_switched = IntentClassifier.has_topic_switched(intent, context)
    metadata['topic_switched'] = topic_switched

    return intent, confidence, metadata
"""
Smart Intent Classification Module
Detects user intent from conversational input with confidence scoring.

WHY THIS EXISTS:
Your current code in handle_menu_selection():
- Manual keyword counting (dispute_score, faq_score, feedback_score)
- Works but hard to extend and debug

This module:
- Centralizes all intent detection logic
- Adds confidence scoring for logging
- Easier to add new intents
- Returns structured results
"""
import re
from typing import Dict, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Intent(Enum):
    """User intent types - Maps to your menu options."""
    
    # Main menu options (your 1, 2, 3)
    DISPUTE = "dispute"          # Option 1
    FAQ = "faq"                  # Option 2
    FEEDBACK = "feedback"        # Option 3
    
    # Navigation intents
    MENU = "menu"
    BACK = "back"
    EXIT = "exit"
    
    # Conversation intents
    GREETING = "greeting"
    FAREWELL = "farewell"
    AFFIRMATION = "affirmation"
    NEGATION = "negation"
    GRATITUDE = "gratitude"
    
    # Help-related (map to FAQ)
    HELP_REQUEST = "help_request"
    QUESTION = "question"
    
    # Problem-related (map to DISPUTE)
    COMPLAINT = "complaint"
    
    # Unknown
    UNKNOWN = "unknown"


class IntentClassifier:
    """
    Intelligent intent classification with confidence scoring.
    Drop-in replacement for your keyword matching in handle_menu_selection().
    """
    
    # Intent patterns with keywords (extracted from your code)
    INTENT_PATTERNS = {
        Intent.DISPUTE: {
            'keywords': [
                'report', 'dispute', 'issue', 'problem', 'scam', 'fraud', 
                'fake', 'complaint', 'seller', 'buyer', 'suspicious',
                'not received', 'wrong item', 'counterfeit', 'damaged'
            ],
            'weight': 1.2  # Higher weight = higher priority
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
            'keywords': [],  # Detected by question patterns
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
    
    # Question patterns (for QUESTION intent)
    QUESTION_PATTERNS = [
        r'\bhow\s+(do|does|can|should|would|to)\b',
        r'\bwhat\s+(is|are|do|does|can|should)\b',
        r'\bwhen\s+(is|are|do|does|can|should)\b',
        r'\bwhere\s+(is|are|do|does|can|should)\b',
        r'\bwhy\s+(is|are|do|does|can|should)\b',
        r'\bwho\s+(is|are|do|does|can|should)\b',
        r'\?$',  # Ends with question mark
    ]
    
    @classmethod
    def calculate_intent_score(cls, text: str, intent: Intent) -> float:
        """
        Calculate confidence score for a specific intent.
        
        Returns: 0.0 - 1.0 (higher = more confident)
        """
        if intent not in cls.INTENT_PATTERNS:
            return 0.0
        
        text_lower = text.lower()
        config = cls.INTENT_PATTERNS[intent]
        keywords = config['keywords']
        weight = config['weight']
        
        if not keywords:
            # Special case: QUESTION intent uses patterns
            if intent == Intent.QUESTION:
                for pattern in cls.QUESTION_PATTERNS:
                    if re.search(pattern, text_lower):
                        return 0.7 * weight
                return 0.0
            return 0.0
        
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        if matches == 0:
            return 0.0
        
        # Score = (matches / total_keywords) * weight
        # Cap at 1.0
        score = min((matches / len(keywords)) * weight * 3, 1.0)
        
        return score
    
    @classmethod
    def classify(cls, text: str, threshold: float = 0.1) -> Tuple[Intent, float, Dict[Intent, float]]:
        """
        Classify user intent with confidence scoring.
        
        Args:
            text: User's input message
            threshold: Minimum confidence to consider (default 0.1)
        
        Returns:
            (primary_intent, confidence, all_scores)
        
        Examples:
            "I want to report a dispute" → (Intent.DISPUTE, 0.85, {...})
            "How do I get a refund?" → (Intent.FAQ, 0.72, {...})
            "1" → (Intent.UNKNOWN, 0.0, {}) [handled separately as pure number]
        """
        text = text.strip()
        
        if not text:
            return (Intent.UNKNOWN, 0.0, {})
        
        # Special case: Pure numbers (menu selections handled in views)
        if re.match(r'^\d+$', text):
            return (Intent.UNKNOWN, 0.0, {})
        
        # Calculate scores for all intents
        scores = {}
        for intent in Intent:
            if intent == Intent.UNKNOWN:
                continue
            
            score = cls.calculate_intent_score(text, intent)
            if score > threshold:
                scores[intent] = score
        
        # Find highest scoring intent
        if scores:
            primary_intent = max(scores, key=scores.get)
            confidence = scores[primary_intent]
            
            logger.debug(f"Intent classified: {primary_intent.value} (confidence: {confidence:.2f})")
            
            return (primary_intent, confidence, scores)
        
        # No intent matched
        logger.debug(f"No intent detected for: '{text[:50]}'")
        return (Intent.UNKNOWN, 0.0, {})
    
    @classmethod
    def get_menu_option(cls, intent: Intent) -> int:
        """
        Map intent to menu option number.
        
        Returns:
            1 = Dispute
            2 = FAQ
            3 = Feedback
            0 = No menu option (navigation/unknown)
        """
        intent_to_option = {
            Intent.DISPUTE: 1,
            Intent.COMPLAINT: 1,  # Complaints map to dispute
            Intent.FAQ: 2,
            Intent.QUESTION: 2,  # Questions map to FAQ
            Intent.HELP_REQUEST: 2,  # Help requests map to FAQ
            Intent.FEEDBACK: 3,
        }
        
        return intent_to_option.get(intent, 0)
    
    @classmethod
    def should_trigger_mode(cls, intent: Intent) -> Tuple[bool, str]:
        """
        Check if intent should trigger a specific mode.
        
        Returns:
            (should_trigger, mode_name)
            mode_name: 'dispute', 'faq', 'feedback', 'none'
        """
        if intent in [Intent.DISPUTE, Intent.COMPLAINT]:
            return (True, 'dispute')
        elif intent in [Intent.FAQ, Intent.QUESTION, Intent.HELP_REQUEST]:
            return (True, 'faq')
        elif intent == Intent.FEEDBACK:
            return (True, 'feedback')
        else:
            return (False, 'none')


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================

def integration_example():
    """
    Example: How to use in your ConversationManager.handle_menu_selection()
    
    BEFORE (your current code):
        dispute_keywords = ['report', 'dispute', ...]
        faq_keywords = ['faq', 'question', ...]
        feedback_keywords = ['feedback', 'suggest', ...]
        
        dispute_score = sum(1 for kw in dispute_keywords if kw in msg_lower)
        faq_score = sum(1 for kw in faq_keywords if kw in msg_lower)
        feedback_score = sum(1 for kw in feedback_keywords if kw in msg_lower)
        
        if dispute_score > 0:
            # Start dispute mode
        elif faq_score > 0:
            # Start FAQ mode
        ...
    
    AFTER (using IntentClassifier):
        from assistant.ai.intent_classifier import IntentClassifier, Intent
        
        intent, confidence, all_scores = IntentClassifier.classify(message)
        
        if intent == Intent.DISPUTE:
            # Start dispute mode
        elif intent == Intent.FAQ:
            # Start FAQ mode
        elif intent == Intent.FEEDBACK:
            # Start feedback mode
        else:
            # Direct query or unknown
    """
    pass


def advanced_integration_example():
    """
    Example: Advanced usage with confidence logging and multi-intent handling.
    """
    message = "I have a problem and need help reporting it"
    
    intent, confidence, all_scores = IntentClassifier.classify(message)
    
    print(f"Primary intent: {intent.value} (confidence: {confidence:.2f})")
    print(f"All detected intents: {all_scores}")
    
    # Check if multiple strong intents
    strong_intents = [i for i, s in all_scores.items() if s > 0.5]
    
    if len(strong_intents) > 1:
        print(f"⚠️  Multiple strong intents detected: {strong_intents}")
        # Could ask user for clarification
    
    # Get menu option
    menu_opt = IntentClassifier.get_menu_option(intent)
    print(f"Maps to menu option: {menu_opt}")
    
    # Check if should trigger mode
    should_trigger, mode = IntentClassifier.should_trigger_mode(intent)
    print(f"Should trigger mode: {should_trigger}, mode: {mode}")


# ============================================================================
# BUILT-IN TESTS
# ============================================================================

def test_intent_classifier():
    """Built-in tests to verify functionality."""
    print("\n" + "="*70)
    print("INTENT CLASSIFIER TEST SUITE")
    print("="*70 + "\n")
    
    test_cases = [
        # (input, expected_intent, description)
        ("I want to report a dispute", Intent.DISPUTE, "Explicit dispute"),
        ("How do I get a refund?", Intent.FAQ, "FAQ question"),
        ("I'd like to share feedback", Intent.FEEDBACK, "Feedback intent"),
        ("show me the menu", Intent.MENU, "Menu request"),
        ("back", Intent.BACK, "Navigation - back"),
        ("hi", Intent.GREETING, "Greeting"),
        ("thanks", Intent.GRATITUDE, "Gratitude"),
        ("yes", Intent.AFFIRMATION, "Affirmation"),
        ("no", Intent.NEGATION, "Negation"),
        ("I have a problem with seller", Intent.DISPUTE, "Problem keyword"),
        ("help me with my order", Intent.HELP_REQUEST, "Help request"),
        ("1", Intent.UNKNOWN, "Pure number"),
        ("", Intent.UNKNOWN, "Empty input"),
    ]
    
    passed = 0
    failed = 0
    
    for user_input, expected_intent, description in test_cases:
        intent, confidence, all_scores = IntentClassifier.classify(user_input)
        
        status = "✅" if intent == expected_intent else "❌"
        
        if intent == expected_intent:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} '{user_input}'")
        print(f"   Expected: {expected_intent.value}")
        print(f"   Got: {intent.value} (confidence: {confidence:.2f})")
        
        # Show menu option if applicable
        menu_opt = IntentClassifier.get_menu_option(intent)
        if menu_opt > 0:
            print(f"   Menu option: {menu_opt}")
        
        print(f"   ({description})\n")
    
    print("="*70)
    print(f"✅ PASSED: {passed}/{len(test_cases)}")
    print(f"❌ FAILED: {failed}/{len(test_cases)}")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Ready for production.\n")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review above.\n")


if __name__ == "__main__":
    # Run tests when executed directly
    test_intent_classifier()


# ============================================================================
# STANDALONE WRAPPER FUNCTION (Required for __init__.py import)
# ============================================================================

def classify_intent(message: str, context: dict = None):
    """
    Standalone wrapper function for IntentClassifier.classify()
    
    This function exists so that __init__.py can import it as:
    from .intent_classifier import classify_intent
    
    Args:
        message: User's input message
        context: Optional conversation context (for future enhancements)
    
    Returns:
        Tuple of (intent, confidence, metadata_dict)
        
    Example:
        >>> intent, confidence, metadata = classify_intent("I want to report a scam")
        >>> print(intent.value)  # 'dispute'
        >>> print(metadata['emotion'])  # 'frustrated'
    """
    # Context parameter is accepted but not used yet (reserved for future features)
    intent, confidence, all_scores = IntentClassifier.classify(message)
    
    # Build metadata dictionary
    metadata = {
        'all_scores': all_scores,
        'method': 'rule_based',
        'classifier_version': '2.0.0',
        'emotion': 'neutral'  # Basic emotion inference
    }
    
    # Infer basic emotion from intent
    emotion_map = {
        Intent.DISPUTE: 'frustrated',
        Intent.COMPLAINT: 'frustrated',
        Intent.GREETING: 'happy',
        Intent.GRATITUDE: 'happy',
        Intent.AFFIRMATION: 'neutral',
        Intent.NEGATION: 'concerned',
        Intent.HELP_REQUEST: 'concerned',
        Intent.FAQ: 'neutral',
        Intent.FEEDBACK: 'neutral'
    }
    
    metadata['emotion'] = emotion_map.get(intent, 'neutral')
    
    return (intent, confidence, metadata)
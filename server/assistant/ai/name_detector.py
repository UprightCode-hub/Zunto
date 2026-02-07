"""
Name detection with validation, correction handling, and avoidance detection.
"""
import re
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class NameDetector:
    """
    Name detection with validation.
    Distinguishes between names and questions, handles corrections and avoidance.
    """

    QUESTION_PATTERNS = [
        r'\bhow\s+(do|does|can|should|would|to|much|many)\b',
        r'\bwhat\s+(is|are|do|does|can|should|about)\b',
        r'\bwhen\s+(is|are|do|does|can|should|will)\b',
        r'\bwhere\s+(is|are|do|does|can|should)\b',
        r'\bwhy\s+(is|are|do|does|can|should|would)\b',
        r'\bwho\s+(is|are|do|does|can|should)\b',
        r'\b(can|could|would|should|may|might)\s+(i|you|we|they)\b',
        r'\b(do|does|did|is|are|was|were)\s+(i|you|we|they)\b',
        r'\btell\s+me\b',
        r'\bshow\s+me\b',
        r'\bhelp\s+(me|with)\b',
        r'\?',
    ]

    CORRECTION_PATTERNS = [
        r"(?:actually|no|sorry|wait),?\s+(?:it's|its|it\s+is)\s+([A-Z][a-z]+)",
        r"(?:i\s+meant|i\s+said)\s+([A-Z][a-z]+)",
        r"(?:not|no)\s+\w+,?\s+(?:it's|its)\s+([A-Z][a-z]+)",
        r"(?:correction|correct\s+it):\s+([A-Z][a-z]+)",
    ]

    AVOIDANCE_PATTERNS = [
        r"(?:don't|dont|do\s+not)\s+(?:want|have)\s+(?:to|a)\s+(?:say|give|share|tell)",
        r"(?:rather\s+not|prefer\s+not|won't|wont)\s+(?:say|tell|share)",
        r"^(none|nothing|n/?a|na|pass|skip)$",
        r"(?:just|why)\s+(?:help|assist|continue)",
        r"^(anonymous|guest|user|customer)$",
        r"(?:private|personal|confidential)",
    ]

    COMMON_WORDS = {
        'hi', 'hey', 'hello', 'sup', 'yo', 'greetings', 'good', 'morning',
        'afternoon', 'evening', 'yes', 'no', 'ok', 'okay', 'sure', 'thanks',
        'thank', 'you', 'please', 'help', 'need', 'want', 'menu', 'back',
        'return', 'home', 'main', 'option', 'options', 'choose', 'select',
        'the', 'a', 'an', 'is', 'are', 'am', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'can', 'could', 'may', 'might', 'must', 'shall', 'about', 'above',
        'after', 'before', 'between', 'into', 'through', 'during', 'all',
        'some', 'any', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'question', 'answer', 'info', 'information', 'how', 'what', 'when',
        'where', 'why', 'who', 'which', 'whose', 'whom'
    }

    NAME_PREFIXES = [
        r"^(my\s+name\s+is|i'?m|i\s+am|call\s+me|it'?s|it\s+is|this\s+is)\s+",
        r"^(name:|user:)\s*",
    ]

    VALID_NAME_CHARS = r"[a-zA-ZÀ-ÿ\u0100-\u017F\u0400-\u04FF\s\-\'\.]"

    @classmethod
    def is_question(cls, text: str) -> bool:
        """Check if text looks like a question."""
        text_lower = text.lower().strip()

        for pattern in cls.QUESTION_PATTERNS:
            if re.search(pattern, text_lower):
                logger.debug(f"Detected question pattern: {pattern}")
                return True

        return False

    @classmethod
    def is_common_word(cls, word: str) -> bool:
        """Check if word is a common word (not a name)."""
        return word.lower() in cls.COMMON_WORDS

    @classmethod
    def detect_correction(cls, text: str, previous_name: Optional[str] = None) -> Tuple[Optional[str], bool]:
        """Detect name correction patterns like "Actually, it's John"."""
        if not previous_name:
            return None, False

        text_lower = text.lower()

        for pattern in cls.CORRECTION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                corrected_name = match.group(1).capitalize()
                if cls._is_valid_name_basic(corrected_name):
                    logger.info(f"Name correction: {previous_name} → {corrected_name}")
                    return corrected_name, True

        return None, False

    @classmethod
    def detect_avoidance(cls, text: str) -> bool:
        """Detect if user is avoiding giving their name."""
        text_lower = text.lower().strip()

        for pattern in cls.AVOIDANCE_PATTERNS:
            if re.search(pattern, text_lower):
                logger.info(f"Name avoidance detected: {text[:30]}...")
                return True

        return False

    @classmethod
    def clean_name_input(cls, text: str) -> str:
        """Remove name prefixes and clean input."""
        text = text.strip()

        for prefix_pattern in cls.NAME_PREFIXES:
            text = re.sub(prefix_pattern, '', text, flags=re.IGNORECASE)

        text = re.sub(r'^(mr\.?|mrs\.?|ms\.?|miss|dr\.?|prof\.?)\s+', '', text, flags=re.IGNORECASE)

        text = text.strip('.,!?;:\'"')

        return text.strip()

    @classmethod
    def _is_valid_name_basic(cls, name: str) -> bool:
        """Quick validation check for corrections."""
        if not name or len(name) < 2 or len(name) > 20:
            return False
        if not re.search(r'[a-zA-Z]', name):
            return False
        if name.lower() in cls.COMMON_WORDS:
            return False
        return True

    @classmethod
    def validate_name(cls, name: str) -> Tuple[bool, str]:
        """
        Validate if text is a plausible name.
        Returns: (is_valid, reason)
        """
        if not name or len(name) < 2:
            return False, "too_short"

        if len(name) > 50:
            return False, "too_long"

        if not re.search(r'[a-zA-Z]', name):
            return False, "no_letters"

        if re.match(r'^\d+$', name):
            return False, "pure_number"

        first_word = name.split()[0] if ' ' in name else name
        if cls.is_common_word(first_word):
            return False, "common_word"

        valid_chars = len(re.findall(cls.VALID_NAME_CHARS, name))
        total_chars = len(name)

        if valid_chars / total_chars < 0.7:
            return False, "invalid_characters"

        if re.search(r'(.)\1{4,}', name):
            return False, "spam_pattern"

        return True, "valid"

    @classmethod
    def extract_name(cls, text: str) -> Optional[str]:
        """Extract likely first name from text. Returns capitalized first name or None."""
        cleaned = cls.clean_name_input(text)

        if not cleaned:
            return None

        words = cleaned.split()

        if not words:
            return None

        potential_name = words[0].strip('.,!?;:\'"')

        is_valid, reason = cls.validate_name(potential_name)

        if is_valid:
            return potential_name.capitalize()
        else:
            logger.debug(f"Name validation failed: {reason} for '{potential_name}'")
            return None

    @classmethod
    def detect(
        cls,
        user_input: str,
        previous_attempt: Optional[str] = None,
        attempt_count: int = 0
    ) -> Tuple[bool, Optional[str], str, Dict]:
        """
        Smart name detection with correction and avoidance handling.
        
        Args:
            user_input: User's message
            previous_attempt: Previous name detected (for corrections)
            attempt_count: Number of failed attempts (for progressive hints)
        
        Returns:
            (is_name, extracted_name, reason, metadata)
        """
        user_input = user_input.strip()

        metadata = {
            'confidence': 0.0,
            'is_correction': False,
            'is_avoidance': False,
            'method': 'none',
            'attempt_count': attempt_count
        }

        if not user_input:
            return (False, None, "empty_input", metadata)

        corrected_name, is_correction = cls.detect_correction(user_input, previous_attempt)
        if is_correction and corrected_name:
            metadata['is_correction'] = True
            metadata['confidence'] = 0.95
            metadata['method'] = 'correction'
            return (True, corrected_name, "name_correction", metadata)

        if cls.detect_avoidance(user_input):
            metadata['is_avoidance'] = True
            metadata['confidence'] = 0.0
            metadata['method'] = 'avoidance'
            return (False, None, "user_declined", metadata)

        if cls.is_question(user_input):
            metadata['method'] = 'question_detected'
            return (False, None, "detected_question", metadata)

        if re.match(r'^\d+$', user_input):
            metadata['method'] = 'number_detected'
            return (False, None, "pure_number", metadata)

        if re.search(r"(my\s+name\s+is|i'?m|i\s+am|call\s+me)", user_input, re.IGNORECASE):
            name = cls.extract_name(user_input)
            if name:
                metadata['confidence'] = 0.90
                metadata['method'] = 'explicit_introduction'
                return (True, name, "explicit_introduction", metadata)
            else:
                metadata['method'] = 'failed_extraction'
                return (False, None, "invalid_after_prefix", metadata)

        words = user_input.split()
        if len(words) <= 3:
            name = cls.extract_name(user_input)
            if name:
                confidence = 0.85 if len(words) == 1 else 0.75
                metadata['confidence'] = confidence
                metadata['method'] = 'simple_name' if len(words) == 1 else 'full_name'
                reason = "simple_name" if len(words) == 1 else "full_name"
                return (True, name, reason, metadata)
            else:
                metadata['method'] = 'failed_validation'
                return (False, None, "validation_failed", metadata)

        metadata['method'] = 'too_complex'
        return (False, None, "too_complex", metadata)

    @classmethod
    def get_retry_hint(cls, attempt_count: int, reason: str) -> str:
        """Generate progressive hints for failed name detection attempts."""
        if attempt_count == 1:
            return (
                "I didn't quite catch your name. Could you try again? "
                "You can say something like: 'My name is Sarah' or just 'Sarah' 😊"
            )
        elif attempt_count == 2:
            return (
                "Hmm, I'm still having trouble detecting your name. "
                "Could you just type your first name? For example: 'John' or 'Mary'"
            )
        else:
            return (
                "I'm having difficulty understanding. Would you like to skip this and "
                "continue as 'Guest'? Just say 'skip' or try one more time with your first name."
            )

    @classmethod
    def detect_with_fallback(cls, user_input: str, fallback: str = "there") -> str:
        """Detect name with fallback to default if detection fails."""
        is_name, extracted_name, reason, metadata = cls.detect(user_input)

        if is_name and extracted_name:
            logger.info(f"Name detected: '{extracted_name}' (method: {metadata['method']}, confidence: {metadata['confidence']:.2f})")
            return extracted_name
        else:
            logger.info(f"Name detection failed: {reason}, using fallback '{fallback}'")
            return fallback


def detect_name(user_input: str, context: dict = None) -> Tuple[Optional[str], float]:
    """
    Standalone function for name detection with correction and avoidance handling.
    
    Args:
        user_input: The user's message text
        context: Optional conversation context with 'previous_name' and 'attempt_count'
    
    Returns:
        (extracted_name, confidence)
    """
    previous_name = None
    attempt_count = 0

    if context:
        previous_name = context.get('previous_name')
        attempt_count = context.get('attempt_count', 0)

    is_name, extracted_name, reason, metadata = NameDetector.detect(
        user_input,
        previous_attempt=previous_name,
        attempt_count=attempt_count
    )

    confidence = metadata.get('confidence', 0.0)
    return (extracted_name, confidence)


def integration_example_upgraded():
    """Example: How to use features in ConversationManager."""
    is_name, name, reason, meta = NameDetector.detect("My name is Sarah")
    if is_name:
        print(f"✅ Name: {name}, Confidence: {meta['confidence']}")

    is_name, name, reason, meta = NameDetector.detect(
        "Actually, it's John",
        previous_attempt="Mike"
    )
    if meta['is_correction']:
        print(f"✅ Correction detected: {name}")

    is_name, name, reason, meta = NameDetector.detect("I'd rather not say")
    if meta['is_avoidance']:
        print("👤 User prefers anonymity, using 'Guest'")

    for attempt in [1, 2, 3]:
        hint = NameDetector.get_retry_hint(attempt, "validation_failed")
        print(f"Attempt {attempt}: {hint}")


def test_name_detector():
    """Built-in tests to verify functionality."""
    print("\n" + "="*70)
    print("NAME DETECTOR TEST SUITE (UPGRADED)")
    print("="*70 + "\n")

    test_cases = [
        ("John", True, "Simple name", None),
        ("My name is Alice", True, "Explicit introduction", None),
        ("Actually, it's Michael", True, "Correction", "Mike"),
        ("I'd rather not say", False, "Avoidance", None),
        ("skip", False, "Skip/avoidance keyword", None),
        ("How do I create an account?", False, "Question - should NOT be name", None),
        ("1", False, "Menu number", None),
        ("José García", True, "International name (Spanish)", None),
    ]

    passed = 0
    failed = 0

    for user_input, expected_is_name, description, previous_name in test_cases:
        is_name, extracted_name, reason, metadata = NameDetector.detect(
            user_input,
            previous_attempt=previous_name
        )

        status = "✅" if is_name == expected_is_name else "❌"

        if is_name == expected_is_name:
            passed += 1
        else:
            failed += 1

        print(f"{status} '{user_input}'")
        print(f"   Expected: {'Name' if expected_is_name else 'Not Name'}")
        print(f"   Got: {'Name' if is_name else 'Not Name'} (reason: {reason})")
        print(f"   Confidence: {metadata['confidence']:.2f}, Method: {metadata['method']}")

        if is_name and extracted_name:
            print(f"   Extracted: '{extracted_name}'")

        if metadata['is_correction']:
            print(f"   🔄 Correction detected!")
        if metadata['is_avoidance']:
            print(f"   👤 User declined to share name")

        print(f"   ({description})\n")

    print("="*70)
    print(f"✅ PASSED: {passed}/{len(test_cases)}")
    print(f"❌ FAILED: {failed}/{len(test_cases)}")
    print("="*70)

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! UPGRADED features working!\n")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review above.\n")


if __name__ == "__main__":
    test_name_detector()
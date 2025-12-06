"""
Smart Name Detection Module
Extracts and validates user names from conversational input.

WHY THIS EXISTS:
Your current code: name = words[0].capitalize()
Problem: "How do I create account?" → name = "How" ❌

This module prevents that by detecting questions vs names.
"""
import re
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class NameDetector:
    """
    Intelligent name detection with validation.
    Distinguishes between names and questions.
    """
    
    # Question indicators (these are NOT names)
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
        r'\?',  # Contains question mark
    ]
    
    # Common non-name words
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
    
    # Name prefixes to strip
    NAME_PREFIXES = [
        r"^(my\s+name\s+is|i'?m|i\s+am|call\s+me|it'?s|it\s+is|this\s+is)\s+",
        r"^(name:|user:)\s*",
    ]
    
    # Valid name character patterns (international support)
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
    def clean_name_input(cls, text: str) -> str:
        """Remove name prefixes and clean input."""
        text = text.strip()
        
        # Remove name prefixes
        for prefix_pattern in cls.NAME_PREFIXES:
            text = re.sub(prefix_pattern, '', text, flags=re.IGNORECASE)
        
        # Remove titles (Mr., Dr., etc.)
        text = re.sub(r'^(mr\.?|mrs\.?|ms\.?|miss|dr\.?|prof\.?)\s+', '', text, flags=re.IGNORECASE)
        
        # Remove punctuation at edges
        text = text.strip('.,!?;:\'"')
        
        return text.strip()
    
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
        
        # Must contain at least one letter
        if not re.search(r'[a-zA-Z]', name):
            return False, "no_letters"
        
        # Can't be pure numbers
        if re.match(r'^\d+$', name):
            return False, "pure_number"
        
        # Check if it's a common word
        first_word = name.split()[0] if ' ' in name else name
        if cls.is_common_word(first_word):
            return False, "common_word"
        
        # Check character composition
        valid_chars = len(re.findall(cls.VALID_NAME_CHARS, name))
        total_chars = len(name)
        
        if valid_chars / total_chars < 0.7:  # At least 70% valid chars
            return False, "invalid_characters"
        
        # Check for spam patterns (repeated characters)
        if re.search(r'(.)\1{4,}', name):  # Same char 5+ times
            return False, "spam_pattern"
        
        return True, "valid"
    
    @classmethod
    def extract_name(cls, text: str) -> Optional[str]:
        """
        Extract likely first name from text.
        Returns: Capitalized first name or None
        """
        cleaned = cls.clean_name_input(text)
        
        if not cleaned:
            return None
        
        # Split into words
        words = cleaned.split()
        
        if not words:
            return None
        
        # Take first word as potential name
        potential_name = words[0].strip('.,!?;:\'"')
        
        # Validate
        is_valid, reason = cls.validate_name(potential_name)
        
        if is_valid:
            # Proper capitalization
            return potential_name.capitalize()
        else:
            logger.debug(f"Name validation failed: {reason} for '{potential_name}'")
            return None
    
    @classmethod
    def detect(cls, user_input: str) -> Tuple[bool, Optional[str], str]:
        """
        Smart name detection with confidence reasoning.
        
        Returns:
            (is_name, extracted_name, reason)
        
        Examples:
            "John" → (True, "John", "simple_name")
            "My name is Alice" → (True, "Alice", "explicit_introduction")
            "How do I create account?" → (False, None, "detected_question")
            "123" → (False, None, "invalid_format")
        """
        user_input = user_input.strip()
        
        if not user_input:
            return (False, None, "empty_input")
        
        # Check 1: Is it a question?
        if cls.is_question(user_input):
            return (False, None, "detected_question")
        
        # Check 2: Pure number (like menu options)
        if re.match(r'^\d+$', user_input):
            return (False, None, "pure_number")
        
        # Check 3: Contains explicit name introduction
        if re.search(r"(my\s+name\s+is|i'?m|i\s+am|call\s+me)", user_input, re.IGNORECASE):
            name = cls.extract_name(user_input)
            if name:
                return (True, name, "explicit_introduction")
            else:
                return (False, None, "invalid_after_prefix")
        
        # Check 4: Short input (1-3 words) - likely a name
        words = user_input.split()
        if len(words) <= 3:
            name = cls.extract_name(user_input)
            if name:
                reason = "simple_name" if len(words) == 1 else "full_name"
                return (True, name, reason)
            else:
                return (False, None, "validation_failed")
        
        # Check 5: Too complex - probably not just a name
        return (False, None, "too_complex")
    
    @classmethod
    def detect_with_fallback(cls, user_input: str, fallback: str = "there") -> str:
        """
        Detect name with fallback to default if detection fails.
        This matches your current behavior: name = words[0].capitalize() or "there"
        
        USE THIS IN YOUR CODE to replace:
            words = message.strip().split()
            name = words[0].capitalize() if words else "there"
        
        WITH:
            name = NameDetector.detect_with_fallback(message, fallback="there")
        """
        is_name, extracted_name, reason = cls.detect(user_input)
        
        if is_name and extracted_name:
            logger.info(f"Name detected: '{extracted_name}' (reason: {reason})")
            return extracted_name
        else:
            logger.info(f"Name detection failed: {reason}, using fallback '{fallback}'")
            return fallback


# ============================================================================
# STANDALONE CONVENIENCE FUNCTION (Required for __init__.py import)
# ============================================================================

def detect_name(user_input: str, context: dict = None) -> Tuple[bool, Optional[str], dict]:
    """
    Standalone convenience function for name detection.
    
    This is a wrapper around NameDetector.detect() that returns metadata
    in a dictionary format for easier integration with the AI module.
    
    Args:
        user_input: The user's message text
        context: Optional conversation context (for future enhancements)
    
    Returns:
        Tuple of (is_name, extracted_name, metadata_dict)
        
    Example:
        >>> is_name, name, meta = detect_name("My name is John")
        >>> print(f"Name: {name}, Confidence: {meta['confidence']}")
        Name: John, Confidence: 0.95
    """
    # Context parameter is accepted but not used yet (reserved for future features)
    is_name, extracted_name, reason = NameDetector.detect(user_input)
    
    # Map reason to confidence level (0.0 to 1.0)
    confidence_map = {
        'explicit_introduction': 0.95,
        'simple_name': 0.90,
        'full_name': 0.85,
        'detected_question': 0.0,
        'pure_number': 0.0,
        'invalid_after_prefix': 0.2,
        'validation_failed': 0.0,
        'too_complex': 0.3,
        'empty_input': 0.0
    }
    
    metadata = {
        'reason': reason,
        'confidence': confidence_map.get(reason, 0.5),
        'original_input': user_input,
        'method': 'rule_based',
        'detector_version': '2.0.0'
    }
    
    return (is_name, extracted_name, metadata)


# ============================================================================
# INTEGRATION EXAMPLES
# ============================================================================

def integration_example_1():
    """
    Example: Replace your current name extraction in ConversationManager.
    
    BEFORE (in your conversation_manager.py):
        words = message.strip().split()
        name = words[0].capitalize() if words else "there"
    
    AFTER:
        from assistant.ai.name_detector import NameDetector
        name = NameDetector.detect_with_fallback(message, fallback="there")
    """
    pass


def integration_example_2():
    """
    Example: Advanced usage with reason logging.
    
    USE CASE: You want to handle different cases differently.
    """
    user_input = "How do I create account?"
    
    is_name, extracted_name, reason = NameDetector.detect(user_input)
    
    if is_name:
        print(f"✅ Name detected: {extracted_name}")
        # Proceed with menu
    elif reason == "detected_question":
        print(f"❓ User asked a question instead of giving name")
        # Answer question first, then ask for name again
    elif reason == "pure_number":
        print(f"🔢 User entered a number (menu option?)")
        # Handle as menu selection
    else:
        print(f"❌ Invalid input: {reason}")
        # Ask for clarification


# ============================================================================
# BUILT-IN TESTS
# ============================================================================

def test_name_detector():
    """Built-in tests to verify functionality."""
    print("\n" + "="*70)
    print("NAME DETECTOR TEST SUITE")
    print("="*70 + "\n")
    
    test_cases = [
        # (input, expected_is_name, description)
        ("John", True, "Simple name"),
        ("John Doe", True, "Full name"),
        ("My name is Alice", True, "Explicit introduction"),
        ("I'm Bob", True, "Casual introduction"),
        ("Call me Sarah", True, "Call me prefix"),
        ("How do I create an account?", False, "Question - should NOT be name"),
        ("What's your name?", False, "Question to AI"),
        ("1", False, "Menu number"),
        ("123", False, "Pure number"),
        ("Tell me about refunds", False, "Request - NOT a name"),
        ("Can you help me?", False, "Help request"),
        ("José García", True, "International name (Spanish)"),
        ("O'Brien", True, "Irish name with apostrophe"),
        ("hi", False, "Common greeting"),
        ("yes", False, "Affirmation"),
        ("menu", False, "Navigation command"),
        ("hello how are you", False, "Greeting phrase"),
        ("", False, "Empty input"),
        ("aaaaaaaaa", False, "Spam pattern"),
    ]
    
    passed = 0
    failed = 0
    
    for user_input, expected_is_name, description in test_cases:
        is_name, extracted_name, reason = NameDetector.detect(user_input)
        
        status = "✅" if is_name == expected_is_name else "❌"
        
        if is_name == expected_is_name:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} '{user_input}'")
        print(f"   Expected: {'Name' if expected_is_name else 'Not Name'}")
        print(f"   Got: {'Name' if is_name else 'Not Name'} (reason: {reason})")
        
        if is_name and extracted_name:
            print(f"   Extracted: '{extracted_name}'")
        
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
    test_name_detector()
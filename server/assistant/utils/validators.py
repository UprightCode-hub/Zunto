"""
Validators - Input validation and security checks for Zunto Assistant.

Contains:
- Message validation
- Name validation
- Email validation
- Security checks
- Data sanitization
- Rate limiting checks
"""
import re
from typing import Tuple, Optional, Dict
from assistant.utils.constants import (
    MESSAGE_MIN_LENGTH,
    MESSAGE_MAX_LENGTH,
    MESSAGE_WARNING_LENGTH,
    NAME_MIN_LENGTH,
    NAME_MAX_LENGTH,
    ALL_STATES,
    ALL_INTENTS,
    ALL_EMOTIONS,
    EXIT_COMMANDS
)


# ============================================================================
# MESSAGE VALIDATION
# ============================================================================

def validate_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user message.
    
    Args:
        message: User's input message
    
    Returns:
        (is_valid, error_message)
    """
    if not message:
        return False, "Message cannot be empty"
    
    # Check if message is only whitespace
    if not message.strip():
        return False, "Message cannot be empty"
    
    # Check minimum length
    if len(message.strip()) < MESSAGE_MIN_LENGTH:
        return False, f"Message is too short (minimum {MESSAGE_MIN_LENGTH} character)"
    
    # Check maximum length
    if len(message) > MESSAGE_MAX_LENGTH:
        return False, f"Message is too long (maximum {MESSAGE_MAX_LENGTH} characters)"
    
    # Check for suspicious patterns (excessive special characters)
    special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s.,!?\'"-]', message)) / len(message)
    if special_char_ratio > 0.5:
        return False, "Message contains too many special characters"
    
    # Check for repeated characters (spam detection)
    if re.search(r'(.)\1{10,}', message):
        return False, "Message contains excessive repeated characters"
    
    # Warning for long messages
    if len(message) > MESSAGE_WARNING_LENGTH:
        return True, f"⚠️ Long message ({len(message)} chars). Consider breaking it up."
    
    return True, None


def is_spam_message(message: str) -> bool:
    """
    Check if message appears to be spam.
    
    Args:
        message: Message to check
    
    Returns:
        True if likely spam
    """
    msg_lower = message.lower()
    
    # Spam indicators
    spam_patterns = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URLs
        r'\b(?:buy|click|discount|offer|winner|prize|free money|earn money)\b.*\b(?:now|here|click)\b',
        r'(?:viagra|cialis|pharmacy|pills)',
        r'(?:\$\d+|\d+\$).*(?:guaranteed|easy|fast)',
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True
    
    # Check for excessive caps (ALL CAPS SPAM)
    if len(message) > 20:
        caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
        if caps_ratio > 0.7:
            return True
    
    # Check for excessive emojis
    emoji_count = sum(1 for c in message if ord(c) > 0x1F300)
    if emoji_count > 20:
        return True
    
    return False


def sanitize_message(message: str) -> str:
    """
    Sanitize message for safe processing.
    
    Args:
        message: Raw message
    
    Returns:
        Sanitized message
    """
    # Remove null bytes
    message = message.replace('\x00', '')
    
    # Normalize whitespace
    message = re.sub(r'\s+', ' ', message)
    
    # Remove leading/trailing whitespace
    message = message.strip()
    
    # Remove control characters except newlines and tabs
    message = ''.join(char for char in message if ord(char) >= 32 or char in '\n\t')
    
    return message


# ============================================================================
# NAME VALIDATION
# ============================================================================

def validate_name(name: str) -> Tuple[bool, Optional[str], Dict]:
    """
    Validate user's name.
    
    Args:
        name: Name to validate
    
    Returns:
        (is_valid, error_message, metadata)
    """
    metadata = {
        'original': name,
        'cleaned': None,
        'warnings': []
    }
    
    if not name:
        return False, "Name cannot be empty", metadata
    
    # Clean name
    cleaned = name.strip()
    metadata['cleaned'] = cleaned
    
    # Check length
    if len(cleaned) < NAME_MIN_LENGTH:
        return False, f"Name is too short (minimum {NAME_MIN_LENGTH} characters)", metadata
    
    if len(cleaned) > NAME_MAX_LENGTH:
        return False, f"Name is too long (maximum {NAME_MAX_LENGTH} characters)", metadata
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
        return False, "Name contains invalid characters", metadata
    
    # Check for suspicious patterns
    if re.search(r'(.)\1{4,}', cleaned):  # Repeated characters
        metadata['warnings'].append("Name has repeated characters")
    
    # Check if it's a common word (not a name)
    common_words = {'hello', 'hi', 'hey', 'test', 'admin', 'user', 'guest'}
    if cleaned.lower() in common_words:
        return False, "Please provide your actual name", metadata
    
    # Check if it's a number
    if cleaned.isdigit():
        return False, "Name cannot be just numbers", metadata
    
    # Warn if too many words (probably not a name)
    word_count = len(cleaned.split())
    if word_count > 4:
        metadata['warnings'].append("Name has many words - using first name only")
    
    return True, None, metadata


def is_likely_name(text: str) -> bool:
    """
    Quick check if text is likely a name.
    Less strict than validate_name.
    
    Args:
        text: Text to check
    
    Returns:
        True if likely a name
    """
    text = text.strip()
    
    # Must have at least 2 characters
    if len(text) < 2:
        return False
    
    # Must start with a letter
    if not text[0].isalpha():
        return False
    
    # Must contain mostly letters
    letter_ratio = sum(1 for c in text if c.isalpha()) / len(text)
    if letter_ratio < 0.7:
        return False
    
    # Check it's not a greeting
    greetings = {'hello', 'hi', 'hey', 'greetings', 'sup', 'yo'}
    if text.lower() in greetings:
        return False
    
    return True


# ============================================================================
# EMAIL VALIDATION
# ============================================================================

def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address.
    
    Args:
        email: Email to validate
    
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    # Check for suspicious patterns
    if '..' in email:
        return False, "Email contains consecutive dots"
    
    # Check length
    if len(email) > 254:  # RFC 5321
        return False, "Email is too long"
    
    local, domain = email.rsplit('@', 1)
    
    if len(local) > 64:
        return False, "Email local part is too long"
    
    return True, None


def sanitize_email(email: str) -> str:
    """Sanitize email address."""
    return email.strip().lower()


# ============================================================================
# STATE VALIDATION
# ============================================================================

def validate_state(state: str) -> bool:
    """
    Validate conversation state.
    
    Args:
        state: State to validate
    
    Returns:
        True if valid state
    """
    return state in ALL_STATES


def validate_state_transition(
    current_state: str,
    new_state: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate state transition.
    
    Args:
        current_state: Current state
        new_state: Proposed new state
    
    Returns:
        (is_valid, error_message)
    """
    # Define valid transitions
    valid_transitions = {
        'greeting': ['awaiting_name'],
        'awaiting_name': ['menu', 'awaiting_name'],  # Can retry
        'menu': ['faq_mode', 'dispute_mode', 'feedback_mode', 'chat_mode', 'menu'],
        'faq_mode': ['menu', 'faq_mode'],
        'dispute_mode': ['menu', 'dispute_mode'],
        'feedback_mode': ['menu', 'feedback_mode', 'dispute_mode'],  # Can escalate
        'chat_mode': ['menu', 'chat_mode']
    }
    
    if current_state not in valid_transitions:
        return False, f"Invalid current state: {current_state}"
    
    if new_state not in valid_transitions[current_state]:
        return False, f"Invalid transition from {current_state} to {new_state}"
    
    return True, None


# ============================================================================
# INTENT & EMOTION VALIDATION
# ============================================================================

def validate_intent(intent: str) -> bool:
    """Validate intent value."""
    return intent in ALL_INTENTS


def validate_emotion(emotion: str) -> bool:
    """Validate emotion value."""
    return emotion in ALL_EMOTIONS


def validate_confidence(confidence: float) -> Tuple[bool, Optional[str]]:
    """
    Validate confidence score.
    
    Args:
        confidence: Score to validate
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(confidence, (int, float)):
        return False, "Confidence must be a number"
    
    if confidence < 0.0 or confidence > 1.0:
        return False, "Confidence must be between 0 and 1"
    
    return True, None


# ============================================================================
# SESSION VALIDATION
# ============================================================================

def validate_session_id(session_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate session ID format.
    
    Args:
        session_id: Session ID to validate
    
    Returns:
        (is_valid, error_message)
    """
    if not session_id:
        return False, "Session ID cannot be empty"
    
    # Check length (UUID is 36 chars with hyphens)
    if len(session_id) < 8 or len(session_id) > 100:
        return False, "Invalid session ID length"
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9\-_]+$', session_id):
        return False, "Session ID contains invalid characters"
    
    return True, None


def is_session_active(last_activity_timestamp: float, timeout_minutes: int = 30) -> bool:
    """
    Check if session is still active.
    
    Args:
        last_activity_timestamp: Unix timestamp of last activity
        timeout_minutes: Session timeout in minutes
    
    Returns:
        True if session is active
    """
    import time
    current_time = time.time()
    time_diff_minutes = (current_time - last_activity_timestamp) / 60
    
    return time_diff_minutes < timeout_minutes


# ============================================================================
# REPORT VALIDATION
# ============================================================================

def validate_report_data(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate report data before saving.
    
    Args:
        data: Report data dict
    
    Returns:
        (is_valid, error_message)
    """
    required_fields = ['message', 'report_type']
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate report_type
    valid_types = ['dispute', 'complaint', 'feedback', 'suggestion', 'bug', 'other']
    if data['report_type'] not in valid_types:
        return False, f"Invalid report type: {data['report_type']}"
    
    # Validate message length
    if len(data['message']) < 10:
        return False, "Report message is too short (minimum 10 characters)"
    
    if len(data['message']) > 5000:
        return False, "Report message is too long (maximum 5000 characters)"
    
    # Validate severity if provided
    if 'severity' in data:
        valid_severities = ['low', 'medium', 'high', 'critical']
        if data['severity'] not in valid_severities:
            return False, f"Invalid severity: {data['severity']}"
    
    return True, None


# ============================================================================
# RATE LIMITING VALIDATION
# ============================================================================

def check_rate_limit(
    request_count: int,
    time_window_seconds: int,
    limit: int
) -> Tuple[bool, Optional[str], int]:
    """
    Check if rate limit is exceeded.
    
    Args:
        request_count: Number of requests in time window
        time_window_seconds: Time window in seconds
        limit: Maximum requests allowed
    
    Returns:
        (is_allowed, error_message, retry_after_seconds)
    """
    if request_count >= limit:
        retry_after = time_window_seconds
        return False, f"Rate limit exceeded. Try again in {retry_after} seconds.", retry_after
    
    return True, None, 0


# ============================================================================
# SECURITY CHECKS
# ============================================================================

def check_for_injection_attempts(text: str) -> Tuple[bool, Optional[str]]:
    """
    Check for SQL injection or other malicious patterns.
    
    Args:
        text: Text to check
    
    Returns:
        (is_safe, threat_type)
    """
    text_lower = text.lower()
    
    # SQL injection patterns
    sql_patterns = [
        r'\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(from|table|where)\b',
        r'--\s*$',  # SQL comment
        r';.*drop\s+table',
        r"'\s*or\s*'1'\s*=\s*'1",
        r'\bexec\s*\(',
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, text_lower):
            return False, "Possible SQL injection attempt"
    
    # Command injection patterns
    cmd_patterns = [
        r'[;&|]\s*(rm|cat|ls|wget|curl|bash|sh)\s',
        r'\$\(.*\)',  # Command substitution
        r'`.*`',      # Backtick execution
    ]
    
    for pattern in cmd_patterns:
        if re.search(pattern, text_lower):
            return False, "Possible command injection attempt"
    
    # XSS patterns
    xss_patterns = [
        r'<script[^>]*>.*</script>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers like onclick=
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, text_lower):
            return False, "Possible XSS attempt"
    
    return True, None


def sanitize_for_display(text: str) -> str:
    """
    Sanitize text for safe display (prevent XSS).
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text
    """
    # HTML escape
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '&': '&amp;'
    }
    
    for char, escape in replacements.items():
        text = text.replace(char, escape)
    
    return text


# ============================================================================
# DATA TYPE VALIDATION
# ============================================================================

def validate_json_field(data: any, field_name: str, expected_type: type) -> Tuple[bool, Optional[str]]:
    """
    Validate JSON field type.
    
    Args:
        data: Data to validate
        field_name: Field name (for error message)
        expected_type: Expected Python type
    
    Returns:
        (is_valid, error_message)
    """
    if data is None:
        return False, f"{field_name} cannot be None"
    
    if not isinstance(data, expected_type):
        return False, f"{field_name} must be {expected_type.__name__}, got {type(data).__name__}"
    
    return True, None


# ============================================================================
# COMPREHENSIVE VALIDATION
# ============================================================================

def validate_chat_request(data: Dict) -> Tuple[bool, Optional[str], Dict]:
    """
    Comprehensive validation of chat request.
    
    Args:
        data: Request data
    
    Returns:
        (is_valid, error_message, sanitized_data)
    """
    sanitized = {}
    
    # Validate message
    if 'message' not in data:
        return False, "Message is required", sanitized
    
    message = data['message']
    is_valid, error = validate_message(message)
    if not is_valid:
        return False, error, sanitized
    
    # Check for spam
    if is_spam_message(message):
        return False, "Message detected as spam", sanitized
    
    # Security check
    is_safe, threat = check_for_injection_attempts(message)
    if not is_safe:
        return False, f"Security threat detected: {threat}", sanitized
    
    # Sanitize message
    sanitized['message'] = sanitize_message(message)
    
    # Validate session_id if provided
    if 'session_id' in data and data['session_id']:
        is_valid, error = validate_session_id(data['session_id'])
        if not is_valid:
            return False, error, sanitized
        sanitized['session_id'] = data['session_id']
    
    # Validate user_id if provided
    if 'user_id' in data and data['user_id']:
        if not isinstance(data['user_id'], int):
            return False, "User ID must be an integer", sanitized
        sanitized['user_id'] = data['user_id']
    
    return True, None, sanitized


# ============================================================================
# EXPORTS
# ============================================================================
__all__ = [
    # Message validation
    'validate_message',
    'is_spam_message',
    'sanitize_message',
    
    # Name validation
    'validate_name',
    'is_likely_name',
    
    # Email validation
    'validate_email',
    'sanitize_email',
    
    # State validation
    'validate_state',
    'validate_state_transition',
    
    # Intent/Emotion validation
    'validate_intent',
    'validate_emotion',
    'validate_confidence',
    
    # Session validation
    'validate_session_id',
    'is_session_active',
    
    # Report validation
    'validate_report_data',
    
    # Rate limiting
    'check_rate_limit',
    
    # Security
    'check_for_injection_attempts',
    'sanitize_for_display',
    
    # Comprehensive validation
    'validate_chat_request'
]
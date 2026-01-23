"""
Utils Package - Shared utilities for Zunto Assistant.

This package contains:
- constants: System-wide configuration and constants
- validators: Input validation and security checks
- formatters: Text and data formatting utilities

Version: 2.0.0
"""

# Import all constants
from .constants import (
    # Version info
    SYSTEM_VERSION,
    SYSTEM_NAME,
    CREATOR_NAME,
    ORGANIZATION,
    
    # States
    STATE_GREETING,
    STATE_AWAITING_NAME,
    STATE_MENU,
    STATE_FAQ_MODE,
    STATE_DISPUTE_MODE,
    STATE_FEEDBACK_MODE,
    STATE_CHAT_MODE,
    ALL_STATES,
    
    # Confidence thresholds
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_FAIR,
    QUALITY_POOR,
    
    # Message limits
    MESSAGE_MIN_LENGTH,
    MESSAGE_MAX_LENGTH,
    MESSAGE_WARNING_LENGTH,
    NAME_MIN_LENGTH,
    NAME_MAX_LENGTH,
    SESSION_TIMEOUT_MINUTES,
    MAX_MESSAGES_PER_SESSION,
    
    # Intents and emotions
    ALL_INTENTS,
    ALL_EMOTIONS,
    EMOTION_WEIGHTS,
    
    # Escalation
    ESCALATION_NONE,
    ESCALATION_CONCERNED,
    ESCALATION_FRUSTRATED,
    ESCALATION_CRITICAL,
    ESCALATION_THRESHOLD,
    
    # Contact info
    ZUNTO_SUPPORT_EMAIL,
    ZUNTO_SUPPORT_TWITTER,
    ZUNTO_SUPPORT_WHATSAPP,
    SUPPORT_RESPONSE_TIME_HOURS,
    
    # Messages
    ERROR_MSG_EMPTY_MESSAGE,
    ERROR_MSG_PROCESSING_FAILED,
    ERROR_MSG_SESSION_EXPIRED,
    SUCCESS_MSG_REPORT_SAVED,
    SUCCESS_MSG_FEEDBACK_SAVED,
    
    # Helper functions
    get_confidence_tier,
    get_escalation_label,
    is_exit_command,
    is_confirmation,
    get_contact_info_formatted
)

# Import validators
from .validators import (
    # Message validation
    validate_message,
    is_spam_message,
    sanitize_message,
    
    # Name validation
    validate_name,
    is_likely_name,
    
    # Email validation
    validate_email,
    sanitize_email,
    
    # State validation
    validate_state,
    validate_state_transition,
    
    # Intent/Emotion validation
    validate_intent,
    validate_emotion,
    validate_confidence,
    
    # Session validation
    validate_session_id,
    is_session_active,
    
    # Report validation
    validate_report_data,
    
    # Rate limiting
    check_rate_limit,
    
    # Security
    check_for_injection_attempts,
    sanitize_for_display,
    
    # Comprehensive validation
    validate_chat_request
)

# Import formatters
from .formatters import (
    # Message formatting
    format_greeting,
    format_menu,
    format_faq_intro,
    format_dispute_intro,
    format_feedback_intro,
    format_completion_message,
    
    # Data formatting
    format_confidence_display,
    format_tier_label,
    format_processing_time,
    format_sentiment,
    format_escalation_level,
    
    # List formatting
    format_numbered_list,
    format_bullet_list,
    format_faq_suggestions,
    
    # Time/Date formatting
    format_datetime,
    format_relative_time,
    format_duration,
    
    # Draft formatting
    format_email_draft,
    format_twitter_draft,
    format_whatsapp_draft,
    
    # Summary formatting
    format_conversation_summary,
    
    # Text cleaning
    clean_message,
    truncate_text,
    capitalize_name,
    
    # Response builders
    build_error_response,
    build_clarification_prompt
)


__version__ = SYSTEM_VERSION
__author__ = CREATOR_NAME
__all__ = [
    # Constants
    'SYSTEM_VERSION',
    'SYSTEM_NAME',
    'CREATOR_NAME',
    'ORGANIZATION',
    'STATE_GREETING',
    'STATE_AWAITING_NAME',
    'STATE_MENU',
    'STATE_FAQ_MODE',
    'STATE_DISPUTE_MODE',
    'STATE_FEEDBACK_MODE',
    'STATE_CHAT_MODE',
    'ALL_STATES',
    'CONFIDENCE_HIGH',
    'CONFIDENCE_MEDIUM',
    'CONFIDENCE_LOW',
    'MESSAGE_MIN_LENGTH',
    'MESSAGE_MAX_LENGTH',
    'ERROR_MSG_EMPTY_MESSAGE',
    'ERROR_MSG_PROCESSING_FAILED',
    'SUCCESS_MSG_REPORT_SAVED',
    
    # Validators
    'validate_message',
    'is_spam_message',
    'sanitize_message',
    'validate_name',
    'is_likely_name',
    'validate_email',
    'validate_state',
    'validate_session_id',
    'validate_report_data',
    'validate_chat_request',
    'check_for_injection_attempts',
    'sanitize_for_display',
    
    # Formatters
    'format_greeting',
    'format_menu',
    'format_faq_intro',
    'format_dispute_intro',
    'format_feedback_intro',
    'format_completion_message',
    'format_confidence_display',
    'format_processing_time',
    'format_sentiment',
    'format_conversation_summary',
    'clean_message',
    'build_error_response',
    'build_clarification_prompt'
]


def get_utils_info():
    """Get utils package information."""
    return {
        'version': __version__,
        'author': __author__,
        'modules': {
            'constants': 'System-wide configuration',
            'validators': 'Input validation and security',
            'formatters': 'Text and data formatting'
        }
    }
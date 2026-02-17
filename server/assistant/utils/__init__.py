#server/assistant/utils/__init__.py
"""
Utils Package - Shared utilities for Zunto Assistant.

This package contains:
- constants: System-wide configuration and constants
- validators: Input validation and security checks
- formatters: Text and data formatting utilities

Version: 2.0.0
"""

                      
from .constants import (
                  
    SYSTEM_VERSION,
    SYSTEM_NAME,
    CREATOR_NAME,
    ORGANIZATION,
    
            
    STATE_GREETING,
    STATE_AWAITING_NAME,
    STATE_MENU,
    STATE_FAQ_MODE,
    STATE_DISPUTE_MODE,
    STATE_FEEDBACK_MODE,
    STATE_CHAT_MODE,
    ALL_STATES,
    
                           
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_FAIR,
    QUALITY_POOR,
    
                    
    MESSAGE_MIN_LENGTH,
    MESSAGE_MAX_LENGTH,
    MESSAGE_WARNING_LENGTH,
    NAME_MIN_LENGTH,
    NAME_MAX_LENGTH,
    SESSION_TIMEOUT_MINUTES,
    MAX_MESSAGES_PER_SESSION,
    
                          
    ALL_INTENTS,
    ALL_EMOTIONS,
    EMOTION_WEIGHTS,
    
                
    ESCALATION_NONE,
    ESCALATION_CONCERNED,
    ESCALATION_FRUSTRATED,
    ESCALATION_CRITICAL,
    ESCALATION_THRESHOLD,
    
                  
    ZUNTO_SUPPORT_EMAIL,
    ZUNTO_SUPPORT_TWITTER,
    ZUNTO_SUPPORT_WHATSAPP,
    SUPPORT_RESPONSE_TIME_HOURS,
    
              
    ERROR_MSG_EMPTY_MESSAGE,
    ERROR_MSG_PROCESSING_FAILED,
    ERROR_MSG_SESSION_EXPIRED,
    SUCCESS_MSG_REPORT_SAVED,
    SUCCESS_MSG_FEEDBACK_SAVED,
    
                      
    get_confidence_tier,
    get_escalation_label,
    is_exit_command,
    is_confirmation,
    get_contact_info_formatted
)

                   
from .validators import (
                        
    validate_message,
    is_spam_message,
    sanitize_message,
    
                     
    validate_name,
    is_likely_name,
    
                      
    validate_email,
    sanitize_email,
    
                      
    validate_state,
    validate_state_transition,
    
                               
    validate_intent,
    validate_emotion,
    validate_confidence,
    
                        
    validate_session_id,
    is_session_active,
    
                       
    validate_report_data,
    
                   
    check_rate_limit,
    
              
    check_for_injection_attempts,
    sanitize_for_display,
    
                              
    validate_chat_request
)

                   
from .formatters import (
                        
    format_greeting,
    format_menu,
    format_faq_intro,
    format_dispute_intro,
    format_feedback_intro,
    format_completion_message,
    
                     
    format_confidence_display,
    format_tier_label,
    format_processing_time,
    format_sentiment,
    format_escalation_level,
    
                     
    format_numbered_list,
    format_bullet_list,
    format_faq_suggestions,
    
                          
    format_datetime,
    format_relative_time,
    format_duration,
    
                      
    format_email_draft,
    format_twitter_draft,
    format_whatsapp_draft,
    
                        
    format_conversation_summary,
    
                   
    clean_message,
    truncate_text,
    capitalize_name,
    
                       
    build_error_response,
    build_clarification_prompt
)


__version__ = SYSTEM_VERSION
__author__ = CREATOR_NAME
__all__ = [
               
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

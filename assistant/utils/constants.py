"""
Constants - System-wide configuration constants for Zunto Assistant.

Contains:
- Confidence thresholds
- State definitions
- Message limits
- Timeout values
- API configuration
- Contact information
- Feature flags
"""

# ============================================================================
# VERSION INFO
# ============================================================================
SYSTEM_VERSION = '2.0.0'
SYSTEM_NAME = 'Gigi (Zunto AI Assistant)'
CREATOR_NAME = 'Wisdom Ekwyugha'
ORGANIZATION = 'Gigi Development Engine (GDE)'

# ============================================================================
# CONVERSATION STATES
# ============================================================================
STATE_GREETING = 'greeting'
STATE_AWAITING_NAME = 'awaiting_name'
STATE_MENU = 'menu'
STATE_FAQ_MODE = 'faq_mode'
STATE_DISPUTE_MODE = 'dispute_mode'
STATE_FEEDBACK_MODE = 'feedback_mode'
STATE_CHAT_MODE = 'chat_mode'

ALL_STATES = [
    STATE_GREETING,
    STATE_AWAITING_NAME,
    STATE_MENU,
    STATE_FAQ_MODE,
    STATE_DISPUTE_MODE,
    STATE_FEEDBACK_MODE,
    STATE_CHAT_MODE
]

# ============================================================================
# CONFIDENCE THRESHOLDS (3-Tier System)
# ============================================================================
CONFIDENCE_HIGH = 0.65      # Tier 1: Return FAQ directly, no LLM call
CONFIDENCE_MEDIUM = 0.40    # Tier 2: Use LLM to enhance answer
CONFIDENCE_LOW = 0.40       # Tier 3: LLM generates from scratch

# Response quality thresholds
QUALITY_EXCELLENT = 0.85    # Excellent response quality
QUALITY_GOOD = 0.65        # Good response quality
QUALITY_FAIR = 0.40        # Fair response quality
QUALITY_POOR = 0.40        # Poor response quality

# ============================================================================
# MESSAGE LIMITS & VALIDATION
# ============================================================================
MESSAGE_MIN_LENGTH = 1
MESSAGE_MAX_LENGTH = 2048
MESSAGE_WARNING_LENGTH = 1500

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 50

# Session limits
SESSION_TIMEOUT_MINUTES = 30
MAX_MESSAGES_PER_SESSION = 100
MAX_CONTEXT_HISTORY = 20

# ============================================================================
# RAG CONFIGURATION
# ============================================================================
RAG_TOP_K = 5                          # Number of FAQs to retrieve
RAG_EMBEDDING_MODEL = 'BAAI/bge-small-en-v1.5'
RAG_DIMENSION = 384                    # BGE-small embedding dimension
RAG_INDEX_TYPE = 'HNSW'               # FAISS index type

# Target performance
RAG_TARGET_QUERY_TIME_MS = 50         # Target: 30ms, acceptable: 50ms
RAG_CACHE_ENABLED = True

# ============================================================================
# LLM CONFIGURATION (Groq)
# ============================================================================
LLM_MODEL_NAME = 'llama-3.3-70b-versatile'
LLM_MAX_TOKENS = 256
LLM_TEMPERATURE = 0.2
LLM_TIMEOUT_SECONDS = 10.0
LLM_MAX_RETRIES = 2

# ============================================================================
# INTENT TYPES
# ============================================================================
INTENT_GREETING = 'greeting'
INTENT_FAQ = 'faq'
INTENT_QUESTION = 'question'
INTENT_DISPUTE = 'dispute'
INTENT_COMPLAINT = 'complaint'
INTENT_ISSUE = 'issue'
INTENT_FEEDBACK = 'feedback'
INTENT_SUGGESTION = 'suggestion'
INTENT_PRAISE = 'praise'
INTENT_GENERAL = 'general'

ALL_INTENTS = [
    INTENT_GREETING,
    INTENT_FAQ,
    INTENT_QUESTION,
    INTENT_DISPUTE,
    INTENT_COMPLAINT,
    INTENT_ISSUE,
    INTENT_FEEDBACK,
    INTENT_SUGGESTION,
    INTENT_PRAISE,
    INTENT_GENERAL
]

# ============================================================================
# EMOTION TYPES
# ============================================================================
EMOTION_NEUTRAL = 'neutral'
EMOTION_HAPPY = 'happy'
EMOTION_EXCITED = 'excited'
EMOTION_FRUSTRATED = 'frustrated'
EMOTION_ANGRY = 'angry'
EMOTION_SAD = 'sad'

ALL_EMOTIONS = [
    EMOTION_NEUTRAL,
    EMOTION_HAPPY,
    EMOTION_EXCITED,
    EMOTION_FRUSTRATED,
    EMOTION_ANGRY,
    EMOTION_SAD
]

# Emotion weights for sentiment calculation
EMOTION_WEIGHTS = {
    EMOTION_HAPPY: 1.0,
    EMOTION_EXCITED: 1.0,
    EMOTION_NEUTRAL: 0.5,
    EMOTION_SAD: -0.5,
    EMOTION_FRUSTRATED: -0.7,
    EMOTION_ANGRY: -1.0
}

# ============================================================================
# ESCALATION LEVELS
# ============================================================================
ESCALATION_NONE = 0         # User is calm
ESCALATION_CONCERNED = 1    # Slightly concerned
ESCALATION_FRUSTRATED = 2   # Frustrated, needs attention
ESCALATION_CRITICAL = 3     # Critical, needs immediate human intervention

ESCALATION_THRESHOLD = 3    # Number of negative messages to trigger escalation

# ============================================================================
# REPORT TYPES & SEVERITY
# ============================================================================
REPORT_TYPE_DISPUTE = 'dispute'
REPORT_TYPE_COMPLAINT = 'complaint'
REPORT_TYPE_FEEDBACK = 'feedback'
REPORT_TYPE_SUGGESTION = 'suggestion'
REPORT_TYPE_BUG = 'bug'
REPORT_TYPE_OTHER = 'other'

SEVERITY_LOW = 'low'
SEVERITY_MEDIUM = 'medium'
SEVERITY_HIGH = 'high'
SEVERITY_CRITICAL = 'critical'

# ============================================================================
# DISPUTE CATEGORIES
# ============================================================================
CATEGORY_SCAM = 'scam'
CATEGORY_PAYMENT = 'payment'
CATEGORY_SHIPPING = 'shipping'
CATEGORY_PRODUCT = 'product'
CATEGORY_SELLER = 'seller'
CATEGORY_BUYER = 'buyer'
CATEGORY_COMMUNICATION = 'communication'
CATEGORY_OTHER = 'other'

ALL_CATEGORIES = [
    CATEGORY_SCAM,
    CATEGORY_PAYMENT,
    CATEGORY_SHIPPING,
    CATEGORY_PRODUCT,
    CATEGORY_SELLER,
    CATEGORY_BUYER,
    CATEGORY_COMMUNICATION,
    CATEGORY_OTHER
]

# ============================================================================
# CONTACT PLATFORMS
# ============================================================================
PLATFORM_EMAIL = 'email'
PLATFORM_TWITTER = 'twitter'
PLATFORM_WHATSAPP = 'whatsapp'
PLATFORM_NONE = 'none'

ALL_PLATFORMS = [
    PLATFORM_EMAIL,
    PLATFORM_TWITTER,
    PLATFORM_WHATSAPP,
    PLATFORM_NONE
]

# ============================================================================
# ZUNTO CONTACT INFORMATION
# ============================================================================
ZUNTO_SUPPORT_EMAIL = 'support@zunto.com'
ZUNTO_SUPPORT_TWITTER = '@ZuntoSupport'
ZUNTO_SUPPORT_WHATSAPP = '+234-XXX-XXX-XXXX'
ZUNTO_WEBSITE = 'https://zunto.com'

# Response time expectations
SUPPORT_RESPONSE_TIME_HOURS = 24

# ============================================================================
# PERSONALIZATION PREFERENCES
# ============================================================================
FORMALITY_FORMAL = 'formal'
FORMALITY_NEUTRAL = 'neutral'
FORMALITY_CASUAL = 'casual'

EMOJI_NONE = 'none'
EMOJI_MINIMAL = 'minimal'
EMOJI_MODERATE = 'moderate'
EMOJI_HIGH = 'high'

RESPONSE_LENGTH_SHORT = 'short'
RESPONSE_LENGTH_MEDIUM = 'medium'
RESPONSE_LENGTH_LONG = 'long'

# ============================================================================
# EMOJIS BY CATEGORY
# ============================================================================
EMOJIS = {
    'greeting': ['👋', '😊', '🎉', '✨'],
    'success': ['✅', '🎊', '👍', '💯'],
    'warning': ['⚠️', '🚨', '❗'],
    'error': ['❌', '😞', '🙁'],
    'help': ['🤔', '💡', '📚', '🔍'],
    'dispute': ['🛡️', '⚖️', '📋'],
    'feedback': ['💭', '💬', '📝'],
    'contact': ['📞', '📧', '💬'],
    'social': ['🐦', '💬', '📱']
}

# ============================================================================
# MENU OPTIONS
# ============================================================================
MENU_OPTION_DISPUTE = '1'
MENU_OPTION_FAQ = '2'
MENU_OPTION_FEEDBACK = '3'

MENU_OPTIONS = {
    MENU_OPTION_DISPUTE: 'Report a Dispute',
    MENU_OPTION_FAQ: 'Ask FAQ Questions',
    MENU_OPTION_FEEDBACK: 'Share Feedback'
}

# ============================================================================
# EXIT COMMANDS
# ============================================================================
EXIT_COMMANDS = [
    'exit', 'quit', 'bye', 'goodbye', 'stop', 
    'menu', 'back', 'cancel', 'done'
]

# ============================================================================
# CONFIRMATION KEYWORDS
# ============================================================================
CONFIRMATION_YES = ['yes', 'y', 'yeah', 'yep', 'sure', 'ok', 'okay', 'fine']
CONFIRMATION_NO = ['no', 'n', 'nope', 'nah', 'not really']

# ============================================================================
# LANGUAGE SUPPORT
# ============================================================================
SUPPORTED_LANGUAGES = [
    'english', 'spanish', 'french', 'chinese', 'arabic', 'portuguese'
]

# Multi-language greetings
GREETINGS_MULTILANG = {
    'english': ['hello', 'hi', 'hey', 'greetings'],
    'spanish': ['hola', 'buenos días', 'buenas tardes'],
    'french': ['bonjour', 'salut', 'bonsoir'],
    'chinese': ['你好', '您好'],
    'arabic': ['مرحبا', 'السلام عليكم']
}

# ============================================================================
# PERFORMANCE TARGETS
# ============================================================================
TARGET_RESPONSE_TIME_MS = 100      # Target total response time
ACCEPTABLE_RESPONSE_TIME_MS = 500  # Acceptable response time
SLOW_RESPONSE_TIME_MS = 1000       # Warning threshold

# Cost optimization targets
COST_SAVINGS_TARGET = 0.65         # 65% cost savings from 3-tier system

# ============================================================================
# FEATURE FLAGS
# ============================================================================
FEATURE_NAME_DETECTION_ENABLED = True
FEATURE_INTENT_CLASSIFICATION_ENABLED = True
FEATURE_CONTEXT_TRACKING_ENABLED = True
FEATURE_RESPONSE_PERSONALIZATION_ENABLED = True
FEATURE_ESCALATION_DETECTION_ENABLED = True
FEATURE_AI_DRAFT_GENERATION_ENABLED = True
FEATURE_SENTIMENT_ANALYSIS_ENABLED = True
FEATURE_MULTI_LANGUAGE_ENABLED = True

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL_DEBUG = 'DEBUG'
LOG_LEVEL_INFO = 'INFO'
LOG_LEVEL_WARNING = 'WARNING'
LOG_LEVEL_ERROR = 'ERROR'

# Log what gets tracked
LOG_USER_MESSAGES = True
LOG_CONTEXT_CHANGES = True
LOG_ESCALATIONS = True
LOG_PERFORMANCE_METRICS = True

# ============================================================================
# ANALYTICS TRACKING
# ============================================================================
TRACK_MESSAGE_COUNT = True
TRACK_SENTIMENT = True
TRACK_CONFIDENCE_SCORES = True
TRACK_PROCESSING_TIME = True
TRACK_ESCALATIONS = True
TRACK_RESOLUTION_SUCCESS = True

# ============================================================================
# ERROR MESSAGES
# ============================================================================
ERROR_MSG_EMPTY_MESSAGE = "I didn't receive a valid message. Could you please try again?"
ERROR_MSG_PROCESSING_FAILED = (
    "I apologize, but I'm having trouble processing your message right now. "
    "Please try again in a moment."
)
ERROR_MSG_SESSION_EXPIRED = "Your session has expired. Let's start fresh!"
ERROR_MSG_TOO_MANY_MESSAGES = (
    "You've reached the message limit for this session. "
    "Please start a new conversation."
)

# ============================================================================
# SUCCESS MESSAGES
# ============================================================================
SUCCESS_MSG_REPORT_SAVED = "Your report has been logged successfully! ✅"
SUCCESS_MSG_FEEDBACK_SAVED = "Your feedback has been recorded! ✅"
SUCCESS_MSG_SESSION_RESET = "Session reset successfully. Let's start fresh!"

# ============================================================================
# RATE LIMITING
# ============================================================================
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_REQUESTS_PER_HOUR = 1000
RATE_LIMIT_BURST_SIZE = 10

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================
CACHE_ENABLED = True
CACHE_TTL_SECONDS = 3600           # 1 hour
CACHE_MAX_SIZE_MB = 100

# ============================================================================
# DATABASE QUERY LIMITS
# ============================================================================
MAX_CONVERSATION_LOGS = 10000      # Max logs per user
MAX_REPORTS = 1000                 # Max reports per user
MAX_SESSIONS = 100                 # Max sessions per user

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_confidence_tier(score: float) -> str:
    """Get confidence tier label from score."""
    if score >= CONFIDENCE_HIGH:
        return 'high'
    elif score >= CONFIDENCE_MEDIUM:
        return 'medium'
    else:
        return 'low'


def get_escalation_label(level: int) -> str:
    """Get human-readable escalation label."""
    labels = {
        ESCALATION_NONE: 'Calm',
        ESCALATION_CONCERNED: 'Concerned',
        ESCALATION_FRUSTRATED: 'Frustrated',
        ESCALATION_CRITICAL: 'Critical'
    }
    return labels.get(level, 'Unknown')


def is_exit_command(message: str) -> bool:
    """Check if message is an exit command."""
    return message.lower().strip() in EXIT_COMMANDS


def is_confirmation(message: str) -> tuple:
    """
    Check if message is a yes/no confirmation.
    Returns: (is_yes, is_no)
    """
    msg = message.lower().strip()
    return (msg in CONFIRMATION_YES, msg in CONFIRMATION_NO)


def get_contact_info_formatted() -> str:
    """Get formatted contact information."""
    return f"""📞 **Our Support Channels:**

🐦 **Twitter/X:** {ZUNTO_SUPPORT_TWITTER}
📧 **Email:** {ZUNTO_SUPPORT_EMAIL}
💬 **WhatsApp:** {ZUNTO_SUPPORT_WHATSAPP}

Our team typically responds within {SUPPORT_RESPONSE_TIME_HOURS} hours."""
"""
Formatters - Text and data formatting utilities for Zunto Assistant.

Contains:
- Message formatting
- Data structure formatting
- Time/date formatting
- Number formatting
- Template rendering
- Response builders
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


# ============================================================================
# MESSAGE FORMATTING
# ============================================================================

def format_greeting(name: str = "there") -> str:
    """
    Format initial greeting message.
    
    Args:
        name: User's name (default: "there")
    
    Returns:
        Formatted greeting
    """
    return f"""Hello! Welcome to Zunto Marketplace! 🎉

I'm Gigi, your virtual assistant. I'm here to help you with anything related to buying, selling, or using our platform.

Before we begin, may I know your name?"""


def format_menu(name: str, show_emojis: bool = True) -> str:
    """
    Format menu options with customizable emoji display.
    
    Args:
        name: User's name
        show_emojis: Whether to include emojis
    
    Returns:
        Formatted menu
    """
    emoji = "😊 " if show_emojis else ""
    
    return f"""Hi {name}! {emoji}Great to meet you!

Here's how I can assist you today:

1️⃣ **Report a Dispute** - Report suspicious activity, scams, or problems with sellers/buyers
2️⃣ **Ask FAQ Questions** - Quick answers to common questions about orders, payments, refunds, and more
3️⃣ **Share Feedback** - Tell us about your experience or suggest improvements

Just type **1**, **2**, or **3**, or describe what you need help with!"""


def format_faq_intro(name: str) -> str:
    """Format FAQ mode introduction."""
    return f"""Perfect {name}! 📚 I'm ready to answer your questions about Zunto.

What would you like to know? (e.g., How do refunds work? How do I verify sellers?)"""


def format_dispute_intro(name: str) -> str:
    """Format dispute mode introduction."""
    return f"""I understand {name}. I'm here to help you report this issue. 🛡️

Please describe what happened in detail. Include:
- What went wrong?
- When did it happen?
- Who was involved (seller/buyer)?
- Any relevant order numbers or details

The more information you provide, the better we can assist you."""


def format_feedback_intro(name: str) -> str:
    """Format feedback mode introduction."""
    return f"""Thank you {name}! 💭 Your feedback helps us improve Zunto.

Please share your thoughts:
- What do you like about Zunto?
- What could be better?
- Any suggestions or features you'd like to see?
- Any issues you've encountered?

Tell me anything - I'm here to listen! 😊"""


def format_completion_message(
    report_id: int,
    report_type: str = 'report',
    custom_message: str = None
) -> str:
    """
    Format completion message with report ID.
    
    Args:
        report_id: Report ID number
        report_type: Type of report (report, dispute, feedback)
        custom_message: Optional custom message
    
    Returns:
        Formatted completion message
    """
    base = f"""Your {report_type} has been logged successfully! ✅

**{report_type.title()} ID:** #{report_id}

"""
    
    if custom_message:
        base += f"{custom_message}\n\n"
    else:
        base += "Our support team will review your case and reach out within 24 hours.\n\n"
    
    base += """What would you like to do next?

1️⃣ **Ask FAQ Questions** - Get quick answers
2️⃣ **Report an Issue** - Need more help?
3️⃣ **Share More Feedback** - Have more to say?

Type 1, 2, 3, or describe what you need!"""
    
    return base


# ============================================================================
# DATA FORMATTING
# ============================================================================

def format_confidence_display(confidence: float) -> str:
    """
    Format confidence score for display.
    
    Args:
        confidence: Score from 0-1
    
    Returns:
        Formatted string (e.g., "85%", "Low (35%)")
    """
    percentage = int(confidence * 100)
    
    if confidence >= 0.85:
        return f"Excellent ({percentage}%)"
    elif confidence >= 0.65:
        return f"High ({percentage}%)"
    elif confidence >= 0.40:
        return f"Medium ({percentage}%)"
    else:
        return f"Low ({percentage}%)"


def format_tier_label(tier: str) -> str:
    """
    Format tier label with emoji and description.
    
    Args:
        tier: 'high', 'medium', or 'low'
    
    Returns:
        Formatted tier label
    """
    tier_info = {
        'high': ('🟢', 'High Confidence', 'Direct answer'),
        'medium': ('🟡', 'Medium Confidence', 'Enhanced answer'),
        'low': ('🔴', 'Low Confidence', 'Generated answer')
    }
    
    emoji, label, desc = tier_info.get(tier, ('⚪', 'Unknown', 'Unknown'))
    return f"{emoji} {label} - {desc}"


def format_processing_time(time_ms: int) -> str:
    """
    Format processing time for display.
    
    Args:
        time_ms: Time in milliseconds
    
    Returns:
        Human-readable time string
    """
    if time_ms < 50:
        return f"⚡ {time_ms}ms (blazing fast!)"
    elif time_ms < 200:
        return f"✨ {time_ms}ms (very fast)"
    elif time_ms < 500:
        return f"✅ {time_ms}ms (fast)"
    elif time_ms < 1000:
        return f"⏱️  {time_ms}ms (acceptable)"
    else:
        seconds = time_ms / 1000
        return f"⏳ {seconds:.2f}s (slow)"


def format_sentiment(sentiment: str, with_emoji: bool = True) -> str:
    """
    Format sentiment with optional emoji.
    
    Args:
        sentiment: 'positive', 'neutral', 'negative'
        with_emoji: Include emoji
    
    Returns:
        Formatted sentiment
    """
    sentiment_map = {
        'positive': ('😊', 'Positive'),
        'neutral': ('😐', 'Neutral'),
        'negative': ('😞', 'Negative')
    }
    
    emoji, label = sentiment_map.get(sentiment, ('❓', 'Unknown'))
    
    if with_emoji:
        return f"{emoji} {label}"
    return label


def format_escalation_level(level: int) -> str:
    """
    Format escalation level with visual indicator.
    
    Args:
        level: 0-3
    
    Returns:
        Formatted escalation level
    """
    levels = {
        0: '🟢 Calm',
        1: '🟡 Concerned',
        2: '🟠 Frustrated',
        3: '🔴 Critical'
    }
    return levels.get(level, '⚪ Unknown')


# ============================================================================
# LIST FORMATTING
# ============================================================================

def format_numbered_list(items: List[str], start: int = 1) -> str:
    """
    Format items as numbered list with emojis.
    
    Args:
        items: List of items to format
        start: Starting number
    
    Returns:
        Formatted numbered list
    """
    emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    
    lines = []
    for i, item in enumerate(items, start=start):
        if i <= len(emoji_numbers):
            emoji = emoji_numbers[i-1]
        else:
            emoji = f"{i}."
        lines.append(f"{emoji} {item}")
    
    return "\n".join(lines)


def format_bullet_list(items: List[str], bullet: str = '•') -> str:
    """
    Format items as bullet list.
    
    Args:
        items: List of items
        bullet: Bullet character
    
    Returns:
        Formatted bullet list
    """
    return "\n".join(f"{bullet} {item}" for item in items)


def format_faq_suggestions(faqs: List[Dict], max_items: int = 3) -> str:
    """
    Format FAQ suggestions as numbered list.
    
    Args:
        faqs: List of FAQ dicts with 'question' key
        max_items: Maximum items to show
    
    Returns:
        Formatted suggestions
    """
    items = [faq['question'] for faq in faqs[:max_items]]
    
    result = "I found a few topics that might help:\n\n"
    result += format_numbered_list(items)
    result += "\n\nWhich one matches your question? (Type the number or rephrase your question)"
    
    return result


# ============================================================================
# TIME/DATE FORMATTING
# ============================================================================

def format_datetime(dt: datetime, include_time: bool = True) -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime object
        include_time: Include time component
    
    Returns:
        Formatted datetime string
    """
    if include_time:
        return dt.strftime('%B %d, %Y at %I:%M %p')
    return dt.strftime('%B %d, %Y')


def format_relative_time(dt: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 hours ago").
    
    Args:
        dt: Datetime object
    
    Returns:
        Relative time string
    """
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"


def format_duration(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
    
    Returns:
        Formatted duration
    """
    if minutes < 1:
        return "less than a minute"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = minutes // 60
        remaining_mins = minutes % 60
        
        result = f"{hours} hour{'s' if hours != 1 else ''}"
        if remaining_mins > 0:
            result += f" and {remaining_mins} minute{'s' if remaining_mins != 1 else ''}"
        
        return result


# ============================================================================
# DRAFT MESSAGE FORMATTING
# ============================================================================

def format_email_draft(subject: str, body: str, recipient: str = None) -> str:
    """
    Format email draft with proper structure.
    
    Args:
        subject: Email subject
        body: Email body
        recipient: Optional recipient name
    
    Returns:
        Formatted email draft
    """
    if recipient:
        greeting = f"To: {recipient}"
    else:
        greeting = "To: Zunto Support Team"
    
    return f"""Subject: {subject}

{greeting}

{body}

Best regards,
[Your Name]"""


def format_twitter_draft(message: str, handle: str = '@ZuntoSupport') -> str:
    """
    Format Twitter/X draft with character limit check.
    
    Args:
        message: Tweet content
        handle: Twitter handle to mention
    
    Returns:
        Formatted tweet with character count
    """
    if not message.startswith(handle):
        message = f"{handle} {message}"
    
    char_count = len(message)
    warning = ""
    
    if char_count > 280:
        warning = f"\n\n⚠️ Warning: {char_count} characters (exceeds 280 limit)"
    
    return f"""{message}

Character count: {char_count}/280{warning}"""


def format_whatsapp_draft(message: str, contact: str = '+234-XXX-XXX-XXXX') -> str:
    """
    Format WhatsApp message draft.
    
    Args:
        message: Message content
        contact: WhatsApp contact number
    
    Returns:
        Formatted WhatsApp message
    """
    return f"""📱 WhatsApp Message:

{message}

---
Send this to: {contact}"""


# ============================================================================
# CONVERSATION SUMMARY FORMATTING
# ============================================================================

def format_conversation_summary(summary: Dict) -> str:
    """
    Format conversation summary for display.
    
    Args:
        summary: Summary dict from ContextManager
    
    Returns:
        Formatted summary
    """
    lines = [
        "📊 **Conversation Summary**",
        "",
        f"👤 User: {summary.get('user_name', 'Unknown')}",
        f"💬 Messages: {summary.get('message_count', 0)}",
        f"⏱️  Duration: {format_duration(summary.get('duration_minutes', 0))}",
        f"😊 Sentiment: {format_sentiment(summary.get('sentiment', 'neutral'))}",
        f"📊 Satisfaction: {format_confidence_display(summary.get('satisfaction_score', 0.5))}",
        f"🚨 Escalation: {format_escalation_level(summary.get('escalation_level', 0))}",
    ]
    
    # Add topics if available
    topics = summary.get('topics_discussed', [])
    if topics:
        lines.append(f"📚 Topics: {', '.join(topics[:5])}")
    
    return "\n".join(lines)


# ============================================================================
# TEXT CLEANING & SANITIZATION
# ============================================================================

def clean_message(message: str) -> str:
    """
    Clean and normalize user message.
    
    Args:
        message: Raw message
    
    Returns:
        Cleaned message
    """
    # Remove excessive whitespace
    message = re.sub(r'\s+', ' ', message)
    
    # Remove leading/trailing whitespace
    message = message.strip()
    
    # Remove excessive punctuation
    message = re.sub(r'([!?.]){3,}', r'\1\1', message)
    
    return message


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def capitalize_name(name: str) -> str:
    """
    Capitalize name properly (handles O'Brien, Al-Hassan, etc.).
    
    Args:
        name: Name to capitalize
    
    Returns:
        Properly capitalized name
    """
    # Handle hyphenated names
    if '-' in name:
        parts = name.split('-')
        return '-'.join(part.capitalize() for part in parts)
    
    # Handle apostrophes (O'Brien)
    if "'" in name:
        parts = name.split("'")
        return "'".join(part.capitalize() for part in parts)
    
    # Standard capitalization
    return name.capitalize()


# ============================================================================
# RESPONSE BUILDERS
# ============================================================================

def build_error_response(
    error_type: str,
    user_friendly: bool = True,
    include_help: bool = True
) -> str:
    """
    Build error response message.
    
    Args:
        error_type: Type of error
        user_friendly: Use friendly language
        include_help: Include help text
    
    Returns:
        Error message
    """
    errors = {
        'empty_message': "I didn't receive a valid message. Could you please try again?",
        'session_expired': "Your session has expired. Let's start fresh!",
        'processing_failed': "I apologize, but I'm having trouble processing your message.",
        'llm_unavailable': "I'm having trouble connecting to my AI brain right now.",
        'rag_unavailable': "I'm having trouble accessing my knowledge base.",
    }
    
    message = errors.get(error_type, "An unexpected error occurred.")
    
    if include_help:
        message += "\n\nYou can try:\n"
        message += "• Rephrasing your message\n"
        message += "• Starting a new conversation\n"
        message += "• Contacting support if the issue persists"
    
    return message


def build_clarification_prompt(
    options: List[str],
    intro: str = "I need a bit more information:"
) -> str:
    """
    Build clarification prompt with options.
    
    Args:
        options: List of clarification options
        intro: Introduction text
    
    Returns:
        Formatted clarification prompt
    """
    result = f"{intro}\n\n"
    result += format_numbered_list(options)
    result += "\n\nPlease choose one or provide more details."
    
    return result
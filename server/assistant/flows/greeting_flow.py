#server/assistant/flows/greeting_flow.py
"""Greeting flow handling menu presentation for authenticated users."""
from typing import Dict
import logging

from assistant.utils.constants import STATE_MENU

logger = logging.getLogger(__name__)


class GreetingFlow:
    """Greeting flow."""

    def __init__(self, session, context_mgr):
        self.session = session
        self.context_mgr = context_mgr
        logger.debug(f"GreetingFlow initialized for session {session.session_id[:8]}")

    def start_conversation(self) -> str:
        self.session.current_state = STATE_MENU
        self.session.save(update_fields=['current_state', 'updated_at'])

        is_returning = self._is_returning_user()
        time_greeting = self._get_time_based_greeting()

        greeting = (
            self._get_returning_user_greeting(time_greeting)
            if is_returning
            else self._get_first_time_greeting(time_greeting)
        )

        self.context_mgr.add_message(
            role='assistant',
            content=greeting,
            confidence=1.0,
            metadata={'greeting_type': 'returning' if is_returning else 'first_time'}
        )

        logger.info(f"Greeting sent: type={'returning' if is_returning else 'first_time'}")

        return greeting

    def _is_returning_user(self) -> bool:
        """Detect if user has interacted before."""
        if self.session.message_count > 0:
            return True

        if self.session.user_id:
            from assistant.models import ConversationSession
            previous_sessions = ConversationSession.objects.filter(
                user_id=self.session.user_id
            ).exclude(session_id=self.session.session_id).count()

            if previous_sessions > 0:
                return True

        return False

    def _get_time_based_greeting(self) -> str:
        """Get appropriate greeting based on current time."""
        from django.utils import timezone

        current_hour = timezone.now().hour

        if 5 <= current_hour < 12:
            return "Good morning"
        elif 12 <= current_hour < 17:
            return "Good afternoon"
        elif 17 <= current_hour < 22:
            return "Good evening"
        else:
            return "Hello"

    def _get_first_time_greeting(self, time_greeting: str) -> str:
        user_name = self._resolve_user_name()
        return (
            f"👋 **{time_greeting}! Welcome to Zunto Marketplace!**\n\n"
            "I'm your Zunto support assistant. I can help you with:\n\n"
            "✨ **Smart Answers** - Lightning-fast responses to your questions (0.03s!)\n"
            "🛡️ **Dispute Resolution** - Professional help with order issues\n"
            "💬 **Natural Conversation** - I understand context and remember our chat\n"
            "📦 **Marketplace Support** - Guidance on orders, shipping, and policies\n\n"
            "I'm here to make your marketplace experience smooth and enjoyable.\n\n"
            f"**How can I help you today, {user_name}?**"
        )

    def _get_returning_user_greeting(self, time_greeting: str) -> str:
        user_name = self._resolve_user_name()
        return (
            f"👋 **{time_greeting}! Welcome back to Zunto!**\n\n"
            f"Great to see you again, **{user_name}**! I'm ready to help you today.\n\n"
            "I remember our previous conversations and can pick up right where we left off.\n\n"
            "**What would you like to do?**"
        )

    def _build_unified_menu(self, name: str) -> str:
        """Build personalized menu with dynamic formality."""
        hints: Dict = self.context_mgr.get_personalization_hints()
        formality = hints.get('formality', 'casual')

        if formality == 'formal':
            greeting = f"Pleased to assist you, **{name}**."
        else:
            greeting = f"Great to assist you, **{name}**! 😊"

        menu = (
            f"{greeting}\n\n"
            "Here's how I can assist you today:\n\n"
            "**1️⃣ Ask Questions (FAQ)**\n"
            "   → Get instant answers about orders, payments, shipping, refunds\n"
            "   → Powered by AI semantic search (0.03s response time!)\n\n"
            "**2️⃣ Report a Dispute**\n"
            "   → Report issues with sellers, scams, or order problems\n"
            "   → I'll help you draft a professional message\n\n"
            "**3️⃣ Share Feedback**\n"
            "   → Tell us about your experience or suggest improvements\n"
            "   → Your input helps us improve!\n\n"
            "---\n\n"
            "💡 **Pro Tip:** You can type a number (1-3) OR just describe what you need!\n\n"
            "*Examples:*\n"
            "• \"How do I track my order?\" → I'll help immediately!\n"
            "• \"I have a problem with a seller\" → I'll start the dispute process\n\n"
            "**What would you like to do?**"
        )

        logger.info(f"Smart menu shown to {name} (formality={formality})")

        return menu

    def _resolve_user_name(self) -> str:
        user = getattr(self.session, 'user', None)
        if user:
            full_name = user.get_full_name().strip()
            if full_name:
                return full_name
            first_name = getattr(user, 'first_name', '').strip()
            if first_name:
                return first_name
        return "there"

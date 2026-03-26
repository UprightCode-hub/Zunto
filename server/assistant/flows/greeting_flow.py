"""
server/assistant/flows/greeting_flow.py

Fixes applied:
  1. homepage_reco mode gets a 2-line compact greeting instead of
     the 6-bullet onboarding wall (wrong format for inline widget)
  2. Standard first-time greeting trimmed from ~150 words to ~40
  3. Returning user greeting trimmed to 2 lines
"""
from typing import Dict
import logging

from assistant.utils.constants import STATE_MENU

logger = logging.getLogger(__name__)


class GreetingFlow:

    def __init__(self, session, context_mgr):
        self.session = session
        self.context_mgr = context_mgr
        logger.debug(f"GreetingFlow initialized for session {session.session_id[:8]}")

    def start_conversation(self) -> str:
        self.session.current_state = STATE_MENU
        self.session.save(update_fields=['current_state', 'updated_at'])

        is_returning = self._is_returning_user()
        time_greeting = self._get_time_based_greeting()

        # homepage_reco: skip the onboarding wall entirely
        from assistant.utils.assistant_modes import ASSISTANT_MODE_HOMEPAGE_RECO
        if getattr(self.session, 'assistant_mode', '') == ASSISTANT_MODE_HOMEPAGE_RECO:
            greeting = self._get_reco_greeting(time_greeting)
        elif is_returning:
            greeting = self._get_returning_user_greeting(time_greeting)
        else:
            greeting = self._get_first_time_greeting(time_greeting)

        self.context_mgr.add_message(
            role='assistant',
            content=greeting,
            confidence=1.0,
            metadata={'greeting_type': 'returning' if is_returning else 'first_time'}
        )

        logger.info(f"Greeting sent: type={'returning' if is_returning else 'first_time'}")
        return greeting

    # -----------------------------------------------------------------------
    # Greeting variants
    # -----------------------------------------------------------------------

    def _get_reco_greeting(self, time_greeting: str) -> str:
        """
        Compact greeting for the inline homepage recommendation widget.
        Gets out of the way immediately so the user can start searching.
        """
        user_name = self._resolve_user_name()
        name_part = f", {user_name}" if user_name != 'there' else ''
        return (
            f"👋 {time_greeting}{name_part}! What are you looking for today?\n\n"
            "I can find products, compare prices, and guide you to the best deals on Zunto."
        )

    def _get_first_time_greeting(self, time_greeting: str) -> str:
        """Standard welcome for support assistant lanes (inbox / FAQ / dispute)."""
        user_name = self._resolve_user_name()
        return (
            f"👋 **{time_greeting}! Welcome to Zunto Marketplace!**\n\n"
            "I'm your Zunto support assistant — here to help with orders, "
            "payments, disputes, and general questions.\n\n"
            f"**How can I help you today, {user_name}?**"
        )

    def _get_returning_user_greeting(self, time_greeting: str) -> str:
        user_name = self._resolve_user_name()
        return (
            f"👋 **{time_greeting}, {user_name}!** Great to see you again.\n\n"
            "**What would you like help with today?**"
        )

    # -----------------------------------------------------------------------
    # Menu builder (used by ConversationManager when user returns to menu)
    # -----------------------------------------------------------------------

    def _build_unified_menu(self, name: str) -> str:
        hints: Dict = self.context_mgr.get_personalization_hints()
        formality = hints.get('formality', 'casual')

        if formality == 'formal':
            greeting = f"Pleased to assist you, **{name}**."
        else:
            greeting = f"Great to assist you, **{name}**! 😊"

        menu = (
            f"{greeting}\n\n"
            "Here's how I can help you today:\n\n"
            "**1️⃣ Ask Questions (FAQ)**\n"
            "   → Get instant answers about orders, payments, shipping, refunds\n\n"
            "**2️⃣ Report a Dispute**\n"
            "   → Report issues with sellers, scams, or order problems\n\n"
            "**3️⃣ Share Feedback**\n"
            "   → Tell us about your experience or suggest improvements\n\n"
            "---\n\n"
            "💡 You can type a number (1–3) or just describe what you need.\n\n"
            "**What would you like to do?**"
        )

        logger.info(f"Smart menu shown to {name} (formality={formality})")
        return menu

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _is_returning_user(self) -> bool:
        if self.session.message_count > 0:
            return True
        if self.session.user_id:
            from assistant.models import ConversationSession
            previous = ConversationSession.objects.filter(
                user_id=self.session.user_id
            ).exclude(session_id=self.session.session_id).count()
            if previous > 0:
                return True
        return False

    def _get_time_based_greeting(self) -> str:
        from django.utils import timezone
        hour = timezone.now().hour
        if 5 <= hour < 12:
            return "Good morning"
        elif 12 <= hour < 17:
            return "Good afternoon"
        elif 17 <= hour < 22:
            return "Good evening"
        else:
            return "Hello"

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
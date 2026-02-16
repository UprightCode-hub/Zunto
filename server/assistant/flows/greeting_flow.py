#server/assistant/flows/greeting_flow.py
"""Greeting flow handling name collection and menu presentation."""
from typing import Tuple, Dict
import logging
from datetime import datetime

from assistant.ai import detect_name
from assistant.utils.constants import STATE_AWAITING_NAME, STATE_MENU

logger = logging.getLogger(__name__)


class GreetingFlow:
    """Greeting flow."""

    def __init__(self, session, context_mgr):
        self.session = session
        self.context_mgr = context_mgr
        logger.debug(f"GreetingFlow initialized for session {session.session_id[:8]}")

    def start_conversation(self) -> str:
        self.session.current_state = STATE_AWAITING_NAME
        self.session.save()

        is_returning = self._is_returning_user()
        time_greeting = self._get_time_based_greeting()

        if is_returning:
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
        return (
            f"👋 **{time_greeting}! Welcome to Zunto Marketplace!**\n\n"
            f"I'm **Gigi**, your intelligent AI assistant powered by advanced natural language processing. "
            f"I can help you with:\n\n"
            f"✨ **Smart Answers** - Lightning-fast responses to your questions (0.03s!)\n"
            f"🛡️ **Dispute Resolution** - Professional help with order issues\n"
            f"💬 **Natural Conversation** - I understand context and remember our chat\n"
            f"🎨 **Creator Insights** - Learn about the AI technology behind me\n\n"
            f"I'm here to make your marketplace experience smooth and enjoyable.\n\n"
            f"**Before we begin, may I know your name?**\n"
            f"*(This helps me personalize our conversation - I support names in any language!)*"
        )

    def _get_returning_user_greeting(self, time_greeting: str) -> str:
        return (
            f"👋 **{time_greeting}! Welcome back to Zunto!**\n\n"
            f"Great to see you again! I'm **Gigi**, and I'm ready to help you today.\n\n"
            f"I remember our previous conversations and can pick up right where we left off.\n\n"
            f"**What's your name?** *(Or type 'same' if you've told me before!)*"
        )

    def handle_name_input(self, message: str) -> Tuple[str, Dict]:
        """Handle name collection and show unified menu."""
        name, confidence = detect_name(message)

        if name:
            self.session.user_name = name
            self.session.current_state = STATE_MENU
            self.session.save()

            response = self._build_unified_menu(name)

            return response, {
                'name_detected': True,
                'name': name,
                'confidence': confidence
            }
        else:
            return (
                "I didn't quite catch that. Could you please share your name? "
                "(Just your first name is fine!)"
            ), {'name_detected': False, 'confidence': 0.0}

    def _build_unified_menu(self, name: str) -> str:
        """Build personalized menu with dynamic formality."""
        hints = self.context_mgr.get_personalization_hints()
        formality = hints.get('formality', 'casual')

        if formality == 'formal':
            greeting = f"Pleased to meet you, **{name}**."
        else:
            greeting = f"Nice to meet you, **{name}**! 😊"

        menu = (
            f"{greeting}\n\n"
            f"Here's how I can assist you today:\n\n"
            f"**1️⃣ Ask Questions (FAQ)**\n"
            f"   → Get instant answers about orders, payments, shipping, refunds\n"
            f"   → Powered by AI semantic search (0.03s response time!)\n\n"
            f"**2️⃣ Report a Dispute**\n"
            f"   → Report issues with sellers, scams, or order problems\n"
            f"   → I'll help you draft a professional message\n\n"
            f"**3️⃣ Share Feedback**\n"
            f"   → Tell us about your experience or suggest improvements\n"
            f"   → Your input helps us improve!\n\n"
            f"**4️⃣ About My Creator** 🎨\n"
            f"   → Learn about Wisdom Ekwugha, the AI engineer who built me\n"
            f"   → Discover the technology and innovation behind this assistant\n\n"
            f"---\n\n"
            f"💡 **Pro Tip:** You can type a number (1-4) OR just describe what you need!\n\n"
            f"*Examples:*\n"
            f"• \"How do I track my order?\" → I'll help immediately!\n"
            f"• \"I have a problem with a seller\" → I'll start the dispute process\n"
            f"• \"Who created you?\" → I'll tell you about Wisdom!\n\n"
            f"**What would you like to do?**"
        )

        logger.info(f"Smart menu shown to {name} (formality={formality})")

        return menu

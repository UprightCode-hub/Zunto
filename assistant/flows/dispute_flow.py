"""
Dispute Flow - Multi-step dispute reporting with AI draft generation.
"""
import logging
from typing import Dict, Optional, Tuple
from assistant.models import Report

logger = logging.getLogger(__name__)


class DisputeFlow:
    """
    Premium dispute reporting flow with AI-assisted message drafting.
    Integrates with Groq for professional communication generation.
    """

    STEP_COLLECT_DESCRIPTION = 'collecting_details'
    STEP_CATEGORIZE = 'categorizing'
    STEP_SHOW_CONTACT = 'show_contact'
    STEP_GENERATE_DRAFT = 'generate_draft'
    STEP_DRAFT_SHOWN = 'draft_shown'
    STEP_COMPLETE = 'complete'

    CATEGORY_KEYWORDS = {
        'scam': ['scam', 'fraud', 'fake', 'cheat', 'lie', 'steal', 'stolen'],
        'payment': ['payment', 'paid', 'money', 'refund', 'charge', 'bank', 'transaction'],
        'shipping': ['shipping', 'delivery', 'package', 'tracking', 'arrive', 'delivered'],
        'product': ['product', 'item', 'quality', 'defective', 'broken', 'damaged', 'wrong'],
        'seller': ['seller', 'vendor', 'merchant', 'shop', 'store'],
        'buyer': ['buyer', 'customer', 'purchaser'],
        'communication': ['respond', 'reply', 'contact', 'message', 'communicate'],
        'other': []
    }

    DISPUTE_INTRO = """I understand {name}. I'm here to help you report this issue. 🛡️

Please describe what happened in detail. Include:
- What went wrong?
- When did it happen?
- Who was involved (seller/buyer)?
- Any relevant order numbers or details

The more information you provide, the better we can assist you."""

    CONTACT_INFO = """Thank you for providing those details, {name}.

📞 **Zunto Project Support Channels:**

🐦 **Twitter/X:** @ZuntoProject
   https://x.com/ZuntoProject
📧 **Email:** zuntoproject@gmail.com
💬 **WhatsApp:** +234-708-359-4102
   https://wa.me/message/PQP6RKHLCYEOJ1
📱 **Instagram:** @zuntoproject
   https://www.instagram.com/zuntoproject

Our team typically responds within 24 hours.

Would you like me to help you draft a professional message to send them?
Type: **email**, **twitter**, **whatsapp**, **instagram**, or **no** if you prefer to write your own."""

    DRAFT_INTRO_TEMPLATE = """Here's a professional {platform} message you can use:

---
{draft}
---

Feel free to copy and modify this message. You can send it to our support team via {platform}.

Would you like me to:
- **Generate** a different version
- **Edit** this one (tell me what to change)
- **Done** - I'm satisfied with this

Type your choice or "menu" to return to main menu."""

    COMPLETION_MESSAGE = """Your dispute report has been logged successfully! ✅

**Report ID:** #{report_id}

Our support team will review your case and reach out within 24 hours. You can also reach out directly using the contact info shared earlier.

Is there anything else I can help you with today?
Type "menu" to see options or ask another question."""

    def __init__(self, session, local_model_adapter=None, context_manager=None):
        """
        Initialize dispute flow.
        
        Args:
            session: ConversationSession instance
            local_model_adapter: LocalModelAdapter (Groq) for draft generation
            context_manager: Optional ContextManager for tracking
        """
        self.session = session
        self.llm = local_model_adapter
        self.context_manager = context_manager
        self.name = session.user_name or "there"

        # Get or initialize context
        self.context = session.context or {}
        if 'dispute' not in self.context:
            self.context['dispute'] = {
                'step': self.STEP_COLLECT_DESCRIPTION,
                'description': '',
                'category': '',
                'platform': '',
                'draft_message': '',
                'report_id': None
            }

    def enter_dispute_mode(self) -> str:
        """
        Enter dispute mode and show intro.
        
        Returns:
            Intro message
        """
        self.session.current_state = 'dispute_mode'
        self.context['dispute']['step'] = self.STEP_COLLECT_DESCRIPTION
        self._save_context()

        if self.context_manager:
            self.context_manager.mark_mode_used('dispute_mode')
            self.context_manager.mark_topic_discussed('dispute')

        logger.info(f"User {self.name} entered dispute mode")

        return self.DISPUTE_INTRO.format(name=self.name)

    def handle_dispute_message(self, message: str) -> Tuple[str, Dict]:
        """
        Handle message in dispute flow based on current step.
        
        Args:
            message: User's input
        
        Returns:
            (reply_text, metadata)
            metadata: {
                'step': str,
                'complete': bool,
                'report_id': int (if complete)
            }
        """
        current_step = self.context['dispute']['step']
        msg_lower = message.lower().strip()

        # Check for exit command
        if msg_lower in ['menu', 'cancel', 'exit', 'back']:
            return self._exit_dispute_flow(), {'step': 'exit', 'complete': False}

        if current_step == self.STEP_COLLECT_DESCRIPTION:
            return self._handle_description(message)

        elif current_step == self.STEP_SHOW_CONTACT:
            return self._handle_contact_choice(message)

        elif current_step == self.STEP_GENERATE_DRAFT:
            return self._handle_draft_generation(message)

        elif current_step == self.STEP_DRAFT_SHOWN:
            return self._handle_draft_feedback(message)

        else:
            return self._exit_dispute_flow(), {'step': 'error', 'complete': False}

    def _handle_description(self, message: str) -> Tuple[str, Dict]:
        """Step 1: Collect dispute description."""
        self.context['dispute']['description'] = message

        category = self._detect_category(message)
        self.context['dispute']['category'] = category

        self.context['dispute']['step'] = self.STEP_SHOW_CONTACT
        self._save_context()

        logger.info(f"Dispute description collected (category: {category})")

        reply = self.CONTACT_INFO.format(name=self.name)

        return reply, {
            'step': self.STEP_SHOW_CONTACT,
            'complete': False,
            'category': category
        }

    def _handle_contact_choice(self, message: str) -> Tuple[str, Dict]:
        """Step 2: Handle user's contact platform choice."""
        msg_lower = message.lower().strip()

        if msg_lower in ['no', 'n', 'nope', 'skip', "i'll write my own"]:
            return self._save_dispute_without_draft()

        platform = None
        if 'email' in msg_lower:
            platform = 'email'
        elif 'twitter' in msg_lower or 'tweet' in msg_lower or 'x' in msg_lower:
            platform = 'twitter'
        elif 'whatsapp' in msg_lower or 'whats app' in msg_lower:
            platform = 'whatsapp'
        elif 'instagram' in msg_lower or 'insta' in msg_lower or 'ig' in msg_lower:
            platform = 'instagram'

        if platform:
            self.context['dispute']['platform'] = platform
            self.context['dispute']['step'] = self.STEP_GENERATE_DRAFT
            self._save_context()

            return self._generate_draft(platform)

        else:
            # Unclear choice - prompt again
            return (
                "I didn't catch that. Would you like a draft for:\n"
                "- **email**\n"
                "- **twitter**\n"
                "- **whatsapp**\n"
                "- **instagram**\n\n"
                "Or type **no** if you prefer to write your own message.",
                {'step': self.STEP_SHOW_CONTACT, 'complete': False}
            )

    def _generate_draft(self, platform: str) -> Tuple[str, Dict]:
        """Generate professional message draft using Groq."""
        description = self.context['dispute']['description']
        category = self.context['dispute']['category']

        # Check if LLM is available
        if not self.llm or not self.llm.is_available():
            logger.warning("LLM unavailable for draft generation")
            return self._save_dispute_without_draft()

        try:
            if platform == 'email':
                prompt = f"""Write a professional email to Zunto marketplace support.

Issue Category: {category}
User's Description: {description}

Write a clear, respectful email (4-5 sentences) that:
- Has a proper subject line
- States the problem clearly
- Requests appropriate action
- Remains professional and courteous
- Includes a polite closing

Format:
Subject: [Subject Line]

Dear Zunto Support Team,

[Email Body]

Best regards,
[User]"""

            elif platform == 'twitter':
                prompt = f"""Write a professional tweet for @ZuntoProject.

Issue Category: {category}
User's Description: {description}

Write a concise, professional tweet (under 280 characters) that:
- Tags @ZuntoProject
- States the issue briefly
- Remains respectful
- Requests help

Format:
@ZuntoProject [Message]"""

            elif platform == 'instagram':
                prompt = f"""Write a professional Instagram DM to @zuntoproject.

Issue Category: {category}
User's Description: {description}

Write a clear, friendly message (3-4 sentences) that:
- States the problem clearly
- Requests appropriate action
- Remains professional but approachable
- Uses a casual but respectful tone

Format:
[Message]"""

            else:  # whatsapp
                prompt = f"""Write a professional WhatsApp message to Zunto support.

Issue Category: {category}
User's Description: {description}

Write a clear, conversational message (3-4 sentences) that:
- States the problem clearly
- Requests appropriate action
- Remains professional but friendly

Format:
[Message]"""

            logger.info(f"Generating {platform} draft using Groq...")
            result = self.llm.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )

            draft = result['response'].strip()

            self.context['dispute']['draft_message'] = draft
            self.context['dispute']['step'] = self.STEP_DRAFT_SHOWN
            self._save_context()

            logger.info(f"Draft generated successfully ({len(draft)} chars)")

            reply = self.DRAFT_INTRO_TEMPLATE.format(
                platform=platform.title(),
                draft=draft
            )

            return reply, {
                'step': self.STEP_DRAFT_SHOWN,
                'complete': False,
                'draft_generated': True
            }

        except Exception as e:
            logger.error(f"Draft generation failed: {e}", exc_info=True)
            return (
                f"I apologize, {self.name}, but I'm having trouble generating the draft right now.\n\n"
                "You can copy your details and send them manually:\n\n"
                f"{description}\n\n"
                "I've logged your report. Our team will review it shortly.\n\n"
                "Is there anything else I can help with?",
                {'step': 'error', 'complete': True}
            )

    def _handle_draft_feedback(self, message: str) -> Tuple[str, Dict]:
        """Step 3: Handle feedback on generated draft."""
        msg_lower = message.lower().strip()

        if 'generate' in msg_lower or 'different' in msg_lower or 'another' in msg_lower:
            platform = self.context['dispute']['platform']
            self.context['dispute']['step'] = self.STEP_GENERATE_DRAFT
            self._save_context()

            logger.info("Regenerating draft per user request")
            return self._generate_draft(platform)

        elif 'edit' in msg_lower:
            return (
                f"Please tell me what you'd like to change, {self.name}.\n\n"
                "For example:\n"
                "- \"Make it more urgent\"\n"
                "- \"Add order number #12345\"\n"
                "- \"Make it shorter\"\n\n"
                "Or describe your changes:",
                {'step': self.STEP_DRAFT_SHOWN, 'complete': False}
            )

        elif 'done' in msg_lower or 'satisfied' in msg_lower or 'good' in msg_lower or 'ok' in msg_lower:
            return self._save_dispute_with_draft()

        else:
            # Unclear response - assume edit request
            return self._regenerate_with_edits(message)

    def _regenerate_with_edits(self, edit_instruction: str) -> Tuple[str, Dict]:
        """Regenerate draft based on user's edit instructions."""
        description = self.context['dispute']['description']
        current_draft = self.context['dispute']['draft_message']
        platform = self.context['dispute']['platform']

        if not self.llm or not self.llm.is_available():
            return (
                "I'm unable to edit the draft right now. You can copy and modify it manually.\n\n"
                "Type 'done' when you're satisfied, or 'menu' to return to main menu.",
                {'step': self.STEP_DRAFT_SHOWN, 'complete': False}
            )

        try:
            prompt = f"""Edit this {platform} message based on the user's request.

Original Message:
{current_draft}

Original Issue:
{description}

User's Edit Request:
{edit_instruction}

Generate an improved version that incorporates the requested changes while maintaining professionalism.

Improved Message:"""

            result = self.llm.generate(prompt=prompt, max_tokens=300, temperature=0.3)
            new_draft = result['response'].strip()

            self.context['dispute']['draft_message'] = new_draft
            self._save_context()

            reply = f"""Here's the updated version:

---
{new_draft}
---

How's this? Type:
- **done** if you're satisfied
- **edit** with more changes
- **generate** for a completely different version"""

            return reply, {'step': self.STEP_DRAFT_SHOWN, 'complete': False}

        except Exception as e:
            logger.error(f"Draft editing failed: {e}")
            return (
                "I had trouble editing that. You can copy the original and modify it manually.\n\n"
                "Type 'done' to proceed or 'menu' to return.",
                {'step': self.STEP_DRAFT_SHOWN, 'complete': False}
            )

    def _detect_category(self, message: str) -> str:
        """Auto-detect dispute category from keywords."""
        msg_lower = message.lower()

        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in msg_lower)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score, default to 'other'
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'other'

    def _save_dispute_with_draft(self) -> Tuple[str, Dict]:
        """Save dispute report with AI-generated draft to database."""
        dispute_data = self.context['dispute']

        report = Report.objects.create(
            user=self.session.user,
            message=dispute_data['description'],
            report_type='dispute',
            category=dispute_data['category'],
            severity='medium',
            ai_generated_draft=dispute_data['draft_message'],
            contact_preference=dispute_data['platform'],
            meta={
                'session_id': self.session.session_id,
                'user_name': self.name,
                'platform': dispute_data['platform']
            }
        )

        logger.info(f"Dispute report saved: Report #{report.id} with draft")

        # Reset dispute context
        self.context['dispute'] = {'step': self.STEP_COMPLETE}
        self.session.current_state = 'menu'
        self._save_context()

        reply = self.COMPLETION_MESSAGE.format(report_id=report.id)

        return reply, {
            'step': 'complete',
            'complete': True,
            'report_id': report.id
        }

    def _save_dispute_without_draft(self) -> Tuple[str, Dict]:
        """Save dispute report without draft generation."""
        dispute_data = self.context['dispute']

        report = Report.objects.create(
            user=self.session.user,
            message=dispute_data['description'],
            report_type='dispute',
            category=dispute_data.get('category', 'other'),
            severity='medium',
            contact_preference='none',
            meta={
                'session_id': self.session.session_id,
                'user_name': self.name
            }
        )

        logger.info(f"Dispute report saved: Report #{report.id} (no draft)")

        # Reset context
        self.context['dispute'] = {'step': self.STEP_COMPLETE}
        self.session.current_state = 'menu'
        self._save_context()

        reply = self.COMPLETION_MESSAGE.format(report_id=report.id)

        return reply, {
            'step': 'complete',
            'complete': True,
            'report_id': report.id
        }

    def _exit_dispute_flow(self) -> str:
        """Exit dispute mode and return to menu."""
        self.session.current_state = 'menu'
        self.context['dispute'] = {'step': self.STEP_COLLECT_DESCRIPTION}
        self._save_context()

        logger.info(f"User {self.name} exited dispute mode")

        return f"""No problem, {self.name}. Returning to main menu.

What would you like to do?

1️⃣ **Report a Dispute** - Start over or report a different issue
2️⃣ **Ask FAQ Questions** - Get quick answers
3️⃣ **Share Feedback** - Tell us what you think

Type 1, 2, 3, or describe what you need!"""

    def _save_context(self):
        """Persist context to session."""
        self.session.context = self.context
        self.session.save(update_fields=['context', 'current_state', 'updated_at'])
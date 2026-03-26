"""FAQ flow for question handling with retrieval support."""
import logging
from typing import Dict, Optional, Tuple, List

from assistant.utils.constants import ConfidenceConfig, STATE_FAQ_MODE, STATE_MENU

logger = logging.getLogger(__name__)


class FAQFlow:
    """FAQ flow handler with retrieval-based responses."""

    FAQ_MODE_INTRO = """Perfect {name}! 📚 I'm ready to answer your questions about Zunto.

What would you like to know? (e.g., How do refunds work? How do I verify sellers?)"""

    CLARIFICATION_TEMPLATE = """I found a few topics that might help:

{suggestions}

Which one matches your question? (Type the number or rephrase your question)"""

    LOW_CONFIDENCE_TEMPLATE = """I'm not entirely sure about that, but here's what I found:

{answer}

💡 **Did this answer your question?**
- Type "yes" if this helped
- Type "no" to rephrase or ask differently
- Type "menu" to see other options"""

    FOLLOW_UP_PROMPT = """Glad I could help! 😊

Do you have any other questions? Or would you like to:
1️⃣ Ask another FAQ
2️⃣ Report an issue
3️⃣ Return to main menu

Just type your question or choose an option!"""

    def __init__(self, session, query_processor, context_manager=None):
        self.session = session
        self.query_processor = query_processor
        self.context_manager = context_manager
        self.name = self._resolve_user_name(session)

    def _resolve_user_name(self, session) -> str:
        try:
            user = getattr(session, 'user', None)
            if user and not user.is_anonymous:
                name = user.get_full_name()
                if name:
                    return name.split()[0]
                return user.email.split('@')[0]
        except Exception:
            pass
        return 'there'

    def enter_faq_mode(self) -> str:
        self.session.current_state = STATE_FAQ_MODE
        self.session.save()

        if self.context_manager:
            self.context_manager.mark_mode_used('faq_mode')

        logger.info(f"User {self.name} entered FAQ mode")
        return self.FAQ_MODE_INTRO.format(name=self.name)

    def handle_faq_query(self, message: str) -> Tuple[str, Dict]:
        msg_lower = message.lower().strip()

        if msg_lower in ['menu', 'main menu', 'back', 'exit']:
            return self._exit_to_menu(), {'success': True, 'action': 'exit'}

        if msg_lower in ['yes', 'y', 'yeah', 'yep', 'that helped', 'thanks', 'thank you']:
            if self.context_manager:
                self.context_manager.mark_resolution(success=True)
            return self.FOLLOW_UP_PROMPT, {'success': True, 'action': 'satisfied'}

        if msg_lower in ['no', 'n', 'nope', 'not really', "didn't help", "that's not it"]:
            if self.context_manager:
                self.context_manager.mark_resolution(success=False)
            return (
                f"I apologize that didn't help, {self.name}. Let me try again.\n\n"
                "Could you rephrase your question or provide more details?"
            ), {'success': False, 'action': 'retry_prompt'}

        logger.info(f"Processing FAQ query: {message[:50]}...")
        result = self.query_processor.process(message)

        confidence = result['confidence']
        tier = self._determine_tier(confidence)

        # ── Topic tracking ─────────────────────────────────────────────────
        # Previously tracked via faq_hit keywords, but faq_hit is now None
        # on the LLM reasoner path. Track via RAG reference IDs instead.
        # This is best-effort — the LLM path populates rag_references_used
        # when RAG evidence was available; falls back silently if not.
        if self.context_manager:
            rag_refs = result.get('metadata', {}).get('rag_references_used', [])
            if rag_refs:
                # Use the first referenced FAQ ID as the topic marker.
                # Downstream analytics can join on FAQ ID if needed.
                self.context_manager.mark_topic_discussed(f"faq_ref:{rag_refs[0]}")

        if tier == 'high':
            reply = self._build_high_confidence_response(result)
            needs_followup = False
            success = True
        elif tier == 'medium':
            reply = self._build_medium_confidence_response(result)
            needs_followup = True
            success = True
        else:
            reply = self._build_low_confidence_response(result)
            needs_followup = True
            success = False

        metadata = {
            'confidence': confidence,
            'tier': tier,
            # faq_hit is None on LLM path — kept for backward compat shape only
            'faq_used': result.get('faq_hit'),
            'needs_followup': needs_followup,
            'success': success,
            'explanation': result.get('explanation', ''),
            'source': result.get('source', 'unknown'),
        }

        logger.info(
            f"FAQ response: tier={tier}, confidence={confidence:.3f}, "
            f"source={metadata['source']}"
        )

        return reply, metadata

    def _determine_tier(self, confidence: float) -> str:
        if confidence >= ConfidenceConfig.RAG['high']:
            return 'high'
        elif confidence >= ConfidenceConfig.RAG['medium']:
            return 'medium'
        else:
            return 'low'

    def _build_high_confidence_response(self, result: Dict) -> str:
        return f"{result['reply']}\n\n{self.FOLLOW_UP_PROMPT}"

    def _build_medium_confidence_response(self, result: Dict) -> str:
        clarification = (
            "\n\n💡 **Is this what you were looking for?**\n"
            "Type 'yes' if this helped, or rephrase your question for more specific info."
        )
        return f"{result['reply']}{clarification}"

    def _build_low_confidence_response(self, result: Dict) -> str:
        return self.LOW_CONFIDENCE_TEMPLATE.format(answer=result['reply'])

    def suggest_related_faqs(self, faqs: List[Dict], max_suggestions: int = 3) -> str:
        suggestions = []
        for i, faq in enumerate(faqs[:max_suggestions], 1):
            suggestions.append(f"{i}️⃣ {faq['question']}")
        return self.CLARIFICATION_TEMPLATE.format(suggestions="\n".join(suggestions))

    def _exit_to_menu(self) -> str:
        self.session.current_state = STATE_MENU
        self.session.save()
        logger.info(f"User {self.name} exited FAQ mode")
        return (
            "Back to the main menu! 👍\n\n"
            "What would you like to do next?\n\n"
            "1️⃣ **Report a Dispute** - Get help with issues or scams\n"
            "2️⃣ **Ask FAQ Questions** - More questions? I'm here!\n"
            "3️⃣ **Share Feedback** - Tell us what you think\n\n"
            "Type 1, 2, 3, or describe what you need!"
        )

    def get_popular_faqs(self, limit: int = 5) -> List[Dict]:
        try:
            rag = self.query_processor.rag_retriever
            popular_keywords = ['refund', 'payment', 'shipping', 'seller', 'order']
            popular_faqs = []
            for faq in rag.faqs:
                keywords = faq.get('keywords', [])
                if any(kw in keywords for kw in popular_keywords):
                    popular_faqs.append(faq)
                    if len(popular_faqs) >= limit:
                        break
            return popular_faqs
        except Exception as e:
            logger.error(f"Failed to get popular FAQs: {e}")
            return []
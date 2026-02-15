"""
FAQ Flow - Smart FAQ question handling with RAG integration.
"""
import logging
from typing import Dict, Optional, Tuple, List

from assistant.utils.constants import ConfidenceConfig, STATE_FAQ_MODE, STATE_MENU

logger = logging.getLogger(__name__)


class FAQFlow:
    """
    Premium FAQ flow handler with smart RAG integration.
    Leverages your 0.03s FAISS + BGE-small-en-v1.5 setup.
    """

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
        """
        Initialize FAQ flow.
        
        Args:
            session: ConversationSession instance
            query_processor: QueryProcessor instance (with RAG)
            context_manager: Optional ContextManager for tracking
        """
        self.session = session
        self.query_processor = query_processor
        self.context_manager = context_manager
        self.name = session.user_name or "there"

    def enter_faq_mode(self) -> str:
        """
        Enter FAQ mode and show intro message.
        
        Returns:
            Intro message
        """
        self.session.current_state = STATE_FAQ_MODE
        self.session.save()

        if self.context_manager:
            self.context_manager.mark_mode_used('faq_mode')

        logger.info(f"User {self.name} entered FAQ mode")

        return self.FAQ_MODE_INTRO.format(name=self.name)

    def handle_faq_query(self, message: str) -> Tuple[str, Dict]:
        """
        Process FAQ query with smart 3-tier handling.
        
        Args:
            message: User's question
        
        Returns:
            (reply_text, metadata)
            metadata: {
                'confidence': float,
                'tier': str,
                'faq_used': dict,
                'needs_followup': bool,
                'success': bool
            }
        """
        msg_lower = message.lower().strip()

        # Check for exit commands
        if msg_lower in ['menu', 'main menu', 'back', 'exit']:
            return self._exit_to_menu(), {'success': True, 'action': 'exit'}

        # Check for yes/no follow-up responses
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
        faq_hit = result.get('faq_hit')

        if tier == 'high':
            reply = self._build_high_confidence_response(result, faq_hit)
            needs_followup = False
            success = True

        elif tier == 'medium':
            reply = self._build_medium_confidence_response(result, faq_hit)
            needs_followup = True
            success = True

        else:  # low tier
            reply = self._build_low_confidence_response(result)
            needs_followup = True
            success = False

        if self.context_manager and faq_hit:
            keywords = faq_hit.get('keywords', [])
            if keywords:
                self.context_manager.mark_topic_discussed(keywords[0])

        metadata = {
            'confidence': confidence,
            'tier': tier,
            'faq_used': faq_hit,
            'needs_followup': needs_followup,
            'success': success,
            'explanation': result.get('explanation', '')
        }

        logger.info(
            f"FAQ response: tier={tier}, confidence={confidence:.3f}, "
            f"explanation={metadata['explanation']}"
        )

        return reply, metadata

    def _determine_tier(self, confidence: float) -> str:
        """Determine confidence tier based on your thresholds."""
        if confidence >= ConfidenceConfig.RAG['high']:
            return 'high'
        elif confidence >= ConfidenceConfig.RAG['medium']:
            return 'medium'
        else:
            return 'low'

    def _build_high_confidence_response(self, result: Dict, faq: Optional[Dict]) -> str:
        """
        Build response for high-confidence matches (≥0.65).
        Direct answer with follow-up prompt.
        """
        answer = result['reply']

        response = f"{answer}\n\n{self.FOLLOW_UP_PROMPT}"

        return response

    def _build_medium_confidence_response(self, result: Dict, faq: Optional[Dict]) -> str:
        """
        Build response for medium-confidence matches (0.40-0.64).
        Answer + clarification prompt.
        """
        answer = result['reply']

        clarification = f"\n\n💡 **Is this what you were looking for?**\nType 'yes' if this helped, or rephrase your question for more specific info."

        return f"{answer}{clarification}"

    def _build_low_confidence_response(self, result: Dict) -> str:
        """
        Build response for low-confidence matches (<0.40).
        Tentative answer + explicit feedback request.
        """
        answer = result['reply']

        return self.LOW_CONFIDENCE_TEMPLATE.format(answer=answer)

    def suggest_related_faqs(self, faqs: List[Dict], max_suggestions: int = 3) -> str:
        """
        Build suggestion list from multiple FAQs.
        Used when query is ambiguous.
        
        Args:
            faqs: List of FAQ matches
            max_suggestions: Max number to show
        
        Returns:
            Formatted suggestion text
        """
        suggestions = []
        for i, faq in enumerate(faqs[:max_suggestions], 1):
            suggestions.append(f"{i}️⃣ {faq['question']}")

        suggestion_text = "\n".join(suggestions)

        return self.CLARIFICATION_TEMPLATE.format(suggestions=suggestion_text)

    def _exit_to_menu(self) -> str:
        """Exit FAQ mode and return to menu."""
        self.session.current_state = STATE_MENU
        self.session.save()

        logger.info(f"User {self.name} exited FAQ mode")

        return f"""Back to the main menu! 👍

What would you like to do next?

1️⃣ **Report a Dispute** - Get help with issues or scams
2️⃣ **Ask FAQ Questions** - More questions? I'm here!
3️⃣ **Share Feedback** - Tell us what you think

Type 1, 2, 3, or describe what you need!"""

    def get_popular_faqs(self, limit: int = 5) -> List[Dict]:
        """
        Get popular FAQ topics to suggest.
        Uses RAG retriever's FAQ list.
        
        Args:
            limit: Number of FAQs to return
        
        Returns:
            List of popular FAQ dicts
        """
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
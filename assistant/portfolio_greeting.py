"""
Portfolio Demo Mode - Modified Greeting Flow
For LinkedIn/Portfolio demonstrations

Shows off your AI development skills while keeping full functionality.
"""
from typing import Tuple, Dict
from assistant.ai import detect_name
from assistant.utils.constants import STATE_AWAITING_NAME, STATE_MENU


class PortfolioGreetingFlow:
    """
    Portfolio-focused greeting flow that highlights creator while maintaining functionality.
    """
    
    def __init__(self, session, context_mgr):
        self.session = session
        self.context_mgr = context_mgr
        # Portfolio mode flag - set True for LinkedIn demo
        self.portfolio_mode = True  # TODO: Make this configurable via settings
    
    def start_conversation(self) -> str:
        """
        Portfolio-focused greeting that introduces YOU as the creator.
        """
        self.session.current_state = STATE_AWAITING_NAME
        self.session.save()
        
        if self.portfolio_mode:
            return self._portfolio_greeting()
        else:
            return self._standard_greeting()
    
    def _portfolio_greeting(self) -> str:
        """
        Portfolio greeting: Introduces Gigi AND Wisdom upfront.
        """
        return (
            "👋 **Hello! I'm Gigi** - an AI assistant created by **Wisdom Ekwugha**.\n\n"
            "I'm a demonstration of advanced conversational AI, featuring:\n"
            "✨ Multi-language name detection\n"
            "🎯 Intent classification with emotion detection\n"
            "📚 RAG-powered FAQ system (0.03s response time)\n"
            "🤖 Smart context management & personalization\n\n"
            "I can help with marketplace queries, answer questions about my creator, "
            "or showcase my AI capabilities.\n\n"
            "**What's your name?** (So I can personalize our conversation!)"
        )
    
    def _standard_greeting(self) -> str:
        """
        Standard greeting for production use.
        """
        return (
            "Hello! Welcome to Zunto Marketplace! 🎉\n\n"
            "I'm Gigi, your virtual assistant. I'm here to help you with anything "
            "related to buying, selling, or using our platform.\n\n"
            "Before we begin, may I know your name?"
        )
    
    def handle_name_input(self, message: str) -> Tuple[str, Dict]:
        """
        Handle name collection with portfolio context.
        """
        # Use premium name detection
        name, confidence = detect_name(message)
        
        if name:
            self.session.user_name = name
            self.session.current_state = STATE_MENU
            self.session.save()
            
            if self.portfolio_mode:
                response = self._portfolio_menu(name)
            else:
                response = self._standard_menu(name)
            
            return response, {
                'name_detected': True,
                'name': name,
                'confidence': confidence
            }
        else:
            # Name not detected - ask again
            return (
                "I didn't quite catch that. Could you please share your name? "
                "(Just your first name is fine!)"
            ), {'name_detected': False, 'confidence': 0.0}
    
    def _portfolio_menu(self, name: str) -> str:
        """
        Portfolio-focused menu that highlights creator info first.
        """
        return (
            f"Nice to meet you, **{name}**! 😊\n\n"
            f"Here's what I can do:\n\n"
            f"🎨 **Learn About My Creator** - Ask me about Wisdom Ekwugha, the AI developer who built me\n"
            f"💡 **See My Capabilities** - Explore my technical features (RAG, NLP, context management)\n"
            f"📚 **Ask FAQ Questions** - Test my knowledge retrieval system\n"
            f"🛠️ **Report Issues** - See my multi-step dispute handling flow\n"
            f"💬 **General Chat** - Have a conversation and see my personalization in action\n\n"
            f"**Try asking:**\n"
            f"• \"Who is your developer?\"\n"
            f"• \"What technologies were used to build you?\"\n"
            f"• \"How do you process questions so fast?\"\n"
            f"• Or anything else you're curious about!"
        )
    
    def _standard_menu(self, name: str) -> str:
        """
        Standard menu for production use.
        """
        return (
            f"Hi {name}! 😊 Great to meet you!\n\n"
            f"Here's how I can assist you today:\n\n"
            f"1️⃣ **Report a Dispute** - Report suspicious activity, scams, or problems with sellers/buyers\n"
            f"2️⃣ **Ask FAQ Questions** - Quick answers to common questions about orders, payments, refunds, and more\n"
            f"3️⃣ **Share Feedback** - Tell us about your experience or suggest improvements\n\n"
            f"Just type **1**, **2**, or **3**, or describe what you need help with!"
        )
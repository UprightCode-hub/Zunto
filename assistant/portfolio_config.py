"""
Portfolio Demo Configuration
assistant/portfolio_config.py

Toggle between Portfolio Mode (LinkedIn demo) and Production Mode.
"""
from django.conf import settings


class PortfolioConfig:
    """
    Configuration for Portfolio Demo Mode.
    
    Portfolio Mode:
    - Emphasizes creator information (Wisdom Ekwugha)
    - Showcases AI capabilities upfront
    - Suggests creator-focused queries
    - Perfect for LinkedIn, portfolio sites, job applications
    
    Production Mode:
    - Standard Zunto marketplace assistant
    - Business-focused features
    - Customer support emphasis
    """
    
    # MAIN TOGGLE - Set True for LinkedIn demo, False for production
    PORTFOLIO_MODE = getattr(settings, 'ASSISTANT_PORTFOLIO_MODE', True)
    
    # Portfolio Mode Settings
    PORTFOLIO_SETTINGS = {
        'greeting_style': 'showcase_creator',  # Options: 'showcase_creator', 'standard'
        'menu_order': 'creator_first',  # Options: 'creator_first', 'features_first', 'standard'
        'suggested_queries': [
            "Who is your developer?",
            "What technologies were used to build you?",
            "Tell me about your creator's background",
            "How do you process questions so fast?",
            "What makes you different from other chatbots?",
        ],
        'highlight_features': True,  # Show technical capabilities in greeting
        'creator_detail_default': 'balanced',  # Options: 'brief', 'balanced', 'detailed'
    }
    
    # Production Mode Settings
    PRODUCTION_SETTINGS = {
        'greeting_style': 'standard',
        'menu_order': 'standard',
        'suggested_queries': [],
        'highlight_features': False,
        'creator_detail_default': 'brief',
    }
    
    @classmethod
    def get_settings(cls) -> dict:
        """Get current mode settings."""
        if cls.PORTFOLIO_MODE:
            return cls.PORTFOLIO_SETTINGS
        return cls.PRODUCTION_SETTINGS
    
    @classmethod
    def is_portfolio_mode(cls) -> bool:
        """Check if portfolio mode is active."""
        return cls.PORTFOLIO_MODE
    
    @classmethod
    def get_greeting_template(cls) -> str:
        """Get appropriate greeting template."""
        settings = cls.get_settings()
        
        if settings['greeting_style'] == 'showcase_creator':
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
        else:
            return (
                "Hello! Welcome to Zunto Marketplace! 🎉\n\n"
                "I'm Gigi, your virtual assistant. I'm here to help you with anything "
                "related to buying, selling, or using our platform.\n\n"
                "Before we begin, may I know your name?"
            )
    
    @classmethod
    def get_menu_template(cls, user_name: str) -> str:
        """Get appropriate menu template."""
        settings = cls.get_settings()
        
        if settings['menu_order'] == 'creator_first':
            menu = f"Nice to meet you, **{user_name}**! 😊\n\n"
            menu += "Here's what I can do:\n\n"
            menu += "🎨 **Learn About My Creator** - Ask me about Wisdom Ekwugha, the AI developer who built me\n"
            menu += "💡 **See My Capabilities** - Explore my technical features (RAG, NLP, context management)\n"
            menu += "📚 **Ask Questions** - Test my knowledge retrieval system\n"
            menu += "🛠️ **Report Issues** - See my multi-step dispute handling\n"
            menu += "💬 **General Chat** - Have a conversation and see my personalization\n\n"
            
            if settings['suggested_queries']:
                menu += "**Try asking:**\n"
                for query in settings['suggested_queries'][:3]:
                    menu += f"• \"{query}\"\n"
            
            return menu
        
        else:
            return (
                f"Hi {user_name}! 😊 Great to meet you!\n\n"
                f"Here's how I can assist you today:\n\n"
                f"1️⃣ **Report a Dispute** - Report suspicious activity, scams, or problems\n"
                f"2️⃣ **Ask FAQ Questions** - Quick answers about orders, payments, refunds\n"
                f"3️⃣ **Share Feedback** - Tell us about your experience\n\n"
                f"Just type **1**, **2**, or **3**, or describe what you need help with!"
            )
    
    @classmethod
    def get_suggested_queries(cls) -> list:
        """Get list of suggested queries for current mode."""
        return cls.get_settings()['suggested_queries']


# Quick access functions
def is_portfolio_mode() -> bool:
    """Check if portfolio mode is active."""
    return PortfolioConfig.is_portfolio_mode()


def get_portfolio_greeting() -> str:
    """Get portfolio mode greeting."""
    return PortfolioConfig.get_greeting_template()


def get_portfolio_menu(user_name: str) -> str:
    """Get portfolio mode menu."""
    return PortfolioConfig.get_menu_template(user_name)
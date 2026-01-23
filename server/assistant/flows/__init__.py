"""
Flows Module - Conversational flow handlers for Zunto AI Assistant.

This module provides specialized conversation flows for different user intents:
- Greeting Flow: Welcome messages and name collection
- FAQ Flow: Answering common questions
- Dispute Flow: Handling seller disputes and scam reports
- Feedback Flow: Collecting user feedback and suggestions
"""

from assistant.flows.greeting_flow import GreetingFlow
from assistant.flows.faq_flow import FAQFlow
from assistant.flows.dispute_flow import DisputeFlow
from assistant.flows.feedback_flow import FeedbackFlow

__all__ = [
    'GreetingFlow',
    'FAQFlow',
    'DisputeFlow',
    'FeedbackFlow',
]

# Module version and info
__version__ = '2.0.0'
__author__ = 'Wisdom Ekwugha'

def get_module_info():
    """Get module information for health checks."""
    return {
        'module': 'assistant.flows',
        'version': __version__,
        'author': __author__,
        'flows': ['greeting', 'faq', 'dispute', 'feedback'],
        'available': True,
    }

def get_flow_for_intent(intent: str):
    """
    Get the appropriate flow handler for a given intent.
    
    Args:
        intent: User intent (e.g., 'greeting', 'faq', 'dispute', 'feedback')
    
    Returns:
        Flow class or None if intent not recognized
    """
    flow_map = {
        'greeting': GreetingFlow,
        'faq': FAQFlow,
        'dispute': DisputeFlow,
        'feedback': FeedbackFlow,
    }
    
    return flow_map.get(intent.lower())
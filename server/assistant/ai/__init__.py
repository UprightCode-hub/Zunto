#server/assistant/ai/__init__.py
              
__version__ = '2.0.0'
__author__ = 'Wisdom Ekwugha'
__email__ = 'ZuntoProject@gmail.com'

                           
from .name_detector import detect_name, NameDetector
from .intent_classifier import classify_intent, Intent, IntentClassifier
from .context_manager import ContextManager
from .response_personalizer import ResponsePersonalizer
from .creator_info import CREATOR_INFO, get_creator_bio, format_creator_card

            
__all__ = [
                    
    'detect_name',
    'NameDetector',
    
                           
    'classify_intent',
    'Intent',
    'IntentClassifier',
    
                        
    'ContextManager',
    
                              
    'ResponsePersonalizer',
    
                  
    'CREATOR_INFO',
    'get_creator_bio',
    'format_creator_card',
]


                      
USAGE_EXAMPLES = {
    'name_detection': """
Detect user's name from input
from assistant import detect_name

is_name, name, metadata = detect_name("Hi, I'm John Smith")
if is_name:
    print(f"Detected name: {name}")
    print(f"Confidence: {metadata['confidence']}")
""",
    
    'intent_classification': """
Classify user intent with emotion
from assistant import classify_intent

intent, confidence, metadata = classify_intent(
    "I want to report a scam seller!",
    context={}
)
print(f"Intent: {intent.value}, Emotion: {metadata['emotion']}")
""",
    
    'context_tracking': """
from assistant import ContextManager

context_mgr = ContextManager(session)
context_mgr.add_message(
    role='user',
    content=user_message,
    intent='dispute',
    emotion='frustrated'
)

hints = context_mgr.get_personalization_hints()
if context_mgr.is_escalated():
    print("User needs escalation!")
""",
    
    'response_personalization': """
from assistant import ResponsePersonalizer

personalizer = ResponsePersonalizer(session)
final_response = personalizer.personalize(
    base_response=raw_answer,
    confidence=0.85,
    emotion='frustrated',
    formality='formal'
)
""",
    
    'complete_pipeline': """
from assistant import (
    detect_name,
    classify_intent,
    ContextManager,
    ResponsePersonalizer
)

if state == 'awaiting_name':
    is_name, name, _ = detect_name(user_input)
    if is_name:
        session.user_name = name

intent, conf, metadata = classify_intent(user_input, session.context)
emotion = metadata['emotion']

context_mgr = ContextManager(session)
context_mgr.add_message('user', user_input, intent.value, emotion)

result = query_processor.process(user_input)

personalizer = ResponsePersonalizer(session)
hints = context_mgr.get_personalization_hints()

final_response = personalizer.personalize(
    base_response=result['reply'],
    confidence=result['confidence'],
    emotion=emotion,
    formality=hints['formality']
)

context_mgr.add_message('assistant', final_response, confidence=result['confidence'])

return final_response
"""
}


def get_usage_example(component: str) -> str:
    """
    Get usage example for a specific component.
    
    Args:
        component: One of 'name_detection', 'intent_classification', 
                  'context_tracking', 'response_personalization', 'complete_pipeline'
    
    Returns:
        Example code string
    """
    return USAGE_EXAMPLES.get(component, "No example available for this component.")


def get_module_info() -> dict:
    """
    Get module information and statistics.
    
    Returns:
        Dict with module stats
    """
    return {
        'version': __version__,
        'author': __author__,
        'components': len(__all__),
        'component_list': __all__,
        'examples_available': list(USAGE_EXAMPLES.keys()),
        'description': 'Conversational assistant components'
    }


                                 
def _validate_imports():
    """Validate that all components imported successfully."""
    import logging
    logger = logging.getLogger(__name__)
    
    missing = []
    for component in __all__:
        if component not in globals():
            missing.append(component)
    
    if missing:
        logger.warning(f"Some AI components failed to import: {missing}")
        logger.warning("Check individual module files for errors.")
    else:
        logger.info(f"✅ AI module v{__version__} loaded successfully - {len(__all__)} components ready")


                
try:
    _validate_imports()
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"AI module validation failed: {e}")

__version__ = '2.1.0'

from .name_detector import detect_name, NameDetector
from .intent_classifier import classify_intent, Intent, IntentClassifier
from .context_manager import ContextManager
from .response_personalizer import ResponsePersonalizer

__all__ = [
    'detect_name',
    'NameDetector',
    'classify_intent',
    'Intent',
    'IntentClassifier',
    'ContextManager',
    'ResponsePersonalizer',
]


def get_module_info() -> dict:
    """Get module information and statistics."""
    return {
        'version': __version__,
        'components': len(__all__),
        'component_list': __all__,
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
        logger.info(f"AI module v{__version__} loaded successfully - {len(__all__)} components ready")


try:
    _validate_imports()
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"AI module validation failed: {e}")

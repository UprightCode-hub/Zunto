#server/assistant/apps.py
"""
Assistant App Configuration

Preloads RAG retriever and rule engine on Django startup for faster response times.
"""
from django.apps import AppConfig
import sys


class AssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assistant'
    verbose_name = 'Marketplace Assistant'

    def ready(self):
        """Initialize processors on startup."""
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)

        management_command = sys.argv[1] if len(sys.argv) > 1 else ''
        skip_preload_commands = {
            'seed_db',
            'migrate',
            'makemigrations',
            'collectstatic',
            'shell',
        }
        if management_command in skip_preload_commands:
            import assistant.signals  # noqa: F401
            return
        
                                                       
        if getattr(settings, 'ASSISTANT_PRELOAD_DATA', True):
            try:
                from assistant.processors.rag_retriever import RAGRetriever
                from assistant.processors.rule_engine import RuleEngine
                from assistant.processors.local_model import LocalModelAdapter
                from assistant.ai.intent_classifier import IntentClassifier
                
                logger.info("Preloading assistant components...")
                
                                                 
                rule_engine = RuleEngine.get_instance()
                logger.info(f"✓ RuleEngine loaded: {rule_engine.get_rule_count()} rules")
                
                                                   
                rag = RAGRetriever.get_instance()
                if rag.is_ready():
                    stats = rag.get_stats()
                    logger.info(f"✓ RAGRetriever loaded: {stats['num_faqs']} FAQs indexed")
                else:
                    logger.warning("⚠ RAGRetriever: Index not found. Run 'python scripts/build_rag_index.py'")
                
                                                                                
                try:
                    llm = LocalModelAdapter.get_instance()
                    if llm.is_available():
                        info = llm.get_model_info()
                        logger.info(f"✓ LocalModelAdapter loaded: {info['model_type']}")
                    else:
                        logger.info("○ LocalModelAdapter: No LLM available (FAQ-only mode)")
                except Exception as e:
                    logger.info(f"○ LocalModelAdapter: {e} (FAQ-only mode)")

                try:
                    IntentClassifier.warm_up()
                    logger.info("✓ IntentClassifier warm-up attempted")
                except Exception as e:
                    logger.info(f"○ IntentClassifier warm-up skipped: {e}")
                
                logger.info("✅ Assistant components preloaded successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to preload assistant components: {e}")
                logger.error("The assistant may not function properly. Check configuration.")

        import assistant.signals  # noqa: F401

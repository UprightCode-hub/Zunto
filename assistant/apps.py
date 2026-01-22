"""
Assistant App Configuration

Preloads RAG retriever and rule engine on Django startup for faster response times.
"""
from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assistant'
    verbose_name = 'Marketplace Assistant'

    def ready(self):
        """Initialize processors on startup."""
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Pre-load components for faster response times
        if getattr(settings, 'ASSISTANT_PRELOAD_DATA', True):
            try:
                from assistant.processors.rag_retriever import RAGRetriever
                from assistant.processors.rule_engine import RuleEngine
                from assistant.processors.local_model import LocalModelAdapter
                
                logger.info("Preloading assistant components...")
                
                # Initialize RuleEngine singleton
                rule_engine = RuleEngine.get_instance()
                logger.info(f"✓ RuleEngine loaded: {rule_engine.get_rule_count()} rules")
                
                # Initialize RAGRetriever singleton
                rag = RAGRetriever.get_instance()
                if rag.is_ready():
                    stats = rag.get_stats()
                    logger.info(f"✓ RAGRetriever loaded: {stats['num_faqs']} FAQs indexed")
                else:
                    logger.warning("⚠ RAGRetriever: Index not found. Run 'python scripts/build_rag_index.py'")
                
                # Initialize LocalModelAdapter (optional - graceful degradation)
                try:
                    llm = LocalModelAdapter.get_instance()
                    if llm.is_available():
                        info = llm.get_model_info()
                        logger.info(f"✓ LocalModelAdapter loaded: {info['model_type']}")
                    else:
                        logger.info("○ LocalModelAdapter: No LLM available (FAQ-only mode)")
                except Exception as e:
                    logger.info(f"○ LocalModelAdapter: {e} (FAQ-only mode)")
                
                logger.info("✅ Assistant components preloaded successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to preload assistant components: {e}")
                logger.error("The assistant may not function properly. Check configuration.")
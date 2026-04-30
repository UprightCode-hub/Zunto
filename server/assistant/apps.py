"""
Assistant App Configuration

Preloads RAG retriever and rule engine on Django startup for faster response times.
"""
import logging
import sys

from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assistant'
    verbose_name = 'Marketplace Assistant'

    def ready(self):
        """Initialize processors on startup."""
        from django.conf import settings

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
                from assistant.ai.intent_classifier import IntentClassifier
                from assistant.processors.local_model import LocalModelAdapter
                from assistant.processors.rag_retriever import RAGRetriever
                from assistant.processors.rule_engine import RuleEngine

                logger.info("Preloading assistant components...")

                rule_engine = RuleEngine.get_instance()
                logger.info("RuleEngine loaded: %s rules", rule_engine.get_rule_count())

                rag = RAGRetriever.get_instance()
                if rag.is_ready():
                    stats = rag.get_stats()
                    logger.info("RAGRetriever loaded: %s FAQs indexed", stats['num_faqs'])
                else:
                    logger.warning("RAGRetriever: Index not found. Run 'python scripts/build_rag_index.py'")

                try:
                    llm = LocalModelAdapter.get_instance()
                    if llm.is_available():
                        info = llm.get_model_info()
                        logger.info("LocalModelAdapter loaded: %s", info['model_type'])
                    else:
                        logger.info("LocalModelAdapter: No LLM available (FAQ-only mode)")
                except Exception as exc:
                    logger.info("LocalModelAdapter: %s (FAQ-only mode)", exc)

                try:
                    IntentClassifier.warm_up()
                    logger.info("IntentClassifier warm-up attempted")
                except Exception as exc:
                    logger.info("IntentClassifier warm-up skipped: %s", exc)

                logger.info("Assistant components preloaded successfully")

            except Exception as exc:
                logger.error("Failed to preload assistant components: %s", exc)
                logger.error("The assistant may not function properly. Check configuration.")

        import assistant.signals  # noqa: F401

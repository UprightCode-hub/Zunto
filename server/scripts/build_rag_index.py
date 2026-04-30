#server/scripts/build_rag_index.py
"""
Build RAG Index Script

Generates lane-separated vector indexes and embeddings from updated_faq.json.
Run this once before starting the server, or whenever FAQs are updated.

Usage:
    python scripts/build_rag_index.py
"""
import os
import sys
import logging
from pathlib import Path

                                                 
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

                                                                 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Django setup failed: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print("\nChecking for common Django settings locations:")
    
                             
    possible_settings = [
        'ZuntoProject/settings.py',
        'config/settings.py',
        'settings.py'
    ]
    
    for settings_path in possible_settings:
        full_path = project_root / settings_path
        if full_path.exists():
            print(f"   Found: {settings_path}")
            module_name = settings_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            print(f"   Try changing line 20 to: 'DJANGO_SETTINGS_MODULE', '{module_name}'")
    
    sys.exit(1)


from assistant.processors.rag_retriever import RAGRetriever, RAG_LANES

                   
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build RAG index from FAQ JSON."""
    
           
    base_dir = project_root / 'assistant'
    default_faq_path = base_dir / 'data' / 'updated_faq.json'
    faq_json_path = default_faq_path
    index_dir = base_dir / 'data' / 'rag_index'
    
                              
    if not faq_json_path.exists():
        logger.error(f"FAQ file not found: {faq_json_path}")
        logger.error("Please ensure updated_faq.json exists in assistant/data/")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("BUILDING RAG INDEX FOR ZUNTO ASSISTANT")
    logger.info("=" * 60)
    logger.info(f"FAQ Source: {faq_json_path}")
    logger.info(f"Index Output: {index_dir}")
    logger.info("")
    
    try:
                              
        logger.info("Initializing RAG retriever...")
        built_stats = []
        for lane in sorted(RAG_LANES):
            logger.info("Building index for lane=%s", lane)
            lane_index_dir = index_dir / lane
            retriever = RAGRetriever(index_dir=str(lane_index_dir), lane=lane)
            retriever.build_index(str(faq_json_path))
            built_stats.append(retriever.get_stats())

        total_faqs = sum(stats['num_faqs'] for stats in built_stats)
        logger.info("")
        logger.info("=" * 60)
        logger.info("INDEX BUILT SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"FAQs Indexed: {total_faqs}")
        for stats in built_stats:
            logger.info(
                "Lane=%s FAQs=%s Ready=%s Backend=%s",
                stats['lane'],
                stats['num_faqs'],
                stats['ready'],
                stats['vector_backend'],
            )
        logger.info(f"Embedding Model: {built_stats[0]['model'] if built_stats else 'unknown'}")
        logger.info(f"Vector Dimension: {built_stats[0]['dimension'] if built_stats else 'unknown'}")
        logger.info("")
        logger.info("You can now start the Django server!")
        logger.info("Run: python manage.py runserver")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid FAQ data: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

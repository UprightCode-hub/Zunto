"""
Build RAG Index Script

Generates FAISS index and embeddings from updated_faq.json.
Run this once before starting the server, or whenever FAQs are updated.

Usage:
    python scripts/build_rag_index.py
"""
import os
import sys
import logging
from pathlib import Path

# CRITICAL: Add project root to Python path FIRST
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Setup Django environment BEFORE any assistant imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    print(f"💡 Current working directory: {os.getcwd()}")
    print(f"💡 Project root: {project_root}")
    print(f"💡 Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print("\n🔍 Checking for common Django settings locations:")
    
    # Try to find settings.py
    possible_settings = [
        'ZuntoProject/settings.py',
        'config/settings.py',
        'settings.py'
    ]
    
    for settings_path in possible_settings:
        full_path = project_root / settings_path
        if full_path.exists():
            print(f"   ✓ Found: {settings_path}")
            module_name = settings_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            print(f"   💡 Try changing line 20 to: 'DJANGO_SETTINGS_MODULE', '{module_name}'")
    
    sys.exit(1)


from assistant.processors.rag_retriever import RAGRetriever

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build RAG index from FAQ JSON."""
    
    # Paths
    base_dir = project_root / 'assistant'
    faq_json_path = base_dir / 'data' / 'updated_faq.json'
    index_dir = base_dir / 'data' / 'rag_index'
    
    # Validate FAQ file exists
    if not faq_json_path.exists():
        logger.error(f"❌ FAQ file not found: {faq_json_path}")
        logger.error("Please ensure updated_faq.json exists in assistant/data/")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🚀 BUILDING RAG INDEX FOR ZUNTO ASSISTANT")
    logger.info("=" * 60)
    logger.info(f"FAQ Source: {faq_json_path}")
    logger.info(f"Index Output: {index_dir}")
    logger.info("")
    
    try:
        # Initialize retriever
        logger.info("Initializing RAG retriever...")
        retriever = RAGRetriever(index_dir=str(index_dir))
        
        # Build index
        logger.info("Building index (this may take a few minutes)...")
        retriever.build_index(str(faq_json_path))
        
        # Verify
        stats = retriever.get_stats()
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ INDEX BUILT SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"FAQs Indexed: {stats['num_faqs']}")
        logger.info(f"Embedding Model: {stats['model']}")
        logger.info(f"Vector Dimension: {stats['dimension']}")
        logger.info(f"Index Ready: {stats['ready']}")
        logger.info("")
        logger.info("You can now start the Django server!")
        logger.info("Run: python manage.py runserver")
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"❌ Invalid FAQ data: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
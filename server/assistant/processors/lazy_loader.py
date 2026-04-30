"""Lazy loading for models."""
import gc
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class LazyLoader:
    """Loads models only when first used."""

    def __init__(self):
        self._sentence_model = None
        self._faiss_module = None

    @property
    def sentence_model(self):
        """Load sentence transformer only when first accessed.

        Reads settings.EMBEDDING_MODEL — the single model setting shared across
        the entire system (product search + FAQ/RAG lanes).  Changing the env
        var EMBEDDING_MODEL takes effect on next process start with no code deploy.
        """
        if self._sentence_model is None:
            logger.info("Loading sentence transformer model...")
            try:
                from sentence_transformers import SentenceTransformer

                model_name = getattr(
                    settings,
                    'EMBEDDING_MODEL',
                    'all-MiniLM-L12-v2',
                )
                self._sentence_model = SentenceTransformer(
                    model_name,
                    device='cpu',
                )
                logger.info(
                    "Sentence transformer loaded successfully (%s)", model_name
                )
            except ImportError:
                logger.warning("sentence_transformers not installed. RAG features will be disabled.")
                return None
            except Exception as exc:
                logger.error("Error loading sentence transformer model: %s", exc)
                return None
        return self._sentence_model

    @property
    def faiss(self):
        """Load index backend on first access."""
        if self._faiss_module is None:
            logger.info("Loading FAISS...")
            try:
                import faiss

                self._faiss_module = faiss
                logger.info("FAISS loaded successfully")
            except ImportError:
                logger.warning("faiss not installed. RAG features will be disabled.")
                return None
            except Exception as exc:
                logger.error("Error loading FAISS: %s", exc)
                return None
        return self._faiss_module

    def create_vector_index(self, embeddings):
        if self.faiss is None:
            logger.error("FAISS not available. Cannot create index.")
            return None

        logger.info("Creating lane vector index...")
        dimension = embeddings.shape[1]
        metric = getattr(self.faiss, 'METRIC_INNER_PRODUCT', 0)
        if hasattr(self.faiss, 'IndexHNSWFlat'):
            try:
                index = self.faiss.IndexHNSWFlat(dimension, 32, metric)
            except TypeError:
                index = self.faiss.IndexFlatIP(dimension)
                index.add(embeddings)
                logger.info("FAISS inner-product index created")
                return index
            index.hnsw.efConstruction = 80
            index.hnsw.efSearch = 64
            index.add(embeddings)
            logger.info("FAISS HNSW index created")
            return index

        index = self.faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        logger.info("FAISS inner-product index created")
        return index

    def create_faiss_index(self, embeddings):
        """Backward-compatible alias for the lane vector index builder."""
        return self.create_vector_index(embeddings)

    def clear_cache(self):
        """Clear loaded models to free memory."""
        logger.info("Clearing AI model cache...")
        self._sentence_model = None
        self._faiss_module = None
        gc.collect()
        logger.info("AI model cache cleared")


_ai_loader = LazyLoader()


def get_ai_loader():
    """Get the global loader instance."""
    return _ai_loader
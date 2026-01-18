"""
RAG Retriever - Memory-efficient semantic search using lazy loading.
"""
import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from django.conf import settings

from .lazy_loader import get_ai_loader

logger = logging.getLogger(__name__)

FAQ_MATCH_THRESHOLD = getattr(settings, 'FAQ_MATCH_THRESHOLD', 0.55)
TOP_K = 5


class RAGRetriever:
    """
    Retrieval-Augmented Generation retriever using FAISS for semantic search.
    Uses lazy loading for memory efficiency on free-tier hosting.
    """

    _instance = None

    def __init__(self, index_dir: Optional[str] = None):
        """
        Initialize RAG retriever.
        
        Args:
            index_dir: Directory containing FAISS index and metadata
        """
        if index_dir is None:
            base_dir = Path(__file__).parent.parent
            index_dir = base_dir / 'data' / 'rag_index'

        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.ai_loader = get_ai_loader()

        self.index = None
        self.faqs = []
        self.embeddings = None
        self.dimension = 768

        self._load_index()

    @classmethod
    def get_instance(cls, index_dir: Optional[str] = None):
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(index_dir)
        return cls._instance

    @property
    def encoder(self):
        """Lazy-load the sentence transformer encoder."""
        return self.ai_loader.sentence_model

    def _load_index(self):
        """Load FAISS index and metadata from disk."""
        index_file = self.index_dir / 'faqs.index'
        metadata_file = self.index_dir / 'metadata.pkl'
        embeddings_file = self.index_dir / 'embeddings.npy'

        if not metadata_file.exists():
            logger.warning("No pre-built index found. Please run build_rag_index.py first.")
            return

        try:
            with open(metadata_file, 'rb') as f:
                self.faqs = pickle.load(f)

            if embeddings_file.exists():
                self.embeddings = np.load(embeddings_file)
                logger.info(f"Loaded embeddings for {len(self.faqs)} FAQs")

            logger.info(f"Loaded metadata with {len(self.faqs)} FAQs")

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            self.faqs = []
            self.embeddings = None

    def _ensure_faiss_index(self):
        """Lazy-load FAISS index only when needed."""
        if self.index is not None:
            return self.index

        if self.embeddings is None:
            logger.warning("No embeddings available to create FAISS index")
            return None

        try:
            self.index = self.ai_loader.create_faiss_index(self.embeddings)
            logger.info("FAISS index created")
            return self.index
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            return None

    def build_index(self, faq_json_path: str):
        """
        Build FAISS index from FAQ JSON file.
        
        Args:
            faq_json_path: Path to updated_faq.json
        """
        logger.info(f"Building index from {faq_json_path}")

        with open(faq_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            faqs = data.get('faqs', [])

        if not faqs:
            raise ValueError("No FAQs found in JSON file")

        logger.info(f"Processing {len(faqs)} FAQs...")

        texts = []
        for faq in faqs:
            text = f"{faq['question']} {faq['answer']}"
            texts.append(text)

        logger.info("Generating embeddings...")
        encoder = self.encoder
        embeddings = encoder.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        self.embeddings = embeddings.astype('float32')
        self.faqs = faqs

        logger.info("Building FAISS index...")
        self.index = self.ai_loader.create_faiss_index(self.embeddings)

        self._save_index()

        logger.info(f"✅ Index built successfully: {len(faqs)} FAQs indexed")

    def _save_index(self):
        """Save index, embeddings, and metadata to disk."""
        try:
            embeddings_file = self.index_dir / 'embeddings.npy'
            np.save(embeddings_file, self.embeddings)
            logger.info(f"Embeddings saved to {embeddings_file}")

            metadata_file = self.index_dir / 'metadata.pkl'
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.faqs, f)
            logger.info(f"Metadata saved to {metadata_file}")

            if self.index is not None:
                import faiss
                index_file = self.index_dir / 'faqs.index'
                faiss.write_index(self.index, str(index_file))
                logger.info(f"FAISS index saved to {index_file}")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def load_faqs(self, faq_list):
        """
        Load FAQs and create embeddings (alternative to build_index).
        
        Args:
            faq_list: List of FAQ dicts with 'question' and 'answer' keys
        """
        if not faq_list:
            logger.warning("No FAQs provided")
            return

        self.faqs = faq_list

        texts = [f"{faq['question']} {faq['answer']}" for faq in faq_list]

        logger.info(f"Creating embeddings for {len(texts)} FAQs...")
        encoder = self.encoder
        self.embeddings = encoder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')

        self.index = self.ai_loader.create_faiss_index(self.embeddings)
        logger.info("✅ FAQs loaded and indexed")

    def search(self, query: str, k: int = TOP_K) -> List[Dict]:
        """
        Search for relevant FAQs using semantic similarity.
        
        Args:
            query: User's question
            k: Number of results to return
        
        Returns:
            List of dicts with 'id', 'question', 'answer', 'keywords', 'score'
        """
        if not query or not self.faqs:
            logger.warning("Cannot search: no FAQs loaded or query empty")
            return []

        try:
            index = self._ensure_faiss_index()
            if index is None:
                logger.error("FAISS index not available")
                return self._fallback_search(query, k)

            encoder = self.encoder
            query_embedding = encoder.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            ).astype('float32')

            scores, indices = index.search(query_embedding, k)

            if len(scores[0]) > 0:
                top_scores = scores[0][:min(3, len(scores[0]))]
                logger.info(f"Top {len(top_scores)} search scores: {[f'{s:.3f}' for s in top_scores]}")
                logger.info(f"Threshold: {FAQ_MATCH_THRESHOLD}")

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.faqs):
                    faq = self.faqs[idx]
                    result = {
                        'id': faq.get('id', idx),
                        'question': faq['question'],
                        'answer': faq['answer'],
                        'keywords': faq.get('keywords', []),
                        'score': float(score)
                    }
                    results.append(result)
                    logger.debug(f"  Match: {faq['question'][:60]}... (score: {score:.3f})")

            results_before_filter = len(results)
            results = [r for r in results if r['score'] >= FAQ_MATCH_THRESHOLD]

            if results:
                logger.info(f"Found {len(results)} relevant FAQs above threshold "
                          f"(top score: {results[0]['score']:.3f})")
            else:
                best_score = scores[0][0] if len(scores[0]) > 0 else None
                if best_score is not None:
                    logger.warning(f"No results above threshold {FAQ_MATCH_THRESHOLD}. "
                                 f"Best match: {best_score:.3f}")

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return self._fallback_search(query, k)

    def _fallback_search(self, query: str, k: int = TOP_K) -> List[Dict]:
        """
        Fallback to simple keyword matching if vector search fails.
        Uses lightweight TF-IDF instead of heavy models.
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            logger.info("Using fallback TF-IDF search")

            questions = [faq['question'] for faq in self.faqs]

            vectorizer = TfidfVectorizer()
            vectors = vectorizer.fit_transform(questions + [query])

            query_vector = vectors[-1]
            question_vectors = vectors[:-1]
            similarities = cosine_similarity(query_vector, question_vectors)[0]

            top_indices = np.argsort(similarities)[::-1][:k]

            results = []
            for idx in top_indices:
                similarity = similarities[idx]
                if similarity >= FAQ_MATCH_THRESHOLD:
                    faq = self.faqs[idx]
                    results.append({
                        'id': faq.get('id', idx),
                        'question': faq['question'],
                        'answer': faq['answer'],
                        'keywords': faq.get('keywords', []),
                        'score': float(similarity)
                    })

            logger.info(f"Fallback search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Alias for search() for backward compatibility.
        Returns results with 'similarity' key instead of 'score'.
        """
        results = self.search(query, k=top_k)
        for r in results:
            r['similarity'] = r.pop('score', 0.0)
        return results

    def is_ready(self) -> bool:
        """Check if index is loaded and ready."""
        return len(self.faqs) > 0

    def get_stats(self) -> Dict:
        """Get retriever statistics."""
        return {
            'ready': self.is_ready(),
            'num_faqs': len(self.faqs),
            'dimension': self.dimension,
            'embeddings_loaded': self.embeddings is not None,
            'faiss_index_loaded': self.index is not None,
            'model': 'sentence-transformers/all-mpnet-base-v2'
        }

    def clear_cache(self):
        """Clear loaded models to free memory."""
        logger.info("Clearing AI model cache")
        self.ai_loader.clear_cache()
        self.index = None
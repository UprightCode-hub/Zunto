"""Lane-separated RAG retriever for assistant support knowledge."""
import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from django.conf import settings

from .lazy_loader import get_ai_loader

logger = logging.getLogger(__name__)

FAQ_MATCH_THRESHOLD = getattr(settings, 'FAQ_MATCH_THRESHOLD', 0.5)
TOP_K = 5
DEFAULT_RAG_LANE = 'platform_help'
KNOWLEDGE_SOURCE_FILENAME = 'updated_faq.json'
RAG_LANES = frozenset({
    'homepage_reco_catalog',
    'buyer_support',
    'seller_support',
    'dispute_resolution',
    'platform_help',
    'trust_safety_account',
})


def normalize_lane(lane: Optional[str]) -> str:
    candidate = (lane or DEFAULT_RAG_LANE).strip().lower()
    if candidate not in RAG_LANES:
        logger.warning("Unknown RAG lane %r; using %s", lane, DEFAULT_RAG_LANE)
        return DEFAULT_RAG_LANE
    return candidate


class RAGRetriever:
    """
    Retrieval-Augmented Generation retriever scoped to one knowledge lane.

    Each lane owns its own metadata and vector index. This keeps customer
    service, buyer/seller support, platform help, trust/safety, and homepage
    catalog knowledge from competing in one mixed FAQ bucket.
    """

    _instances: Dict[str, 'RAGRetriever'] = {}

    def __init__(self, index_dir: Optional[str] = None, lane: Optional[str] = None):
        self.lane = normalize_lane(lane)

        if index_dir is None:
            base_dir = Path(__file__).parent.parent
            index_dir = base_dir / 'data' / 'rag_index' / self.lane

        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.ai_loader = get_ai_loader()
        self.index = None
        self.faqs: List[Dict] = []
        self.embeddings = None
        self.dimension = 384
        self.vector_backend = 'faiss_hnsw_ip'

        self._load_index()

    @classmethod
    def get_instance(cls, index_dir: Optional[str] = None, lane: Optional[str] = None):
        """Get or create a singleton retriever for one lane."""
        normalized_lane = normalize_lane(lane)
        if index_dir is None and normalized_lane in cls._instances:
            return cls._instances[normalized_lane]

        instance = cls(index_dir=index_dir, lane=normalized_lane)
        if index_dir is None:
            cls._instances[normalized_lane] = instance
        return instance

    @property
    def encoder(self):
        """Lazy-load the sentence transformer encoder."""
        return self.ai_loader.sentence_model

    @staticmethod
    def knowledge_source_path() -> Path:
        return Path(__file__).parent.parent / 'data' / KNOWLEDGE_SOURCE_FILENAME

    def _lane_filter(self, faqs: List[Dict]) -> List[Dict]:
        return [
            faq for faq in faqs
            if normalize_lane(faq.get('primary_lane')) == self.lane
        ]

    @staticmethod
    def _document_text(faq: Dict) -> str:
        tags = ' '.join(faq.get('secondary_tags') or [])
        keywords = ' '.join(faq.get('keywords') or [])
        return ' '.join(
            str(part).strip()
            for part in [
                faq.get('question', ''),
                faq.get('answer', ''),
                keywords,
                tags,
                faq.get('priority', ''),
            ]
            if part
        )

    def _load_index(self):
        """Load lane metadata and embeddings from disk, or fallback to JSON."""
        metadata_file = self.index_dir / 'metadata.pkl'
        embeddings_file = self.index_dir / 'embeddings.npy'

        if not metadata_file.exists():
            logger.warning(
                "No pre-built RAG index for lane %s. Falling back to canonical JSON.",
                self.lane,
            )
            fallback_json = self.knowledge_source_path()
            if fallback_json.exists():
                try:
                    with open(fallback_json, 'r', encoding='utf-8') as f:
                        payload = json.load(f)
                    self.faqs = self._lane_filter(payload.get('faqs', []))
                    logger.info("Loaded %s %s FAQs from JSON fallback", len(self.faqs), self.lane)
                except Exception as exc:
                    logger.error("Failed loading canonical FAQ JSON fallback: %s", exc)
            return

        try:
            with open(metadata_file, 'rb') as f:
                self.faqs = self._lane_filter(pickle.load(f))

            if embeddings_file.exists():
                self.embeddings = np.load(embeddings_file)
                if len(self.embeddings.shape) == 2:
                    self.dimension = int(self.embeddings.shape[1])
                logger.info("Loaded %s embeddings for lane %s", len(self.faqs), self.lane)

            logger.info("Loaded %s metadata records for lane %s", len(self.faqs), self.lane)

        except Exception as exc:
            logger.error("Failed to load RAG index for lane %s: %s", self.lane, exc)
            self.faqs = []
            self.embeddings = None

    def _ensure_vector_index(self):
        """Lazy-load the vector index only when needed."""
        if self.index is not None:
            return self.index

        if self.embeddings is None:
            logger.warning("No embeddings available for RAG lane %s", self.lane)
            return None

        try:
            self.index = self.ai_loader.create_vector_index(self.embeddings)
            logger.info("Vector index created for RAG lane %s", self.lane)
            return self.index
        except Exception as exc:
            logger.error("Failed to create vector index for lane %s: %s", self.lane, exc)
            return None

    def build_index(self, faq_json_path: str, lane: Optional[str] = None):
        """Build this lane's vector index from the canonical FAQ JSON file."""
        if lane is not None and normalize_lane(lane) != self.lane:
            return self.get_instance(lane=lane).build_index(faq_json_path)

        logger.info("Building RAG index for lane %s from %s", self.lane, faq_json_path)

        with open(faq_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            faqs = self._lane_filter(data.get('faqs', []))

        if not faqs:
            raise ValueError(f"No FAQs found for RAG lane {self.lane}")

        texts = [self._document_text(faq) for faq in faqs]

        encoder = self.encoder
        if encoder is None:
            raise RuntimeError("Sentence transformer unavailable; cannot build RAG index")

        embeddings = encoder.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        self.embeddings = embeddings.astype('float32')
        self.faqs = faqs
        self.dimension = int(self.embeddings.shape[1])
        self.index = self.ai_loader.create_vector_index(self.embeddings)

        self._save_index()
        logger.info("Index built successfully for lane %s: %s FAQs", self.lane, len(faqs))

    def _save_index(self):
        """Save lane embeddings, metadata, and optional FAISS index."""
        try:
            embeddings_file = self.index_dir / 'embeddings.npy'
            np.save(embeddings_file, self.embeddings)

            metadata_file = self.index_dir / 'metadata.pkl'
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.faqs, f)

            if self.index is not None:
                import faiss

                index_file = self.index_dir / 'faqs.index'
                faiss.write_index(self.index, str(index_file))

            manifest_file = self.index_dir / 'manifest.json'
            manifest_file.write_text(
                json.dumps(
                    {
                        'lane': self.lane,
                        'num_faqs': len(self.faqs),
                        'dimension': self.dimension,
                        'vector_backend': self.vector_backend,
                        'source': KNOWLEDGE_SOURCE_FILENAME,
                    },
                    indent=2,
                ),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.error("Failed to save RAG index for lane %s: %s", self.lane, exc)

    def load_faqs(self, faq_list):
        """Load lane FAQs and create embeddings without writing to disk."""
        lane_faqs = self._lane_filter(faq_list)
        if not lane_faqs:
            logger.warning("No FAQs provided for RAG lane %s", self.lane)
            return

        self.faqs = lane_faqs
        texts = [self._document_text(faq) for faq in lane_faqs]

        encoder = self.encoder
        if encoder is None:
            logger.warning("Sentence transformer unavailable for RAG lane %s", self.lane)
            return

        self.embeddings = encoder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype('float32')
        self.dimension = int(self.embeddings.shape[1])
        self.index = self.ai_loader.create_vector_index(self.embeddings)
        logger.info("FAQs loaded and indexed for RAG lane %s", self.lane)

    def search(self, query: str, k: int = TOP_K, lane: Optional[str] = None) -> List[Dict]:
        """Search this lane for relevant FAQs using semantic similarity."""
        if lane is not None and normalize_lane(lane) != self.lane:
            return self.get_instance(lane=lane).search(query, k=k)

        if not query or not self.faqs:
            logger.warning("Cannot search RAG lane %s: no FAQs loaded or query empty", self.lane)
            return []

        try:
            index = self._ensure_vector_index()
            if index is None:
                return self._fallback_search(query, k)

            encoder = self.encoder
            if encoder is None:
                return self._fallback_search(query, k)

            query_embedding = encoder.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).astype('float32')

            raw_scores, indices = index.search(query_embedding, k)
            unfiltered_results = []
            for raw_score, idx in zip(raw_scores[0], indices[0]):
                if idx < 0 or idx >= len(self.faqs):
                    continue
                faq = self.faqs[idx]
                confidence = self._score_to_confidence(float(raw_score))
                unfiltered_results.append(self._result_from_faq(faq, idx, confidence, float(raw_score)))

            unfiltered_results.sort(key=lambda item: item['score'], reverse=True)
            results = [r for r in unfiltered_results if r['score'] >= FAQ_MATCH_THRESHOLD]
            if not results and unfiltered_results:
                results = [unfiltered_results[0]]

            logger.info(
                "RAG lane %s returned %s results for query %r",
                self.lane,
                len(results),
                query[:80],
            )
            return results

        except Exception as exc:
            logger.error("Search failed for RAG lane %s: %s", self.lane, exc, exc_info=True)
            return self._fallback_search(query, k)

    @staticmethod
    def _score_to_confidence(raw_score: float) -> float:
        """Convert normalized inner product to a confidence-like 0..1 score."""
        return max(0.0, min(1.0, raw_score))

    def _result_from_faq(self, faq: Dict, idx: int, score: float, raw_score: float) -> Dict:
        return {
            'id': faq.get('id', idx),
            'question': faq.get('question', ''),
            'answer': faq.get('answer', ''),
            'keywords': faq.get('keywords', []),
            'primary_lane': faq.get('primary_lane', self.lane),
            'secondary_tags': faq.get('secondary_tags', []),
            'priority': faq.get('priority', 'useful'),
            'status': faq.get('status', 'active'),
            'score': score,
            'raw_score': raw_score,
            'lane': self.lane,
            'vector_backend': self.vector_backend,
        }

    def _fallback_search(self, query: str, k: int = TOP_K) -> List[Dict]:
        """Fallback to lane-local TF-IDF if vector search is unavailable."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            texts = [self._document_text(faq) for faq in self.faqs]
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
            vectors = vectorizer.fit_transform(texts + [query])

            similarities = cosine_similarity(vectors[-1], vectors[:-1])[0]
            top_indices = np.argsort(similarities)[::-1][:k]

            results = [
                self._result_from_faq(self.faqs[idx], idx, float(similarities[idx]), float(similarities[idx]))
                for idx in top_indices
            ]
            return [r for r in results if r['score'] >= FAQ_MATCH_THRESHOLD] or results[:1]

        except Exception as exc:
            logger.error("Fallback search failed for RAG lane %s: %s", self.lane, exc)
            query_terms = [term for term in (query or '').lower().split() if term]
            scored = []
            for idx, faq in enumerate(self.faqs):
                text = self._document_text(faq).lower()
                score = sum(1 for term in query_terms if term in text)
                if score > 0:
                    scored.append((score, idx, faq))
            scored.sort(reverse=True)
            return [
                self._result_from_faq(faq, idx, 0.7, float(score))
                for score, idx, faq in scored[:k]
            ]

    def retrieve(self, query: str, top_k: int = 3, lane: Optional[str] = None) -> List[Dict]:
        """Backward-compatible alias for search()."""
        results = self.search(query, k=top_k, lane=lane)
        for result in results:
            result['similarity'] = result.pop('score', 0.0)
        return results

    def is_ready(self) -> bool:
        """Check if this lane has loaded knowledge."""
        return len(self.faqs) > 0

    def get_stats(self) -> Dict:
        """Get retriever statistics."""
        return {
            'ready': self.is_ready(),
            'lane': self.lane,
            'num_faqs': len(self.faqs),
            'dimension': self.dimension,
            'embeddings_loaded': self.embeddings is not None,
            'faiss_index_loaded': self.index is not None,
            'vector_backend': self.vector_backend,
            'model': 'sentence-transformers/paraphrase-MiniLM-L3-v2',
        }

    def clear_cache(self):
        """Clear loaded models to free memory."""
        logger.info("Clearing AI model cache")
        self.ai_loader.clear_cache()
        self.index = None

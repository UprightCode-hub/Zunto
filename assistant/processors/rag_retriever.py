"""
RAG Retriever - Semantic search over FAQs using sentence-transformers + FAISS.
"""
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Configuration
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
FAQ_MATCH_THRESHOLD = 0.55  
TOP_K = 5


class RAGRetriever:
    """
    Retrieval-Augmented Generation retriever using FAISS for semantic search.
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
        
        self.encoder = None
        self.index = None
        self.faqs = []
        self.dimension = 768  # all-mpnet-base-v2 dimension
        
        # Load encoder
        self._load_encoder()
        
        # Try to load existing index
        self._load_index()
    
    @classmethod
    def get_instance(cls, index_dir: Optional[str] = None):
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(index_dir)
        return cls._instance
    
    def _load_encoder(self):
        """Load sentence transformer encoder."""
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self.encoder = SentenceTransformer(EMBEDDING_MODEL)
            self.dimension = self.encoder.get_sentence_embedding_dimension()
            logger.info(f"Encoder loaded (dimension: {self.dimension})")
        except Exception as e:
            logger.error(f"Failed to load encoder: {e}")
            raise RuntimeError(f"Cannot initialize RAG without encoder: {e}")
    
    def _load_index(self):
        """Load FAISS index and metadata from disk."""
        index_file = self.index_dir / 'faqs.index'
        metadata_file = self.index_dir / 'metadata.pkl'
        
        if not index_file.exists() or not metadata_file.exists():
            logger.warning("No pre-built index found. Please run build_rag_index.py first.")
            return
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            
            # Load metadata
            with open(metadata_file, 'rb') as f:
                self.faqs = pickle.load(f)
            
            logger.info(f"Loaded index with {len(self.faqs)} FAQs")
        
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            self.index = None
            self.faqs = []
    
    def build_index(self, faq_json_path: str):
        """
        Build FAISS index from FAQ JSON file.
        
        Args:
            faq_json_path: Path to updated_faq.json
        """
        logger.info(f"Building index from {faq_json_path}")
        
        # Load FAQ JSON
        with open(faq_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            faqs = data.get('faqs', [])
        
        if not faqs:
            raise ValueError("No FAQs found in JSON file")
        
        logger.info(f"Processing {len(faqs)} FAQs...")
        
        # Prepare texts for embedding (question + answer for richer context)
        texts = []
        for faq in faqs:
            text = f"{faq['question']} {faq['answer']}"
            texts.append(text)
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        # Create FAISS index
        logger.info("Building FAISS index...")
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine sim with normalized vectors)
        self.index.add(embeddings.astype('float32'))
        
        # Save index
        index_file = self.index_dir / 'faqs.index'
        faiss.write_index(self.index, str(index_file))
        logger.info(f"Index saved to {index_file}")
        
        # Save metadata
        self.faqs = faqs
        metadata_file = self.index_dir / 'metadata.pkl'
        with open(metadata_file, 'wb') as f:
            pickle.dump(faqs, f)
        logger.info(f"Metadata saved to {metadata_file}")
        
        logger.info(f"✅ Index built successfully: {len(faqs)} FAQs indexed")
    
    def search(self, query: str, k: int = TOP_K) -> List[Dict]:
        """
        Search for relevant FAQs using semantic similarity.
        
        Args:
            query: User's question
            k: Number of results to return
        
        Returns:
            List of dicts:
            [
                {
                    'id': int,
                    'question': str,
                    'answer': str,
                    'keywords': List[str],
                    'score': float  # Cosine similarity (0-1)
                },
                ...
            ]
        """
        if not query or not self.index or not self.faqs:
            logger.warning("Cannot search: index not loaded or query empty")
            return []
        
        try:
            # Encode query
            query_embedding = self.encoder.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            ).astype('float32')
            
            # Search FAISS index
            scores, indices = self.index.search(query_embedding, k)
            
            # Debug logging - show what scores we're getting
            if len(scores[0]) > 0:
                top_scores = scores[0][:min(3, len(scores[0]))]
                logger.info(f"Top {len(top_scores)} search scores: {[f'{s:.3f}' for s in top_scores]}")
                logger.info(f"Threshold: {FAQ_MATCH_THRESHOLD}")
            
            # Format results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.faqs):  # Valid index
                    faq = self.faqs[idx]
                    result = {
                        'id': faq.get('id', idx),
                        'question': faq['question'],
                        'answer': faq['answer'],
                        'keywords': faq.get('keywords', []),
                        'score': float(score)
                    }
                    results.append(result)
                    
                    # Log each result for debugging
                    logger.debug(f"  Match: {faq['question'][:60]}... (score: {score:.3f})")
            
            # Filter by threshold
            results_before_filter = len(results)
            results = [r for r in results if r['score'] >= FAQ_MATCH_THRESHOLD]
            
            if results:
                logger.info(f"Found {len(results)} relevant FAQs above threshold (top score: {results[0]['score']:.3f})")
            else:
                best_score = scores[0][0] if len(scores[0]) > 0 else None
                if best_score is not None:
                    logger.warning(f"No results above threshold {FAQ_MATCH_THRESHOLD}. "
                                 f"Best match was {results_before_filter} result(s) with top score {best_score:.3f}")
                else:
                    logger.warning(f"No results above threshold {FAQ_MATCH_THRESHOLD}.")
            
            return results
        
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []
    
    def is_ready(self) -> bool:
        """Check if index is loaded and ready."""
        return self.index is not None and len(self.faqs) > 0
    
    def get_stats(self) -> Dict:
        """Get retriever statistics."""
        return {
            'ready': self.is_ready(),
            'num_faqs': len(self.faqs),
            'dimension': self.dimension,
            'model': EMBEDDING_MODEL
        }
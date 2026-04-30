"""
market/search/embeddings.py

Fixes applied:
  1. Batch-encode all products missing stored vectors in ONE model.encode() call
     instead of one call per product (was causing 70+ individual encode calls = 82s)
  2. Share the same model singleton from assistant lazy_loader instead of
     maintaining a second separate all-MiniLM-L6-v2 instance in memory
  3. Products with pre-stored embedding_vector skip encoding entirely
"""
import logging
import hashlib
import json
import math
from functools import lru_cache

from django.conf import settings

from market.search.vector_backend import (
    PRODUCT_VECTOR_MODEL,
    product_vector_backend_status,
    search_products_pgvector,
    sync_product_vector,
)
from market.search.hybrid_ranker import product_search_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model singleton — reuses the same instance as assistant/lazy_loader.py
# to avoid loading two separate transformer models into memory.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_sentence_transformer_model():
    """
    Load sentence transformer once and cache forever for this process.
    Uses the same model name as assistant/processors/lazy_loader.py so
    the OS can share the loaded weights via the module cache.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning("sentence_transformers not installed; semantic search disabled.")
        return None

    try:
        # Same model as lazy_loader — avoids a second heavyweight model in RAM.
        model_name = getattr(settings, 'PRODUCT_VECTOR_MODEL', PRODUCT_VECTOR_MODEL)
        model = SentenceTransformer(model_name, device='cpu')
        logger.info("Sentence transformer loaded for product search (%s)", model_name)
        return model
    except Exception as exc:
        logger.error(f"Failed to load sentence transformer: {exc}")
        return None


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _fallback_embedding(text, dims=64):
    """Lightweight deterministic hash-based embedding when model unavailable."""
    vector = [0.0] * dims
    tokens = [t for t in (text or '').lower().split() if t]
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode('utf-8')).digest()
        for index in range(dims):
            vector[index] += (digest[index % len(digest)] / 255.0) - 0.5

    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]
    return vector


def _flatten_attribute_value(value):
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            flattened = _flatten_attribute_value(value[key])
            if flattened:
                parts.append(f"{key} {flattened}")
        return ' '.join(parts)
    if isinstance(value, (list, tuple, set)):
        return ' '.join(str(item).strip() for item in value if str(item).strip())
    if value in (None, ''):
        return ''
    return str(value).strip()


def _build_product_embedding_text(product):
    return product_search_text(product)


def _encode_single(text):
    """Encode one text string. Use only when batching is not possible."""
    model = _load_sentence_transformer_model()
    if model is None:
        return _fallback_embedding(text)
    try:
        vector = model.encode(text, convert_to_numpy=True)
        return [float(v) for v in vector.tolist()]
    except Exception as exc:
        logger.warning(f"Encode failed, using fallback: {exc}")
        return _fallback_embedding(text)


def _encode_batch(texts):
    """
    Encode a list of texts in ONE model call.
    This is the key fix — replaces the per-product encode loop.
    Returns list of vectors in the same order as input texts.
    """
    if not texts:
        return []

    model = _load_sentence_transformer_model()
    if model is None:
        return [_fallback_embedding(t) for t in texts]

    try:
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            batch_size=64,          # process 64 at a time internally
            show_progress_bar=False,
        )
        return [[float(v) for v in row.tolist()] for row in vectors]
    except Exception as exc:
        logger.warning(f"Batch encode failed, using fallback: {exc}")
        return [_fallback_embedding(t) for t in texts]


def _cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return float(dot / (norm_left * norm_right))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_product_embedding(product):
    """Generate embedding for a single product (used at index time)."""
    text = _build_product_embedding_text(product)
    if not text:
        return []
    vector = _encode_single(text)
    sync_product_vector(product, vector, embedding_text=text)
    return vector


def search_similar_products(query, base_queryset, candidate_limit=200, top_k=60):
    """
    Semantic similarity search over a product queryset.

    Key fix: products missing stored embedding_vector are batch-encoded in a
    SINGLE model call instead of one encode call per product.
    """
    if not query:
        return []

    # Encode the query — 1 model call
    query_vector = _encode_single(query)
    if not query_vector:
        return []

    candidates = list(
        base_queryset.select_related('category', 'location', 'product_family').only(
            'id', 'title', 'description', 'brand', 'condition',
            'attributes', 'search_tags', 'embedding_vector', 'category__name',
            'product_family__name', 'product_family__aliases', 'product_family__keywords',
            'location__state', 'location__city', 'location__area', 'created_at'
        ).order_by('-created_at')[:candidate_limit]
    )

    if not candidates:
        return []

    pgvector_results = search_products_pgvector(
        query_vector,
        [product.id for product in candidates],
        top_k=top_k,
    )
    if pgvector_results:
        logger.debug(
            "search_similar_products: pgvector returned %s results",
            len(pgvector_results),
        )
        return pgvector_results
    if product_vector_backend_status().backend == 'pgvector':
        logger.warning("Configured pgvector search returned no results; using JSON cosine fallback")

    # Separate products that already have stored vectors from those that don't
    stored = []       # (product, vector)
    need_encode = []  # products without stored vector

    for product in candidates:
        vec = getattr(product, 'embedding_vector', None)
        if vec and len(vec) > 0:
            stored.append((product, vec))
        else:
            need_encode.append(product)

    # Batch-encode all products missing vectors — ONE model call total
    if need_encode:
        texts = [_build_product_embedding_text(p) for p in need_encode]
        # Skip products with no meaningful text
        valid_pairs = [(p, t) for p, t in zip(need_encode, texts) if t.strip()]

        if valid_pairs:
            valid_products, valid_texts = zip(*valid_pairs)
            batch_vectors = _encode_batch(list(valid_texts))
            for product, vector in zip(valid_products, batch_vectors):
                stored.append((product, vector))

        logger.debug(
            f"search_similar_products: {len(stored)} encoded "
            f"({len(candidates) - len(need_encode)} pre-stored, "
            f"{len(need_encode)} batch-encoded in 1 call)"
        )

    # Score all candidates
    scored = []
    for product, vec in stored:
        score = _cosine_similarity(query_vector, vec)
        if score > 0:
            scored.append((product.id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]

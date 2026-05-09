"""
market/search/embeddings.py

Unified embedding model: all-MiniLM-L12-v2 (384-dim).
Both the product-search lane (this file) and the FAQ/RAG lane (lazy_loader.py)
share a single model controlled by settings.EMBEDDING_MODEL.

Improvements:
  1. Batch-encode products missing stored vectors in ONE model.encode() call —
     eliminates per-product encode loops (was 70+ calls = ~82s).
  2. normalize_embeddings=True on all encode paths — unit-norm vectors make
     inner-product equivalent to cosine similarity for FAISS and pgvector.
  3. Products with pre-stored embedding_vector skip encoding entirely.
"""
import logging
import hashlib
import math
import re

from django.conf import settings
from django.db.models import Q

from market.search.vector_backend import (
    PRODUCT_VECTOR_MODEL,
    PRODUCT_VECTOR_DIMENSIONS,
    product_vector_backend_status,
    search_product_vectors,
    sync_product_vector,
)
from market.search.hybrid_ranker import product_search_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared model singleton — single instance for the whole process.
# Both this module and assistant/processors/lazy_loader.py resolve their model
# name from settings.EMBEDDING_MODEL, so only one model is ever loaded.
# ---------------------------------------------------------------------------

def _load_sentence_transformer_model():
    """
    Load the shared sentence transformer once per process and cache it.
    Reads settings.EMBEDDING_MODEL (env var: EMBEDDING_MODEL) so the model
    can be changed or rolled back without a code deploy.
    Falls back to the value resolved at vector_backend import time if the
    setting is absent (should not happen in a correctly configured env).
    """
    if getattr(settings, 'RENDER_FREE_TIER', False):
        logger.info("Sentence transformer loading skipped on Render free tier.")
        return None

    if getattr(settings, 'AI_COMPONENTS_DISABLED', False):
        logger.info("Sentence transformer loading skipped; AI components are disabled.")
        return None

    try:
        from assistant.processors.lazy_loader import get_ai_loader

        return get_ai_loader().sentence_model
    except Exception as exc:
        logger.error("Failed to load sentence transformer: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _fallback_embedding(text, dims=None):
    """Lightweight deterministic hash-based embedding when model unavailable."""
    dims = int(dims or PRODUCT_VECTOR_DIMENSIONS)
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
    """Encode one text string. Use only when batching is not possible.

    normalize_embeddings=True produces unit-norm vectors, so inner-product
    and cosine similarity are equivalent — required for FAISS IndexFlatIP
    and pgvector cosine distance to behave correctly.
    """
    if getattr(settings, 'RENDER_FREE_TIER', False):
        return None

    model = _load_sentence_transformer_model()
    if model is None:
        return _fallback_embedding(text)
    try:
        vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return [float(v) for v in vector.tolist()]
    except Exception as exc:
        logger.warning(f"Encode failed, using fallback: {exc}")
        return _fallback_embedding(text)


def _encode_batch(texts):
    """
    Encode a list of texts in ONE model call.
    Returns list of unit-normalized vectors in the same order as input texts.
    normalize_embeddings=True is required for inner-product search correctness.
    """
    if not texts:
        return []

    if getattr(settings, 'RENDER_FREE_TIER', False):
        return []

    model = _load_sentence_transformer_model()
    if model is None:
        return [_fallback_embedding(t) for t in texts]

    try:
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
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


def _search_products_orm_text(query, base_queryset, candidate_limit=200, top_k=60):
    """Lightweight text fallback for free-tier deployments."""
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", str(query or "").lower())
        if len(token) > 2
    ][:8]
    if not tokens:
        return []

    text_query = Q()
    for token in tokens:
        text_query |= (
            Q(title__icontains=token)
            | Q(description__icontains=token)
            | Q(brand__icontains=token)
            | Q(condition__icontains=token)
            | Q(category__name__icontains=token)
            | Q(product_family__name__icontains=token)
        )

    candidates = list(
        base_queryset.select_related('category', 'location', 'product_family')
        .filter(text_query)
        .distinct()
        .order_by('-is_verified_product', '-views_count', '-favorites_count', '-created_at')[:candidate_limit]
    )
    if not candidates:
        return []

    scored = []
    token_count = max(1, len(tokens))
    for product in candidates:
        text = product_search_text(product).lower()
        score = sum(1 for token in tokens if token in text) / token_count
        if score > 0:
            scored.append((product.id, float(score)))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_product_embedding(product):
    """Generate embedding for a single product (used at index time)."""
    text = _build_product_embedding_text(product)
    if not text:
        return []
    vector = _encode_single(text)
    if vector is None:
        return []
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
    if getattr(settings, 'RENDER_FREE_TIER', False):
        return _search_products_orm_text(
            query,
            base_queryset,
            candidate_limit=candidate_limit,
            top_k=top_k,
        )

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

    vector_backend_results = search_product_vectors(
        query_vector,
        [product.id for product in candidates],
        top_k=top_k,
    )
    if vector_backend_results:
        logger.debug(
            "search_similar_products: vector backend returned %s results",
            len(vector_backend_results),
        )
        return vector_backend_results
    if product_vector_backend_status().backend == 'pgvector':
        logger.warning("Configured vector backend returned no results; using JSON cosine fallback")

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

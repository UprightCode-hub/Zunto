"""
market/search/embeddings.py

Unified embedding model: all-MiniLM-L12-v2 (384-dim).
Both the product-search lane (this file) and the FAQ/RAG lane (lazy_loader.py)
share a single model controlled by settings.EMBEDDING_MODEL.

Key behaviour:
  - Model loads LAZILY on first use, never at startup.
  - pgvector is always tried first when a query vector is available.
  - Falls back to ORM keyword search only when encoding genuinely fails.
  - RENDER_FREE_TIER no longer bypasses pgvector — vectors are in the DB,
    so we use them as long as the model can encode the query.
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
# Model loader — always lazy, never at import/startup time
# ---------------------------------------------------------------------------

def _load_sentence_transformer_model():
    """
    Load the shared sentence transformer once per process and cache it.
    Never called at startup — only when a search or embed is requested.
    """
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
    """
    Encode one text string using the sentence transformer.
    Returns None if the model cannot be loaded — callers should fall back
    to keyword search in that case.
    """
    if not text or not text.strip():
        return None

    model = _load_sentence_transformer_model()
    if model is None:
        return None

    try:
        vector = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [float(v) for v in vector.tolist()]
    except Exception as exc:
        logger.warning("Encode failed: %s", exc)
        return None


def _encode_batch(texts):
    """
    Encode a list of texts in one model call.
    Returns list of unit-normalised vectors, or empty list on failure.
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
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [[float(v) for v in row.tolist()] for row in vectors]
    except Exception as exc:
        logger.warning("Batch encode failed, using fallback: %s", exc)
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
    """Keyword fallback — used when the sentence transformer is unavailable."""
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
        .order_by('-is_verified_product', '-views_count', '-favorites_count', '-created_at')
        [:candidate_limit]
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
    """Generate and store embedding for a single product."""
    text = _build_product_embedding_text(product)
    if not text:
        return []
    vector = _encode_single(text)
    if not vector:
        return []
    sync_product_vector(product, vector, embedding_text=text)
    return vector


def search_similar_products(query, base_queryset, candidate_limit=200, top_k=60):
    """
    Semantic similarity search over a product queryset.

    Strategy (in order):
      1. Encode the query with the sentence transformer.
      2. If encoding succeeds, search pgvector — fast, semantically aware.
      3. If pgvector returns results, return them directly.
      4. If encoding fails (model not loaded / OOM) fall back to keyword search.

    This means pgvector is used whenever the model is available, regardless
    of RENDER_FREE_TIER — the vectors are already in the DB, so we use them.
    """
    if not query:
        return []

    # Step 1: try to encode the query
    query_vector = _encode_single(query)

    # Step 2: if encoding failed, go straight to keyword search
    if not query_vector:
        logger.debug("search_similar_products: no query vector, using ORM text fallback")
        return _search_products_orm_text(
            query, base_queryset,
            candidate_limit=candidate_limit,
            top_k=top_k,
        )

    # Step 3: fetch candidates
    candidates = list(
        base_queryset.select_related('category', 'location', 'product_family').only(
            'id', 'title', 'description', 'brand', 'condition',
            'attributes', 'search_tags', 'embedding_vector',
            'category__name', 'product_family__name',
            'product_family__aliases', 'product_family__keywords',
            'location__state', 'location__city', 'location__area',
            'created_at',
        ).order_by('-created_at')[:candidate_limit]
    )

    if not candidates:
        return []

    # Step 4: try pgvector first — vectors are already synced in the DB
    vector_backend_results = search_product_vectors(
        query_vector,
        [product.id for product in candidates],
        top_k=top_k,
    )
    if vector_backend_results:
        logger.debug(
            "search_similar_products: pgvector returned %s results",
            len(vector_backend_results),
        )
        return vector_backend_results

    if product_vector_backend_status().backend == 'pgvector':
        logger.warning("pgvector returned no results; falling back to JSON cosine")

    # Step 5: JSON cosine fallback using stored embedding_vector fields
    stored = []
    need_encode = []

    for product in candidates:
        vec = getattr(product, 'embedding_vector', None)
        if vec and len(vec) > 0:
            stored.append((product, vec))
        else:
            need_encode.append(product)

    if need_encode:
        texts = [_build_product_embedding_text(p) for p in need_encode]
        valid_pairs = [(p, t) for p, t in zip(need_encode, texts) if t.strip()]
        if valid_pairs:
            valid_products, valid_texts = zip(*valid_pairs)
            batch_vectors = _encode_batch(list(valid_texts))
            for product, vector in zip(valid_products, batch_vectors):
                stored.append((product, vector))

    scored = []
    for product, vec in stored:
        score = _cosine_similarity(query_vector, vec)
        if score > 0:
            scored.append((product.id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
import hashlib
import math
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_sentence_transformer_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception:
        return None


def _fallback_embedding(text, dims=64):
    vector = [0.0] * dims
    tokens = [token for token in (text or '').lower().split() if token]
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode('utf-8')).digest()
        for index in range(dims):
            vector[index] += (digest[index % len(digest)] / 255.0) - 0.5

    norm = math.sqrt(sum(value * value for value in vector))
    if norm > 0:
        vector = [value / norm for value in vector]
    return vector


def _build_product_embedding_text(product):
    category_name = ''
    category = getattr(product, 'category', None)
    if category is not None:
        category_name = getattr(category, 'name', '') or ''

    parts = [
        getattr(product, 'title', '') or '',
        getattr(product, 'description', '') or '',
        category_name,
    ]
    return ' '.join(part.strip() for part in parts if part and part.strip())


def _encode_text(text):
    model = _load_sentence_transformer_model()
    if model is None:
        return _fallback_embedding(text)

    try:
        vector = model.encode(text, convert_to_numpy=True)
        return [float(value) for value in vector.tolist()]
    except Exception:
        return _fallback_embedding(text)


def _cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return float(dot / (norm_left * norm_right))


def generate_product_embedding(product):
    text = _build_product_embedding_text(product)
    if not text:
        return []
    return _encode_text(text)


def search_similar_products(query, base_queryset, candidate_limit=200, top_k=60):
    query_vector = _encode_text(query or '')
    if not query_vector:
        return []

    candidates = list(
        base_queryset.select_related('category').only(
            'id', 'title', 'description', 'embedding_vector', 'category__name', 'created_at'
        ).order_by('-created_at')[:candidate_limit]
    )

    scored = []
    for product in candidates:
        product_vector = getattr(product, 'embedding_vector', None) or generate_product_embedding(product)
        if not product_vector:
            continue
        score = _cosine_similarity(query_vector, product_vector)
        if score > 0:
            scored.append((product.id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]

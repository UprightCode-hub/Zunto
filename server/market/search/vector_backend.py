"""Production vector backend helpers for marketplace product retrieval.

The homepage recommender owns product vectors. Support RAG lanes continue to
use their lane-scoped FAQ retriever and must not share this table.
"""
import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

PRODUCT_VECTOR_LANE = 'homepage_reco_catalog'
PRODUCT_VECTOR_DIMENSIONS = int(getattr(settings, 'PRODUCT_VECTOR_DIMENSIONS', 384))


def _default_table_for_dimensions(dimensions: int) -> str:
    return 'market_product_vector' if int(dimensions) == 384 else f'market_product_vector_{int(dimensions)}'


PRODUCT_VECTOR_TABLE = (
    str(getattr(settings, 'PRODUCT_VECTOR_TABLE', '') or '').strip()
    or _default_table_for_dimensions(PRODUCT_VECTOR_DIMENSIONS)
)
# Internal alias: PRODUCT_VECTOR_MODEL holds the active embedding model name.
# Source of truth is settings.EMBEDDING_MODEL (env var: EMBEDDING_MODEL).
PRODUCT_VECTOR_MODEL = getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L12-v2')
_TABLE_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?$')


@dataclass(frozen=True)
class VectorBackendStatus:
    backend: str
    ready: bool
    lane: str
    reason: str = ''
    table: str = PRODUCT_VECTOR_TABLE
    dimensions: int = PRODUCT_VECTOR_DIMENSIONS


def configured_product_vector_backend() -> str:
    return str(getattr(settings, 'PRODUCT_VECTOR_BACKEND', 'auto') or 'auto').strip().lower()


def _render_free_tier() -> bool:
    return bool(getattr(settings, 'RENDER_FREE_TIER', False))


def _is_postgres() -> bool:
    return connection.vendor == 'postgresql'


def _table_sql() -> str:
    if not _TABLE_RE.match(PRODUCT_VECTOR_TABLE):
        raise ValueError(f"Unsafe product vector table name: {PRODUCT_VECTOR_TABLE!r}")
    return PRODUCT_VECTOR_TABLE


def product_text_hash(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def _clean_vector(vector: Sequence[float]) -> List[float]:
    cleaned = []
    for value in vector or []:
        try:
            cleaned.append(float(value))
        except (TypeError, ValueError):
            return []
    return cleaned


def _vector_literal(vector: Sequence[float]) -> str:
    cleaned = _clean_vector(vector)
    return '[' + ','.join(f'{value:.9g}' for value in cleaned) + ']'


def pgvector_table_ready() -> bool:
    if not _is_postgres():
        return False

    try:
        table = _table_sql()
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass(%s)", [table])
            table_exists = bool(cursor.fetchone()[0])
            if not table_exists:
                return False
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            return bool(cursor.fetchone()[0])
    except Exception as exc:
        logger.warning("pgvector readiness check failed: %s", exc)
        return False


def product_vector_backend_status() -> VectorBackendStatus:
    configured = configured_product_vector_backend()
    if _render_free_tier():
        if pgvector_table_ready():
            return VectorBackendStatus(
                backend='pgvector',
                ready=True,
                lane=PRODUCT_VECTOR_LANE,
                reason='Postgres pgvector table and extension ready',
            )
        return VectorBackendStatus(
            backend='orm_text',
            ready=True,
            lane=PRODUCT_VECTOR_LANE,
            reason='Render free tier: JSON cosine fallback disabled; use ORM text fallback',
        )

    if configured not in {'auto', 'json_cosine', 'pgvector'}:
        return VectorBackendStatus(
            backend='json_cosine',
            ready=True,
            lane=PRODUCT_VECTOR_LANE,
            reason=f"unknown backend {configured!r}; using JSON cosine fallback",
        )

    if configured == 'json_cosine':
        return VectorBackendStatus(
            backend='json_cosine',
            ready=True,
            lane=PRODUCT_VECTOR_LANE,
            reason='configured JSON cosine fallback',
        )

    if pgvector_table_ready():
        return VectorBackendStatus(
            backend='pgvector',
            ready=True,
            lane=PRODUCT_VECTOR_LANE,
            reason='Postgres pgvector table and extension ready',
        )

    return VectorBackendStatus(
        backend='json_cosine' if configured == 'auto' else configured,
        ready=configured == 'auto',
        lane=PRODUCT_VECTOR_LANE,
        reason='configured vector backend unavailable; using JSON cosine fallback',
    )


def _sync_product_vector_pgvector(product, vector: Sequence[float], embedding_text: str = '') -> bool:
    if not pgvector_table_ready():
        return False

    cleaned = _clean_vector(vector)
    if len(cleaned) != PRODUCT_VECTOR_DIMENSIONS:
        logger.warning(
            "Skipping pgvector sync for product %s: expected %s dimensions, got %s",
            getattr(product, 'id', ''),
            PRODUCT_VECTOR_DIMENSIONS,
            len(cleaned),
        )
        return False

    try:
        table = _table_sql()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {table}
                    (product_id, embedding, embedding_dimensions, embedding_model, text_hash, updated_at)
                VALUES (%s, %s::vector, %s, %s, %s, NOW())
                ON CONFLICT (product_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    embedding_dimensions = EXCLUDED.embedding_dimensions,
                    embedding_model = EXCLUDED.embedding_model,
                    text_hash = EXCLUDED.text_hash,
                    updated_at = NOW()
                """,
                [
                    str(product.id),
                    _vector_literal(cleaned),
                    PRODUCT_VECTOR_DIMENSIONS,
                    PRODUCT_VECTOR_MODEL,
                    product_text_hash(embedding_text),
                ],
            )
        return True
    except Exception as exc:
        logger.warning("pgvector product sync failed for %s: %s", getattr(product, 'id', ''), exc)
        return False


def sync_product_vector(product, vector: Sequence[float], embedding_text: str = '') -> bool:
    """Upsert one product vector into the configured vector backend when ready."""
    status = product_vector_backend_status()
    if status.backend == 'pgvector' and status.ready:
        return _sync_product_vector_pgvector(product, vector, embedding_text=embedding_text)
    return False


def _search_products_pgvector(
    query_vector: Sequence[float],
    candidate_ids: Iterable,
    *,
    top_k: int,
) -> List[Tuple[object, float]]:
    """Search product vectors in pgvector, constrained to the caller's candidate IDs."""
    if not pgvector_table_ready():
        return []

    ids = [str(product_id) for product_id in candidate_ids if product_id]
    cleaned = _clean_vector(query_vector)
    if not ids or len(cleaned) != PRODUCT_VECTOR_DIMENSIONS:
        return []

    vector_literal = _vector_literal(cleaned)
    try:
        table = _table_sql()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT product_id::text,
                       GREATEST(0.0::double precision, 1.0 - (embedding <=> %s::vector)) AS score
                FROM {table}
                WHERE product_id::text = ANY(%s)
                  AND embedding_dimensions = %s
                  AND embedding_model = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [vector_literal, ids, PRODUCT_VECTOR_DIMENSIONS, PRODUCT_VECTOR_MODEL, vector_literal, int(top_k)],
            )
            return [(row[0], float(row[1])) for row in cursor.fetchall()]
    except Exception as exc:
        if _render_free_tier():
            logger.warning("pgvector product search failed; using ORM text fallback: %s", exc)
        else:
            logger.warning("pgvector product search failed; falling back to JSON cosine: %s", exc)
        return []


def search_product_vectors(
    query_vector: Sequence[float],
    candidate_ids: Iterable,
    *,
    top_k: int,
) -> List[Tuple[object, float]]:
    status = product_vector_backend_status()
    if status.backend == 'pgvector' and status.ready:
        return _search_products_pgvector(query_vector, candidate_ids, top_k=top_k)
    return []


def search_products_pgvector(
    query_vector: Sequence[float],
    candidate_ids: Iterable,
    *,
    top_k: int,
) -> List[Tuple[object, float]]:
    """Backward-compatible wrapper for older tests/imports."""
    return _search_products_pgvector(query_vector, candidate_ids, top_k=top_k)


def bulk_sync_product_vectors(product_vector_pairs, embedding_text_map=None) -> int:
    """
    Write multiple product vectors to the configured backend in one operation.

    Args:
        product_vector_pairs: iterable of (product, vector) tuples.
        embedding_text_map:   optional {product.id: text} for text hashing.
                              Falls back to empty string per entry if absent.
    Returns:
        Number of vectors successfully written.
    """
    pairs = list(product_vector_pairs)
    if not pairs:
        return 0

    status = product_vector_backend_status()
    embedding_text_map = embedding_text_map or {}

    if status.backend == 'pgvector' and status.ready:
        return _bulk_sync_pgvector(pairs, embedding_text_map)

    # json_cosine: vectors live on Product.embedding_vector only — nothing to write here
    return 0


def _bulk_sync_pgvector(pairs, embedding_text_map) -> int:
    """Upsert all vectors inside a single cursor context."""
    if not pgvector_table_ready():
        return 0

    rows = []
    for product, vector in pairs:
        cleaned = _clean_vector(vector)
        if len(cleaned) != PRODUCT_VECTOR_DIMENSIONS:
            logger.warning(
                "bulk pgvector: skipping product %s — wrong dimensions (%s)",
                getattr(product, 'id', ''),
                len(cleaned),
            )
            continue
        embedding_text = embedding_text_map.get(product.id, '')
        rows.append((
            str(product.id),
            _vector_literal(cleaned),
            PRODUCT_VECTOR_DIMENSIONS,
            PRODUCT_VECTOR_MODEL,
            product_text_hash(embedding_text),
        ))

    if not rows:
        return 0

    table = _table_sql()
    try:
        with connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    f"""
                    INSERT INTO {table}
                        (product_id, embedding, embedding_dimensions, embedding_model, text_hash, updated_at)
                    VALUES (%s, %s::vector, %s, %s, %s, NOW())
                    ON CONFLICT (product_id) DO UPDATE SET
                        embedding        = EXCLUDED.embedding,
                        embedding_dimensions = EXCLUDED.embedding_dimensions,
                        embedding_model  = EXCLUDED.embedding_model,
                        text_hash        = EXCLUDED.text_hash,
                        updated_at       = NOW()
                    """,
                    list(row),
                )
        return len(rows)
    except Exception as exc:
        logger.warning("bulk pgvector sync failed: %s", exc)
        return 0

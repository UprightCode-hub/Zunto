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
PRODUCT_VECTOR_TABLE = getattr(settings, 'PRODUCT_VECTOR_TABLE', 'market_product_vector')
PRODUCT_VECTOR_DIMENSIONS = int(getattr(settings, 'PRODUCT_VECTOR_DIMENSIONS', 384))
PRODUCT_VECTOR_MODEL = getattr(settings, 'PRODUCT_VECTOR_MODEL', 'paraphrase-MiniLM-L3-v2')
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
        backend='json_cosine' if configured == 'auto' else 'pgvector',
        ready=configured == 'auto',
        lane=PRODUCT_VECTOR_LANE,
        reason='pgvector unavailable; using JSON cosine fallback',
    )


def sync_product_vector(product, vector: Sequence[float], embedding_text: str = '') -> bool:
    """Upsert one product vector into the production pgvector table when ready."""
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
                    (product_id, embedding, embedding_model, text_hash, updated_at)
                VALUES (%s, %s::vector, %s, %s, NOW())
                ON CONFLICT (product_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model,
                    text_hash = EXCLUDED.text_hash,
                    updated_at = NOW()
                """,
                [
                    str(product.id),
                    _vector_literal(cleaned),
                    PRODUCT_VECTOR_MODEL,
                    product_text_hash(embedding_text),
                ],
            )
        return True
    except Exception as exc:
        logger.warning("pgvector product sync failed for %s: %s", getattr(product, 'id', ''), exc)
        return False


def search_products_pgvector(
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
                  AND embedding_model = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [vector_literal, ids, PRODUCT_VECTOR_MODEL, vector_literal, int(top_k)],
            )
            return [(row[0], float(row[1])) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning("pgvector product search failed; falling back to JSON cosine: %s", exc)
        return []

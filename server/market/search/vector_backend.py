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


def _is_postgres() -> bool:
    return connection.vendor == 'postgresql'


def _is_sqlite() -> bool:
    return connection.vendor == 'sqlite'


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


def _load_sqlite_vec_extension() -> bool:
    if not _is_sqlite():
        return False

    try:
        import sqlite_vec
    except Exception as exc:
        logger.info("sqlite-vec package unavailable: %s", exc)
        return False

    try:
        connection.ensure_connection()
        raw_connection = connection.connection
        raw_connection.enable_load_extension(True)
        sqlite_vec.load(raw_connection)
        raw_connection.enable_load_extension(False)
        return True
    except Exception as exc:
        logger.warning("sqlite-vec extension load failed: %s", exc)
        try:
            connection.connection.enable_load_extension(False)
        except Exception:
            pass
        return False


def sqlite_vec_table_ready() -> bool:
    if not _load_sqlite_vec_extension():
        return False

    try:
        table = _table_sql()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {table}
                USING vec0(
                    embedding float[{PRODUCT_VECTOR_DIMENSIONS}],
                    product_id text,
                    embedding_model text,
                    text_hash text
                )
                """
            )
        return True
    except Exception as exc:
        logger.warning("sqlite-vec readiness check failed: %s", exc)
        return False


def product_vector_backend_status() -> VectorBackendStatus:
    configured = configured_product_vector_backend()
    if configured not in {'auto', 'json_cosine', 'pgvector', 'sqlite_vec'}:
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

    if configured in {'auto', 'sqlite_vec'} and sqlite_vec_table_ready():
        return VectorBackendStatus(
            backend='sqlite_vec',
            ready=True,
            lane=PRODUCT_VECTOR_LANE,
            reason='SQLite sqlite-vec virtual table ready',
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


def _sync_product_vector_sqlite_vec(product, vector: Sequence[float], embedding_text: str = '') -> bool:
    if not sqlite_vec_table_ready():
        return False

    cleaned = _clean_vector(vector)
    if len(cleaned) != PRODUCT_VECTOR_DIMENSIONS:
        logger.warning(
            "Skipping sqlite-vec sync for product %s: expected %s dimensions, got %s",
            getattr(product, 'id', ''),
            PRODUCT_VECTOR_DIMENSIONS,
            len(cleaned),
        )
        return False

    try:
        from sqlite_vec import serialize_float32

        table = _table_sql()
        with connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {table} WHERE product_id = %s AND embedding_model = %s",
                [str(product.id), PRODUCT_VECTOR_MODEL],
            )
            cursor.execute(
                f"""
                INSERT INTO {table}
                    (product_id, embedding, embedding_model, text_hash)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    str(product.id),
                    serialize_float32(cleaned),
                    PRODUCT_VECTOR_MODEL,
                    product_text_hash(embedding_text),
                ],
            )
        return True
    except Exception as exc:
        logger.warning("sqlite-vec product sync failed for %s: %s", getattr(product, 'id', ''), exc)
        return False


def sync_product_vector(product, vector: Sequence[float], embedding_text: str = '') -> bool:
    """Upsert one product vector into the configured vector backend when ready."""
    status = product_vector_backend_status()
    if status.backend == 'pgvector' and status.ready:
        return _sync_product_vector_pgvector(product, vector, embedding_text=embedding_text)
    if status.backend == 'sqlite_vec' and status.ready:
        return _sync_product_vector_sqlite_vec(product, vector, embedding_text=embedding_text)
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


def _search_products_sqlite_vec(
    query_vector: Sequence[float],
    candidate_ids: Iterable,
    *,
    top_k: int,
) -> List[Tuple[object, float]]:
    if not sqlite_vec_table_ready():
        return []

    ids = {str(product_id) for product_id in candidate_ids if product_id}
    cleaned = _clean_vector(query_vector)
    if not ids or len(cleaned) != PRODUCT_VECTOR_DIMENSIONS:
        return []

    try:
        from sqlite_vec import serialize_float32

        table = _table_sql()
        sqlite_k = min(max(int(top_k) * 20, len(ids), int(top_k)), 5000)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT product_id, distance
                FROM {table}
                WHERE embedding MATCH %s
                  AND k = %s
                  AND embedding_model = %s
                ORDER BY distance
                """,
                [serialize_float32(cleaned), sqlite_k, PRODUCT_VECTOR_MODEL],
            )
            results = []
            for product_id, distance in cursor.fetchall():
                product_id = str(product_id)
                if product_id not in ids:
                    continue
                score = 1.0 / (1.0 + max(float(distance), 0.0))
                results.append((product_id, score))
                if len(results) >= int(top_k):
                    break
            return results
    except Exception as exc:
        import traceback; traceback.print_exc()
        logger.warning("sqlite-vec product search failed; falling back to JSON cosine: %s", exc)
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
    if status.backend == 'sqlite_vec' and status.ready:
        return _search_products_sqlite_vec(query_vector, candidate_ids, top_k=top_k)
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

    if status.backend == 'sqlite_vec' and status.ready:
        return _bulk_sync_sqlite_vec(pairs, embedding_text_map)

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
                        (product_id, embedding, embedding_model, text_hash, updated_at)
                    VALUES (%s, %s::vector, %s, %s, NOW())
                    ON CONFLICT (product_id) DO UPDATE SET
                        embedding        = EXCLUDED.embedding,
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


def _bulk_sync_sqlite_vec(pairs, embedding_text_map) -> int:
    """
    All DELETEs and INSERTs inside a single cursor context = one write lock
    acquisition for the entire batch instead of two per product.
    sqlite_vec virtual tables do not support multi-row INSERT syntax,
    so we still loop the INSERTs, but they share one transaction.
    """
    if not sqlite_vec_table_ready():
        return 0

    try:
        from sqlite_vec import serialize_float32
    except ImportError:
        logger.warning("sqlite_vec not importable in bulk sync")
        return 0

    rows = []
    for product, vector in pairs:
        cleaned = _clean_vector(vector)
        if len(cleaned) != PRODUCT_VECTOR_DIMENSIONS:
            logger.warning(
                "bulk sqlite_vec: skipping product %s — wrong dimensions (%s)",
                getattr(product, 'id', ''),
                len(cleaned),
            )
            continue
        embedding_text = embedding_text_map.get(product.id, '')
        rows.append((
            str(product.id),
            serialize_float32(cleaned),
            PRODUCT_VECTOR_MODEL,
            product_text_hash(embedding_text),
        ))

    if not rows:
        return 0

    table = _table_sql()
    count = 0
    try:
        with connection.cursor() as cursor:
            # One bulk DELETE — one SQL statement for all IDs
            product_ids = [row[0] for row in rows]
            placeholders = ','.join(['%s'] * len(product_ids))
            cursor.execute(
                f"DELETE FROM {table} "
                f"WHERE product_id IN ({placeholders}) AND embedding_model = %s",
                product_ids + [PRODUCT_VECTOR_MODEL],
            )
            # Individual INSERTs required by sqlite_vec virtual table protocol,
            # but inside the same cursor = same transaction = one lock acquisition
            for product_id, serialized, model_name, text_hash in rows:
                cursor.execute(
                    f"""
                    INSERT INTO {table}
                        (product_id, embedding, embedding_model, text_hash)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [product_id, serialized, model_name, text_hash],
                )
                count += 1
    except Exception as exc:
        logger.warning("bulk sqlite_vec sync failed after %s inserts: %s", count, exc)

    return count
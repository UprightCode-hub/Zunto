"""
server/assistant/utils/response_cache.py

LLM and RAG response caching for the assistant.

Uses Django's cache framework — works with:
  - django_redis (production, Redis DB 0)
  - locmem (development, in-process)
No additional dependencies. No code changes needed between environments.

Cache layers:
  1. LLM response cache — keyed by (assistant_mode, normalized_message)
     TTL: 1 hour. Only caches high-confidence, non-dispute responses.
     Saves 600-2000ms + one Groq token budget per cache hit.

    2. RAG search cache — keyed by lane + normalized_query
     TTL: 30 minutes. Caches FAISS + FAQ results.
     Saves ~80-150ms per hit, reduces model encode calls.

Cache key format:
    zunto:llm_v1:{assistant_mode}:{md5(normalized_message)}
    zunto:rag_v2:{lane}:{md5(normalized_query)}

The version suffix (v1) allows instant cache invalidation across all
keys if the response format or model changes — just bump the version.
"""
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Version — bump this to invalidate all cached responses instantly
# ---------------------------------------------------------------------------
_LLM_CACHE_VERSION = 'v1'
_RAG_CACHE_VERSION = 'v2'

# ---------------------------------------------------------------------------
# TTLs
# ---------------------------------------------------------------------------
LLM_CACHE_TTL = 3600        # 1 hour — LLM responses for stable questions
RAG_CACHE_TTL = 1800        # 30 minutes — FAISS search results

# ---------------------------------------------------------------------------
# Modes that should never be cached (session/context-specific)
# ---------------------------------------------------------------------------
_NEVER_CACHE_MODES = frozenset({'customer_service'})

# Minimum confidence to cache — don't persist uncertain responses
_MIN_CACHE_CONFIDENCE = 0.50


# ---------------------------------------------------------------------------
# Message normalization
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """
    Normalize a message for cache key generation.
    Makes semantically identical messages hash to the same key.

    "How do I track my ORDER??" → "how do i track my order"
    "what's  the  return  policy" → "whats the return policy"
    """
    text = (text or '').lower().strip()
    text = re.sub(r"[^\w\s]", '', text)    # remove punctuation
    text = re.sub(r'\s+', ' ', text)       # collapse whitespace
    return text


def _md5(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# LLM response cache
# ---------------------------------------------------------------------------

def _llm_cache_key(assistant_mode: Optional[str], message: str) -> str:
    mode = (assistant_mode or 'unknown').lower()
    normalized = _normalize(message)
    digest = _md5(normalized)
    return f'llm_{_LLM_CACHE_VERSION}:{mode}:{digest}'


def get_llm_cache(
    message: str,
    assistant_mode: Optional[str] = None,
) -> Optional[Dict]:
    """
    Retrieve a cached LLM response.
    Returns the result dict or None on miss.
    """
    if assistant_mode in _NEVER_CACHE_MODES:
        return None

    key = _llm_cache_key(assistant_mode, message)
    try:
        cached = cache.get(key)
        if cached is not None:
            logger.info(f"✅ LLM cache HIT [{assistant_mode}]: {message[:50]!r}")
            return cached
    except Exception as e:
        logger.warning(f"LLM cache GET failed (non-fatal): {e}")

    return None


def set_llm_cache(
    message: str,
    result: Dict,
    assistant_mode: Optional[str] = None,
    ttl: int = LLM_CACHE_TTL,
) -> None:
    """
    Store a LLM response in cache.

    Skips caching if:
    - Mode is in _NEVER_CACHE_MODES (customer_service)
    - Confidence is below _MIN_CACHE_CONFIDENCE
    - Result came from an error or fallback path
    - Result source is rule_engine (already fast, no benefit)
    """
    if assistant_mode in _NEVER_CACHE_MODES:
        return

    source = result.get('source', '')
    if source in ('rule_engine', 'error_fallback', 'rag_fallback'):
        return

    confidence = result.get('confidence', 0.0)
    if confidence < _MIN_CACHE_CONFIDENCE:
        return

    # Don't cache if LLM itself errored and fell back to RAG
    if result.get('metadata', {}).get('fallback_used'):
        return

    key = _llm_cache_key(assistant_mode, message)
    try:
        # Tag the result so callers know it came from cache
        cacheable = {**result, 'source': 'cache', 'cache_original_source': source}
        cache.set(key, cacheable, timeout=ttl)
        logger.debug(f"LLM cache SET [{assistant_mode}] confidence={confidence:.2f}: {message[:50]!r}")
    except Exception as e:
        logger.warning(f"LLM cache SET failed (non-fatal): {e}")


def invalidate_llm_cache(
    message: str,
    assistant_mode: Optional[str] = None,
) -> None:
    """Manually invalidate a specific LLM cache entry."""
    key = _llm_cache_key(assistant_mode, message)
    try:
        cache.delete(key)
        logger.info(f"LLM cache invalidated: {key}")
    except Exception as e:
        logger.warning(f"LLM cache DELETE failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# RAG search cache
# ---------------------------------------------------------------------------

def _rag_cache_key(query: str, lane: Optional[str] = None) -> str:
    normalized_lane = (lane or 'unknown').lower().strip() or 'unknown'
    normalized = _normalize(query)
    digest = _md5(normalized)
    return f'rag_{_RAG_CACHE_VERSION}:{normalized_lane}:{digest}'


def get_rag_cache(query: str, lane: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Retrieve cached RAG search results.
    Returns list of result dicts or None on miss.
    """
    key = _rag_cache_key(query, lane)
    try:
        cached = cache.get(key)
        if cached is not None:
            logger.debug(f"RAG cache HIT: {query[:50]!r}")
            return cached
    except Exception as e:
        logger.warning(f"RAG cache GET failed (non-fatal): {e}")
    return None


def set_rag_cache(
    query: str,
    results: List[Dict],
    lane: Optional[str] = None,
    ttl: int = RAG_CACHE_TTL,
) -> None:
    """
    Store RAG search results. Only caches if results are non-empty.
    """
    if not results:
        return

    key = _rag_cache_key(query, lane)
    try:
        cache.set(key, results, timeout=ttl)
        logger.debug(f"RAG cache SET ({len(results)} results): {query[:50]!r}")
    except Exception as e:
        logger.warning(f"RAG cache SET failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Cache stats helper (for admin/monitoring)
# ---------------------------------------------------------------------------

def get_cache_info() -> Dict[str, Any]:
    """
    Return basic cache info for monitoring.
    Works with both Redis and locmem backends.
    """
    info = {
        'llm_ttl_seconds': LLM_CACHE_TTL,
        'rag_ttl_seconds': RAG_CACHE_TTL,
        'llm_version': _LLM_CACHE_VERSION,
        'rag_version': _RAG_CACHE_VERSION,
        'never_cache_modes': list(_NEVER_CACHE_MODES),
        'min_confidence_to_cache': _MIN_CACHE_CONFIDENCE,
    }

    try:
        # Check if backend is Redis and expose connection info
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        redis_info = conn.info('memory')
        info['redis_used_memory_human'] = redis_info.get('used_memory_human', 'unknown')
        info['backend'] = 'redis'
    except Exception:
        info['backend'] = 'locmem'

    return info

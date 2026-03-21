"""Lightweight cache-backed observability helpers for assistant runtime metrics."""

from __future__ import annotations

from typing import Dict

from django.core.cache import cache

PREFIX = 'assistant:metrics:'


def _metric_key(name: str) -> str:
    return f'{PREFIX}{name}'


def incr(name: str, value: int = 1) -> None:
    key = _metric_key(name)
    try:
        cache.incr(key, value)
    except Exception:
        # key missing or backend limitations; initialize then continue
        try:
            cache.set(key, value, timeout=None)
        except Exception:
            pass


def observe_ms(name: str, duration_ms: int) -> None:
    incr(f'{name}.count', 1)
    incr(f'{name}.sum_ms', max(0, int(duration_ms)))


def get_snapshot(metric_names: Dict[str, str]) -> Dict[str, int]:
    snapshot = {}
    for alias, name in metric_names.items():
        value = cache.get(_metric_key(name), 0)
        try:
            snapshot[alias] = int(value or 0)
        except Exception:
            snapshot[alias] = 0
    return snapshot

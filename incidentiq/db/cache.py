"""In-memory LRU cache and single-worker concurrency enforcement for IncidentIQ."""

import logging
import os
from collections import OrderedDict
from typing import Any

from incidentiq.db.repository import get_incident_from_db, upsert_incident

logger = logging.getLogger("incidentiq.cache")

MAX_INCIDENTS_IN_MEMORY = int(os.getenv("MAX_INCIDENTS_IN_MEMORY", "1000"))


def check_single_worker() -> None:
    """Enforces single-worker operation when running with in-memory state."""
    workers_str = (
        os.getenv("WEB_CONCURRENCY")
        or os.getenv("UVICORN_WORKERS")
        or os.getenv("WORKERS")
    )
    if workers_str:
        try:
            w = int(workers_str)
            if w > 1:
                raise RuntimeError(
                    f"Configuration Error: IncidentIQ is configured with {w} workers. "
                    "Single-worker mode (workers=1) is strictly enforced when running in-memory state. "
                    "Set WORKERS=1 to proceed."
                )
        except ValueError:
            pass


class IncidentLRUCache:
    """LRU Cache for incidents with automatic database fallback and write-through eviction."""

    def __init__(self, capacity: int = MAX_INCIDENTS_IN_MEMORY) -> None:
        self.capacity = capacity
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str, default: Any = None) -> dict[str, Any] | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        # Cache miss: fetch from database
        db_inc = get_incident_from_db(key)
        if db_inc:
            self.set(key, db_inc)
            return db_inc
        return default

    def set(self, key: str, value: dict[str, Any]) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
        else:
            if len(self._cache) >= self.capacity:
                # Evict oldest incident and ensure it is saved to DB
                evicted_id, evicted_data = self._cache.popitem(last=False)
                try:
                    upsert_incident(evicted_data)
                except Exception as e:  # noqa: BLE001
                    logger.error(
                        f"Failed to persist evicted incident {evicted_id}: {e}"
                    )
            self._cache[key] = value

    def pop(self, key: str, default: Any = None) -> dict[str, Any] | None:
        return self._cache.pop(key, default)

    def clear(self) -> None:
        self._cache.clear()

    def __getitem__(self, key: str) -> dict[str, Any]:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        if key in self._cache:
            return True
        db_inc = get_incident_from_db(key)
        if db_inc:
            self.set(key, db_inc)
            return True
        return False

    def values(self) -> list[dict[str, Any]]:
        return list(self._cache.values())

    def items(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self._cache.items())

    def keys(self) -> list[str]:
        return list(self._cache.keys())

    def __len__(self) -> int:
        return len(self._cache)

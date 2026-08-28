"""Persistent last-known-good map cache, keyed by mapHeadId.

Brand-agnostic store used by the fetch flow to survive undecryptable ("Key B")
cloud uploads. See .plans/completed/map-reliability.md (Phase 1) for design.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
_STORAGE_KEY_FMT = f"{DOMAIN}_map_cache_{{entry_id}}"


@dataclass
class CachedMap:
    """One map's last-known-good render."""

    map_head_id: int
    png: bytes
    attributes: dict[str, Any]
    vector: dict[str, Any]
    content_hash: str
    timestamp: float

    def to_json(self) -> dict[str, Any]:
        return {
            "map_head_id": self.map_head_id,
            "png_b64": base64.b64encode(self.png).decode("ascii"),
            "attributes": self.attributes,
            "vector": self.vector,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> CachedMap | None:
        """Build from a persisted record; None if the record is malformed."""
        try:
            return cls(
                map_head_id=int(data["map_head_id"]),
                png=base64.b64decode(data["png_b64"]),
                attributes=data.get("attributes") or {},
                vector=data.get("vector") or {},
                content_hash=data["content_hash"],
                timestamp=float(data["timestamp"]),
            )
        except (KeyError, TypeError, ValueError) as ex:
            _LOGGER.warning("Discarding corrupt map-cache entry: %s", ex)
            return None


class MapCache:
    """Loads/saves last-known-good map renders, keyed by mapHeadId.

    One instance per config entry (own `.storage` file). Not brand-specific:
    any brand's fetch flow may upsert into this cache. HA's executor/event
    loop model means callers only ever touch this from the event loop (a
    fetch worker hands decoded results back and awaits the upsert there), so
    no additional locking is needed for concurrent upserts.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, _STORAGE_KEY_FMT.format(entry_id=entry_id)
        )
        self._maps: dict[int, CachedMap] = {}
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    async def async_load(self) -> None:
        """Load the persisted cache from disk. Call once at setup.

        Missing file, unreadable JSON, or a schema-version mismatch all
        result in an empty cache rather than a crash — the cache is a
        best-effort optimization, never load-bearing for correctness.
        """
        try:
            raw = await self._store.async_load()
        except Exception as ex:  # noqa: BLE001 - corrupt storage must not block setup
            _LOGGER.warning("Map cache unreadable, starting empty: %s", ex)
            raw = None

        self._maps = {}
        if raw is not None and isinstance(raw, dict) and raw.get("version") == STORAGE_VERSION:
            for entry in (raw.get("maps") or {}).values():
                cached = CachedMap.from_json(entry)
                if cached is not None:
                    self._maps[cached.map_head_id] = cached
        elif raw is not None:
            _LOGGER.info("Map cache schema mismatch (expected v%s); starting empty",
                         STORAGE_VERSION)
        self._loaded = True

    def get(self, map_head_id: int) -> CachedMap | None:
        return self._maps.get(map_head_id)

    def all(self) -> dict[int, CachedMap]:
        """Every cached entry, keyed by mapHeadId."""
        return dict(self._maps)

    async def async_upsert(
        self,
        map_head_id: int,
        *,
        png: bytes,
        attributes: dict[str, Any],
        vector: dict[str, Any],
        content_hash: str,
        timestamp: float,
    ) -> bool:
        """Insert/replace the entry for `map_head_id` iff the hash changed.

        Returns True if storage was written, False when an identical poll
        was a no-op (hash matches the cached entry already).
        """
        existing = self._maps.get(map_head_id)
        if existing is not None and existing.content_hash == content_hash:
            return False
        self._maps[map_head_id] = CachedMap(
            map_head_id=map_head_id,
            png=png,
            attributes=attributes,
            vector=vector,
            content_hash=content_hash,
            timestamp=timestamp,
        )
        await self._async_save()
        return True

    async def async_prune(self, keep_ids: set[int]) -> bool:
        """Drop cached entries whose id isn't in `keep_ids`.

        Callers must never pass an empty set from a transient/failed map-list
        read (a real empty result would wipe every cached map) — only call
        this with an actual, non-empty map-list snapshot.
        Returns True if storage was rewritten (something was actually dropped).
        """
        to_drop = [k for k in self._maps if k not in keep_ids]
        if not to_drop:
            return False
        for k in to_drop:
            del self._maps[k]
        await self._async_save()
        return True

    async def _async_save(self) -> None:
        await self._store.async_save({
            "version": STORAGE_VERSION,
            "maps": {str(k): v.to_json() for k, v in self._maps.items()},
        })

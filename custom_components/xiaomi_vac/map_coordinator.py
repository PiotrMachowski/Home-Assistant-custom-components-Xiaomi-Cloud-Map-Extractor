"""Cloud map coordinator: periodically fetch + parse the active map."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud.connector import XiaomiCloud
from .cloud.mqtt import MqttMessage
from .const import (
    CONF_DEVICE_ID,
    CONF_MAC,
    CONF_MODEL,
    CONF_PASS_TOKEN,
    CONF_SERVER,
    CONF_SERVICE_TOKEN,
    CONF_SSECURITY,
    CONF_USER_ID,
    CONF_USERNAME,
    CONF_WIFI_SN,
    DOMAIN,
    MAP_IDLE_INTERVAL,
    MAP_SCAN_INTERVAL,
)
from .coordinator import XiaomiVacuumCoordinator
from .device import IjaiVacuumDevice
from .map import MapFetcher, MapResult, SessionExpired
from .map_cache import MapCache
from .map_parsers import parser_key, required_map_key_inputs
from .spec.types import MapCapability

# activities where the map is actually changing
_ACTIVE = {"cleaning", "returning"}

# ijai-specific MQTT identifiers for map events (plan: Out of scope for other brands)
_SIID_MAP = 10
_EIID_MAP_UPLOAD = 6   # event_occured/10/6 = "test-upload-map" (fresh map uploaded)
_PIID_CUR_MAP = 2      # properties_changed/10/2 = curMapId

# Burst window: collapse multiple upload events within this window into one fetch
_DEBOUNCE_SECONDS = 2.0
_MAP_UPLOAD_THROTTLE_SECONDS = 30.0
_MAP_REFRESH_WAIT_SECONDS = 120.0
_MAP_REFRESH_POLL_SECONDS = 3.0
_REFRESH_READY_ACTIVITIES = {"docked", "idle"}

# Cloud upload slots tried every cycle for the active map (per map-reliability
# Phase 0: divergence between them is real but not gated on any local state,
# so both are read every poll rather than treating one as a fallback).
_SLOTS = ("0", "1")

# Cache key for devices whose map capability has no map-list catalogue at all
# (single physical map, e.g. viomi/dreame/roidmi profiles without get_map_list).
# There is exactly one map, so a fixed key round-trips the cache correctly.
_SINGLE_MAP_ID = 0

# Vector keys that only make sense for the CURRENTLY active map; stripped from
# any other cached map shown in `.maps` so its stale position doesn't render on
# the wrong floor plan (map-reliability Phase 2: live-overlay scoping).
_LIVE_ONLY_VECTOR_KEYS = ("path", "vacuum", "goto", "vacuum_room", "vacuum_room_name")

_LOGGER = logging.getLogger(__name__)


def _static_only(vector: dict) -> dict:
    return {k: v for k, v in vector.items() if k not in _LIVE_ONLY_VECTOR_KEYS}


class XiaomiMapCoordinator(DataUpdateCoordinator[MapResult]):
    """Holds a logged-in cloud session and refreshes the map."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device: IjaiVacuumDevice,
        control: XiaomiVacuumCoordinator,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:map:{entry.data[CONF_MODEL]}",
            update_interval=timedelta(seconds=MAP_IDLE_INTERVAL),
        )
        self.entry = entry
        self._device = device
        self._control = control
        self._cloud: XiaomiCloud | None = None
        self._fetcher: MapFetcher | None = None
        self._cache: MapCache | None = None
        # Last successful get-map-list read ([{name,id,cur}...]), kept up to date
        # every cycle EVEN WHEN no map decrypts, so the "Active Map" select can
        # list/switch maps independent of whether the current upload is readable.
        self._map_list_meta: list[dict] = []
        # Whether this profile has a map-list catalogue at all (set in _build).
        # A device without one has exactly one physical map -> _SINGLE_MAP_ID.
        self._has_map_list = False
        # MQTT-signaled curMapId; used in _resolve_active_id when the map-list
        # read for this cycle failed (None = not yet signaled by MQTT).
        self._mqtt_active_id: int | None = None
        self._mqtt_debounce_task: asyncio.Task | None = None
        self._mqtt_refresh_needs_upload = False
        self._mqtt_upload_waiters: set[asyncio.Future[None]] = set()
        self._last_upload_request_at: dict[int, float] = {}
        self._last_live_at: float | None = None
        self._refresh_map_lock = asyncio.Lock()
        self._pending_entry_updates: dict[str, str] = {}

    @property
    def device(self) -> IjaiVacuumDevice:
        return self._device

    @property
    def control(self) -> XiaomiVacuumCoordinator:
        return self._control

    @property
    def map_list_meta(self) -> list[dict]:
        """Latest [{name,id,cur}...] from get-map-list; available even when no
        map decrypts, so the Active Map select isn't gated on decrypt success."""
        return self._map_list_meta

    def _tune_interval(self) -> None:
        """Poll fast while the vacuum is moving, slowly when docked/idle."""
        data = self._control.data
        active = bool(data and data.activity in _ACTIVE)
        secs = MAP_SCAN_INTERVAL if active else MAP_IDLE_INTERVAL
        new = timedelta(seconds=secs)
        if self.update_interval != new:
            self.update_interval = new

    async def async_on_mqtt_message(self, msg: MqttMessage) -> None:
        """Handle an MQTT message routed from the integration setup.

        Triggered by: upload event (siid 10 / eiid 6) or curMapId change (siid 10 / piid 2).
        """
        if msg.kind == "property" and msg.siid == _SIID_MAP and msg.piid == _PIID_CUR_MAP:
            try:
                self._mqtt_active_id = int(msg.value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
            _LOGGER.debug("MQTT curMapId=%s — scheduling map refresh", self._mqtt_active_id)
            self._schedule_mqtt_refresh(request_upload=True)
        elif msg.kind == "event" and msg.siid == _SIID_MAP and msg.eiid == _EIID_MAP_UPLOAD:
            _LOGGER.debug("MQTT map upload event — scheduling map refresh")
            self._notify_mqtt_upload_waiters()
            self._schedule_mqtt_refresh(request_upload=True)

    def _new_mqtt_upload_waiter(self) -> asyncio.Future[None]:
        waiter: asyncio.Future[None] = self.hass.loop.create_future()
        self._mqtt_upload_waiters.add(waiter)
        waiter.add_done_callback(self._mqtt_upload_waiters.discard)
        return waiter

    def _notify_mqtt_upload_waiters(self) -> None:
        for waiter in tuple(self._mqtt_upload_waiters):
            if not waiter.done():
                waiter.set_result(None)

    def _fresh_live_after(self, since: float) -> bool:
        return self._last_live_at is not None and self._last_live_at > since

    async def _async_wait_for_mqtt_upload(
        self, waiter: asyncio.Future[None], since: float,
    ) -> None:
        deadline = time.monotonic() + _MAP_REFRESH_WAIT_SECONDS
        while time.monotonic() < deadline:
            if self._fresh_live_after(since):
                return
            if waiter.done():
                await self.async_request_refresh()
                return
            await asyncio.sleep(1)
        if self._fresh_live_after(since):
            return
        raise HomeAssistantError("Timed out waiting for a fresh map upload event")

    async def _async_poll_for_live_map(self, since: float) -> None:
        deadline = time.monotonic() + _MAP_REFRESH_WAIT_SECONDS
        while time.monotonic() < deadline:
            await self.async_request_refresh()
            if self._fresh_live_after(since):
                return
            remaining = deadline - time.monotonic()
            await asyncio.sleep(min(_MAP_REFRESH_POLL_SECONDS, max(0.0, remaining)))
        raise HomeAssistantError("Timed out waiting for a readable fresh map")

    async def async_refresh_map_with_movement(
        self, *, confirm_movement: bool, use_mqtt: bool,
    ) -> None:
        """Briefly start the vacuum to force a fresh map upload, then dock."""
        if confirm_movement is not True:
            raise HomeAssistantError("Refresh map requires confirm_movement: true")
        if self._refresh_map_lock.locked():
            raise HomeAssistantError("A map refresh is already running")

        async with self._refresh_map_lock:
            if self._device.profile.map is None:
                raise HomeAssistantError("This vacuum has no supported map capability")
            await self._control.async_request_refresh()
            status = self._control.data
            if status is None or status.activity not in _REFRESH_READY_ACTIVITIES:
                raise HomeAssistantError("Refresh map is only available while docked or idle")
            if self._device.core.start is None or self._device.core.charge is None:
                raise HomeAssistantError("This vacuum cannot start and return to dock")

            since = self._last_live_at or 0.0
            waiter = self._new_mqtt_upload_waiter() if use_mqtt else None
            dock_on_exit = False
            try:
                dock_on_exit = True
                await self.hass.async_add_executor_job(self._device.start)
                await self._control.async_request_refresh()
                if waiter is not None:
                    await self._async_wait_for_mqtt_upload(waiter, since)
                else:
                    await self._async_poll_for_live_map(since)
            finally:
                if waiter is not None and not waiter.done():
                    waiter.cancel()
                if dock_on_exit:
                    with contextlib.suppress(Exception):
                        await self.hass.async_add_executor_job(self._device.return_home)
                    with contextlib.suppress(Exception):
                        await self._control.async_request_refresh()

    def _schedule_mqtt_refresh(self, *, request_upload: bool = False) -> None:
        """Cancel any pending debounce task and start a fresh one."""
        self._mqtt_refresh_needs_upload = self._mqtt_refresh_needs_upload or request_upload
        if self._mqtt_debounce_task is not None:
            self._mqtt_debounce_task.cancel()
        self._mqtt_debounce_task = self.hass.async_create_task(
            self._mqtt_debounced_refresh()
        )

    async def _mqtt_debounced_refresh(self) -> None:
        try:
            await asyncio.sleep(_DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            return
        self._mqtt_debounce_task = None
        request_upload = self._mqtt_refresh_needs_upload
        self._mqtt_refresh_needs_upload = False
        if request_upload:
            await self.async_request_map_upload(self._mqtt_active_id)
        await self.async_refresh()

    def _known_active_map_id(self) -> int | None:
        if self._mqtt_active_id is not None:
            return self._mqtt_active_id
        for meta in self._map_list_meta:
            if meta.get("cur") and meta.get("id") is not None:
                try:
                    return int(meta["id"])
                except (TypeError, ValueError):
                    return None
        if self.data is not None and self.data.map_id is not None:
            return self.data.map_id
        return None

    async def async_request_map_upload(self, map_id: int | None = None) -> bool:
        """Ask the vacuum to upload a fresh cloud blob for a map-list map."""
        target = self._known_active_map_id() if map_id is None else map_id
        if target is None:
            return False
        target = int(target)
        now = time.monotonic()
        # None sentinel, not 0.0: monotonic() is ~uptime, so a 0.0 default
        # falsely throttles the first request within 30s of boot.
        last = self._last_upload_request_at.get(target)
        if last is not None and now - last < _MAP_UPLOAD_THROTTLE_SECONDS:
            _LOGGER.debug("Skipping throttled map upload request for map_id=%s", target)
            return False
        self._last_upload_request_at[target] = now
        try:
            await self.hass.async_add_executor_job(
                self._device.request_map_upload, target
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Map upload request failed for map_id=%s: %s", target, err)
            return False
        return True

    def _build(self) -> MapFetcher:
        """Blocking: restore the saved cloud session and construct a fetcher.

        wifi_sn and mac are read LIVE from the device (the source of truth for
        the map AES key); the values stashed at setup time can be empty/stale.
        """
        d = self.entry.data
        self._pending_entry_updates = {}
        # No password: the saved session is restored and renewed via passToken.
        cloud = XiaomiCloud(d[CONF_USERNAME])
        cloud.restore_session(d[CONF_USER_ID], d[CONF_SSECURITY], d[CONF_SERVICE_TOKEN],
                              d.get(CONF_PASS_TOKEN))
        self._cloud = cloud

        brand = parser_key(self._device.profile)
        required = required_map_key_inputs(brand)

        cap = self._device.profile.map
        self._has_map_list = isinstance(cap, MapCapability) and cap.get_map_list is not None

        wifi_sn = ""
        mac = ""
        if required:
            live_sn = self._device.get_wifi_sn(d[CONF_USER_ID])
            live_mac = self._device.get_mac()
            stored_sn = d.get(CONF_WIFI_SN) or ""
            stored_mac = d.get(CONF_MAC) or ""
            wifi_sn = live_sn or stored_sn
            mac = live_mac or stored_mac
            if live_sn and live_sn != stored_sn:
                self._pending_entry_updates[CONF_WIFI_SN] = live_sn
            if live_mac and live_mac != stored_mac:
                self._pending_entry_updates[CONF_MAC] = live_mac

        _LOGGER.debug(
            "Map key inputs: brand=%s wifi_sn=%r mac=%s user_id=%s device_id=%s model=%s",
            brand, wifi_sn, mac, d[CONF_USER_ID], d[CONF_DEVICE_ID], d[CONF_MODEL],
        )
        if "wifi_sn" in required and not wifi_sn:
            raise UpdateFailed(
                "Missing map key input wifi_sn: could not read it live or from storage"
            )
        if "device_mac" in required and not mac:
            # An empty mac silently produces the wrong AES key (decrypt fails
            # with "Padding is incorrect"), so refuse to build with one.
            raise UpdateFailed(
                "Missing map key input mac: could not read it live or from storage"
            )

        return MapFetcher(
            cloud,
            server=d[CONF_SERVER],
            user_id=d[CONF_USER_ID],
            device_id=d[CONF_DEVICE_ID],
            model=d[CONF_MODEL],
            mac=mac,
            wifi_sn=wifi_sn,
            parser_brand=brand,
        )

    def _persist_pending_entry_updates(self) -> None:
        if not self._pending_entry_updates:
            return
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, **self._pending_entry_updates},
        )
        self._pending_entry_updates = {}

    async def _ensure_cache(self) -> MapCache:
        if self._cache is None:
            cache = MapCache(self.hass, self.entry.entry_id)
            await cache.async_load()
            self._cache = cache
        return self._cache

    def _fetch_slots(self) -> list[MapResult | None]:
        """Blocking: try every cloud slot for the active map this cycle.

        Each slot's SessionExpired is caught independently instead of
        short-circuiting the rest of the list: the object backing one slot
        (e.g. Map Obj Name) can be permanently unavailable server-side while
        a different object for the same device (e.g. Trajectory Obj Name)
        still resolves fine — that's not a dead session, just a dead object.
        SessionExpired is only re-raised when EVERY slot came back with no
        URL, since that's the actual "whole session is dead" signal the
        coordinator's refresh/reauth handling wants.
        """
        results: list[MapResult | None] = []
        any_resolved = False
        for slot in _SLOTS:
            try:
                results.append(self._fetcher.fetch(slot))
                any_resolved = True
            except SessionExpired:
                results.append(None)
        if not any_resolved:
            raise SessionExpired()
        return results

    def _resolve_active_id(
        self, active_meta: dict | None, decoded: list[MapResult], maps_meta: list[dict],
    ) -> int | None:
        """Which map this cycle's data belongs to, in order of trust:

        1. A live blob's own embedded id (ground truth from the cloud blob
           itself — ijai only; other brands never carry one).
        2. The local map-list's "cur" entry (independent of the cloud fetch).
        3. A fixed single-map key, but ONLY when this profile has no map-list
           capability at all — an empty `maps_meta` from a transient read
           failure on a multi-map device must NOT be mistaken for that.
        """
        for r in decoded:
            if r.map_id is not None:
                return r.map_id
        if active_meta and active_meta.get("id") is not None:
            try:
                return int(active_meta["id"])
            except (TypeError, ValueError):
                pass
        # Use the MQTT-signaled id when map-list read failed this cycle.
        if self._mqtt_active_id is not None:
            return self._mqtt_active_id
        if not self._has_map_list and not maps_meta:
            return _SINGLE_MAP_ID
        return None

    def _serve(
        self, cache: MapCache, active_id: int | None, maps_meta: list[dict],
    ) -> MapResult | None:
        """Build the result to serve from whatever the cache now holds for
        `active_id` (a live decode this cycle was already upserted before this
        runs, so cache and live are never out of sync — serve-parity holds by
        construction). None only when nothing has ever been cached for it.
        """
        if active_id is None:
            return None
        entry = cache.get(active_id)
        if entry is None:
            return None
        name_by_id = {
            int(m["id"]): m.get("name") for m in maps_meta if m.get("id") is not None
        }
        served = MapResult(
            image_png=entry.png,
            attributes=entry.attributes,
            vector=entry.vector,
            map_id=active_id,
            content_hash=entry.content_hash,
        )
        served.maps = [
            {
                **(cached.vector if map_id == active_id else _static_only(cached.vector)),
                "map_id": map_id,
                "map_name": name_by_id.get(map_id),
                "active": map_id == active_id,
            }
            for map_id, cached in cache.all().items()
        ]
        return served

    async def _async_update_data(self) -> MapResult:
        self._tune_interval()
        try:
            if self._fetcher is None:
                self._fetcher = await self.hass.async_add_executor_job(self._build)
                self._persist_pending_entry_updates()
            cache = await self._ensure_cache()

            # The map list (distinct physical maps) drives multi-map; best-effort
            # so a flaky local read never blocks the active-map fetch.
            try:
                maps_meta = await self.hass.async_add_executor_job(self._device.map_list)
            except Exception:  # noqa: BLE001
                maps_meta = []
            # Keep the switchable map list current even if the rest of this cycle
            # fails to produce a readable map. Never clobber a good list with a
            # transient empty read (same guard as cache prune).
            if maps_meta:
                self._map_list_meta = maps_meta

            try:
                slot_results = await self.hass.async_add_executor_job(self._fetch_slots)
            except SessionExpired:
                # Token likely expired — renew it with the passToken and retry.
                # If renewal fails, the passToken is dead too: ask the user to
                # re-auth (raises a reauth flow) rather than dead-end.
                if not await self._refresh_and_persist():
                    raise ConfigEntryAuthFailed("Xiaomi cloud map session expired") from None
                try:
                    slot_results = await self.hass.async_add_executor_job(self._fetch_slots)
                except SessionExpired:
                    # The passToken renewal just above proved the account
                    # credentials are valid, so a second empty map URL right
                    # after isn't an auth problem — the cloud simply has
                    # nothing to serve yet (no map uploaded under this
                    # obj_name, region mismatch, transient hiccup). Reporting
                    # this as ConfigEntryAuthFailed would force a reauth the
                    # user can never satisfy (login keeps succeeding, then
                    # immediately bounces back to reauth every cycle).
                    raise UpdateFailed(
                        "Xiaomi cloud has no map available (session is valid)"
                    ) from None

            decoded = [r for r in slot_results if r is not None]
            active_meta = next((m for m in maps_meta if m.get("cur")), None)
            active_id = self._resolve_active_id(active_meta, decoded, maps_meta)
            _LOGGER.debug(
                "Map cycle: slot keys=%s active_id=%s maps_listed=%d",
                ["A" if r is not None else "B" for r in slot_results],
                active_id, len(maps_meta),
            )

            # Whichever slot decrypted (Key A) wins and refreshes the cache for
            # this map id; both slots being None just means both were Key B this
            # cycle — normal, not an error, and handled by serving from cache.
            live = decoded[0] if decoded else None
            if live is not None and active_id is not None:
                live_at = time.time()
                self._last_live_at = live_at
                await cache.async_upsert(
                    active_id,
                    png=live.image_png,
                    attributes=live.attributes,
                    vector=live.vector,
                    content_hash=live.content_hash,
                    timestamp=live_at,
                )

            # Prune maps the device no longer lists, but never off a transient
            # empty read (map-reliability Phase 0 eviction decision).
            if maps_meta:
                keep_ids = {int(m["id"]) for m in maps_meta if m.get("id") is not None}
                if keep_ids:
                    await cache.async_prune(keep_ids)

            result = self._serve(cache, active_id, maps_meta)
            if result is None:
                # Nothing live AND nothing cached for this map id yet. This is
                # the normal cold-start state: the vacuum's current upload is a
                # bad ("Key B") blob that Mi Home can't read either, and we have
                # no prior good copy to fall back on. Not an error and not
                # actionable by the user — the cache fills the moment the vacuum
                # next uploads a good blob (any normal clean/dock does it), and
                # we serve silently from then on. So: no repair notice, no
                # warning-level log; just stay unavailable and keep polling.
                #
                # It's also what a fetcher built with stale key inputs produces
                # (wifi_sn/mac read while the device was briefly unreachable at
                # startup), so drop the fetcher to re-read live values next cycle.
                self._fetcher = None
                _LOGGER.debug(
                    "No readable map yet for active_id=%s: current upload is a "
                    "bad blob and nothing cached — waiting for a good upload",
                    active_id,
                )
                raise UpdateFailed("Waiting for a readable map upload from the vacuum")
            _LOGGER.debug(
                "Serving map active_id=%s (%s this cycle), %d map(s) cached",
                active_id, "live+cached" if decoded else "from cache",
                len(cache.all()),
            )
            return result
        except (UpdateFailed, ConfigEntryAuthFailed):
            raise
        except SessionExpired:
            raise ConfigEntryAuthFailed("Xiaomi cloud map session expired") from None
        except Exception as err:  # noqa: BLE001
            self._fetcher = None
            raise UpdateFailed(f"Map update error: {err}") from err

    async def _refresh_and_persist(self) -> bool:
        """Renew the cloud session via passToken and save the new tokens."""
        if self._cloud is None:
            return False
        if not await self.hass.async_add_executor_job(self._cloud.refresh):
            return False
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                CONF_SERVICE_TOKEN: self._cloud.service_token,
                CONF_SSECURITY: self._cloud.ssecurity,
                CONF_PASS_TOKEN: self._cloud.pass_token or "",
            },
        )
        _LOGGER.info("Renewed Xiaomi cloud session via passToken")
        return True

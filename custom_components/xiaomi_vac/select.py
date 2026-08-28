"""Selects: fan speed, water level, cleaning mode, sweep type, active map."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import XiaomiConfigEntry
from .const import DOMAIN
from .coordinator import XiaomiVacuumCoordinator
from .map_coordinator import XiaomiMapCoordinator
from .spec.types import MapCapability
from .vacuum import _cloud_set_current_map, _has_cloud_session

# Serialise commands to the device (one MIoT write at a time).
PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)

# (key, core attr holding {name: raw}, VacuumStatus attr with current raw, device setter)
SELECTS = (
    ("fan_speed", "fan_speeds", "fan_speed_raw", "set_fan_speed"),
    ("water_level", "water_levels", "water_level_raw", "set_water_level"),
    ("mode", "modes", "mode_raw", "set_mode"),
    ("sweep_type", "sweep_types", "sweep_type_raw", "set_sweep_type"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: XiaomiConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.control
    core = coordinator.device.core
    # Build only the selects whose core value table exists for this model —
    # no empty "sweep type" dropdown on a model that lacks it (e.g. dreame).
    entities: list[SelectEntity] = [
        XiaomiVacuumSelect(coordinator, entry, *cfg)
        for cfg in SELECTS
        if getattr(core, cfg[1])
    ]

    map_coordinator = entry.runtime_data.map
    cap = coordinator.device.profile.map
    if (
        map_coordinator is not None
        and isinstance(cap, MapCapability)
        and cap.set_current_map is not None
        and cap.get_map_list is not None
    ):
        entities.append(XiaomiActiveMapSelect(map_coordinator, entry))

    async_add_entities(entities)


class XiaomiVacuumSelect(CoordinatorEntity[XiaomiVacuumCoordinator], SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key, spec_attr, status_attr, setter):
        super().__init__(coordinator)
        self._key = key
        self._status_attr = status_attr
        self._setter = setter
        self._options_map: dict[str, int] = getattr(coordinator.device.core, spec_attr)
        self._reverse = {v: k for k, v in self._options_map.items()}
        self._attr_translation_key = key
        self._attr_options = list(self._options_map)
        base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, base)})

    @property
    def current_option(self) -> str | None:
        return self._reverse.get(getattr(self.coordinator.data, self._status_attr))

    async def async_select_option(self, option: str) -> None:
        setter = getattr(self.coordinator.device, self._setter)
        await self.hass.async_add_executor_job(setter, option)
        await self.coordinator.async_request_refresh()


def _map_label(m: dict) -> str:
    """Label for a get-map-list entry ({name,id,cur})."""
    return m.get("name") or f"Map {m['id']}"


class XiaomiActiveMapSelect(CoordinatorEntity[XiaomiMapCoordinator], SelectEntity):
    """Switch the vacuum's active map.

    Populated from `get-map-list` (via the coordinator's `map_list_meta`), NOT
    from decrypted map data — so the dropdown lists and switches maps even when
    the current cloud upload is undecryptable ("Key B"). Switching serves the
    new map from cache immediately when a readable copy exists.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "active_map"

    def __init__(self, coordinator: XiaomiMapCoordinator, entry: XiaomiConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base}_active_map"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, base)})

    def _maps(self) -> list[dict]:
        return self.coordinator.map_list_meta

    @property
    def available(self) -> bool:
        # Available whenever we know the map list, regardless of whether the
        # active map's upload currently decrypts (a Key-B active map must not
        # make the switch control disappear — that's when you need it most).
        return bool(self._maps())

    @property
    def options(self) -> list[str]:
        return [_map_label(m) for m in self._maps()]

    @property
    def current_option(self) -> str | None:
        return next((_map_label(m) for m in self._maps() if m.get("cur")), None)

    async def async_select_option(self, option: str) -> None:
        target = next((m for m in self._maps() if _map_label(m) == option), None)
        if target is None:
            return
        map_id = int(target["id"])
        data = self._entry.data
        if _has_cloud_session(data):
            # ijai proven, xiaomi inferred, viomi/dreame/roidmi best-effort-unverified — plan v1.2.2
            try:
                await self.hass.async_add_executor_job(
                    _cloud_set_current_map, data, self.coordinator.device, map_id
                )
                _LOGGER.debug("%s: map-switch served via cloud", self.coordinator.device.model)
            except Exception as cloud_err:  # noqa: BLE001
                _LOGGER.warning(
                    "%s: cloud map-switch failed, falling back to local: %s",
                    self.coordinator.device.model,
                    cloud_err,
                )
                await self.hass.async_add_executor_job(
                    self.coordinator.device.set_current_map, map_id
                )
                _LOGGER.debug("%s: map-switch served via local", self.coordinator.device.model)
        else:
            await self.hass.async_add_executor_job(
                self.coordinator.device.set_current_map, map_id
            )
            _LOGGER.debug(
                "%s: map-switch served via local (no cloud session)",
                self.coordinator.device.model,
            )
        await self.coordinator.async_request_map_upload(map_id)
        await self.coordinator.async_request_refresh()

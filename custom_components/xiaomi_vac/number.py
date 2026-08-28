"""Number: voice volume."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import XiaomiConfigEntry
from .const import DOMAIN
from .coordinator import XiaomiVacuumCoordinator

# Serialise commands to the device (one MIoT write at a time).
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: XiaomiConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.control
    if coordinator.device.core.volume is not None:
        async_add_entities([VolumeNumber(coordinator, entry)])


# Spec-verified volume value-ranges (Phase 0 of the parity plan, verified
# 03-07-2026 via miot-spec.org). ijai/xiaomi/viomi cores use 0-10
# (ijai.v17 hardware-verified); dreame's audio service volume is 0-100
# (all 6 distinct dreame cores checked: p2008/p2009/p2114a/p2149o/p2150a/
# r2215). xiaomi.ov21gl/ov71gl are the JSON-map xiaomi profiles (E1/E8)
# and diverge from the xiaomi brand default at 0-100 — checked first.
_VOLUME_MAX_BY_PROFILE_ID = {"xiaomi.ov21gl": 100, "xiaomi.ov71gl": 100}
_VOLUME_MAX_BY_BRAND = {"dreame": 100}
_VOLUME_MAX_DEFAULT = 10


class VolumeNumber(CoordinatorEntity[XiaomiVacuumCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "volume"
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base}_volume"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, base)})
        profile = coordinator.device.profile
        self._attr_native_max_value = (
            _VOLUME_MAX_BY_PROFILE_ID.get(profile.profile_id)
            or _VOLUME_MAX_BY_BRAND.get(profile.brand, _VOLUME_MAX_DEFAULT)
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.volume_raw

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.device.set_volume, int(value)
        )
        await self.coordinator.async_request_refresh()

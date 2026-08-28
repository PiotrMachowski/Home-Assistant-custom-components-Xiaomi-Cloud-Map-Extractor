"""Map camera entity. Carries the full plug-and-play attribute contract."""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import XiaomiConfigEntry
from .const import DOMAIN
from .map_coordinator import XiaomiMapCoordinator

# Read-only platform fed by the coordinator; no device writes to serialise.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: XiaomiConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    map_coordinator = entry.runtime_data.map
    if map_coordinator is not None:
        async_add_entities([XiaomiVacuumMapCamera(map_coordinator, entry)])


class XiaomiVacuumMapCamera(CoordinatorEntity[XiaomiMapCoordinator], Camera):
    _attr_has_entity_name = True
    _attr_translation_key = "map"
    _attr_content_type = "image/png"
    # The map geometry (rooms/calibration/walls…) is a live plug-and-play
    # contract for map cards, not history data. Keep it off the recorder so
    # the multi-KB blob isn't rewritten to the DB on every poll.
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, coordinator: XiaomiMapCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base}_map"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, base)})

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.image_png

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data.attributes

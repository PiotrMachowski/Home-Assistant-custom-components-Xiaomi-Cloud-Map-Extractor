"""Vacuum entity for Xiaomi (ijai-family) vacuums."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import XiaomiConfigEntry
from .cloud.connector import XiaomiCloud
from .const import (
    CONF_DEVICE_ID,
    CONF_PASS_TOKEN,
    CONF_SERVER,
    CONF_SERVICE_TOKEN,
    CONF_SSECURITY,
    CONF_USER_ID,
    CONF_USERNAME,
    DOMAIN,
)
from .coordinator import XiaomiVacuumCoordinator
from .device import IjaiVacuumDevice
from .spec.types import MapCapability

# Serialise commands to the device (one MIoT write at a time).
PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)

_ACTIVITY = {
    "cleaning": VacuumActivity.CLEANING,
    "paused": VacuumActivity.PAUSED,
    "idle": VacuumActivity.IDLE,
    "returning": VacuumActivity.RETURNING,
    "docked": VacuumActivity.DOCKED,
    "error": VacuumActivity.ERROR,
}

_BASE_SUPPORT = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.STATE
)

async def async_setup_entry(
    hass: HomeAssistant, entry: XiaomiConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.control
    async_add_entities([XiaomiVacuum(coordinator, entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "clean_segment",
        {vol.Required("segments"): vol.All(cv.ensure_list, [vol.Coerce(int)])},
        "async_clean_segment",
    )
    platform.async_register_entity_service(
        "refresh_map",
        {vol.Required("confirm_movement"): vol.All(cv.boolean, vol.Equal(True))},
        "async_refresh_map",
    )


class XiaomiVacuum(CoordinatorEntity[XiaomiVacuumCoordinator], StateVacuumEntity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: XiaomiVacuumCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._device = coordinator.device
        core = self._device.core
        support = _BASE_SUPPORT
        if core.charge is not None:
            support |= VacuumEntityFeature.RETURN_HOME
        if core.locate is not None or core.alarm is not None:
            support |= VacuumEntityFeature.LOCATE
        self._attr_supported_features = support
        base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base}_vacuum"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, base)},
            manufacturer="Xiaomi",
            model=self._device.model,
            name=entry.title,
        )

    @property
    def activity(self) -> VacuumActivity:
        return _ACTIVITY.get(self.coordinator.data.activity, VacuumActivity.IDLE)

    @property
    def extra_state_attributes(self) -> dict:
        return {"fault": self.coordinator.data.fault, "model": self._device.model}

    async def async_start(self) -> None:
        await self.hass.async_add_executor_job(self._device.start)
        await self.coordinator.async_request_refresh()

    async def async_stop(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._device.stop)
        await self.coordinator.async_request_refresh()

    async def async_return_to_base(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._device.return_home)
        await self.coordinator.async_request_refresh()

    async def async_refresh_map(self, confirm_movement: bool) -> None:
        data = self._entry.runtime_data
        if data.map is None:
            raise HomeAssistantError("Refresh map requires a cloud map session")
        await data.map.async_refresh_map_with_movement(
            confirm_movement=confirm_movement,
            use_mqtt=data.mqtt is not None,
        )

    async def async_pause(self) -> None:
        await self.hass.async_add_executor_job(self._device.pause)
        await self.coordinator.async_request_refresh()

    async def async_locate(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(self._device.locate)

    async def async_clean_segment(self, segments: list[int]) -> None:
        """Clean one or more rooms by their map room id (tap-to-clean)."""
        data = self._entry.data
        if _has_cloud_session(data):
            # ijai proven, xiaomi inferred, viomi/dreame/roidmi best-effort-unverified — plan v1.2.2
            try:
                await self.hass.async_add_executor_job(
                    _cloud_clean_segments, data, self._device, segments
                )
                _LOGGER.debug("%s: room-clean served via cloud", self._device.model)
                await self.coordinator.async_request_refresh()
                return
            except Exception as cloud_err:  # noqa: BLE001
                _LOGGER.warning(
                    "%s: cloud room-clean failed, falling back to local (may no-op on ijai): %s",
                    self._device.model,
                    cloud_err,
                )
        # Local fallback — also used when no cloud session is configured.
        try:
            await self.hass.async_add_executor_job(self._device.clean_segments, segments)
            _LOGGER.debug("%s: room-clean served via local", self._device.model)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Room cleaning failed: {err}") from err
        await self.coordinator.async_request_refresh()


def _has_cloud_session(data: dict) -> bool:
    return all(
        data.get(k)
        for k in (
            CONF_USERNAME, CONF_USER_ID, CONF_SSECURITY,
            CONF_SERVICE_TOKEN, CONF_SERVER, CONF_DEVICE_ID,
        )
    )


def _cloud_action_ok(response: object) -> bool:
    if not isinstance(response, dict):
        return False
    if response.get("code", 0) != 0:
        return False
    result = response.get("result")
    if isinstance(result, dict) and result.get("code", 0) != 0:
        return False
    if isinstance(result, list):
        return all(not isinstance(item, dict) or item.get("code", 0) == 0 for item in result)
    return True


def _cloud_clean_segments(data: dict, device: IjaiVacuumDevice, segments: list[int]) -> None:
    required = (
        data.get(CONF_USERNAME),
        data.get(CONF_USER_ID),
        data.get(CONF_SSECURITY),
        data.get(CONF_SERVICE_TOKEN),
        data.get(CONF_SERVER),
        data.get(CONF_DEVICE_ID),
    )
    if not all(required):
        raise ValueError("Room cleaning cloud fallback requires a Xiaomi cloud session")

    # Same preference order as device.clean_segments: set-room-clean takes
    # map room ids; start-room-sweep wants Mijia ids and fails with map ids.
    attempts = [
        params
        for params in (
            device.room_clean_set_params(segments),
            device.room_clean_start_params(segments),
        )
        if params is not None
    ]
    if not attempts:
        raise ValueError(f"{device.model} has no supported room-clean action")

    cloud = XiaomiCloud(str(data[CONF_USERNAME]))
    cloud.restore_session(
        data[CONF_USER_ID],
        data[CONF_SSECURITY],
        data[CONF_SERVICE_TOKEN],
        data.get(CONF_PASS_TOKEN),
    )
    for action, params in attempts:
        response = cloud.cloud_action(
            str(data[CONF_SERVER]),
            str(data[CONF_DEVICE_ID]),
            action.siid,
            action.aiid,
            params,
        )
        if _cloud_action_ok(response):
            return
    raise ValueError("Xiaomi cloud rejected every room-clean action")


def _cloud_set_current_map(data: dict, device: IjaiVacuumDevice, map_id: int) -> None:
    # ijai proven, xiaomi inferred, viomi/dreame/roidmi best-effort-unverified — plan v1.2.2
    cap = device.profile.map
    if not isinstance(cap, MapCapability):
        raise ValueError(f"{device.model} has no cloud-mappable map capability")
    action = cap.set_current_map
    if action is None:
        raise ValueError(f"{device.model} has no set-current-map action")
    cloud = XiaomiCloud(str(data[CONF_USERNAME]))
    cloud.restore_session(
        data[CONF_USER_ID],
        data[CONF_SSECURITY],
        data[CONF_SERVICE_TOKEN],
        data.get(CONF_PASS_TOKEN),
    )
    response = cloud.cloud_action(
        str(data[CONF_SERVER]),
        str(data[CONF_DEVICE_ID]),
        action.siid,
        action.aiid,
        [int(map_id)],
    )
    if not _cloud_action_ok(response):
        raise ValueError(f"Xiaomi cloud rejected map-switch: {response}")

"""Polling coordinator for a Xiaomi vacuum (local MIoT)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from miio.exceptions import DeviceException

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .device import DeviceCommunicationError, IjaiVacuumDevice, VacuumStatus

_LOGGER = logging.getLogger(__name__)


class XiaomiVacuumCoordinator(DataUpdateCoordinator[VacuumStatus]):
    """Fetches status from the vacuum over local MIoT on an interval."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device: IjaiVacuumDevice
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{device.model}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.device = device
        self.entry = entry

    async def _async_update_data(self) -> VacuumStatus:
        try:
            return await self.hass.async_add_executor_job(self.device.status)
        except (DeviceException, DeviceCommunicationError) as err:
            raise UpdateFailed(f"Error polling vacuum: {err}") from err

from typing import Self

from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN,
    CONF_MAC,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_MODEL,
    CONF_DEVICE_ID, CONF_NAME
)
from homeassistant.helpers.device_registry import DeviceInfo, CONNECTION_NETWORK_MAC
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .connector.model import XiaomiCloudMapExtractorData
from .connector.vacuums.base.model import VacuumApi
from .const import CONF_SERVER, CONF_USED_MAP_API, DOMAIN
from .coordinator import XiaomiCloudMapExtractorDataUpdateCoordinator
from .types import XiaomiCloudMapExtractorConfigEntry


class XiaomiCloudMapExtractorEntity(CoordinatorEntity[XiaomiCloudMapExtractorDataUpdateCoordinator]):
    _attr_has_entity_name = True
    _host: str
    _token: str
    _mac: str
    _username: str
    _password: str
    _model: str
    _device_id: str
    _server: str
    _used_map_api: VacuumApi

    def __init__(
            self: Self,
            coordinator: XiaomiCloudMapExtractorDataUpdateCoordinator,
            config_entry: XiaomiCloudMapExtractorConfigEntry
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._host = config_entry.data[CONF_HOST]
        self._token = config_entry.data[CONF_TOKEN]
        self._mac = config_entry.data[CONF_MAC]
        self._username = config_entry.data[CONF_USERNAME]
        self._password = config_entry.data[CONF_PASSWORD]
        self._model = config_entry.data[CONF_MODEL]
        self._name = config_entry.data[CONF_NAME]
        self._device_id = config_entry.data[CONF_DEVICE_ID]
        self._server = config_entry.data[CONF_SERVER]
        self._used_map_api = VacuumApi(config_entry.data[CONF_USED_MAP_API])
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=self._used_map_api.title(),
            name=self._name,
            model=self._model,
        )
        self._attr_unique_id = f"{self._device_id}"

    def _data(self: Self) -> XiaomiCloudMapExtractorData | None:
        return self.coordinator.data

    @property
    def extra_state_attributes(self: Self) -> dict[str, any]:
        data = self._data()
        if data is None:
            return {}
        attributes = {}
        if data.last_update_timestamp:
            attributes["last_update_timestamp"] = data.last_update_timestamp
        if data.last_successful_update_timestamp:
            attributes["last_successful_update_timestamp"] = data.last_successful_update_timestamp
        if data.map_data:
            attributes["calibration_points"] = data.map_data.calibration()
            attributes["rooms"] = data.map_data.rooms
        return attributes

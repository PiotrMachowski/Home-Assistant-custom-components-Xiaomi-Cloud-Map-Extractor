import asyncio
import logging
from typing import Optional

from homeassistant.components import camera
from homeassistant.components.camera import Image
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.xiaomi_cloud_map_extractor.common.connector import Connector

_LOGGER = logging.getLogger(__name__)


class ValetudoConnector(Connector):
    def __init__(self, hass: HomeAssistant, map_data_entity_id: str):
        self.two_factor_auth_url = None
        self._hass = hass
        self._map_data_entity_id = map_data_entity_id
        self._raw_map_data = None
        self._vacuum_name = None
        self._name = "Valetudo Map Data Extractor"

    def login(self):
        return True

    def get_raw_map_data(self, map_url) -> Optional[bytes]:
        image: Image
        try:
            image = asyncio.run_coroutine_threadsafe(camera.async_get_image(self._hass, self._map_data_entity_id),
                                                     self._hass.loop).result()

        except HomeAssistantError as err:
            _LOGGER.error("Error getting image from valetudo camera entity: %s", err)
            return None

        return image.content

    def get_device_details(self, token, country):
        return None, None, "Valetudo", "valetudo"

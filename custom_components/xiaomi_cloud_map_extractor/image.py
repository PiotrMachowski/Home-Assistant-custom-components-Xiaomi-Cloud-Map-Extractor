import logging
from typing import Self

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_flow import XiaomiCloudMapExtractorConfigEntry
from .const import CONTENT_TYPE
from .coordinator import XiaomiCloudMapExtractorDataUpdateCoordinator
from .entity import XiaomiCloudMapExtractorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: XiaomiCloudMapExtractorConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities([XiaomiCloudMapExtractorImageEntity(hass, coordinator, config_entry)])


class XiaomiCloudMapExtractorImageEntity(XiaomiCloudMapExtractorEntity, ImageEntity):

    def __init__(
            self: Self,
            hass: HomeAssistant,
            coordinator: XiaomiCloudMapExtractorDataUpdateCoordinator,
            config_entry: XiaomiCloudMapExtractorConfigEntry
    ) -> None:
        XiaomiCloudMapExtractorEntity.__init__(self, coordinator, config_entry)
        ImageEntity.__init__(self, hass)
        self.content_type = CONTENT_TYPE

    def image(self: Self) -> bytes | None:
        data = self._data()
        if data is None:
            return None
        return data.map_image

    @property
    def image_last_updated(self: Self):
        data = self._data()
        if data is None:
            return None
        return data.last_successful_update_timestamp

    @property
    def name(self: Self) -> str:
        return "Live Map"

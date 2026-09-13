from __future__ import annotations

import logging

from aiohttp import ClientSession
from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN,
    CONF_MAC,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_MODEL,
    CONF_DEVICE_ID
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from vacuum_map_parser_base.config.color import ColorsPalette, SupportedColor
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig, TrimConfig
from vacuum_map_parser_base.config.size import Sizes, Size

from .connector import XiaomiCloudMapExtractorConnector
from .connector.model import XiaomiCloudMapExtractorConnectorConfiguration
from .connector.vacuums.base.model import VacuumApi
from .const import (
    CONF_SERVER,
    CONF_USED_MAP_API,
    PLATFORMS,
    CONF_SIZES,
    CONF_COLORS,
    CONF_DRAWABLES,
    CONF_IMAGE_CONFIG,
    CONF_IMAGE_CONFIG_SCALE,
    CONF_IMAGE_CONFIG_ROTATE,
    CONF_IMAGE_CONFIG_TRIM_LEFT,
    CONF_IMAGE_CONFIG_TRIM_RIGHT,
    CONF_IMAGE_CONFIG_TRIM_TOP,
    CONF_IMAGE_CONFIG_TRIM_BOTTOM,
    CONF_ROOM_COLORS
)
from .coordinator import XiaomiCloudMapExtractorDataUpdateCoordinator
from .store import restore_connector_config
from .types import XiaomiCloudMapExtractorConfigEntry, XiaomiCloudMapExtractorRuntimeData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: XiaomiCloudMapExtractorConfigEntry) -> bool:
    xcme_configuration = to_configuration(entry)

    def session_creator() -> ClientSession:
        return async_create_clientsession(hass)

    connector_config = await restore_connector_config(hass, xcme_configuration.mac)
    xcme_connector = XiaomiCloudMapExtractorConnector(session_creator, xcme_configuration, connector_config, hass)
    xcme_update_coordinator = XiaomiCloudMapExtractorDataUpdateCoordinator(hass, xcme_connector)
    await xcme_update_coordinator.async_config_entry_first_refresh()
    entry.runtime_data = XiaomiCloudMapExtractorRuntimeData(xcme_update_coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: XiaomiCloudMapExtractorConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: XiaomiCloudMapExtractorConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def to_configuration(entry: XiaomiCloudMapExtractorConfigEntry) -> XiaomiCloudMapExtractorConnectorConfiguration:
    host = entry.data[CONF_HOST]
    token = entry.data[CONF_TOKEN]
    device_id = entry.data[CONF_DEVICE_ID]
    if device_id is None:
        raise ConfigEntryAuthFailed()
    model = entry.data[CONF_MODEL]
    mac = entry.data[CONF_MAC]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    server = entry.data[CONF_SERVER]
    used_api = VacuumApi(entry.data[CONF_USED_MAP_API])

    scale = entry.options[CONF_IMAGE_CONFIG][CONF_IMAGE_CONFIG_SCALE]
    rotate = entry.options[CONF_IMAGE_CONFIG][CONF_IMAGE_CONFIG_ROTATE]
    trim_left = entry.options[CONF_IMAGE_CONFIG][CONF_IMAGE_CONFIG_TRIM_LEFT]
    trim_right = entry.options[CONF_IMAGE_CONFIG][CONF_IMAGE_CONFIG_TRIM_RIGHT]
    trim_top = entry.options[CONF_IMAGE_CONFIG][CONF_IMAGE_CONFIG_TRIM_TOP]
    trim_bottom = entry.options[CONF_IMAGE_CONFIG][CONF_IMAGE_CONFIG_TRIM_BOTTOM]
    image_config = ImageConfig(scale, rotate, TrimConfig(trim_left, trim_right, trim_top, trim_bottom))

    colors = ColorsPalette({SupportedColor(k): tuple(v) for k, v in entry.options[CONF_COLORS].items()},
                           {k: tuple(v) for k, v in entry.options[CONF_ROOM_COLORS].items()})

    drawables = [Drawable(e) for e in entry.options[CONF_DRAWABLES]]
    sizes = Sizes({Size(k): v for k, v in entry.options[CONF_SIZES].items()})
    texts = []

    config = XiaomiCloudMapExtractorConnectorConfiguration(
        host,
        token,
        username,
        password,
        server,
        used_api,
        device_id,
        mac,
        model,
        image_config,
        colors,
        drawables,
        sizes,
        texts,
    )
    return config

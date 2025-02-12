from __future__ import annotations

from typing import Any

from homeassistant.const import (CONF_TOKEN, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME, CONF_MAC)
from homeassistant.core import HomeAssistant

from .const import CONF_USED_MAP_API, CONF_SERVER
from .types import XiaomiCloudMapExtractorConfigEntry


async def async_get_config_entry_diagnostics(
        hass: HomeAssistant, entry: XiaomiCloudMapExtractorConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator

    entry_data = entry.as_dict()
    entry_data["data"].pop(CONF_TOKEN)
    entry_data["data"].pop(CONF_MODEL)
    entry_data["data"].pop(CONF_SERVER)
    entry_data["data"].pop(CONF_USED_MAP_API)
    entry_data["data"].pop(CONF_PASSWORD)
    entry_data["data"].pop(CONF_USERNAME)
    entry_data["data"].pop(CONF_MAC)
    entry_data.pop("unique_id")
    return {
        "config_entry_data": entry_data,
        "device_data": coordinator.data.as_dict(),
    }

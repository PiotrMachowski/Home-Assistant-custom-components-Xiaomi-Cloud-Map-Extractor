from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .coordinator import XiaomiCloudMapExtractorDataUpdateCoordinator


@dataclass
class XiaomiCloudMapExtractorRuntimeData:
    coordinator: XiaomiCloudMapExtractorDataUpdateCoordinator


type XiaomiCloudMapExtractorConfigEntry = ConfigEntry[XiaomiCloudMapExtractorRuntimeData]

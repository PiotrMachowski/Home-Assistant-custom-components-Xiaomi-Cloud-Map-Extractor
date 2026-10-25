import logging
from typing import Self

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .connector import XiaomiCloudMapExtractorConnector
from .connector.model import XiaomiCloudMapExtractorData
from .connector.utils.exceptions import (
    XiaomiCloudMapExtractorException,
    FailedLoginException,
    TwoFactorAuthRequiredException,
    InvalidDeviceTokenException,
    InvalidCredentialsException,
    CaptchaRequiredException,
    DeviceNotFoundException,
)
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class XiaomiCloudMapExtractorDataUpdateCoordinator(DataUpdateCoordinator[XiaomiCloudMapExtractorData]):

    def __init__(
            self: Self,
            hass: HomeAssistant,
            connector: XiaomiCloudMapExtractorConnector,
    ) -> None:
        self.connector = connector
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_UPDATE_INTERVAL,
                         update_method=self.update_data)

    async def update_data(self: Self) -> XiaomiCloudMapExtractorData:
        try:
            return await self.connector.get_data()
        except (
                FailedLoginException,
                InvalidCredentialsException,
                InvalidDeviceTokenException,
                TwoFactorAuthRequiredException,
                CaptchaRequiredException,
                DeviceNotFoundException,
        ) as err:
            _LOGGER.error(err)
            _LOGGER.debug("Triggering reauth flow...")
            raise ConfigEntryAuthFailed(err) from err
        except XiaomiCloudMapExtractorException as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching xiaomi_cloud_map_extractor data: %s", err)
            raise UpdateFailed(err) from err

    async def force_update_data(self) -> None:
        self.connector.force_refresh()
        await self.async_request_refresh()

    async def set_auto_updating(self, updating: bool) -> None:
        self.connector.set_auto_updating(updating)

    def is_auto_updating(self) -> bool:
        return self.connector.is_auto_updating()

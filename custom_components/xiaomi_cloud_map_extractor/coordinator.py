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
    InvalidCredentialsException
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
                TwoFactorAuthRequiredException
        ) as err:
            _LOGGER.error(err)
            _LOGGER.debug("Triggering reauth flow...")
            raise ConfigEntryAuthFailed(err) from err
        except XiaomiCloudMapExtractorException as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err

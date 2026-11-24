import logging
from dataclasses import dataclass
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


@dataclass(frozen=True)
class AuthIssue:
    """Why the background update needs the user; the reauth flow reads it to explain what happened."""
    reason: str
    verification_url: str | None = None


def auth_issue_for(err: XiaomiCloudMapExtractorException) -> AuthIssue:
    if isinstance(err, CaptchaRequiredException):
        return AuthIssue("captcha_required")
    if isinstance(err, TwoFactorAuthRequiredException):
        return AuthIssue("verification_required", err.url)
    if isinstance(err, InvalidCredentialsException):
        return AuthIssue("invalid_credentials")
    if isinstance(err, (DeviceNotFoundException, InvalidDeviceTokenException)):
        return AuthIssue("device_not_found")
    return AuthIssue("session_expired")


class XiaomiCloudMapExtractorDataUpdateCoordinator(DataUpdateCoordinator[XiaomiCloudMapExtractorData]):

    def __init__(
            self: Self,
            hass: HomeAssistant,
            connector: XiaomiCloudMapExtractorConnector,
    ) -> None:
        self.connector = connector
        self.auth_issue: AuthIssue | None = None
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_UPDATE_INTERVAL,
                         update_method=self.update_data)

    async def update_data(self: Self) -> XiaomiCloudMapExtractorData:
        try:
            data = await self.connector.get_data()
        except (
                FailedLoginException,
                InvalidCredentialsException,
                InvalidDeviceTokenException,
                TwoFactorAuthRequiredException,
                CaptchaRequiredException,
                DeviceNotFoundException,
        ) as err:
            self.auth_issue = auth_issue_for(err)
            _LOGGER.debug("Triggering reauth flow (%s)...", self.auth_issue.reason)
            raise ConfigEntryAuthFailed(
                str(err), translation_domain=DOMAIN, translation_key=self.auth_issue.reason
            ) from err
        except XiaomiCloudMapExtractorException as err:
            raise UpdateFailed(str(err)) from err
        self.auth_issue = None
        return data

    async def force_update_data(self) -> None:
        self.connector.force_refresh()
        await self.async_request_refresh()

    async def set_auto_updating(self, updating: bool) -> None:
        self.connector.set_auto_updating(updating)

    def is_auto_updating(self) -> bool:
        return self.connector.is_auto_updating()

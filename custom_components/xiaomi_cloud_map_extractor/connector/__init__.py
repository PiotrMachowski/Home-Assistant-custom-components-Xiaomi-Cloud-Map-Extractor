import logging
from collections.abc import Callable
from datetime import datetime
from typing import Self, Type

from aiohttp import ClientSession

from .model import (
    XiaomiCloudMapExtractorData,
    XiaomiCloudMapExtractorConnectorConfiguration,
    XiaomiCloudMapExtractorConnectorStatus
)
from .utils import to_image
from .utils.exceptions import (
    DeviceNotFoundException,
    InvalidCredentialsException,
    InvalidDeviceTokenException,
    TwoFactorAuthRequiredException,
    FailedLoginException,
    FailedMapDownloadException,
    FailedMapParseException
)
from .vacuums.base.model import VacuumConfig, VacuumApi
from .vacuums.base.vacuum_base import BaseXiaomiCloudVacuum
from .vacuums.vacuum_dreame import DreameCloudVacuum
from .vacuums.vacuum_roborock import RoborockCloudVacuum
from .vacuums.vacuum_roidmi import RoidmiCloudVacuum
from .vacuums.vacuum_unsupported import UnsupportedCloudVacuum
from .vacuums.vacuum_viomi import ViomiCloudVacuum
from .vacuums.vacuum_ijai import IjaiCloudVacuum
from .vacuums.vacuum_xiaomi import XiaomiCloudVacuum
from .xiaomi_cloud.connector import (
    XiaomiCloudConnector,
    XiaomiCloudDeviceInfo,
    XiaomiCloudConnectorConfig,
)

_LOGGER = logging.getLogger(__name__)

AVAILABLE_VACUUM_PLATFORMS: dict[VacuumApi, Type[BaseXiaomiCloudVacuum]] = {v.vacuum_platform(): v for v in [
    RoborockCloudVacuum,
    ViomiCloudVacuum,
    RoidmiCloudVacuum,
    DreameCloudVacuum,
    IjaiCloudVacuum,
    XiaomiCloudVacuum,
    UnsupportedCloudVacuum
]}


class XiaomiCloudMapExtractorConnector:
    _used_api: VacuumApi
    _config: XiaomiCloudMapExtractorConnectorConfiguration
    _cloud_connector: XiaomiCloudConnector | None
    _vacuum_connector: BaseXiaomiCloudVacuum | None
    _map_cache: XiaomiCloudMapExtractorData
    _status: XiaomiCloudMapExtractorConnectorStatus
    _server: str | None
    _session_creator: Callable[[], ClientSession]
    _connector_config: XiaomiCloudConnectorConfig | None
    _forced_refresh: bool
    _auto_update: bool

    def __init__(
        self: Self,
        session_creator: Callable[[], ClientSession],
        config: XiaomiCloudMapExtractorConnectorConfiguration,
        connector_config: XiaomiCloudConnectorConfig | None,
    ) -> None:
        self._config = config
        self._connector_config = connector_config
        self._session_creator = session_creator
        self._cloud_connector = None
        self._vacuum_connector: BaseXiaomiCloudVacuum | None = None
        self._map_cache = XiaomiCloudMapExtractorData()
        self._status: XiaomiCloudMapExtractorConnectorStatus = XiaomiCloudMapExtractorConnectorStatus.UNINITIALIZED
        self._server = None
        self._used_api = self._config.used_api
        self._forced_refresh = False
        self._auto_update = True

    async def get_data(self: Self) -> XiaomiCloudMapExtractorData:
        if self._should_get_map():
            _LOGGER.debug("Downloading new map.")
            await self._get_map()
        else:
            _LOGGER.debug("Using cached map.")
        return self._map_cache

    async def _update(self: Self) -> None:
        if self._cloud_connector is None:
            if self._connector_config is None:
                _LOGGER.debug("Creating a new connector...")
                self._cloud_connector = XiaomiCloudConnector(self._session_creator)
            else:
                _LOGGER.debug("Restoring connector configuration...")
                self._cloud_connector = await XiaomiCloudConnector.from_config(
                    self._connector_config, self._session_creator
                )

        if not self._is_authenticated():
            _LOGGER.debug("Logging in...")
            if self._config.username is None or self._config.password is None:
                raise FailedLoginException()
            await self._cloud_connector.login_with_credentials(self._config.username, self._config.password)
            if not self._is_authenticated():
                _LOGGER.error("Not authenticated!")
                raise FailedLoginException()
            _LOGGER.debug("Logged in.")
        if self._vacuum_connector is None or self._status == XiaomiCloudMapExtractorConnectorStatus.UNINITIALIZED:
            _LOGGER.debug("Initializing...")
            await self._initialize()
            _LOGGER.debug("Initialized.")

        _LOGGER.debug("Downloading map...")
        map_data, map_raw_data = await self._vacuum_connector.get_map()
        _LOGGER.debug("Downloaded map.")
        if map_data is None:
            raise FailedMapDownloadException()
        self._map_cache.map_data = map_data
        self._map_cache.map_image = to_image(map_data)
        self._map_cache.map_data_raw = map_raw_data

    def _is_authenticated(self: Self) -> bool:
        return self._cloud_connector.is_authenticated()

    async def _initialize(self: Self) -> None:
        _LOGGER.debug("Retrieving device info, server: %s", self._config.server)
        device_details = await self._cloud_connector.get_device_details(self._config.device_id, self._config.server)

        if device_details is not None:
            self._server = device_details.server
            _LOGGER.debug("Retrieved device model: %s", device_details.model)
            self._vacuum_connector = self._create_device(device_details)
            _LOGGER.debug("Created device, used api: %s", self._used_api)
            self._status = XiaomiCloudMapExtractorConnectorStatus.OK
        else:
            _LOGGER.error("Failed to retrieve model")
            raise DeviceNotFoundException()

    def _should_get_map(self: Self) -> bool:
        if self._forced_refresh:
            self._forced_refresh = False
            return True
        return (
            self._map_cache is None or
            self._vacuum_connector is None or
            (self._vacuum_connector.should_update_map and self._auto_update)
        )

    async def _get_map(self: Self) -> None:
        try:
            await self._update()
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.OK
            self._map_cache.last_successful_update_timestamp = datetime.now()
            self._map_cache.two_factor_url = None
        except DeviceNotFoundException as e:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.DEVICE_NOT_FOUND
            raise e
        except InvalidCredentialsException as e:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.INVALID_CREDENTIALS
            raise e
        except FailedLoginException as e:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.FAILED_LOGIN
            raise e
        except InvalidDeviceTokenException as e:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.INVALID_TOKEN
            raise e
        except FailedMapDownloadException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.FAILED_MAP_DOWNLOAD
        except FailedMapParseException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.FAILED_MAP_PARSING
        except TwoFactorAuthRequiredException as e:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.TWO_FACTOR_REQUIRED
            self._map_cache.two_factor_url = e.url
            raise e
        finally:
            self._map_cache.last_update_timestamp = datetime.now()
            if self._vacuum_connector:
                self._map_cache.additional_vacuum_data = self._vacuum_connector.additional_data()

    def _create_device(self: Self, device_details: XiaomiCloudDeviceInfo) -> BaseXiaomiCloudVacuum:
        vacuum_config = VacuumConfig(
            self._cloud_connector,
            device_details,
            self._config.server,
            self._config.device_id,
            self._config.host,
            self._config.token,
            self._config.model,
            self._config.colors,
            self._config.drawables,
            self._config.image_config,
            self._config.sizes,
            self._config.texts,
        )
        vacuum_class = AVAILABLE_VACUUM_PLATFORMS.get(self._used_api, UnsupportedCloudVacuum)
        return vacuum_class(vacuum_config)

    def force_refresh(self):
        self._forced_refresh = True

    def set_auto_updating(self, updating: bool) -> None:
        self._auto_update = updating

    def is_auto_updating(self) -> bool:
        return self._auto_update

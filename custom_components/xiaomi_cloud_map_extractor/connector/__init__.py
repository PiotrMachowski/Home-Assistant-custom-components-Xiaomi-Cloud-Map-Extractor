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
from .xiaomi_cloud.connector import XiaomiCloudConnector, XiaomiCloudDeviceInfo

_LOGGER = logging.getLogger(__name__)

AVAILABLE_VACUUM_PLATFORMS: dict[VacuumApi, Type[BaseXiaomiCloudVacuum]] = {v.vacuum_platform(): v for v in [
    RoborockCloudVacuum,
    ViomiCloudVacuum,
    RoidmiCloudVacuum,
    DreameCloudVacuum,
    UnsupportedCloudVacuum
]}


class XiaomiCloudMapExtractorConnector:
    _used_api: VacuumApi
    _config: XiaomiCloudMapExtractorConnectorConfiguration
    _cloud_connector: XiaomiCloudConnector
    _vacuum_connector: BaseXiaomiCloudVacuum | None
    _map_cache: XiaomiCloudMapExtractorData
    _status: XiaomiCloudMapExtractorConnectorStatus
    _server: str | None

    def __init__(self: Self, session_creator: Callable[[], ClientSession],
                 config: XiaomiCloudMapExtractorConnectorConfiguration) -> None:
        self._config = config
        self._cloud_connector = XiaomiCloudConnector(session_creator, self._config.username, self._config.password)
        self._vacuum_connector: BaseXiaomiCloudVacuum | None = None
        self._map_cache = XiaomiCloudMapExtractorData()
        self._status: XiaomiCloudMapExtractorConnectorStatus = XiaomiCloudMapExtractorConnectorStatus.UNINITIALIZED
        self._server = None
        self._used_api = self._config.used_api

    async def get_data(self: Self) -> XiaomiCloudMapExtractorData:
        if self._should_get_map():
            _LOGGER.debug("Downloading new map.")
            await self._get_map()
        else:
            _LOGGER.debug("Using cached map.")
        return self._map_cache

    async def _update(self: Self) -> None:
        if not self._is_authenticated():
            _LOGGER.debug("Logging in...")
            await self._cloud_connector.login()
            if not self._is_authenticated():
                _LOGGER.error("Not authenticated!")
                raise FailedLoginException()
            _LOGGER.debug("Logged in.")
        if self._vacuum_connector is None or self._status == XiaomiCloudMapExtractorConnectorStatus.UNINITIALIZED:
            _LOGGER.debug("Initializing...")
            await self._initialize()
            _LOGGER.debug("Initialized.")

        _LOGGER.debug("Downloading map...")
        map_data, map_saved, map_raw_data = await self._vacuum_connector.get_map()
        _LOGGER.debug("Downloaded map.")
        if map_data is None:
            raise FailedMapDownloadException()
        self._map_cache.map_data = map_data
        self._map_cache.map_saved = map_saved
        self._map_cache.map_image = to_image(map_data)
        self._map_cache.map_data_raw = map_raw_data

    def _is_authenticated(self: Self) -> bool:

        return self._cloud_connector.is_authenticated()

    async def _initialize(self: Self) -> None:
        _LOGGER.debug("Retrieving device info, server: %s", self._config.server)
        device_details = await self._cloud_connector.get_device_details(self._config.token, self._config.server)

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
        return self._map_cache is None or self._vacuum_connector is None or self._vacuum_connector.should_update_map

    async def _get_map(self: Self) -> None:
        self._map_cache.last_update_timestamp = datetime.now()
        try:
            await self._update()
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.OK
            self._map_cache.last_successful_update_timestamp = datetime.now()
            self._map_cache.two_factor_url = None
        except DeviceNotFoundException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.DEVICE_NOT_FOUND
        except InvalidCredentialsException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.INVALID_CREDENTIALS
        except FailedLoginException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.FAILED_LOGIN
        except InvalidDeviceTokenException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.INVALID_TOKEN
        except FailedMapDownloadException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.FAILED_MAP_DOWNLOAD
        except FailedMapParseException:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.FAILED_MAP_PARSING
        except TwoFactorAuthRequiredException as e:
            self._map_cache.status = XiaomiCloudMapExtractorConnectorStatus.TWO_FACTOR_REQUIRED
            self._map_cache.two_factor_url = e.url

    def _create_device(self: Self, device_details: XiaomiCloudDeviceInfo) -> BaseXiaomiCloudVacuum:
        store_map_path = self._config.store_map_path if self._config.store_map_raw else None
        vacuum_config = VacuumConfig(
            self._cloud_connector,
            self._config.server,
            device_details.user_id,
            self._config.device_id,
            self._config.host,
            self._config.token,
            self._config.model,
            self._config.colors,
            self._config.drawables,
            self._config.image_config,
            self._config.sizes,
            self._config.texts,
            store_map_path
        )
        vacuum_class = AVAILABLE_VACUUM_PLATFORMS.get(self._used_api, UnsupportedCloudVacuum)
        return vacuum_class(vacuum_config)

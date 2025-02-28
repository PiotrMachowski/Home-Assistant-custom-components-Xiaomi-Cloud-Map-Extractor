import logging
from abc import ABC, abstractmethod
from typing import Self

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_base.config.text import Text
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_base.map_data_parser import MapDataParser

from .model import VacuumConfig, VacuumApi
from ...utils.exceptions import FailedMapDownloadException, FailedMapParseException
from ...xiaomi_cloud.connector import XiaomiCloudConnector

_LOGGER = logging.getLogger(__name__)


class BaseXiaomiCloudVacuum(ABC):
    model: str
    _connector: XiaomiCloudConnector
    _server: str
    _user_id: int
    _device_id: str
    _palette: ColorsPalette
    _drawables: list[Drawable]
    _image_config: ImageConfig
    _sizes: Sizes
    _texts: list[Text]
    _store_map_path: str | None

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        self.model = vacuum_config.model
        self._connector = vacuum_config.connector
        self._server = vacuum_config.server
        self._user_id = vacuum_config.device_info.user_id
        self._device_id = vacuum_config.device_id
        self._palette = vacuum_config.palette
        self._drawables = vacuum_config.drawables
        self._image_config = vacuum_config.image_config
        self._sizes = vacuum_config.sizes
        self._texts = vacuum_config.texts
        self._store_map_path = vacuum_config.store_map_path

    @staticmethod
    @abstractmethod
    def vacuum_platform() -> VacuumApi:
        pass

    @property
    @abstractmethod
    def map_archive_extension(self: Self) -> str:
        pass

    @property
    def should_update_map(self: Self) -> bool:
        return True

    @property
    @abstractmethod
    def map_data_parser(self: Self) -> MapDataParser:
        pass

    def decode_and_parse(self: Self, raw_map: bytes) -> MapData:
        decoded_map = self.map_data_parser.unpack_map(raw_map)
        return self.map_data_parser.parse(decoded_map)

    @abstractmethod
    async def get_map_url(self: Self, map_name: str) -> str | None:
        pass

    async def get_map_name(self: Self) -> str | None:
        return "0"

    async def get_map(self: Self) -> tuple[MapData, bool, bytes]:
        _LOGGER.debug("Getting map name...")
        map_name = await self.get_map_name()
        _LOGGER.debug("Got map name: \"%s\".", map_name)
        _LOGGER.debug("Downloading map...")
        raw_map_data = await self.get_raw_map_data(map_name)
        if raw_map_data is None:
            _LOGGER.error("FailedMapDownloadException")
            raise FailedMapDownloadException()
        _LOGGER.debug("Downloaded raw map: \"%d\".", len(raw_map_data))
        map_stored = False
        if self._store_map_path is not None:
            self.store_map(raw_map_data)
            map_stored = True
        _LOGGER.debug("Parsing map...")
        map_data = self.decode_and_parse(raw_map_data)
        _LOGGER.debug("Parsed map: (%d x %d)", map_data.image.dimensions.height, map_data.image.dimensions.width)
        if map_data is not None:
            map_data.map_name = map_name
        else:
            _LOGGER.error("FailedMapParseException")
            raise FailedMapParseException()
        return map_data, map_stored, raw_map_data

    async def get_raw_map_data(self: Self, map_name: str | None) -> bytes | None:
        if map_name is None:
            return None
        map_url = await self.get_map_url(map_name)
        return await self._connector.get_raw_map_data(map_url)

    def store_map(self: Self, raw_map_data: bytes) -> None:
        with open(f"{self._store_map_path}/map_data_{self.model}.{self.map_archive_extension}", "wb") as raw_map_file:
            raw_map_file.write(raw_map_data)

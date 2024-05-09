from abc import ABC, abstractmethod
from dataclasses import dataclass

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_base.config.text import Text
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_base.map_data_parser import MapDataParser

from .xiaomi_cloud_connector import XiaomiCloudConnector

@dataclass
class VacuumConfig:
    connector: XiaomiCloudConnector
    country: str
    user_id: str
    device_id: str
    host: str
    token: str
    model: str
    _mac: str
    palette: ColorsPalette
    drawables: list[Drawable]
    image_config: ImageConfig
    sizes: Sizes
    texts: list[Text]
    store_map_path: str | None


class XiaomiCloudVacuum(ABC):

    def __init__(self, vacuum_config: VacuumConfig):
        self.model = vacuum_config.model
        self._connector = vacuum_config.connector
        self._country = vacuum_config.country
        self._user_id = vacuum_config.user_id
        self._device_id = vacuum_config.device_id
        self._palette = vacuum_config.palette
        self._drawables = vacuum_config.drawables
        self._image_config = vacuum_config.image_config
        self._sizes = vacuum_config.sizes
        self._texts = vacuum_config.texts
        self._store_map_path = vacuum_config.store_map_path

    @property
    @abstractmethod
    def map_archive_extension(self) -> str:
        pass

    @property
    @abstractmethod
    def should_get_map_from_vacuum(self) -> bool:
        pass

    @property
    def should_update_map(self) -> bool:
        return True

    @property
    @abstractmethod
    def map_data_parser(self) -> MapDataParser:
        pass

    def decode_and_parse(self, raw_map: bytes) -> MapData:
        decoded_map = self.map_data_parser.unpack_map(raw_map)
        return self.map_data_parser.parse(decoded_map)

    @abstractmethod
    def get_map_url(self, map_name: str) -> str | None:
        pass

    def get_map_name(self) -> str | None:
        return "0"

    def get_map(self) -> tuple[MapData | None, bool]:
        map_name = self.get_map_name()
        raw_map_data = self.get_raw_map_data(map_name)
        if raw_map_data is None:
            return None, False
        map_stored = False
        if self._store_map_path is not None:
            self.store_map(raw_map_data)
            map_stored = True
        map_data = self.decode_and_parse(raw_map_data)
        if map_data is not None:
            map_data.map_name = map_name
        return map_data, map_stored

    def get_raw_map_data(self, map_name: str | None) -> bytes | None:
        if map_name is None:
            return None
        map_url = self.get_map_url(map_name)
        return self._connector.get_raw_map_data(map_url)

    def store_map(self, raw_map_data):
        with open(f"{self._store_map_path}/map_data_{self.model}.{self.map_archive_extension}", "wb") as raw_map_file:
            raw_map_file.write(raw_map_data)

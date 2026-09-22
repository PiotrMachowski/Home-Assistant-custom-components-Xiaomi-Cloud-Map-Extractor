from typing import Self, Any

from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_base.map_data_parser import MapDataParser

from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2


class UnsupportedCloudVacuum(BaseXiaomiCloudVacuumV2):
    _unsupported_map_data_parser: MapDataParser

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        super().__init__(vacuum_config)
        self._unsupported_map_data_parser = UnsupportedMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.UNSUPPORTED

    @property
    def map_archive_extension(self: Self):
        return "unknown"

    async def should_update_map(self: Self) -> bool:
        return False

    @property
    def map_data_parser(self: Self) -> MapDataParser:
        return self._unsupported_map_data_parser

    def decode_and_parse(self: Self, raw_map: bytes) -> MapData | None:
        return self._unsupported_map_data_parser.create_empty(f"Vacuum\n{self.model}\nis not supported")


class UnsupportedMapDataParser(MapDataParser):

    def parse(self, raw: bytes, *args: Any, **kwargs: Any) -> MapData:
        return MapData()

    def unpack_map(self, raw_encoded: bytes, *args: Any, **kwargs: Any) -> bytes:
        return b"NO_DATA"

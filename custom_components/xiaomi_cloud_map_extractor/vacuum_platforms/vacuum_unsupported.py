from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_base.map_data_parser import MapDataParser

from .vacuum_base import VacuumConfig
from .vacuum_v2 import XiaomiCloudVacuumV2


class UnsupportedCloudVacuum(XiaomiCloudVacuumV2):

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._unsupported_map_data_parser = MapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @property
    def map_archive_extension(self):
        return "unknown"

    @property
    def map_data_parser(self) -> MapDataParser:
        return self._unsupported_map_data_parser

    def decode_and_parse(self, raw_map: bytes) -> MapData | None:
        return self._unsupported_map_data_parser.create_empty(f"Vacuum\n{self.model}\nis not supported")

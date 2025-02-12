from typing import Self

from vacuum_map_parser_viomi.map_data_parser import ViomiMapDataParser
from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2


class ViomiCloudVacuum(BaseXiaomiCloudVacuumV2):
    _viomi_map_data_parser: ViomiMapDataParser

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        super().__init__(vacuum_config)
        self._viomi_map_data_parser = ViomiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.VIOMI

    @property
    def map_archive_extension(self: Self) -> str:
        return "zlib"

    @property
    def map_data_parser(self: Self) -> ViomiMapDataParser:
        return self._viomi_map_data_parser

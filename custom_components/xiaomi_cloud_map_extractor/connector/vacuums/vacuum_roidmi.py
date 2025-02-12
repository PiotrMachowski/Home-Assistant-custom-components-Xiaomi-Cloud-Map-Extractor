from typing import Self

from vacuum_map_parser_roidmi.map_data_parser import RoidmiMapDataParser
from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2


class RoidmiCloudVacuum(BaseXiaomiCloudVacuumV2):
    _roidmi_map_data_parser: RoidmiMapDataParser

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        super().__init__(vacuum_config)
        self._roidmi_map_data_parser = RoidmiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.ROIDMI

    def map_archive_extension(self: Self) -> str:
        return "gz"

    @property
    def map_data_parser(self: Self) -> RoidmiMapDataParser:
        return self._roidmi_map_data_parser

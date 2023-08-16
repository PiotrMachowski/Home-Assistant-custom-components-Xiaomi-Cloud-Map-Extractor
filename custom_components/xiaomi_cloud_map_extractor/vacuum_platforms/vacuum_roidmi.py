from vacuum_map_parser_roidmi.map_data_parser import RoidmiMapDataParser

from .vacuum_base import VacuumConfig
from .vacuum_v2 import XiaomiCloudVacuumV2


class RoidmiCloudVacuum(XiaomiCloudVacuumV2):

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._roidmi_map_data_parser = RoidmiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    def map_archive_extension(self) -> str:
        return "gz"

    @property
    def map_data_parser(self) -> RoidmiMapDataParser:
        return self._roidmi_map_data_parser

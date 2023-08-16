from vacuum_map_parser_viomi.map_data_parser import ViomiMapDataParser

from .vacuum_base import VacuumConfig
from .vacuum_v2 import XiaomiCloudVacuumV2


class ViomiCloudVacuum(XiaomiCloudVacuumV2):

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._viomi_map_data_parser = ViomiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @property
    def map_archive_extension(self) -> str:
        return "zlib"

    @property
    def map_data_parser(self) -> ViomiMapDataParser:
        return self._viomi_map_data_parser

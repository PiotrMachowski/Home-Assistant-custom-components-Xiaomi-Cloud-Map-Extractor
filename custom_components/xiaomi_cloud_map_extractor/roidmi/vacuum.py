import gzip

from ..common.map_data import MapData
from ..common.vacuum_v2 import XiaomiCloudVacuumV2
from .map_data_parser import MapDataParserRoidmi


class RoidmiVacuum(XiaomiCloudVacuumV2):

    def __init__(self, connector, country, user_id, device_id, model):
        super().__init__(connector, country, user_id, device_id, model)

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config) -> MapData:
        unzipped = gzip.decompress(raw_map)
        return MapDataParserRoidmi.parse(unzipped, colors, drawables, texts, sizes, image_config)

    def get_map_archive_extension(self):
        return "gz"

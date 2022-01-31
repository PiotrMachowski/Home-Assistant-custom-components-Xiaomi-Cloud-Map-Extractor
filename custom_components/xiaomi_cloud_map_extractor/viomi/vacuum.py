import zlib

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.vacuum_v2 import XiaomiCloudVacuumV2
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, ImageConfig, Sizes, Texts
from custom_components.xiaomi_cloud_map_extractor.viomi.map_data_parser import MapDataParserViomi


class ViomiVacuum(XiaomiCloudVacuumV2):

    def __init__(self, connector, country, user_id, device_id, model):
        super().__init__(connector, country, user_id, device_id, model)

    def decode_map(self,
                   raw_map: bytes,
                   colors: Colors,
                   drawables: Drawables,
                   texts: Texts,
                   sizes: Sizes,
                   image_config: ImageConfig) -> MapData:
        unzipped = zlib.decompress(raw_map)
        return MapDataParserViomi.parse(unzipped, colors, drawables, texts, sizes, image_config)

    def get_map_archive_extension(self) -> str:
        return "zlib"

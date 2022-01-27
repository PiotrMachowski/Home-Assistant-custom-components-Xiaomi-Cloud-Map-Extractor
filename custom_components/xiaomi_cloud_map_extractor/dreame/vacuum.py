from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.vacuum_v2 import XiaomiCloudVacuumV2
from custom_components.xiaomi_cloud_map_extractor.dreame.map_data_parser import MapDataParserDreame

class DreameVacuum(XiaomiCloudVacuumV2):

    def __init__(self, connector, country, user_id, device_id, model):
        super().__init__(connector, country, user_id, device_id, model)

    def get_map_archive_extension(self):
        return "b64"

    def decode_map(self, raw_map: bytes, colors, drawables, texts, sizes, image_config) -> MapData:
        # with open('/config/frozen_map_data_dreame.vacuum.p2008.b64', 'rb') as f:
        #     raw_map_file = f.read()
        #     raw_map_string = raw_map_file.decode()
        #     return MapDataParserDreame.decode_map(raw_map_string, colors, drawables, texts, sizes, image_config)
        raw_map_string = raw_map.decode()
        return MapDataParserDreame.decode_map(raw_map_string, colors, drawables, texts, sizes, image_config)

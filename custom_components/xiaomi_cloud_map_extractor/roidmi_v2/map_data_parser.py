import json

from custom_components.xiaomi_cloud_map_extractor.roidmi.map_data_parser import MapDataParserRoidmi


class MapDataParserRoidmiV2(MapDataParserRoidmi):

    @staticmethod
    def split_raw(raw: bytes):
        # bitmap pixels are only 0..9 / 127 / 255, so '{"' uniquely marks the JSON tail
        map_info_start = raw.find(b'{"')
        map_info = json.loads(raw[map_info_start:])
        width = map_info["width"]
        height = map_info["height"]
        return raw[map_info_start - width * height:map_info_start], map_info

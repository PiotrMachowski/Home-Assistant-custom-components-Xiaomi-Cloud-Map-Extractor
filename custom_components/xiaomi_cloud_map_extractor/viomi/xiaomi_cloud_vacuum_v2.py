import zlib

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.xiaomi_cloud_vacuum import XiaomiCloudVacuum
from custom_components.xiaomi_cloud_map_extractor.viomi.map_data_parser_v2 import MapDataParserV2


class XiaomiCloudVacuumV2(XiaomiCloudVacuum):

    def __init__(self, connector, country, user_id, device_id, model):
        super().__init__(connector, country, user_id, device_id, model)

    def get_map_url(self, map_name):
        url = self._connector.get_api_url(self._country) + '/v2/home/get_interim_file_url'
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = self._connector.execute_api_call(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config) -> MapData:
        unzipped = zlib.decompress(raw_map)
        return MapDataParserV2.parse(unzipped, colors, drawables, texts, sizes, image_config)

    def should_get_map_from_vacuum(self):
        return False

    def get_map_archive_extension(self):
        return "zlib"

import gzip
from typing import Optional

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.roidmi.vacuum import RoidmiVacuum
from custom_components.xiaomi_cloud_map_extractor.roidmi_v2.map_data_parser import MapDataParserRoidmiV2
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, ImageConfig, Sizes, Texts


class RoidmiVacuumV2(RoidmiVacuum):

    def get_map_url(self, map_name: str) -> Optional[str]:
        url = self._connector.get_api_url(self._country) + '/v2/home/get_interim_file_url_pro'
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = self._connector.execute_api_call_encrypted(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

    def decode_map(self,
                   raw_map: bytes,
                   colors: Colors,
                   drawables: Drawables,
                   texts: Texts,
                   sizes: Sizes,
                   image_config: ImageConfig) -> MapData:
        unzipped = gzip.decompress(raw_map)
        return MapDataParserRoidmiV2.parse(unzipped, colors, drawables, texts, sizes, image_config)

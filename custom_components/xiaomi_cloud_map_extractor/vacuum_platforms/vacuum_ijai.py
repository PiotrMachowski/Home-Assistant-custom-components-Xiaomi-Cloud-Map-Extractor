import zlib

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.vacuum_v2 import XiaomiCloudVacuumV2
from custom_components.xiaomi_cloud_map_extractor.common.xiaomi_cloud_connector import XiaomiCloudConnector
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, ImageConfig, Sizes, Texts
from custom_components.xiaomi_cloud_map_extractor.ijai.map_data_parser import MapDataParserIjai
from custom_components.xiaomi_cloud_map_extractor.ijai.aes_decryptor import *

class IjaiCloudVacuum(XiaomiCloudVacuumV2):

    def __init__(self, connector: XiaomiCloudConnector, country: str, user_id: str, device_id: str, model: str, mac:str):
        super().__init__(connector, country, user_id, device_id, model, mac)

    def get_map_url(self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._country) + '/v2/home/get_interim_file_url/pro'

    def decode_map(self,
                   raw_map: bytes,
                   colors: Colors,
                   drawables: Drawables,
                   texts: Texts,
                   sizes: Sizes,
                   image_config: ImageConfig) -> MapData:
        
        unzipped = zlib.decompress(raw_map)

        return MapDataParserIjai.parse(unzipped, colors, drawables, texts, sizes, image_config)

    def get_map_archive_extension(self) -> str:
        return "zlib"

    def decrypt_map(self, data:bytes, wifi_info_sn:str, user_id:str, device_id:str, model:str, mac:str):
        return unGzipCommon(data=data, \
                            wifi_info_sn=wifi_info_sn, \
                            owner_id=str(user_id), \
                            device_id=device_id, \
                            model=model, \
                            device_mac=mac);
import io
from typing import Optional

import PIL
from PIL.Image import Image
from custom_components.xiaomi_cloud_map_extractor.valetudo.map_data_parser import MapDataParserValetudo

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.vacuum_v2 import XiaomiCloudVacuumV2
from custom_components.xiaomi_cloud_map_extractor.common.xiaomi_cloud_connector import Connector
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, ImageConfig, Sizes, Texts


class ValetudoVacuum(XiaomiCloudVacuumV2):

    def __init__(self, connector: Connector, country: str, user_id: str, device_id: str, model: str):
        super().__init__(connector, country, user_id, device_id, model)

    def get_map_archive_extension(self) -> str:
        return "json"

    def get_map_url(self, map_name: str) -> Optional[str]:
        return ""

    def decode_map(self, raw_map: bytes, colors: Colors, drawables: Drawables, texts: Texts, sizes: Sizes,
                   image_config: ImageConfig) -> MapData:
        image = PIL.Image.open(io.BytesIO(raw_map))
        image.load()

        raw_map_string = image.info["ValetudoMap"]
        return MapDataParserValetudo.decode_map(raw_map_string, colors, drawables, texts, sizes, image_config)

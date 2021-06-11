from typing import Optional

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.vacuum_v2 import XiaomiCloudVacuumV2


class DreameVacuum(XiaomiCloudVacuumV2):

    def __init__(self, connector, country, user_id, device_id, model):
        super().__init__(connector, country, user_id, device_id, model)

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config) -> Optional[MapData]:
        return None

    def get_map_archive_extension(self):
        return "b64"

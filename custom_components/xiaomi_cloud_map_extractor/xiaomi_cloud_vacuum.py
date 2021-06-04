from abc import abstractmethod
from typing import Optional, Tuple

import xiaomi_cloud_vacuum_v1
import xiaomi_cloud_vacuum_v2
from .const import V2_MODELS
from .map_data import MapData


class XiaomiCloudVacuum:

    def __init__(self, connector, country, user_id, device_id, model):
        self._connector = connector
        self._country = country
        self._user_id = user_id
        self._device_id = device_id
        self._model = model

    def get_map(self, map_name, colors, drawables, texts, sizes, image_config, store_response=False) \
            -> Tuple[Optional[MapData], bool]:
        response = self.get_raw_map_data(map_name)
        if response is None:
            return None, False
        map_stored = False
        if store_response:
            file1 = open("/tmp/map_data.gz", "wb")
            file1.write(response)
            file1.close()
            map_stored = True
        map_data = self.decode_map(response, colors, drawables, texts, sizes, image_config)
        map_data.map_name = map_name
        return map_data, map_stored

    def get_raw_map_data(self, map_name) -> Optional[bytes]:
        if map_name is None:
            return None
        map_url = self.get_map_url(map_name)
        return self._connector.get_raw_map_data(map_url)

    @abstractmethod
    def get_map_url(self, map_name):
        pass

    @abstractmethod
    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config) -> MapData:
        pass

    @abstractmethod
    def should_get_map_from_vacuum(self):
        pass

    @staticmethod
    def create(connector, country, user_id, device_id, model):
        if model in V2_MODELS:
            return xiaomi_cloud_vacuum_v2.XiaomiCloudVacuumV2(connector, country, user_id, device_id, model)
        return xiaomi_cloud_vacuum_v1.XiaomiCloudVacuumV1(connector, country, user_id, device_id, model)

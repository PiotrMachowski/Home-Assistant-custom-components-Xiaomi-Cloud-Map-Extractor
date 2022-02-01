from abc import abstractmethod
from typing import Optional, Tuple

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.common.map_data_parser import MapDataParser
from custom_components.xiaomi_cloud_map_extractor.common.xiaomi_cloud_connector import XiaomiCloudConnector
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, ImageConfig, Sizes, Texts


class XiaomiCloudVacuum:

    def __init__(self, connector: XiaomiCloudConnector, country: str, user_id: str, device_id: str, model: str):
        self._connector = connector
        self._country = country
        self._user_id = user_id
        self._device_id = device_id
        self.model = model

    def get_map(self,
                map_name: str,
                colors: Colors,
                drawables: Drawables,
                texts: Texts,
                sizes: Sizes,
                image_config: ImageConfig,
                store_map_path: Optional[str] = None) -> Tuple[Optional[MapData], bool]:
        response = self.get_raw_map_data(map_name)
        if response is None:
            return None, False
        map_stored = False
        if store_map_path is not None:
            raw_map_file = open(f"{store_map_path}/map_data_{self.model}.{self.get_map_archive_extension()}", "wb")
            raw_map_file.write(response)
            raw_map_file.close()
            map_stored = True
        map_data = self.decode_map(response, colors, drawables, texts, sizes, image_config)
        if map_data is None:
            return None, map_stored
        map_data.map_name = map_name
        return map_data, map_stored

    def get_raw_map_data(self, map_name: Optional[str]) -> Optional[bytes]:
        if map_name is None:
            return None
        map_url = self.get_map_url(map_name)
        return self._connector.get_raw_map_data(map_url)

    def decode_map(self,
                   raw_map: bytes,
                   colors: Colors,
                   drawables: Drawables,
                   texts: Texts,
                   sizes: Sizes,
                   image_config: ImageConfig) -> Optional[MapData]:
        return MapDataParser.create_empty(colors, f"Vacuum\n{self.model}\nis not supported")

    @abstractmethod
    def get_map_url(self, map_name: str) -> Optional[str]:
        pass

    @abstractmethod
    def should_get_map_from_vacuum(self) -> bool:
        pass

    def get_map_archive_extension(self) -> str:
        pass

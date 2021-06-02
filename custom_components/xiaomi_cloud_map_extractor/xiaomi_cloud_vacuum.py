from abc import abstractmethod
import gzip
import zlib

from .map_data_parser import MapDataParser, ViomiMapDataParser
from .const import V2_MODELS


class XiaomiCloudVacuum:

    def __init__(self, connector, country, user_id, device_id, model):
        self._connector = connector
        self._country = country
        self._user_id = user_id
        self._device_id = device_id
        self._model = model

    def get_map(self, map_name, colors, drawables, texts, sizes, image_config, store_response=False):
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

    def get_raw_map_data(self, map_name):
        if map_name is None:
            return None
        map_url = self.get_map_url(map_name)
        return self._connector.get_raw_map_data(map_url)

    @abstractmethod
    def get_map_url(self, map_name):
        pass

    @abstractmethod
    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config):
        pass

    @abstractmethod
    def should_get_map_from_vacuum(self):
        pass

    @staticmethod
    def create(connector, country, user_id, device_id, model):
        if model in V2_MODELS:
            return XiaomiCloudVacuumV2(connector, country, user_id, device_id, model)
        return XiaomiCloudVacuumV1(connector, country, user_id, device_id, model)


class XiaomiCloudVacuumV1(XiaomiCloudVacuum):

    def __init__(self, connector, country, user_id, device_id, model):
        super().__init__(connector, country, user_id, device_id, model)

    def get_map_url(self, map_name):
        url = self._connector.get_api_url(self._country) + "/home/getmapfileurl"
        params = {
            "data": '{"obj_name":"' + map_name + '"}'
        }
        api_response = self._connector.execute_api_call(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config):
        unzipped = gzip.decompress(raw_map)
        return MapDataParser.parse(unzipped, colors, drawables, texts, sizes, image_config)

    def should_get_map_from_vacuum(self):
        return True


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

    def decode_map(self, raw_map, colors, drawables, texts, sizes, image_config):
        unzipped = zlib.decompress(raw_map)
        return ViomiMapDataParser.parse(unzipped, colors, drawables, texts, sizes, image_config)

    def should_get_map_from_vacuum(self):
        return False

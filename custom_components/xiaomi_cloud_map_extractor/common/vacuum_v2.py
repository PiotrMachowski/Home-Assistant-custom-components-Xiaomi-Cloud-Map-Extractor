from __future__ import annotations

from custom_components.xiaomi_cloud_map_extractor.common.vacuum import XiaomiCloudVacuum
from custom_components.xiaomi_cloud_map_extractor.common.xiaomi_cloud_connector import XiaomiCloudConnector


class XiaomiCloudVacuumV2(XiaomiCloudVacuum):

    def __init__(self, connector: XiaomiCloudConnector, country: str, user_id: str, device_id: str, model: str):
        super().__init__(connector, country, user_id, device_id, model)

    def get_map_url(self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._country) + '/v2/home/get_interim_file_url'
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = self._connector.execute_api_call_encrypted(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

    def should_get_map_from_vacuum(self) -> bool:
        return False

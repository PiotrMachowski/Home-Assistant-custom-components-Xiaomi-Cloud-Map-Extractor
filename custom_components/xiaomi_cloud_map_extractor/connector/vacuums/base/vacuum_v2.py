from abc import ABC
from typing import Self

from .vacuum_base import BaseXiaomiCloudVacuum


class BaseXiaomiCloudVacuumV2(BaseXiaomiCloudVacuum, ABC):

    async def get_map_url(self: Self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._server) + '/v2/home/get_interim_file_url'
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = await self._connector.execute_api_call_encrypted(url, params)
        if api_response is None or "result" not in api_response or "url" not in api_response["result"]:
            return None
        return api_response["result"]["url"]

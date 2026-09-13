from abc import ABC
import logging
from typing import Self, Any

from .vacuum_base import BaseXiaomiCloudVacuum, VacuumConfig
from ...utils.dict_operations import path_extractor

_LOGGER = logging.getLogger(__name__)


class BaseXiaomiCloudVacuumV2(BaseXiaomiCloudVacuum, ABC):
    last_used_url: str | None = None

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        super().__init__(vacuum_config)
        self.last_used_url = None

    async def get_map_url(self: Self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._server) + '/v2/home/get_interim_file_url'
        self.last_used_url = url
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = await self._connector.execute_api_call_encrypted(url, params)
        url = path_extractor(api_response, "result.url")
        if url is None:
            _LOGGER.warning(
                "Primary Xiaomi map URL response did not include result.url: code=%s message=%s",
                path_extractor(api_response, "code"),
                path_extractor(api_response, "message"),
            )
            return await self.get_fallback_map_url(map_name)
        return url

    async def get_fallback_map_url(self: Self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._server) + '/v2/home/get_interim_file_url_pro'
        self.last_used_url = url
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = await self._connector.execute_api_call_encrypted(url, params)
        url = path_extractor(api_response, "result.url")
        if url is None:
            _LOGGER.warning(
                "Fallback Xiaomi map URL response did not include result.url: code=%s message=%s",
                path_extractor(api_response, "code"),
                path_extractor(api_response, "message"),
            )
        return url

    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        return {**super_data, "last_used_url": self.last_used_url}

import asyncio
import logging
from typing import Self

from vacuum_map_parser_viomi.map_data_parser import ViomiMapDataParser
from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2

_LOGGER = logging.getLogger(__name__)

# Viomi vacuums do not keep a map in the cloud. They upload the current map only
# when asked to via the `set_uploadmap` miio command; the uploaded map then
# becomes available as cloud object "1". Without this request the cloud object
# does not exist and the map download fails with "Object Not Found".
_UPLOAD_MAP_METHOD = "set_uploadmap"
_UPLOAD_MAP_PARAMS = [1]
_VIOMI_MAP_NAME = "1"
_MAP_UPLOAD_DELAY = 3


class ViomiCloudVacuum(BaseXiaomiCloudVacuumV2):
    _viomi_map_data_parser: ViomiMapDataParser

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        super().__init__(vacuum_config)
        self._viomi_map_data_parser = ViomiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.VIOMI

    @property
    def map_archive_extension(self: Self) -> str:
        return "zlib"

    @property
    def map_data_parser(self: Self) -> ViomiMapDataParser:
        return self._viomi_map_data_parser

    async def get_map_name(self: Self) -> str | None:
        _LOGGER.debug("Requesting viomi map upload via cloud RPC")
        response = await self._connector.get_other_info(
            self._device_id, _UPLOAD_MAP_METHOD, _UPLOAD_MAP_PARAMS)
        if response is None or response.get("code") != 0:
            _LOGGER.warning("Viomi map upload request was not acknowledged: %s", response)
            return None
        await asyncio.sleep(_MAP_UPLOAD_DELAY)
        return _VIOMI_MAP_NAME

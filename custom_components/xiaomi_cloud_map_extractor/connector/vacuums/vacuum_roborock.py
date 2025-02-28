import logging
from typing import Self

from miio import RoborockVacuum, DeviceException

from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser
from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_base import BaseXiaomiCloudVacuum
from ..utils.backoff import Backoff
from ..utils.exceptions import InvalidDeviceTokenException

_LOGGER = logging.getLogger(__name__)

MISSING_MAP_VALUE = "retry"
OFF_UPDATES = 3


class RoborockCloudVacuum(BaseXiaomiCloudVacuum):
    _roborock_map_data_parser: RoborockMapDataParser
    _vacuum: RoborockVacuum
    _backoff: Backoff
    _off_counter: int

    def __init__(self: Self, vacuum_config: VacuumConfig) -> None:
        super().__init__(vacuum_config)
        self._roborock_map_data_parser = RoborockMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )
        self._vacuum = RoborockVacuum(vacuum_config.host, vacuum_config.token)
        self._backoff = Backoff(0.2, 15)
        self._off_counter = 0

    async def get_map_url(self: Self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._server) + "/home/getmapfileurl"
        params = {
            "data": '{"obj_name":"' + map_name + '"}'
        }
        api_response = await self._connector.execute_api_call_encrypted(url, params)
        if (
                api_response is None
                or "result" not in api_response
                or api_response["result"] is None
                or "url" not in api_response["result"]):
            return None
        return api_response["result"]["url"]

    @property
    def should_update_map(self: Self) -> bool:
        try:
            code = self._vacuum.status().state_code
            _LOGGER.debug("Vacuum status: %d", code)
            is_moving = code in [
                1,  # Starting
                4,  # Remote control active
                5,  # Cleaning
                6,  # Returning home
                7,  # Manual mode
                11,  # Spot cleaning
                15,  # Docking
                16,  # Going to target
                17,  # Zoned cleaning
                18,  # Segment cleaning
                26,  # Going to wash the mop
            ]
            if is_moving:
                self._off_counter = 0
                _LOGGER.debug("Vacuum is moving. Updating map.")
                return True
            else:
                self._off_counter += 1
                _LOGGER.debug("Vacuum is not moving. Off counter: %d", self._off_counter)
                return self._off_counter <= OFF_UPDATES

        except DeviceException as de:
            if "token" in repr(de):
                raise InvalidDeviceTokenException()
            return False

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.ROBOROCK

    @property
    def map_archive_extension(self: Self) -> str:
        return "gz"

    @property
    def map_data_parser(self: Self) -> RoborockMapDataParser:
        return self._roborock_map_data_parser

    async def get_map_name(self: Self) -> str:
        map_name = MISSING_MAP_VALUE
        self._backoff.reset()
        remaining_attempts = 10
        while map_name == MISSING_MAP_VALUE and remaining_attempts > 0:
            _LOGGER.debug("Retrieving map name from device, remaining_attempts: %d", remaining_attempts)
            try:
                map_name = self._vacuum.map()[0]  # todo async
                _LOGGER.debug("Map name %s", map_name)
                if map_name != MISSING_MAP_VALUE:
                    return map_name
            except OSError as exc:
                _LOGGER.warning("Got OSError while fetching the state: %s", exc)
            except DeviceException as exc:
                _LOGGER.warning("Got exception while fetching the state: %s", exc)
            finally:
                remaining_attempts = remaining_attempts - 1
                await self._backoff.sleep()
        return map_name

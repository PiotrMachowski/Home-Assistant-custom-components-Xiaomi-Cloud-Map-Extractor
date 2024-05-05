import logging
import time

from miio import RoborockVacuum, DeviceException
from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

from .vacuum_base import VacuumConfig, XiaomiCloudVacuum

_LOGGER = logging.getLogger(__name__)


class RoborockCloudVacuum(XiaomiCloudVacuum):

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._roborock_map_data_parser = RoborockMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )
        self._vacuum = RoborockVacuum(vacuum_config.host, vacuum_config.token)

    def get_map_url(self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._country) + "/home/getmapfileurl"
        params = {
            "data": '{"obj_name":"' + map_name + '"}'
        }
        api_response = self._connector.execute_api_call_encrypted(url, params)
        if (api_response is None or "result" not in api_response or api_response["result"] is None or "url" not in api_response["result"]):
            return None
        return api_response["result"]["url"]

    @property
    def should_get_map_from_vacuum(self) -> bool:
        return True

    @property
    def should_update_map(self) -> bool:
        return self._vacuum.status().state_code not in [
            2,  # Charger disconnected
            3,  # Idle
            8,  # Charging
            9,  # Charging problem
            13,  # Shutting down
            14,  # Updating
            100,  # Charging complete
            101,  # Device offline
        ]

    @property
    def map_archive_extension(self) -> str:
        return "gz"

    @property
    def map_data_parser(self) -> RoborockMapDataParser:
        return self._roborock_map_data_parser

    def get_map_name(self) -> str:
        map_name = "retry"
        counter = 10
        while map_name == "retry" and counter > 0:
            _LOGGER.debug("Retrieving map name from device")
            time.sleep(0.1)
            try:
                map_name = self._vacuum.map()[0]
                _LOGGER.debug("Map name %s", map_name)
            except OSError as exc:
                _LOGGER.error("Got OSError while fetching the state: %s", exc)
            except DeviceException as exc:
                _LOGGER.warning("Got exception while fetching the state: %s", exc)
            finally:
                counter = counter - 1
        return map_name

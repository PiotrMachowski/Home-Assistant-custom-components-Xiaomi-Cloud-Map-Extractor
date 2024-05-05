
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser
from miio.miot_device import MiotDevice

from .vacuum_v2 import XiaomiCloudVacuumV2
from .vacuum_base import VacuumConfig
import logging
_LOGGER = logging.getLogger(__name__)

class IjaiCloudVacuum(XiaomiCloudVacuumV2):
    WIFI_STR_LEN = 18
    WIFI_STR_POS = 11

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._token = vacuum_config.token
        self._host = vacuum_config.host
        self._mac = vacuum_config._mac
        self._wifi_info_sn = None

        self._ijai_map_data_parser = IjaiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

    @property
    def map_archive_extension(self) -> str:
        return "zlib"

    @property
    def map_data_parser(self) -> IjaiMapDataParser:
        return self._ijai_map_data_parser

    def get_map_url(self, map_name: str) -> str | None:
        url = self._connector.get_api_url(self._country) + '/v2/home/get_interim_file_url_pro'
        params = {
            "data": f'{{"obj_name":"{self._user_id}/{self._device_id}/{map_name}"}}'
        }
        api_response = self._connector.execute_api_call_encrypted(url, params)
        if api_response is None or ("result" not in api_response) or (api_response["result"] is None) or ("url" not in api_response["result"]):
            self._LOGGER.debug(f"API returned {api_response['code']}" + "(" + api_response["message"] + ")")
            return None
        return api_response["result"]["url"]

    def decode_and_parse(self, raw_map: bytes):
        if self._wifi_info_sn is None or self._wifi_info_sn == "":
            device = MiotDevice(self._host, self._token)
            props = device.get_property_by(7, 45)[0]["value"].split(',')
            self._wifi_info_sn = props[self.WIFI_STR_POS].replace('"', '')[:self.WIFI_STR_LEN]
            _LOGGER.debug(f"wifi_sn = {self._wifi_info_sn}")

        decoded_map = self.map_data_parser.unpack_map(
            raw_map,
            wifi_sn=self._wifi_info_sn,
            owner_id=str(self._user_id),
            device_id=str(self._device_id),
            model=self.model,
            device_mac=self._mac)
        return self.map_data_parser.parse(decoded_map)

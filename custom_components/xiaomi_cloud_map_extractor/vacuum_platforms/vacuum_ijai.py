
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser
from miio.miot_device import MiotDevice

from .vacuum_v2 import XiaomiCloudVacuumV2
from .vacuum_base import VacuumConfig
import logging
_LOGGER = logging.getLogger(__name__)

class IjaiCloudVacuum(XiaomiCloudVacuumV2):
    WIFI_STR_LEN = 18

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

    def get_wifi_info_sn(self):
        device = MiotDevice(self._host, self._token)

        wifi_info_sn = None

        # aggressivly searching for Serial Number in first siid
        # 1,3 on 2019 - 2021 vacuums; 1,5 on 2022 and newer vacuums
        piids = [3, 5]

        for piid in piids:
            data = device.get_property_by(1, piid)
            if "value" in data[0] and (len(data[0]["value"]) == self.WIFI_STR_LEN and data[0]["value"].isalnum() and data[0]["value"].isupper()):
                wifi_info_sn = data[0]["value"]
                break

        if not wifi_info_sn:
            # property 7, 45 (sweep -> multi-prop-vacuum) on all miot vacuums
            got_from_vacuum = device.get_property_by(7, 45)

            for prop in got_from_vacuum[0]["value"].split(','):
                cleaned_prop = str(prop).replace('"', '')

                if str(self._user_id) in cleaned_prop:
                    cleaned_prop = cleaned_prop.split(';')[0]

                if len(cleaned_prop) == self.WIFI_STR_LEN and cleaned_prop.isalnum() and cleaned_prop.isupper():
                    wifi_info_sn = cleaned_prop
        return wifi_info_sn

    def decode_and_parse(self, raw_map: bytes):
        GET_PROP_RETRIES = 5
        if self._wifi_info_sn is None or self._wifi_info_sn == "":
            _LOGGER.debug(f"host={self._host}, token={self._token}")
            for _ in range(GET_PROP_RETRIES):
                try:
                    self._wifi_info_sn = self.get_wifi_info_sn()
                    _LOGGER.debug(f"wifi_sn = {self._wifi_info_sn}")
                    break
                except:
                    _LOGGER.warn("Failed to get wifi_sn from vacuum")

        decoded_map = self.map_data_parser.unpack_map(
            raw_map,
            wifi_sn=self._wifi_info_sn,
            owner_id=str(self._user_id),
            device_id=str(self._device_id),
            model=self.model,
            device_mac=self._mac)
        return self.map_data_parser.parse(decoded_map)

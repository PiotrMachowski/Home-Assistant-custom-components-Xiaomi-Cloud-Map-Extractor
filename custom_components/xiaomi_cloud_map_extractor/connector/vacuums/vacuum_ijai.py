import logging
import json
from typing import Self, Any
from homeassistant.const import Platform

from miio.miot_device import MiotDevice
from miio.exceptions import DeviceException
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser
from vacuum_map_parser_ijai.status_mapping import get_status_mapping
from vacuum_map_parser_ijai.aes_decryptor import gen_md5_key

from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2
from .base.model import VacuumConfig, VacuumApi
from ..utils.exceptions import FailedConnectionException

_LOGGER = logging.getLogger(__name__)
OFF_UPDATES = 3


class IjaiCloudVacuum(BaseXiaomiCloudVacuumV2):
    WIFI_INFO_SN_POSSIBLE_LEN = [18, 20]

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._token = vacuum_config.token
        self._host = vacuum_config.host
        self._mac = vacuum_config.device_info.mac
        self._wifi_info_sn = None

        self._miot_device = MiotDevice(self._host, self._token, timeout=2)

        self._ijai_map_data_parser = IjaiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

        self._status_mapping = get_status_mapping(self.model)
        self._off_counter = 0

    @property
    def should_update_map(self: Self) -> bool:
        try:
            status_value = self.get_status_from_miot_state()
            if status_value is None:
                status_value = self._miot_device.get_property_by(self._status_mapping.siid,
                                                                 self._status_mapping.piid)[0]["value"]

            if status_value in self._status_mapping.idle_at:
                self._off_counter += 1
                _LOGGER.debug(
                    "Vacuum is not moving. Off counter: %d", self._off_counter)
                return self._off_counter <= OFF_UPDATES
            else:
                self._off_counter = 0
                return True
        except DeviceException as de:
            if "token" not in repr(de):
                _LOGGER.debug("Local vacuum status check failed; trying cloud map update anyway.", exc_info=de)
                return True
            raise FailedConnectionException(de)

    def get_status_from_miot_state(self) -> int | None:
        entity_id = self.get_xiaomi_miot_entity_id()
        if self._hass is None or entity_id is None:
            return None
        state = self._hass.states.get(entity_id)
        if state is None:
            return None
        status_value = state.attributes.get("vacuum.status")
        return status_value if isinstance(status_value, int) else None

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.IJAI

    @property
    def map_archive_extension(self) -> str:
        return "zlib.enc"

    @property
    def map_data_parser(self) -> IjaiMapDataParser:
        return self._ijai_map_data_parser

    async def get_map_url(self, map_name: str) -> str | None:
        return await self.get_fallback_map_url(map_name)

    async def get_fallback_map_url(self: Self, map_name: str) -> str | None:
        api_response = await self.request_xiaomi_miot_api(
            "v2/home/get_interim_file_url_pro",
            {"obj_name": f"{self._user_id}/{self._device_id}/{map_name}"}
        )
        if (api_response or {}).get("result", {}).get("url"):
            return api_response["result"]["url"]
        return await super().get_fallback_map_url(map_name)

    async def get_map(self):
        if self._wifi_info_sn is None or self._wifi_info_sn == "":
            try:
                self._wifi_info_sn = await self.get_cloud_wifi_info_sn()
                if self._wifi_info_sn:
                    _LOGGER.debug("Got wifi_sn from Xiaomi cloud")
            except Exception:
                _LOGGER.debug("Failed to get wifi_sn from Xiaomi cloud", exc_info=True)
        return await super().get_map()

    async def get_cloud_wifi_info_sn(self) -> str | None:
        if (wifi_info_sn := self.get_wifi_info_sn_from_miot_state()) is not None:
            return wifi_info_sn

        response = await self.request_xiaomi_miot_api(
            "miotspec/prop/get",
            {
                "params": [
                    {"did": str(self._device_id), "siid": 1, "piid": 3},
                    {"did": str(self._device_id), "siid": 1, "piid": 5},
                    {"did": str(self._device_id), "siid": 7, "piid": 45},
                ]
            }
        )
        if (wifi_info_sn := self.extract_wifi_info_sn_from_items((response or {}).get("result", []))) is not None:
            return wifi_info_sn

        url = self._connector.get_api_url(self._server) + '/miotspec/prop/get'
        params = {
            "data": json.dumps({
                "params": [
                    {"did": str(self._device_id), "siid": 1, "piid": 3},
                    {"did": str(self._device_id), "siid": 1, "piid": 5},
                    {"did": str(self._device_id), "siid": 7, "piid": 45},
                ]
            }, separators=(",", ":"))
        }
        response = await self._connector.execute_api_call_encrypted(url, params)
        return self.extract_wifi_info_sn_from_items((response or {}).get("result", []))

    def get_wifi_info_sn_from_miot_state(self) -> str | None:
        entity_id = self.get_xiaomi_miot_entity_id()
        if self._hass is None or entity_id is None:
            return None
        state = self._hass.states.get(entity_id)
        if state is None:
            return None
        value = state.attributes.get("sweep.multi_prop_vacuum")
        return self.extract_wifi_info_sn_from_items([{"value": value}])

    def extract_wifi_info_sn_from_items(self, items: list[dict[str, Any]]) -> str | None:
        for item in items:
            value = item.get("value")
            if isinstance(value, str) and self.is_wifi_info_sn(value):
                return value
            if not isinstance(value, str):
                continue
            for prop in value.split(','):
                cleaned_prop = str(prop).replace('"', '')
                if str(self._user_id) in cleaned_prop:
                    cleaned_prop = cleaned_prop.split(';')[0]
                if self.is_wifi_info_sn(cleaned_prop):
                    return cleaned_prop
        return None

    async def request_xiaomi_miot_api(self, api: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if self._hass is None:
            return None
        entity_id = self.get_xiaomi_miot_entity_id()
        if entity_id is None:
            return None
        try:
            response = await self._hass.services.async_call(
                "xiaomi_miot",
                "request_xiaomi_api",
                {
                    "entity_id": entity_id,
                    "api": api,
                    "data": data,
                    "method": "POST",
                    "crypt": True,
                },
                blocking=True,
                return_response=True,
            )
        except Exception:
            _LOGGER.debug("Xiaomi MIOT service fallback failed", exc_info=True)
            return None
        return response if isinstance(response, dict) else None

    def get_xiaomi_miot_entity_id(self) -> str | None:
        if self._hass is None:
            return None
        mac_suffix = (self._mac or "").replace(":", "").lower()[-4:]
        model_suffix = self.model.split(".")[-1].lower()
        candidates = []
        for state in self._hass.states.async_all(Platform.VACUUM):
            entity_id = state.entity_id.lower()
            if model_suffix in entity_id and mac_suffix and mac_suffix in entity_id:
                return state.entity_id
            if state.attributes.get("sweep.multi_prop_vacuum") is not None:
                candidates.append(state.entity_id)
        if len(candidates) == 1:
            return candidates[0]
        return None

    def is_wifi_info_sn(self, value: str) -> bool:
        return (
            len(value) in self.WIFI_INFO_SN_POSSIBLE_LEN
            and value.isalnum()
            and value.isupper()
        )

    def get_wifi_info_sn(self):
        wifi_info_sn = None

        # aggressively searching for Serial Number in first siid
        # 1,3 on 2019 - 2021 vacuums; 1,5 on 2022 and newer vacuums
        piids = [3, 5]

        for piid in piids:
            data = self._miot_device.get_property_by(1, piid)
            if (
                "value" in data[0]
                and self.is_wifi_info_sn(data[0]["value"])
            ):
                wifi_info_sn = data[0]["value"]
                break

        if not wifi_info_sn:
            # property 7, 45 (sweep -> multi-prop-vacuum) on all miot vacuums
            got_from_vacuum = self._miot_device.get_property_by(7, 45)

            for prop in got_from_vacuum[0]["value"].split(','):
                cleaned_prop = str(prop).replace('"', '')

                if str(self._user_id) in cleaned_prop:
                    cleaned_prop = cleaned_prop.split(';')[0]

                if (
                        cleaned_prop.isalnum()
                        and self.is_wifi_info_sn(cleaned_prop)):
                    wifi_info_sn = cleaned_prop
        return wifi_info_sn

    def decode_and_parse(self, raw_map: bytes) -> MapData:
        GET_PROP_RETRIES = 5
        if self._wifi_info_sn is None or self._wifi_info_sn == "":
            for _ in range(GET_PROP_RETRIES):
                try:
                    self._wifi_info_sn = self.get_wifi_info_sn()
                    _LOGGER.debug(f"Got wifi_sn {self._wifi_info_sn}")
                    break
                except Exception as ex:
                    _LOGGER.error("Failed to get wifi_sn from vacuum")
                    raise FailedConnectionException(ex)

        decoded_map = self.map_data_parser.unpack_map(
            raw_map,
            wifi_sn=self._wifi_info_sn,
            owner_id=str(self._user_id),
            device_id=str(self._device_id),
            model=self.model,
            device_mac=self._mac)
        return self.map_data_parser.parse(decoded_map)

    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        if self._wifi_info_sn is None:
            return super_data
        enc_key = gen_md5_key(self._wifi_info_sn, str(self._user_id), str(self._device_id), self.model, self._mac)
        return {**super_data, "enc_key": enc_key}

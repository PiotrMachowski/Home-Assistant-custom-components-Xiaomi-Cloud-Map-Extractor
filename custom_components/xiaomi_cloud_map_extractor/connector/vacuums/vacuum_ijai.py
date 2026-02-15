import logging
from typing import Self, Any

from miio.miot_device import MiotDevice
from miio.exceptions import DeviceException
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser
from vacuum_map_parser_ijai.status_mapping import get_status_mapping, is_K3_model
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
                return False
            raise FailedConnectionException(de)

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
        if is_K3_model(self.model):
            return await self.get_fallback_map_url(map_name)
        else:
            return await super().get_map_url(map_name)

    def get_wifi_info_sn(self):
        wifi_info_sn = None

        # aggressively searching for Serial Number in first siid
        # 1,3 on 2019 - 2021 vacuums; 1,5 on 2022 and newer vacuums
        piids = [3, 5]

        for piid in piids:
            data = self._miot_device.get_property_by(1, piid)
            if (
                "value" in data[0]
                and len(data[0]["value"]) in self.WIFI_INFO_SN_POSSIBLE_LEN
                and data[0]["value"].isupper()
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
                        len(cleaned_prop) in self.WIFI_INFO_SN_POSSIBLE_LEN
                        and cleaned_prop.isalnum()
                        and cleaned_prop.isupper()):
                    wifi_info_sn = cleaned_prop
        return wifi_info_sn

    def decode_and_parse(self, raw_map: bytes) -> MapData:
        GET_PROP_RETRIES = 5
        if self._wifi_info_sn is None or self._wifi_info_sn == "":
            _LOGGER.debug(f"host={self._host}, token={self._token}")
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

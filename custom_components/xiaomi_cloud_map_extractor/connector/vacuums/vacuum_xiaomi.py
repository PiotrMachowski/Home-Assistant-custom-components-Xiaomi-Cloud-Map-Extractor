import logging
import json
import base64
from typing import Self, Any

from miio.miot_device import MiotDevice
from miio.exceptions import DeviceException
from vacuum_map_parser_base.map_data import MapData
from .vacuum_map_parser_xiaomi.map_data_parser import XiaomiMapDataParser
from .vacuum_map_parser_xiaomi.status_mapping import get_status_mapping
from .vacuum_map_parser_xiaomi.aes_decryptor import gen_md5_key

from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2
from .base.model import VacuumConfig, VacuumApi
from ..utils.exceptions import FailedConnectionException

_LOGGER = logging.getLogger(__name__)
OFF_UPDATES = 3


class XiaomiCloudVacuum(BaseXiaomiCloudVacuumV2):
    WIFI_INFO_SN_LEN = 20

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._token = vacuum_config.token
        self._host = vacuum_config.host

        self._miot_device = MiotDevice(self._host, self._token, timeout=2)

        self._xiaomi_map_data_parser = XiaomiMapDataParser(
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
        return VacuumApi.XIAOMI

    @property
    def map_archive_extension(self) -> str:
        return "zlib.enc"

    @property
    def map_data_parser(self) -> XiaomiMapDataParser:
        return self._xiaomi_map_data_parser

    async def get_map_url(self, map_name: str) -> str | None:
        return await self.get_fallback_map_url(map_name)

    def decode_and_parse(self, raw_map: bytes) -> MapData:
                      
        raw_map= base64.decodebytes(json.loads(raw_map)["data"].encode('latin1'))
        raw_map=raw_map.hex()

        decoded_map = self.map_data_parser.unpack_map(
            raw_map,
            model=self.model.replace("xiaomi","mi"),
            device_id=str(self._device_id))
        return self.map_data_parser.parse(decoded_map)

    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        enc_key = gen_md5_key(self.model.replace("xiaomi","mi"),str(self._device_id))
        return {**super_data, "enc_key": enc_key}

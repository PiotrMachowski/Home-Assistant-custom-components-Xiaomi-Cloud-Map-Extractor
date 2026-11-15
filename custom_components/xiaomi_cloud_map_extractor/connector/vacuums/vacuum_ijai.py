import logging
import zlib
from typing import Self, Any

from miio.miot_device import MiotDevice
from miio.exceptions import DeviceException
from vacuum_map_parser_base.map_data import MapData, Room
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser
from vacuum_map_parser_ijai.status_mapping import get_status_mapping
from vacuum_map_parser_ijai.aes_decryptor import gen_md5_key

from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2
from .base.model import VacuumConfig, VacuumApi
from ..utils.exceptions import FailedConnectionException, FailedMapParseException

_LOGGER = logging.getLogger(__name__)
OFF_UPDATES = 3

# Some ijai vacuums (e.g. ijai.vacuum.v3) do not always encrypt the map with
# the cloud device id: the "device_id" part of the key can also be a small
# index ("0", "2", ...). These values are tried after the real device id.
MAP_KEY_FALLBACK_IDS = [str(i) for i in range(10)]
DECRYPT_ERRORS = (ValueError, zlib.error)


def _safe_parse_rooms(map_data_rooms: dict[int, Room]) -> None:
    # Workaround for vacuum_map_parser_ijai: live maps may not contain the
    # current map in mapInfo, which makes the original _parse_rooms fail with
    # UnboundLocalError ('current_map'). Room names are read anyway.
    robot_map = IjaiMapDataParser.robot_map
    map_id = robot_map.mapHead.mapHeadId
    current_map = next((m for m in robot_map.mapInfo if m.mapHeadId == map_id), None)
    if current_map is not None:
        _LOGGER.debug("map#%d: %s", current_map.mapHeadId, current_map.mapName)
    else:
        _LOGGER.debug("map#%d not found in mapInfo", map_id)
    for r in robot_map.roomDataInfo:
        if map_data_rooms is not None and r.roomId in map_data_rooms:
            map_data_rooms[r.roomId].name = r.roomName
            map_data_rooms[r.roomId].pos_x = r.roomNamePost.x
            map_data_rooms[r.roomId].pos_y = r.roomNamePost.y


IjaiMapDataParser._parse_rooms = staticmethod(_safe_parse_rooms)


class IjaiCloudVacuum(BaseXiaomiCloudVacuumV2):
    WIFI_INFO_SN_POSSIBLE_LEN = [18, 20]

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._token = vacuum_config.token
        self._host = vacuum_config.host
        self._mac = vacuum_config.device_info.mac
        self._wifi_info_sn = None
        self._map_encryption_device_id = str(self._device_id)

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
        return await self.get_fallback_map_url(map_name)

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

    def _map_key_ids(self) -> list[str]:
        # Last working id first, then the real device id, then the fallbacks.
        ids = [self._map_encryption_device_id, str(self._device_id), *MAP_KEY_FALLBACK_IDS]
        return list(dict.fromkeys(ids))

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

        kwargs = {
            "wifi_sn": self._wifi_info_sn,
            "owner_id": str(self._user_id),
            "model": self.model,
            "device_mac": self._mac,
        }
        last_err: Exception | None = None
        for key_id in self._map_key_ids():
            try:
                decoded_map = self.map_data_parser.unpack_map(raw_map, device_id=key_id, **kwargs)
            except DECRYPT_ERRORS as err:
                last_err = err
                continue
            if key_id != self._map_encryption_device_id:
                _LOGGER.debug("Map decrypted with key id %s", key_id)
            self._map_encryption_device_id = key_id
            return self.map_data_parser.parse(decoded_map)

        # Do not fail the whole update (entities would become unavailable):
        # report a parse failure so the connector keeps the last valid map.
        _LOGGER.warning(
            "Failed to decrypt map with any known key (%s), keeping last valid map", last_err)
        raise FailedMapParseException() from last_err

    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        if self._wifi_info_sn is None:
            return super_data
        enc_key = gen_md5_key(self._wifi_info_sn, str(self._user_id), self._map_encryption_device_id, self.model, self._mac)
        return {**super_data, "enc_key": enc_key}

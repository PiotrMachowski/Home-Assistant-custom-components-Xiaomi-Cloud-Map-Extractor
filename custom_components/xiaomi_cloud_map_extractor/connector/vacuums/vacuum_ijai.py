import asyncio
import logging
import time
import zlib
from typing import Self, Any

from miio.miot_device import MiotDevice
from miio.exceptions import DeviceException
from google.protobuf.message import DecodeError
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser
from vacuum_map_parser_ijai.status_mapping import get_status_mapping
from vacuum_map_parser_ijai.aes_decryptor import gen_md5_key

from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2
from .base.model import VacuumConfig, VacuumApi
from ..utils.exceptions import FailedConnectionException, FailedMapParseException
from ..utils.dict_operations import path_extractor

_LOGGER = logging.getLogger(__name__)
OFF_UPDATES = 3
# Ask the vacuum to (re)upload its current map to the cloud at most this often.
MAP_UPLOAD_REQUEST_INTERVAL = 30


class IjaiCloudVacuum(BaseXiaomiCloudVacuumV2):
    WIFI_INFO_SN_POSSIBLE_LEN = [18, 19, 20]

    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._token = vacuum_config.token
        self._host = vacuum_config.host
        self._mac = vacuum_config.device_info.mac
        self._wifi_info_sn = None
        self._last_upload_request = 0.0

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
        url = await self.get_fallback_map_url(map_name)
        if url is not None:
            return url
        # Some Ijai models (e.g. ijai.vacuum.v1, ijai.vacuum.v3) don't serve
        # maps through get_interim_file_url_pro; fall back to the standard endpoint.
        return await super().get_map_url(map_name)

    async def get_raw_map_data(self, map_name: str | None) -> bytes | None:
        if self._wifi_info_sn is None or self._wifi_info_sn == "":
            self._wifi_info_sn = await self._resolve_wifi_info_sn()
        await self._request_map_upload()
        return await super().get_raw_map_data(map_name)

    async def _request_map_upload(self) -> None:
        # The map object in the Xiaomi cloud is only refreshed when the vacuum
        # uploads it (e.g. while the Xiaomi Home map screen is open), so it can
        # be stale and fail to decrypt. Ask the vacuum for an upload first
        # (map service siid 10, upload-by-maptype, type 0 = real map).
        now = time.monotonic()
        if now - self._last_upload_request < MAP_UPLOAD_REQUEST_INTERVAL:
            return
        self._last_upload_request = now
        try:
            response = await self._connector.get_other_info(
                self._device_id, "action",
                parameters={"did": self._device_id, "siid": 10, "aiid": 6,
                            "in": [{"piid": 7, "value": 0}]},
            )
            if path_extractor(response, "result.code") == 0:
                await asyncio.sleep(2)
        except Exception as ex:
            _LOGGER.debug("Map upload request failed: %r", ex)

    async def _resolve_wifi_info_sn(self) -> str | None:
        # The local MiIO lookup requires the vacuum to be reachable on the
        # same network as Home Assistant. When it isn't (different site,
        # VLAN isolation, etc.), fall back to reading the same properties
        # through the Xiaomi cloud RPC relay instead.
        try:
            wifi_info_sn = self.get_wifi_info_sn()
            if wifi_info_sn:
                return wifi_info_sn
            _LOGGER.debug("Local wifi_sn lookup returned nothing, trying cloud")
        except Exception as ex:
            _LOGGER.debug("Local wifi_sn lookup failed (%r), trying cloud", ex)
        return await self._get_wifi_info_sn_cloud()

    async def _get_wifi_info_sn_cloud(self) -> str | None:
        piids = [3, 5]
        for piid in piids:
            value = await self._get_cloud_property(1, piid)
            if (
                value is not None
                and len(str(value)) in self.WIFI_INFO_SN_POSSIBLE_LEN
                and str(value).isupper()
            ):
                return str(value)

        value = await self._get_cloud_property(7, 45)
        if value:
            for prop in str(value).split(','):
                cleaned_prop = str(prop).replace('"', '')

                if str(self._user_id) in cleaned_prop:
                    cleaned_prop = cleaned_prop.split(';')[0]

                if (
                        len(cleaned_prop) in self.WIFI_INFO_SN_POSSIBLE_LEN
                        and cleaned_prop.isalnum()
                        and cleaned_prop.isupper()):
                    return cleaned_prop
        return None

    async def _get_cloud_property(self, siid: int, piid: int) -> Any:
        response = await self._connector.get_other_info(
            self._device_id, "get_properties",
            parameters=[{"did": self._device_id, "siid": siid, "piid": piid}],
        )
        return path_extractor(response, "result.0.value")

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
        if not self._wifi_info_sn:
            _LOGGER.error("Failed to get wifi_sn from vacuum (local and cloud)")
            raise FailedConnectionException(Exception("wifi_sn could not be resolved"))

        try:
            decoded_map = self.map_data_parser.unpack_map(
                raw_map,
                wifi_sn=self._wifi_info_sn,
                owner_id=str(self._user_id),
                device_id=str(self._device_id),
                model=self.model,
                device_mac=self._mac)
            return self.map_data_parser.parse(decoded_map)
        except (ValueError, zlib.error, DecodeError) as ex:
            # Typically a stale map object in the cloud; raising a known
            # exception lets the connector keep serving the last good map.
            _LOGGER.warning("Could not decode Ijai map (%r), keeping last map", ex)
            raise FailedMapParseException() from ex

    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        if self._wifi_info_sn is None:
            return super_data
        enc_key = gen_md5_key(self._wifi_info_sn, str(self._user_id), str(self._device_id), self.model, self._mac)
        return {**super_data, "enc_key": enc_key}

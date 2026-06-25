import base64
import json
import logging
from dataclasses import dataclass
from typing import Self, Any

from miio.exceptions import DeviceException
from miio.miot_device import MiotDevice
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_xiaomi.aes_decryptor import gen_md5_key
from vacuum_map_parser_xiaomi.map_data_parser import XiaomiMapDataParser
from vacuum_map_parser_xiaomi.status_mapping import XiaomiVacuumStatusMapping, get_status_mapping

from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2
from .xiaomi_miot_enrichment import (
    apply_json_map_calibration,
    apply_vacuum_room,
    merge_live_map_data,
    normalize_restricted_map_payload,
    normalize_json_map_payload,
    parse_vacuum_position_value,
)
from ..utils.dict_operations import path_extractor
from ..utils.exceptions import FailedConnectionException, FailedMapDownloadException, FailedMapParseException

_LOGGER = logging.getLogger(__name__)
OFF_UPDATES = 3

@dataclass
class XiaomiVacuumPropertyMapping:
    """Dataclass containing mapping for map property"""

    # vacuum map service id
    siid: int = 10

    # current map property id in vacuum map service
    piid: int = 1


@dataclass
class XiaomiVacuumLiveDataMapping:
    """Dataclass containing mapping for live map data properties."""

    # vacuum map service id
    siid: int

    # trajectory object name property id
    trajectory_piid: int

    # current vacuum position property id
    position_piid: int

    # restricted sweep areas service/property ids
    restricted_areas_siid: int | None = None
    restricted_areas_piid: int | None = None

    # restricted virtual walls service/property ids
    restricted_walls_siid: int | None = None
    restricted_walls_piid: int | None = None


_NON_STANDARD_MAP_PROP = [
    (
        [
            "xiaomi.vacuum.b108gl",
        ],
        XiaomiVacuumPropertyMapping(siid=7),
    ),
    (
        [
            "xiaomi.vacuum.b108gp",
            "xiaomi.vacuum.ov32gl",
            "xiaomi.vacuum.ov43gl",
            "xiaomi.vacuum.ov51",
            "xiaomi.vacuum.ov81",
        ],
        XiaomiVacuumPropertyMapping(siid=9),
    ),
    (
        [
            "xiaomi.vacuum.b106bk",
            "xiaomi.vacuum.b106tr",
            "xiaomi.vacuum.b112",
            "xiaomi.vacuum.b112bk",
            "xiaomi.vacuum.b112gl",
            "xiaomi.vacuum.b112tr",
            "xiaomi.vacuum.c101",
            "xiaomi.vacuum.c101eu",
            "xiaomi.vacuum.c102",
            "xiaomi.vacuum.c104",
            "xiaomi.vacuum.e101gl",
        ],
        XiaomiVacuumPropertyMapping(piid=2),
    ),
]

_LIVE_DATA_PROP = [
    (
        [
            "xiaomi.vacuum.b108gl",
        ],
        XiaomiVacuumLiveDataMapping(
            siid=7,
            trajectory_piid=2,
            position_piid=4,
            restricted_areas_siid=2,
            restricted_areas_piid=11,
            restricted_walls_siid=2,
            restricted_walls_piid=12,
        ),
    ),
]

_NON_STANDARD_STATUS_PROP = [
    (
        [
            "xiaomi.vacuum.b108gl",
        ],
        # 4 is cleaning/running for b108gl, so it must not be treated as idle.
        XiaomiVacuumStatusMapping(idle_at=(0, 1, 2, 3, 5, 8, 10)),
    ),
]

class XiaomiCloudVacuum(BaseXiaomiCloudVacuumV2):
    def __init__(self, vacuum_config: VacuumConfig):
        super().__init__(vacuum_config)
        self._token = vacuum_config.token
        self._host = vacuum_config.host

        self._miot_device = MiotDevice(self._host, self._token, timeout=2, mapping={})

        self._xiaomi_map_data_parser = XiaomiMapDataParser(
            vacuum_config.palette,
            vacuum_config.sizes,
            vacuum_config.drawables,
            vacuum_config.image_config,
            vacuum_config.texts
        )

        self._status_mapping = next(
            (mapping for models, mapping in _NON_STANDARD_STATUS_PROP if self.model in models),
            get_status_mapping(self.model),
        )
        self._off_counter = 0
        self._last_status_value = None

        self._vacuum_map = next((mapping for models, mapping in _NON_STANDARD_MAP_PROP if self.model in models), XiaomiVacuumPropertyMapping())
        self._live_data = next((mapping for models, mapping in _LIVE_DATA_PROP if self.model in models), None)

    @staticmethod
    def _cloud_object_name_candidates(response: Any) -> list[str]:
        names: list[str] = []

        def add(name: Any) -> None:
            if name is None:
                return
            value = str(name).strip()
            if not value:
                return
            if value not in names:
                names.append(value)
            short_value = value.split("/")[-1]
            if short_value and short_value not in names:
                names.append(short_value)

        if isinstance(response, dict):
            add(response.get("obj_name"))
        elif isinstance(response, str):
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                add(response)
            else:
                if isinstance(parsed, dict):
                    add(parsed.get("obj_name"))
                else:
                    add(response)
        elif isinstance(response, int):
            add(response)

        return names

    def _cloud_object_path(self: Self, obj_name: str) -> str:
        if "/" in obj_name:
            return obj_name
        return f"{self._user_id}/{self._device_id}/{obj_name}"

    async def _get_cloud_object_url(self: Self, obj_name: str) -> str | None:
        obj_path = self._cloud_object_path(obj_name)
        params = {"data": json.dumps({"obj_name": obj_path}, separators=(",", ":"))}

        for endpoint in ("get_interim_file_url_pro", "get_interim_file_url"):
            url = self._connector.get_api_url(self._server) + f"/v2/home/{endpoint}"
            self.last_used_url = url
            api_response = await self._connector.execute_api_call_encrypted(url, params)
            if file_url := path_extractor(api_response, "result.url"):
                return file_url
            _LOGGER.debug("No cloud file URL from %s for object %s", endpoint, obj_path)

        return None

    async def _get_raw_cloud_object_data(self: Self, obj_name: str) -> bytes | None:
        map_url = await self._get_cloud_object_url(obj_name)
        return await self._connector.get_raw_map_data(map_url)

    @property
    def should_update_map(self: Self) -> bool:
        try:
            status_value = self._get_status_value()

            if self._is_status_idle(status_value):
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

    def _get_status_value(self: Self):
        self._last_status_value = self._miot_device.get_property_by(
            self._status_mapping.siid,
            self._status_mapping.piid,
        )[0]["value"]
        return self._last_status_value

    def _is_status_idle(self: Self, status_value: Any) -> bool:
        return status_value in self._status_mapping.idle_at

    @staticmethod
    def vacuum_platform() -> VacuumApi:
        return VacuumApi.XIAOMI

    @property
    def map_archive_extension(self) -> str:
        return "zlib.enc"

    @property
    def map_data_parser(self) -> XiaomiMapDataParser:
        return self._xiaomi_map_data_parser
    
    async def get_map_name(self: Self) -> str:
        response = self._miot_device.get_property_by(self._vacuum_map.siid,
                                                     self._vacuum_map.piid)[0].get("value")

        candidates = self._cloud_object_name_candidates(response)
        if not candidates:
            return await super().get_map_name()
        return candidates[0]

    async def get_map_url(self, map_name: str) -> str | None:
        return await self.get_fallback_map_url(map_name)

    async def get_map(self: Self) -> tuple[MapData, bytes]:
        _LOGGER.debug("Getting map name...")
        map_name_response = self._miot_device.get_property_by(self._vacuum_map.siid,
                                                              self._vacuum_map.piid)[0].get("value")
        map_name_candidates = self._cloud_object_name_candidates(map_name_response) or [await super().get_map_name()]
        _LOGGER.debug("Got map name candidates: %s.", map_name_candidates)
        _LOGGER.debug("Downloading map...")
        map_name = None
        raw_map_data = None
        for candidate in map_name_candidates:
            if candidate is None:
                continue
            raw_map_data = await self._get_raw_cloud_object_data(candidate)
            if raw_map_data is not None:
                map_name = candidate
                break

        if raw_map_data is None:
            _LOGGER.error("FailedMapDownloadException: map name candidates=%s, last endpoint=%s",
                          map_name_candidates, self.last_used_url)
            raise FailedMapDownloadException()

        map_last_used_url = self.last_used_url
        _LOGGER.debug("Downloaded raw map: \"%d\".", len(raw_map_data))

        try:
            status_value = self._get_status_value()
        except DeviceException as de:
            _LOGGER.debug("Failed to retrieve MIOT status: %s", de)
            status_value = self._last_status_value

        vacuum_position = self._get_vacuum_position()
        trajectory_payload = await self._get_trajectory_payload()
        restricted_areas_payload, restricted_walls_payload = self._get_restricted_payloads()
        self.last_used_url = map_last_used_url

        _LOGGER.debug("Parsing map...")
        map_data = self.decode_and_parse(
            raw_map_data,
            vacuum_position,
            trajectory_payload,
            restricted_areas_payload,
            restricted_walls_payload,
            use_path_position_fallback=status_value is not None and not self._is_status_idle(status_value),
        )
        if map_data is not None:
            map_data.map_name = map_name
        else:
            _LOGGER.error("FailedMapParseException")
            raise FailedMapParseException()
        _LOGGER.debug("Parsed map: (%d x %d)", map_data.image.dimensions.height, map_data.image.dimensions.width)
        return map_data, raw_map_data

    async def _get_trajectory_payload(self: Self) -> bytes | None:
        if self._live_data is None:
            return None

        try:
            response = self._miot_device.get_property_by(
                self._live_data.siid,
                self._live_data.trajectory_piid,
            )[0].get("value")
        except DeviceException as de:
            _LOGGER.debug("Failed to retrieve MIOT trajectory object name: %s", de)
            return None

        for trajectory_name in self._cloud_object_name_candidates(response):
            trajectory_payload = await self._get_raw_cloud_object_data(trajectory_name)
            if trajectory_payload is not None:
                return trajectory_payload
        return None

    def _get_vacuum_position(self: Self):
        if self._live_data is None:
            return None

        try:
            response = self._miot_device.get_property_by(
                self._live_data.siid,
                self._live_data.position_piid,
            )[0].get("value")
        except DeviceException as de:
            _LOGGER.debug("Failed to retrieve MIOT vacuum position: %s", de)
            return None

        return parse_vacuum_position_value(response)

    def _get_optional_property_value(self: Self, siid: int | None, piid: int | None):
        if siid is None or piid is None:
            return None

        try:
            return self._miot_device.get_property_by(siid, piid)[0].get("value")
        except DeviceException as de:
            _LOGGER.debug("Failed to retrieve MIOT property %s/%s: %s", siid, piid, de)
            return None

    def _get_restricted_payloads(self: Self) -> tuple[Any | None, Any | None]:
        if self._live_data is None:
            return None, None

        return (
            self._get_optional_property_value(
                self._live_data.restricted_areas_siid,
                self._live_data.restricted_areas_piid,
            ),
            self._get_optional_property_value(
                self._live_data.restricted_walls_siid,
                self._live_data.restricted_walls_piid,
            ),
        )

    def decode_and_parse(
        self,
        raw_map: bytes,
        vacuum_position=None,
        trajectory_payload=None,
        restricted_areas_payload=None,
        restricted_walls_payload=None,
        use_path_position_fallback=False,
    ) -> MapData:
        # Try parsing as JSON first (old format), otherwise use raw data directly (new format)
        try:
            raw_map = base64.decodebytes(json.loads(raw_map)["data"].encode("latin1"))
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            # Data may not be JSON-wrapped
            pass
        
        raw_map = raw_map.hex()
        decoded_map = self.map_data_parser.unpack_map(
            raw_map,
            model=self.model.replace("xiaomi", "mi"),
            device_id=str(self._device_id),
        )
        if self._live_data is None and vacuum_position is None and trajectory_payload is None:
            return self.map_data_parser.parse(decoded_map)

        try:
            payload = json.loads(decoded_map)
        except json.JSONDecodeError:
            return self.map_data_parser.parse(decoded_map)

        payload = normalize_json_map_payload(payload)
        payload = merge_live_map_data(payload, vacuum_position, trajectory_payload, use_path_position_fallback)
        payload = normalize_restricted_map_payload(payload, restricted_areas_payload, restricted_walls_payload)
        map_data = self.map_data_parser.parse(payload)
        apply_json_map_calibration(map_data, payload)
        apply_vacuum_room(map_data, payload)
        return map_data
    
    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        enc_key = gen_md5_key(
            self.model.replace("xiaomi", "mi"),
            str(self._device_id),
        )

        return {**super_data, "enc_key": enc_key}

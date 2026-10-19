import base64
import dataclasses
import json
import struct
import zlib
import logging
from dataclasses import dataclass
from typing import Self, Any

from miio.exceptions import DeviceException
from miio.miot_device import MiotDevice
from vacuum_map_parser_base.map_data import MapData
from vacuum_map_parser_xiaomi.aes_decryptor import gen_md5_key
from vacuum_map_parser_xiaomi.map_data_parser import XiaomiMapDataParser
from vacuum_map_parser_xiaomi.status_mapping import get_status_mapping

from .base.model import VacuumConfig, VacuumApi
from .base.vacuum_v2 import BaseXiaomiCloudVacuumV2
from ..utils.exceptions import FailedConnectionException

_LOGGER = logging.getLogger(__name__)
OFF_UPDATES = 3

@dataclass
class XiaomiVacuumPropertyMapping:
    """Dataclass containing mapping for map property"""

    # vacuum map service id
    siid: int = 10

    # current map property id in vacuum map service
    piid: int = 1

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

class XiaomiCloudVacuum(BaseXiaomiCloudVacuumV2):
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
        # b108gl (S20+) reports 4 = "working", which the default mapping treats as idle.
        # Status values per https://home.miot-spec.com/spec/xiaomi.vacuum.b108gl
        if self.model == "xiaomi.vacuum.b108gl":
            self._status_mapping = dataclasses.replace(self._status_mapping, idle_at=(1, 2, 3, 5, 8, 10))
        self._off_counter = 0
        self._live_trajectory: list[dict[str, Any]] = []
        self._live_position: dict[str, Any] | None = None

        self._vacuum_map = next((mapping for models, mapping in _NON_STANDARD_MAP_PROP if self.model in models), XiaomiVacuumPropertyMapping())

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
    
    async def get_map_name(self: Self) -> str:
        response = self._miot_device.get_property_by(self._vacuum_map.siid,
                                                     self._vacuum_map.piid)[0].get("value")

        if response is None:
            return super().get_map_name()

        if isinstance(response, int):
            return str(response)
        else:
            map_name = None
            try:
                map_name = json.loads(response).get("obj_name", None)
            except json.JSONDecodeError:
                if isinstance(response, str) and "/" in response:
                    map_name = response
            if map_name is None:
                return super().get_map_name()
            return map_name.split("/")[-1]

    async def get_map_url(self, map_name: str) -> str | None:
        return await self.get_fallback_map_url(map_name)

    def decode_and_parse(self, raw_map: bytes) -> MapData:
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
        if self.model == "xiaomi.vacuum.b108gl":
            decoded_map = self._with_live_data(decoded_map)
        return self.map_data_parser.parse(decoded_map)

    # The b108gl (S20+) cloud map has no robot or path. The robot publishes its
    # position as MIoT 7-4 ({"position": [x, y, yaw_mrad]}) and names a cloud trajectory object
    # as 7-2 (zlib records of <marker:u8 x:i32 y:i32>, marker 2 = sweep, 3 = mop).
    async def get_map(self: Self) -> tuple[MapData, bytes]:
        if self.model == "xiaomi.vacuum.b108gl":
            await self._read_live_data()
        return await super().get_map()

    async def _read_live_data(self: Self) -> None:
        self._live_trajectory, self._live_position = [], None
        try:
            status = self._miot_device.get_property_by(2, 1)[0].get("value")
            if status in (2, 3, 8):  # docked: 7-2 still names the last clean's trajectory
                return
            position = json.loads(self._miot_device.get_property_by(7, 4)[0].get("value") or "{}").get("position")
            if position and len(position) >= 2 and 1100 not in position[:2] and any(position[:2]):
                yaw = position[2] / 1000 if len(position) > 2 else 0  # milliradians, parser wants radians
                self._live_position = {"x": position[0], "y": position[1], "yaw": yaw}
            obj = json.loads(self._miot_device.get_property_by(7, 2)[0].get("value") or "{}").get("obj_name")
            raw = await self.get_raw_map_data(obj.split("/")[-1]) if obj else None
            if raw:
                self._live_trajectory = _decode_trajectory(raw)
        except Exception as e:  # live data is optional, never fail the map for it
            _LOGGER.debug("Failed to read b108gl live data: %s", e)

    def _with_live_data(self: Self, decoded_map: Any) -> Any:
        try:
            payload = json.loads(decoded_map)
        except (TypeError, json.JSONDecodeError):
            return decoded_map
        if self._live_trajectory and not payload.get("paths"):
            payload["paths"] = self._live_trajectory
        if self._live_position:
            payload["position"] = self._live_position
        elif self._live_trajectory:
            payload["position"] = {**self._live_trajectory[-1], "yaw": 0}
        return json.dumps(payload)
    
    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        enc_key = gen_md5_key(
            self.model.replace("xiaomi", "mi"),
            str(self._device_id),
        )

        return {**super_data, "enc_key": enc_key}


_TRAJECTORY_RECORD = struct.Struct("<Bii")


def _decode_trajectory(raw: bytes) -> list[dict[str, Any]]:
    try:
        raw = base64.b64decode(json.loads(raw)["data"])
    except (ValueError, KeyError, TypeError):
        try:
            raw = base64.b64decode(raw, validate=True)
        except ValueError:
            pass
    try:
        data = zlib.decompress(raw)
    except zlib.error:
        data = raw
    points, i = [], 0
    while i + _TRAJECTORY_RECORD.size <= len(data):
        marker, x, y = _TRAJECTORY_RECORD.unpack_from(data, i)
        if marker not in (2, 3) or abs(x) > 1_000_000 or abs(y) > 1_000_000:
            i += 1  # header or out-of-step byte
            continue
        points.append({"x": x, "y": y})
        i += _TRAJECTORY_RECORD.size
    return points

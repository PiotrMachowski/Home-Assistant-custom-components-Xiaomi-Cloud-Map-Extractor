import base64
import json
import logging
from dataclasses import dataclass
from typing import Self, Any

from miio.exceptions import DeviceException
from miio.miot_device import MiotDevice
from vacuum_map_parser_base.map_data import MapData, Obstacle, ObstacleDetails
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
        self._off_counter = 0

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

        # Fix for models where map_room_info has all room_id=0 (e.g. xiaomi.vacuum.ov21gl).
        # When all room_ids are identical the parser collapses every room into a single
        # Room object. In that case use grid_id directly as the room identifier.
        payload = None
        if isinstance(decoded_map, str):
            try:
                payload = json.loads(decoded_map)
            except Exception:
                pass
        elif isinstance(decoded_map, dict):
            payload = decoded_map

        if payload is not None:
            payload = self._normalize_firmware_map_objects(payload)
            payload = self._fix_map_room_info(payload)
            map_data = self.map_data_parser.parse(payload)
            # Inject AI obstacles post-parse (library doesn't handle them)
            obstacles = self._extract_obstacles(payload)
            if obstacles is not None and not map_data.obstacles:
                map_data.obstacles = obstacles
            return map_data

        return self.map_data_parser.parse(decoded_map)

    @staticmethod
    def _normalize_firmware_map_objects(payload: dict) -> dict:
        """Convert firmware-specific fb_regions/fb_walls to the library's expected format.

        The firmware uses:
          fb_regions: [{"fb_point": [x0,y0,x1,y1,x2,y2,x3,y3], ...}]
          fb_walls:   [{"wall_points": [x0,y0,x1,y1], ...}]

        The library (vacuum_map_parser_xiaomi) expects:
          fb_regions: [{"type": "no_go"|"wall", "points": [{"x":..,"y":..}, ...]}, ...]

        By normalizing before parse(), the library renders them in the camera image.
        """
        payload = dict(payload)
        normalized: list[dict] = []

        for r in payload.get("fb_regions") or []:
            if not isinstance(r, dict):
                continue
            fb_point = r.get("fb_point")
            if fb_point and len(fb_point) == 8:
                x0, y0, x1, y1, x2, y2, x3, y3 = fb_point
                normalized.append({
                    "type": "no_go",
                    "points": [
                        {"x": x0, "y": y0},
                        {"x": x1, "y": y1},
                        {"x": x2, "y": y2},
                        {"x": x3, "y": y3},
                    ],
                })
            else:
                normalized.append(r)

        for w in payload.get("fb_walls") or []:
            if not isinstance(w, dict):
                continue
            wp = w.get("wall_points")
            if wp and len(wp) == 4:
                x0, y0, x1, y1 = wp
                # Library uses points[0] and points[2] for wall endpoints
                normalized.append({
                    "type": "wall",
                    "points": [
                        {"x": x0, "y": y0},
                        {"x": 0, "y": 0},
                        {"x": x1, "y": y1},
                        {"x": 0, "y": 0},
                    ],
                })

        if normalized:
            payload["fb_regions"] = normalized

        return payload

    @staticmethod
    def _extract_obstacles(payload: dict) -> list[Obstacle] | None:
        """Extract AI-detected obstacles from payload (library does not handle these)."""
        ai_obj = payload.get("ai_obj")
        if not ai_obj:
            return None
        parsed = [
            Obstacle(obj["pos_x"], obj["pos_y"], ObstacleDetails(type=obj.get("type")))
            for obj in ai_obj
            if isinstance(obj, dict) and obj.get("notshow", 0) == 0
            and "pos_x" in obj and "pos_y" in obj
        ]
        return parsed or None

    @staticmethod
    def _fix_map_room_info(payload: dict) -> dict:
        """Fix map_room_info when all room_ids are identical (firmware quirk).

        Some models (e.g. xiaomi.vacuum.ov21gl) set room_id=0 for every entry in
        map_room_info. The upstream parser uses room_id as the dict key, so every
        room overwrites the previous one. When this is detected, replace room_id with
        grid_id so each room gets a unique identifier that also matches the id field
        used in room_attrs.
        """
        map_room_info = payload.get("map_room_info")
        if not isinstance(map_room_info, list) or len(map_room_info) <= 1:
            return payload

        room_ids = [e.get("room_id") for e in map_room_info if isinstance(e, dict)]
        if len(set(room_ids)) != 1:
            return payload  # room_ids are already unique, nothing to fix

        _LOGGER.debug(
            "map_room_info has all room_id=%s; using grid_id as room identifier", room_ids[0]
        )
        fixed_info = [
            {**e, "room_id": e["grid_id"]} if isinstance(e, dict) and "grid_id" in e else e
            for e in map_room_info
        ]
        return {**payload, "map_room_info": fixed_info}
    
    def additional_data(self: Self) -> dict[str, Any]:
        super_data = super().additional_data()
        enc_key = gen_md5_key(
            self.model.replace("xiaomi", "mi"),
            str(self._device_id),
        )

        return {**super_data, "enc_key": enc_key}

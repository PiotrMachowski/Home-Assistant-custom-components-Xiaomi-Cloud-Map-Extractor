"""Xiaomi map parser."""

import base64
import logging
import math
import json
import zlib
from types import SimpleNamespace
from typing import Any

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_base.config.text import Text
from vacuum_map_parser_base.map_data import Area, ImageData, MapData, Path, Point, Room, Wall, Zone
from vacuum_map_parser_base.map_data_parser import MapDataParser

from .aes_decryptor import decrypt
from .xiaomi_coordinate_transforms import Transformer
from .image_parser import XiaomiImageParser

_LOGGER = logging.getLogger(__name__)


class XiaomiMapDataParser(MapDataParser):
    """Xiaomi map parser."""

    POSITION_UNKNOWN = 1100
    VIRTUALWALL_TYPE_WALL = 2
    VIRTUALWALL_TYPE_NO_MOP = 6
    VIRTUALWALL_TYPE_NO_GO = 3

    def __init__(
        self,
        palette: ColorsPalette,
        sizes: Sizes,
        drawables: list[Drawable],
        image_config: ImageConfig,
        texts: list[Text]
    ):
        super().__init__(palette, sizes, drawables, image_config, texts)
        self._image_parser = XiaomiImageParser(palette, image_config, drawables)

    def unpack_map(self, raw_encoded: bytes, *args: Any, **kwargs: Any) -> bytes:
        return decrypt(
                raw_encoded,
                kwargs['model'],
                kwargs['device_id'])

    def parse(self, raw: Any, *args: Any, **kwargs: Any) -> MapData:
        if raw is None:
            return None

        # Decryptor returns a JSON string for newer Xiaomi vacuums.
        if isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("Map data is a string but not valid JSON") from exc
            return self._parse_json_payload(payload)

        # Some callers might already pass the decoded dict.
        if isinstance(raw, dict):
            return self._parse_json_payload(raw)

        raise TypeError(f"Unsupported map data type: {type(raw)!r}")

    @staticmethod
    def _json_yaw_to_degrees(yaw: Any) -> float:
        """Convert Xiaomi JSON yaw values to degrees.

        Observed formats:
        - centi-degrees (e.g. 2470 -> 24.70°)
        - radians (rare)
        - degrees
        """
        try:
            value = float(yaw)
        except (TypeError, ValueError):
            return 0.0

        # Radians are typically within [-2π, 2π]
        if abs(value) <= (2 * math.pi + 0.001):
            return value * 180.0 / math.pi

        # Many Xiaomi payloads use centi-degrees.
        if abs(value) > 180.0:
            return (value / 100.0) % 180.0

        return value % 180.0

    @staticmethod
    def _room_number_to_grid_id(room_number: int) -> int:
        """Convert pixel-based room_number (10..59) to Xiaomi grid_id (3..)."""
        return int(room_number) - XiaomiImageParser.MAP_ROOM_MIN + 3

    
    def _normalize_json_map_pixels(self, raw: bytes) -> bytes:
        """
        Normalize JSON-based Xiaomi map pixels so they fit
        XiaomiImageParser expectations.
        """
        ROOM_MIN = XiaomiImageParser.MAP_ROOM_MIN  # usually 10

        out = bytearray(len(raw))

        for i, v in enumerate(raw):
            if v == 0:
                out[i] = 0  # unknown

            # JSON free / base pixels
            elif v in (1, 2):
                out[i] = 127  # free space

            # JSON room ids (THIS IS THE IMPORTANT PART)
            elif 3 <= v <= 63:
                out[i] = ROOM_MIN + (v - 3)

            else:
                out[i] = 128  # wall / blocked

        return bytes(out)

    def _parse_json_payload(self, payload: dict[str, Any]) -> MapData:
        """Parse decrypted JSON payload and produce a MapData identical in
        structure to the protobuf-based parser.
        """

        # ---- Basic map metadata -------------------------------------------------
        map_id = payload.get("map_id", 0)
        map_width = payload.get("width")
        map_height = payload.get("height")
        map_resolution = payload.get("resolution", 50)  # mm per pixel (typical)
        origin_x = payload.get("origin_x", 0)
        origin_y = payload.get("origin_y", 0)

        raw_map_data_b64 = payload.get("map_data")
        if not raw_map_data_b64 or map_width is None or map_height is None:
            _LOGGER.debug("JSON map payload missing map_data/width/height")
            return MapData(0, 1)

        try:
            map_bytes = zlib.decompress(base64.b64decode(raw_map_data_b64))
        except Exception as exc:
            raise RuntimeError("Failed to decode JSON map_data (base64+zlib)") from exc

        # ---- Create MapData -----------------------------------------------------
        map_data = MapData(0, 1)

        # ---- Minimal map head so Transformer works -----------------------------
        # The JSON `RobotMap.proto` in this repo is *not* the protobuf map format
        # used by the original Xiaomi parser; we only need bounds + pixel size.
        self.robot_map = SimpleNamespace()
        self.robot_map.mapHead = SimpleNamespace(
            mapHeadId=map_id,
            sizeX=int(map_width),
            sizeY=int(map_height),
            resolution=float(map_resolution),
            minX=float(origin_x),
            minY=float(origin_y),
            maxX=float(origin_x) + float(map_width) * float(map_resolution),
            maxY=float(origin_y) + float(map_height) * float(map_resolution),
        )

        self.coord_transformer = Transformer(self.robot_map)
        normalized_map = self._normalize_json_map_pixels(map_bytes)

        # ---- Parse image --------------------------------------------------------

        image, rooms_raw, cleaned_areas = self._image_parser.parse(
            normalized_map, int(map_width), int(map_height)
        )

        if image is None:
            image = self._image_generator.create_empty_map_image()

        map_data.image = ImageData(
            int(map_width) * int(map_height),
            0,
            0,
            int(map_height),
            int(map_width),
            self._image_config,
            image,
            self.coord_transformer.map_to_image,
        )

        # ---- Rooms --------------------------------------------------------------
        rooms_out: dict[int, Room] = {}

        # Map (pixel room number -> grid_id -> room_id).
        grid_to_room: dict[int, int] = {}
        map_room_info = payload.get("map_room_info")
        if isinstance(map_room_info, list):
            for entry in map_room_info:
                if not isinstance(entry, dict):
                    continue
                try:
                    grid_id = int(entry.get("grid_id"))
                    room_id = int(entry.get("room_id"))
                except (TypeError, ValueError):
                    continue
                grid_to_room[grid_id] = room_id

        for room_number, room in rooms_raw.items():
            grid_id = self._room_number_to_grid_id(room_number)
            room_id = grid_to_room.get(grid_id, grid_id)
            rooms_out[room_id] = Room(
                self.coord_transformer.image_to_map_x(room[0]),
                self.coord_transformer.image_to_map_y(room[1]),
                self.coord_transformer.image_to_map_x(room[2]),
                self.coord_transformer.image_to_map_y(room[3]),
                room_id,
            )

        # Best-effort naming from room_attrs
        room_attrs = payload.get("room_attrs")
        if isinstance(room_attrs, list):
            for r in room_attrs:
                if not isinstance(r, dict):
                    continue
                rid = r.get("room_id") or r.get("grid_id") or r.get("id")
                try:
                    rid_int = int(rid)
                except (TypeError, ValueError):
                    continue
                if rid_int in rooms_out:
                    rooms_out[rid_int].name = r.get("name") or r.get("room_name")
                    # Some payloads use name_pos_x/y for the label position.
                    rooms_out[rid_int].pos_x = r.get("text_x", r.get("name_pos_x"))
                    rooms_out[rid_int].pos_y = r.get("text_y", r.get("name_pos_y"))

        map_data.rooms = rooms_out
        # cleaned_areas contains pixel-room numbers; convert to room IDs.
        cleaned_rooms_out = set()
        for room_number in cleaned_areas:
            try:
                grid_id = self._room_number_to_grid_id(int(room_number))
            except (TypeError, ValueError):
                continue
            cleaned_rooms_out.add(grid_to_room.get(grid_id, grid_id))
        map_data.cleaned_rooms = cleaned_rooms_out

        # ---- Charger ------------------------------------------------------------
        if payload.get("have_pile"):
            map_data.charger = Point(
                x=payload.get("pile_x", 0),
                y=payload.get("pile_y", 0),
                a=self._json_yaw_to_degrees(payload.get("pile_yaw", 0)),
            )

        # ---- Robot pose ---------------------------------------------------------
        position = payload.get("position")
        if isinstance(position, dict):
            map_data.vacuum_position = Point(
                x=position.get("x", 0),
                y=position.get("y", 0),
                a=self._json_yaw_to_degrees(position.get("yaw", 0)),
            )

        # ---- Path / history -----------------------------------------------------
        paths = payload.get("paths")
        points_src = None
        if isinstance(paths, dict):
            points_src = paths.get("points")
        elif isinstance(paths, list):
            points_src = paths

        if isinstance(points_src, list):
            points = []
            for p in points_src:
                if not isinstance(p, dict):
                    continue
                pt = Point(
                    x=p.get("x", 0),
                    y=p.get("y", 0),
                )
                # If angle is present, keep it.
                if "yaw" in p:
                    pt.a = self._json_yaw_to_degrees(p.get("yaw"))
                points.append(pt)
            if points:
                map_data.path = Path(len(points), 1, 0, [points])

        # ---- Virtual walls / no-go areas ---------------------------------------
        walls = []
        no_go = []
        no_mop = []

        for area in payload.get("fb_regions", []) or []:
            if not isinstance(area, dict):
                continue
            pts = area.get("points")
            if not pts or len(pts) != 4:
                continue

            p = [Point(pt["x"], pt["y"]) for pt in pts]

            atype = area.get("type")
            if atype == "wall":
                walls.append(Wall(p[0].x, p[0].y, p[2].x, p[2].y))
            elif atype == "no_go":
                no_go.append(Area(p[0].x, p[0].y, p[1].x, p[1].y,
                                p[2].x, p[2].y, p[3].x, p[3].y))
            elif atype == "no_mop":
                no_mop.append(Area(p[0].x, p[0].y, p[1].x, p[1].y,
                                p[2].x, p[2].y, p[3].x, p[3].y))

        map_data.walls = walls
        map_data.no_go_areas = no_go
        map_data.no_mopping_areas = no_mop

        # ---- Zones --------------------------------------------------------------
        zones = []
        for z in payload.get("current_cleaning_config", {}).get("zones", []):
            if not isinstance(z, dict):
                continue
            zones.append(
                Zone(
                    z["x1"],
                    z["y1"],
                    z["x2"],
                    z["y2"],
                )
            )
        map_data.zones = zones

        # ---- Draw ---------------------------------------------------------------
        if map_data.image is not None and not map_data.image.is_empty:
            self._image_generator.draw_map(map_data)

        return map_data

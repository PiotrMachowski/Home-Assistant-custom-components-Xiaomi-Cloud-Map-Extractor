"""MIOT helpers for Xiaomi vacuums that omit live data from cloud map JSON."""

import base64
import json
import logging
import math
import struct
import zlib
from typing import Any

from vacuum_map_parser_base.map_data import MapData, Point

_LOGGER = logging.getLogger(__name__)

POSITION_UNKNOWN = 1100
TRAJECTORY_POINT_MARKER = 0x02
TRAJECTORY_SEGMENT_MARKER = 0x03
MAX_TRAJECTORY_COORD = 1_000_000
MIN_CALIBRATION_PIXELS = 10
MIN_MOP_SEGMENT_POINTS = 3
MAX_MOP_SEGMENT_GAP = 500


def json_yaw_to_degrees(yaw: Any) -> float:
    try:
        value = float(yaw)
    except (TypeError, ValueError):
        return 0.0

    if abs(value) <= (2 * math.pi + 0.001):
        return value * 180.0 / math.pi

    if abs(value) > 180.0:
        return (value / 100.0) % 180.0

    return value % 180.0


def extract_cloud_object_name(response: Any) -> str | None:
    if response is None:
        return None

    if isinstance(response, int):
        return str(response)

    if isinstance(response, str):
        if "/" in response:
            return response.split("/")[-1]
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                obj_name = parsed.get("obj_name")
                if isinstance(obj_name, str):
                    return obj_name.split("/")[-1]
        except json.JSONDecodeError:
            return None

    if isinstance(response, dict):
        obj_name = response.get("obj_name")
        if isinstance(obj_name, str):
            return obj_name.split("/")[-1]

    return None


def parse_vacuum_position_value(value: Any) -> Point | None:
    if value is None:
        return None

    if isinstance(value, Point):
        return value

    if isinstance(value, dict):
        data = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped in ("0", "0,0", "0,0,0"):
            return None
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            parts = [part.strip() for part in stripped.split(",")]
            if len(parts) < 2:
                return None
            data = {
                "x": parts[0],
                "y": parts[1],
                "yaw": parts[2] if len(parts) > 2 else 0,
            }
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        data = {"x": value[0], "y": value[1], "yaw": value[2] if len(value) > 2 else 0}
    else:
        return None

    if not isinstance(data, dict):
        return None

    try:
        x = float(data.get("x", data.get("pos_x", data.get("cur_x", 0))))
        y = float(data.get("y", data.get("pos_y", data.get("cur_y", 0))))
    except (TypeError, ValueError):
        return None

    if x == 0 and y == 0:
        return None
    if x == POSITION_UNKNOWN or y == POSITION_UNKNOWN:
        return None

    yaw = data.get("yaw", data.get("phi", data.get("angle", data.get("a", 0))))
    return Point(x, y, json_yaw_to_degrees(yaw))


def vacuum_position_to_payload(position: Point) -> dict[str, float]:
    payload: dict[str, float] = {"x": position.x, "y": position.y}
    if position.a is not None:
        payload["yaw"] = position.a
    return payload


def _trajectory_distance(a: dict[str, int], b: dict[str, int]) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def _mark_mop_segments(points: list[dict[str, int]]) -> None:
    segment: list[dict[str, int]] = []

    def flush_segment() -> None:
        if len(segment) >= MIN_MOP_SEGMENT_POINTS:
            for point in segment:
                point["sweep_mop_mode"] = 1
        segment.clear()

    for point in points:
        if point.pop("_miot_marker", None) != TRAJECTORY_SEGMENT_MARKER:
            flush_segment()
            continue

        if segment and _trajectory_distance(segment[-1], point) > MAX_MOP_SEGMENT_GAP:
            flush_segment()
        segment.append(point)

    flush_segment()


def parse_b108_binary_trajectory(data: bytes) -> list[dict[str, int]]:
    """Parse b108gl trajectory blob (zlib-decompressed): marker + i32 x + i32 y points."""
    points: list[dict[str, int]] = []
    index = 0
    while index < len(data):
        marker = data[index]
        if marker in (TRAJECTORY_POINT_MARKER, TRAJECTORY_SEGMENT_MARKER) and index + 8 < len(data):
            x, y = struct.unpack_from("<ii", data, index + 1)
            if abs(x) <= MAX_TRAJECTORY_COORD and abs(y) <= MAX_TRAJECTORY_COORD:
                points.append({"x": x, "y": y, "_miot_marker": marker})
            index += 9
        else:
            index += 1
    _mark_mop_segments(points)
    return points


def decompress_trajectory_bytes(raw: bytes) -> bytes | None:
    if not raw:
        return None

    payload = raw
    try:
        text = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        text = None

    if text:
        if text.startswith("{"):
            try:
                wrapper = json.loads(text)
            except json.JSONDecodeError:
                wrapper = None
            if isinstance(wrapper, dict):
                encoded = wrapper.get("data")
                if isinstance(encoded, str):
                    try:
                        payload = base64.b64decode(encoded)
                    except ValueError:
                        return None
        else:
            try:
                payload = base64.b64decode(text)
            except ValueError:
                payload = raw

    try:
        return zlib.decompress(payload)
    except zlib.error:
        if payload[:1] in (bytes([TRAJECTORY_POINT_MARKER]), bytes([TRAJECTORY_SEGMENT_MARKER])):
            return payload
        return None


def decode_trajectory_cloud_payload(raw: bytes) -> list[dict[str, int]] | None:
    decompressed = decompress_trajectory_bytes(raw)
    if decompressed is None:
        return None

    points = parse_b108_binary_trajectory(decompressed)
    if points:
        _LOGGER.debug("Parsed %d trajectory points from cloud payload", len(points))
        return points

    return None


def decode_jsonish_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if not stripped:
        return None

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _to_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _point_from_value(value: Any) -> dict[str, float] | None:
    if isinstance(value, dict):
        x = _to_number(value.get("x", value.get("pos_x", value.get("x0"))))
        y = _to_number(value.get("y", value.get("pos_y", value.get("y0"))))
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        x = _to_number(value[0])
        y = _to_number(value[1])
    else:
        return None

    if x is None or y is None:
        return None
    return {"x": x, "y": y}


def _points_from_flat_numbers(values: list[Any]) -> list[dict[str, float]] | None:
    numbers = [_to_number(value) for value in values]
    if any(value is None for value in numbers):
        return None
    return [{"x": numbers[index], "y": numbers[index + 1]} for index in range(0, len(numbers), 2)]


def _points_from_value(value: Any, expected_points: int) -> list[dict[str, float]] | None:
    if isinstance(value, dict):
        if expected_points == 2 and all(key in value for key in ("x0", "y0", "x1", "y1")):
            return _points_from_flat_numbers([value["x0"], value["y0"], value["x1"], value["y1"]])
        if expected_points == 4 and all(key in value for key in ("x0", "y0", "x1", "y1", "x2", "y2", "x3", "y3")):
            return _points_from_flat_numbers([
                value["x0"], value["y0"], value["x1"], value["y1"],
                value["x2"], value["y2"], value["x3"], value["y3"],
            ])
        if expected_points == 4 and all(key in value for key in ("x1", "y1", "x2", "y2")):
            x1 = _to_number(value["x1"])
            y1 = _to_number(value["y1"])
            x2 = _to_number(value["x2"])
            y2 = _to_number(value["y2"])
            if None not in (x1, y1, x2, y2):
                return [{"x": x1, "y": y1}, {"x": x2, "y": y1}, {"x": x2, "y": y2}, {"x": x1, "y": y2}]

        for key in ("points", "area_points", "region_points", "wall_points", "coordinates", "vertices"):
            if key in value:
                points = _points_from_value(value[key], expected_points)
                if points is not None:
                    return points

    if not isinstance(value, (list, tuple)):
        return None

    if len(value) == expected_points * 2:
        points = _points_from_flat_numbers(list(value))
        if points is not None:
            return points

    points = [_point_from_value(point) for point in value[:expected_points]]
    if len(points) == expected_points and all(point is not None for point in points):
        return points

    return None


def _iter_restricted_items(value: Any, expected_points: int) -> list[Any]:
    value = decode_jsonish_value(value)
    if value is None:
        return []
    if isinstance(value, dict):
        for key in ("areas", "zones", "regions", "walls", "restricted_areas", "restricted_walls", "value"):
            if key in value:
                items = _iter_restricted_items(value[key], expected_points)
                if items:
                    return items
        return [value]
    if isinstance(value, list):
        chunk_size = expected_points * 2
        if value and len(value) % chunk_size == 0 and _points_from_flat_numbers(value) is not None:
            return [value[index:index + chunk_size] for index in range(0, len(value), chunk_size)]
        return value
    return []


def _wall_region_from_points(points: list[dict[str, float]]) -> dict[str, Any]:
    return {
        "type": "wall",
        "points": [points[0], points[0], points[1], points[1]],
    }


def normalize_restricted_map_payload(
    payload: dict[str, Any],
    restricted_areas: Any | None = None,
    restricted_walls: Any | None = None,
) -> dict[str, Any]:
    normalized = dict(payload)
    regions: list[dict[str, Any]] = []

    existing_regions = normalized.get("fb_regions")
    if isinstance(existing_regions, list):
        regions.extend(region for region in existing_regions if isinstance(region, dict))

    for wall in normalized.get("fb_walls", []) or []:
        points = _points_from_value(wall, 2)
        if points is not None:
            regions.append(_wall_region_from_points(points))

    for area in _iter_restricted_items(restricted_areas, 4):
        points = _points_from_value(area, 4)
        if points is not None:
            regions.append({"type": "no_go", "points": points})

    for wall in _iter_restricted_items(restricted_walls, 2):
        points = _points_from_value(wall, 2)
        if points is not None:
            regions.append(_wall_region_from_points(points))

    if regions:
        normalized["fb_regions"] = regions

    return normalized


def _has_path_data(paths: Any) -> bool:
    if paths is None:
        return False
    if isinstance(paths, list):
        return len(paths) > 0
    if isinstance(paths, dict):
        points = paths.get("points")
        return isinstance(points, list) and len(points) > 0
    return False


def _last_path_point(paths: Any) -> dict[str, Any] | None:
    if isinstance(paths, dict):
        points = paths.get("points")
    else:
        points = paths

    if not isinstance(points, list):
        return None

    for point in reversed(points):
        if isinstance(point, dict) and "x" in point and "y" in point:
            return point

    return None


def extract_paths_for_map_payload(source: Any) -> Any | None:
    if source is None:
        return None

    if isinstance(source, bytes):
        return decode_trajectory_cloud_payload(source)

    if isinstance(source, str):
        stripped = source.strip()
        if not stripped:
            return None
        try:
            source = json.loads(stripped)
        except json.JSONDecodeError:
            try:
                return decode_trajectory_cloud_payload(stripped.encode("ascii"))
            except UnicodeEncodeError:
                return None

    if isinstance(source, dict):
        for key in ("paths", "path", "trajectory"):
            if _has_path_data(source.get(key)):
                return source.get(key)
        if _has_path_data(source.get("points")):
            return source
        if all(k in source for k in ("x", "y")) or isinstance(source.get("points"), list):
            return source

    if isinstance(source, list) and source:
        return source

    return None


def merge_live_map_data(
    payload: dict[str, Any],
    vacuum_position: Point | None,
    trajectory_payload: Any | None,
) -> dict[str, Any]:
    merged = dict(payload)

    if vacuum_position is not None:
        merged["position"] = vacuum_position_to_payload(vacuum_position)
        _LOGGER.debug("Merged MIOT vacuum position into map payload")

    if not _has_path_data(merged.get("paths")):
        paths = extract_paths_for_map_payload(trajectory_payload)
        if paths is not None:
            merged["paths"] = paths
            _LOGGER.debug("Merged MIOT trajectory into map payload")

    if not isinstance(merged.get("position"), dict):
        last_point = _last_path_point(merged.get("paths"))
        if last_point is not None:
            merged["position"] = {
                "x": last_point["x"],
                "y": last_point["y"],
                "yaw": last_point.get("yaw", 0),
            }
            _LOGGER.debug("Using last trajectory point as vacuum position")

    return merged


def _json_map_pixel_at(payload: dict[str, Any], x: float, y: float) -> int | None:
    try:
        resolution = float(payload.get("resolution") or 50)
        width = int(payload.get("width"))
        height = int(payload.get("height"))
        origin_x = float(payload.get("origin_x") or 0)
        origin_y = float(payload.get("origin_y") or 0)
        grid_x = int((x - origin_x) / resolution)
        grid_y = int((y - origin_y) / resolution)
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    if grid_x < 0 or grid_y < 0 or grid_x >= width or grid_y >= height:
        return None

    raw_map_data_b64 = payload.get("map_data")
    if not isinstance(raw_map_data_b64, str):
        return None

    try:
        map_bytes = zlib.decompress(base64.b64decode(raw_map_data_b64))
        return int(map_bytes[grid_y * width + grid_x])
    except (IndexError, TypeError, ValueError, zlib.error):
        return None


def _is_known_json_map_pixel(value: int | None) -> bool:
    return value is not None and value != 0


def normalize_json_map_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert grid-based pile coordinates to world millimeters for JSON maps."""
    normalized = dict(payload)
    try:
        resolution = float(payload.get("resolution") or 50)
        width = int(payload.get("width"))
        height = int(payload.get("height"))
        pile_x = float(payload.get("pile_x"))
        pile_y = float(payload.get("pile_y"))
    except (TypeError, ValueError):
        return normalized

    if not payload.get("have_pile"):
        return normalized

    if _is_known_json_map_pixel(_json_map_pixel_at(payload, pile_x, pile_y)):
        return normalized

    if 0 <= pile_x <= width and 0 <= pile_y <= height:
        origin_x = float(payload.get("origin_x") or 0)
        origin_y = float(payload.get("origin_y") or 0)
        normalized["pile_x"] = origin_x + pile_x * resolution
        normalized["pile_y"] = origin_y + pile_y * resolution

    return normalized


def apply_json_map_calibration(map_data: MapData, payload: dict[str, Any]) -> None:
    """Scale calibration vectors so vacuum map card gets non-degenerate points."""
    if map_data.image is None or map_data.image.is_empty:
        return

    resolution = float(payload.get("resolution") or 50)
    vacuum_step_mm = resolution * MIN_CALIBRATION_PIXELS
    map_data._calibration_center = 0
    map_data._calibration_diff = max(1.0, vacuum_step_mm / 10.0)


def apply_vacuum_room(map_data: MapData, payload: dict[str, Any]) -> None:
    """Resolve the current vacuum room from the live position and JSON room pixels."""
    if map_data.vacuum_position is None:
        return

    try:
        resolution = float(payload.get("resolution") or 50)
        width = int(payload.get("width"))
        height = int(payload.get("height"))
        origin_x = float(payload.get("origin_x") or 0)
        origin_y = float(payload.get("origin_y") or 0)
        grid_x = int((map_data.vacuum_position.x - origin_x) / resolution)
        grid_y = int((map_data.vacuum_position.y - origin_y) / resolution)
    except (TypeError, ValueError, ZeroDivisionError):
        return

    if grid_x < 0 or grid_y < 0 or grid_x >= width or grid_y >= height:
        return

    raw_map_data_b64 = payload.get("map_data")
    if not isinstance(raw_map_data_b64, str):
        return

    try:
        map_bytes = zlib.decompress(base64.b64decode(raw_map_data_b64))
        grid_id = int(map_bytes[grid_y * width + grid_x])
    except (IndexError, TypeError, ValueError, zlib.error):
        return

    if grid_id < 3 or grid_id > 63:
        return

    room_id = grid_id
    for entry in payload.get("map_room_info", []) or []:
        if not isinstance(entry, dict):
            continue
        try:
            if int(entry.get("grid_id")) == grid_id:
                room_id = int(entry.get("room_id"))
                break
        except (TypeError, ValueError):
            continue

    map_data.vacuum_room = room_id
    room = (map_data.rooms or {}).get(room_id)
    map_data.vacuum_room_name = room and room.name

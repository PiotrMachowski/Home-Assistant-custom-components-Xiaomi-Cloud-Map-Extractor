import base64
import logging
import json
import re
import zlib
from enum import IntEnum, Enum
from typing import Optional, List

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData, Point, ImageData, Path, Area
from custom_components.xiaomi_cloud_map_extractor.common.map_data_parser import MapDataParser
from custom_components.xiaomi_cloud_map_extractor.dreame.image_handler import ImageHandlerDreame

_LOGGER = logging.getLogger(__name__)


class MapDataHeader:
    def __init__(self):
        self.map_index: Optional[int] = None
        self.frame_type: Optional[int] = None
        self.vacuum_position: Optional[Point] = None
        self.charger_position: Optional[Point] = None
        self.image_pixel_size: Optional[int] = None
        self.image_width: Optional[int] = None
        self.image_height: Optional[int] = None
        self.image_left: Optional[int] = None
        self.image_top: Optional[int] = None


class MapDataParserDreame(MapDataParser):
    HEADER_SIZE = 27
    PATH_REGEX = r'(?P<operator>[SL])(?P<x>-?\d+),(?P<y>-?\d+)'

    class PathOperators(str, Enum):
        START = "S"
        RELATIVE_LINE = "L"

    class FrameTypes(IntEnum):
        I = 73
        P = 80

    class MapDataTypes(str, Enum):
        REGULAR = "regular"
        RISM = "rism"  # Room - information

    @staticmethod
    def decode_map(raw_map: str, colors, drawables, texts, sizes, image_config,
                   map_data_type=MapDataTypes.REGULAR) -> MapData:
        _LOGGER.debug(f'decoding {map_data_type} type map')
        raw_map_string = raw_map.replace('_', '/').replace('-', '+')
        unzipped = zlib.decompress(base64.decodebytes(raw_map_string.encode("utf8")))
        return MapDataParserDreame.parse(unzipped, colors, drawables, texts, sizes, image_config, map_data_type)

    @staticmethod
    def parse(raw: bytes, colors, drawables, texts, sizes, image_config,
              map_data_type: MapDataTypes) -> Optional[MapData]:
        map_data = MapData()

        header = MapDataParserDreame.parse_header(raw)

        if header.frame_type != MapDataParserDreame.FrameTypes.I:
            _LOGGER.error("unsupported map frame type")
            return

        if len(raw) >= MapDataParserDreame.HEADER_SIZE + header.image_width * header.image_height:
            image_raw = raw[
                MapDataParserDreame.HEADER_SIZE:
                MapDataParserDreame.HEADER_SIZE + header.image_width * header.image_height
            ]
            additional_data_raw = raw[MapDataParserDreame.HEADER_SIZE + header.image_width * header.image_height:]
            additional_data_json = json.loads(additional_data_raw.decode("utf8"))
            _LOGGER.debug(f'map additional_data: {additional_data_json}')

            map_data.charger = header.charger_position
            map_data.vacuum_position = header.vacuum_position

            if additional_data_json.get("rism") and\
                    additional_data_json.get("ris") and additional_data_json["ris"] == 2:
                rism_map_data = MapDataParserDreame.decode_map(
                    additional_data_json["rism"],
                    colors,
                    drawables,
                    texts,
                    sizes,
                    image_config,
                    MapDataParserDreame.MapDataTypes.RISM
                )
                map_data.no_go_areas = rism_map_data.no_go_areas

            if additional_data_json.get("tr"):
                map_data.path = MapDataParserDreame.parse_path(additional_data_json["tr"])

            if additional_data_json.get("vw"):
                if additional_data_json["vw"].get("rect"):
                    map_data.no_go_areas = MapDataParserDreame.parse_areas(additional_data_json["vw"]["rect"])

            map_data.image = MapDataParserDreame.parse_image(image_raw, header, colors, image_config, map_data_type)

            if not map_data.image.is_empty:
                MapDataParserDreame.draw_elements(colors, drawables, sizes, map_data, image_config)

        return map_data

    @staticmethod
    def parse_header(raw: bytes) -> Optional[MapDataHeader]:
        header = MapDataHeader()

        if not raw or len(raw) < MapDataParserDreame.HEADER_SIZE:
            _LOGGER.error("wrong header size for map")
            return

        header.map_index = MapDataParserDreame.read_int_16_le(raw)
        header.frame_type = MapDataParserDreame.read_int_8(raw, 4)
        header.vacuum_position = Point(
            MapDataParserDreame.read_int_16_le(raw, 5),
            MapDataParserDreame.read_int_16_le(raw, 7),
            MapDataParserDreame.read_int_16_le(raw, 9)
        )
        header.charger_position = Point(
            MapDataParserDreame.read_int_16_le(raw, 11),
            MapDataParserDreame.read_int_16_le(raw, 13),
            MapDataParserDreame.read_int_16_le(raw, 15)
        )
        header.image_pixel_size = MapDataParserDreame.read_int_16_le(raw, 17)
        header.image_width = MapDataParserDreame.read_int_16_le(raw, 19)
        header.image_height = MapDataParserDreame.read_int_16_le(raw, 21)
        header.image_left = round(MapDataParserDreame.read_int_16_le(raw, 23) / header.image_pixel_size)
        header.image_top = round(MapDataParserDreame.read_int_16_le(raw, 25) / header.image_pixel_size)

        _LOGGER.debug(f'decoded map header : {header.__dict__}')

        return header

    @staticmethod
    def parse_image(image_raw: bytes, header: MapDataHeader, colors, image_config,
                    map_data_type: MapDataTypes) -> ImageData:

        image = ImageHandlerDreame.parse(image_raw, header, colors, image_config, map_data_type)

        return ImageData(
            header.image_width * header.image_height,
            header.image_top,
            header.image_left,
            header.image_height,
            header.image_width,
            image_config,
            image,
            lambda p: MapDataParserDreame.map_to_image(p, header.image_pixel_size)
        )

    @staticmethod
    def map_to_image(p: Point, image_pixel_size: int) -> Point:
        return Point(
            p.x / image_pixel_size,
            p.y / image_pixel_size
        )

    @staticmethod
    def parse_path(path_string: str) -> Path:
        r = re.compile(MapDataParserDreame.PATH_REGEX)
        matches = [m.groupdict() for m in r.finditer(path_string)]

        current_path = []
        path_points = []
        current_position = Point(0, 0)
        for match in matches:
            if match["operator"] == MapDataParserDreame.PathOperators.START:
                current_path = []
                path_points.append(current_path)
                current_position = Point(int(match["x"]), int(match["y"]))
            elif match["operator"] == MapDataParserDreame.PathOperators.RELATIVE_LINE:
                current_position = Point(current_position.x + int(match["x"]), current_position.y + int(match["y"]))
            else:
                _LOGGER.error(f'invalid path operator {match["operator"]}')
            current_path.append(current_position)

        path_points = [item for sublist in path_points for item in sublist]
        return Path(None, None, None, path_points)

    @staticmethod
    def parse_areas(areas: list) -> List[Area]:
        parsed_areas = []
        for area in areas:
            x_coords = sorted([area[0], area[2]])
            y_coords = sorted([area[1], area[3]])
            parsed_areas.append(
                Area(
                    x_coords[0], y_coords[0],
                    x_coords[1], y_coords[0],
                    x_coords[1], y_coords[1],
                    x_coords[0], y_coords[1]
                )
            )
        return parsed_areas

    @staticmethod
    def read_int_8(data: bytes, offset: int = 0):
        return int.from_bytes(data[offset:offset + 1], byteorder='big', signed=True)

    @staticmethod
    def read_int_8_le(data: bytes, offset: int = 0):
        return int.from_bytes(data[offset:offset + 1], byteorder='little', signed=True)

    @staticmethod
    def read_int_16(data: bytes, offset: int = 0):
        return int.from_bytes(data[offset:offset + 2], byteorder='big', signed=True)

    @staticmethod
    def read_int_16_le(data: bytes, offset: int = 0):
        return int.from_bytes(data[offset:offset + 2], byteorder='little', signed=True)

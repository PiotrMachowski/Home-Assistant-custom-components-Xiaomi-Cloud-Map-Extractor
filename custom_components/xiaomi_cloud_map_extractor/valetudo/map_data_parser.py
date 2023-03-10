import json
import logging
from typing import Tuple

from custom_components.xiaomi_cloud_map_extractor.common.map_data import Area, MapData, Path, Point, Room, Wall, \
    ImageData
from custom_components.xiaomi_cloud_map_extractor.common.map_data_parser import MapDataParser
from custom_components.xiaomi_cloud_map_extractor.valetudo.image_handler import ImageHandlerValetudo

_LOGGER = logging.getLogger(__name__)


class MapDataParserValetudo(MapDataParser):
    @staticmethod
    def map_to_image(point: Point, height: int) -> Point:
        return Point(point.x, height - point.y)

    @staticmethod
    def parse_points(coordinates) -> list[Point]:
        points = []

        for index in range(0, len(coordinates), 2):
            points.append(Point(coordinates[index], coordinates[index + 1]))

        return points

    @staticmethod
    def parse_point_map_entity(entity) -> Point:
        return Point(entity["points"][0], entity["points"][1], entity["metaData"]["angle"])

    @staticmethod
    def parse_polygon_map_entity(entity) -> Area:
        points = MapDataParserValetudo.parse_points(entity["points"])

        return Area(points[0].x, points[0].y,
                    points[1].x, points[1].y,
                    points[2].x, points[2].y,
                    points[3].x, points[3].y)

    @staticmethod
    def parse_line_map_entity(entity) -> Wall:
        points = MapDataParserValetudo.parse_points(entity["points"])

        return Wall(points[0].x, points[0].y, points[1].x, points[1].y)

    @staticmethod
    def decompress_pixels(compressed_pixels: list[int]) -> list[int]:
        pixels = []
        for i in range(0, len(compressed_pixels), 3):
            x_start = compressed_pixels[i]
            y = compressed_pixels[i + 1]
            count = compressed_pixels[i + 2]
            for j in range(0, count):
                pixels.append((x_start + j))
                pixels.append(y)
        return pixels

    @staticmethod
    def parse_walls(layer) -> list[int]:
        return MapDataParserValetudo.decompress_pixels(layer["compressedPixels"])

    @staticmethod
    def parse_room(layer, pixel_size) -> Tuple[Room, list[int]]:

        dimensions = layer["dimensions"]
        meta_data = layer["metaData"]
        name = None
        if "name" in meta_data:
            name = meta_data["name"]
        segment_id = int(meta_data["segmentId"])
        xmin = dimensions["x"]["min"]
        xmax = dimensions["x"]["max"]
        ymin = dimensions["y"]["min"]
        ymax = dimensions["y"]["max"]
        xavg = dimensions["x"]["avg"] * pixel_size
        yavg = dimensions["y"]["avg"] * pixel_size

        return Room(segment_id, xmin, ymin, xmax, ymax, name, xavg, yavg), MapDataParserValetudo.decompress_pixels(
            layer["compressedPixels"])

    @staticmethod
    def parse_path_map_entity(entity) -> list[Point]:
        return MapDataParserValetudo.parse_points(entity["points"])

    @staticmethod
    def decode_map(raw_map: str, colors, drawables, texts, sizes, image_config) -> MapData:

        map_data = MapData()
        map_data.no_go_areas = []
        map_data.no_mopping_areas = []
        map_data.walls = []

        map_object = json.loads(raw_map)

        pixel_size = int(map_object["pixelSize"])

        paths = []

        for entity in map_object["entities"]:
            if entity["type"] == "robot_position":
                map_data.vacuum_position = MapDataParserValetudo.parse_point_map_entity(entity)
                # Fix for common\map_data_parser drawing symbol rotated by -90°
                map_data.vacuum_position.a = map_data.vacuum_position.a - 90
            elif entity["type"] == "charger_location":
                map_data.charger = MapDataParserValetudo.parse_point_map_entity(entity)
                # Fix for common\map_data_parser drawing symbol rotated by -90°
                map_data.charger.a = map_data.charger.a - 90
            elif entity["type"] == "no_go_area":
                map_data.no_go_areas.append(MapDataParserValetudo.parse_polygon_map_entity(entity))
            elif entity["type"] == "no_mop_area":
                map_data.no_mopping_areas.append(MapDataParserValetudo.parse_polygon_map_entity(entity))
            elif entity["type"] == "virtual_wall":
                map_data.walls.append(MapDataParserValetudo.parse_line_map_entity(entity))
            elif entity["type"] == "path":
                paths.append(MapDataParserValetudo.parse_path_map_entity(entity))

        map_data.path = Path(None, None, None, paths)

        walls = None
        rooms = []
        x_min = 0
        x_max = 0
        y_min = 0
        y_max = 0

        for layer in map_object["layers"]:
            if layer["type"] == "wall":
                if walls is not None:
                    _LOGGER.warning("Multiple wall layers detected in map data!")
                else:
                    walls = MapDataParserValetudo.parse_walls(layer)
                    x_min = layer["dimensions"]["x"]["min"]
                    x_max = layer["dimensions"]["x"]["max"]
                    y_min = layer["dimensions"]["y"]["min"]
                    y_max = layer["dimensions"]["y"]["max"]

            elif layer["type"] == "segment":
                rooms.append(MapDataParserValetudo.parse_room(layer, pixel_size))

        map_data.rooms = dict(map(lambda x: (x[0].number, x[0]), rooms))

        original_width = map_object["size"]["x"]
        original_height = map_object["size"]["y"]

        left = x_min
        width = x_max - x_min
        top = y_min
        height = y_max - y_min

        image, left, top = ImageHandlerValetudo.draw(walls,
                                                     rooms,
                                                     width,
                                                     height,
                                                     colors,
                                                     image_config,
                                                     pixel_size,
                                                     left,
                                                     top)

        map_data.image = ImageData(
            image.width * image.height,
            -top * pixel_size,
            left * pixel_size,
            image.height,
            image.width,
            image_config,
            image,
            lambda p: MapDataParserValetudo.map_to_image(p, image.height))

        MapDataParserValetudo.draw_elements(colors, drawables, sizes, map_data, image_config)

        return map_data

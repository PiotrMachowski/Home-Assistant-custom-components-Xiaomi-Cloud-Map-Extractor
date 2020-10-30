from typing import List, Dict, Optional

from .const import *
from .image_handler import ImageHandler


class MapDataParser:
    CHARGER = 1
    IMAGE = 2
    PATH = 3
    GOTO_PATH = 4
    GOTO_PREDICTED_PATH = 5
    CURRENTLY_CLEANED_ZONES = 6
    GOTO_TARGET = 7
    ROBOT_POSITION = 8
    NO_GO_AREAS = 9
    VIRTUAL_WALLS = 10
    BLOCKS = 11
    NO_MOPPING_AREAS = 12
    OBSTACLES = 13
    DIGEST = 1024
    MM = 50
    SIZE = 1024

    @staticmethod
    def parse(raw: bytes, colors, drawables, texts, sizes, image_config):
        map_data = MapData()
        map_header_length = MapDataParser.get_int16(raw, 0x02)
        map_data.major_version = MapDataParser.get_int16(raw, 0x08)
        map_data.minor_version = MapDataParser.get_int16(raw, 0x0A)
        map_data.map_index = MapDataParser.get_int32(raw, 0x0C)
        map_data.map_sequence = MapDataParser.get_int32(raw, 0x10)
        block_start_position = map_header_length
        img_start = None
        while block_start_position < len(raw):
            block_header_length = MapDataParser.get_int16(raw, block_start_position + 0x02)
            header = MapDataParser.get_bytes(raw, block_start_position, block_header_length)
            block_type = MapDataParser.get_int16(header, 0x00)
            block_data_length = MapDataParser.get_int32(header, 0x04)
            block_data_start = block_start_position + block_header_length
            data = MapDataParser.get_bytes(raw, block_data_start, block_data_length)
            if block_type == MapDataParser.CHARGER:
                map_data.charger = MapDataParser.parse_charger(block_start_position, raw)
            elif block_type == MapDataParser.IMAGE:
                img_start = block_start_position
                image, rooms = MapDataParser.parse_image(block_data_length, block_header_length, data, header, colors,
                                                         image_config)
                map_data.image = image
                map_data.rooms = rooms
            elif block_type == MapDataParser.ROBOT_POSITION:
                map_data.vacuum_position = MapDataParser.parse_vacuum_position(block_data_length, data)
            elif block_type == MapDataParser.PATH:
                map_data.path = MapDataParser.parse_path(block_start_position, header, raw)
            elif block_type == MapDataParser.GOTO_PATH:
                map_data.goto_path = MapDataParser.parse_path(block_start_position, header, raw)
            elif block_type == MapDataParser.GOTO_PREDICTED_PATH:
                map_data.predicted_path = MapDataParser.parse_path(block_start_position, header, raw)
            elif block_type == MapDataParser.CURRENTLY_CLEANED_ZONES:
                map_data.zones = MapDataParser.parse_zones(data, header)
            elif block_type == MapDataParser.GOTO_TARGET:
                map_data.goto = MapDataParser.parse_goto_target(data)
            elif block_type == MapDataParser.DIGEST:
                map_data.is_valid = True
            elif block_type == MapDataParser.VIRTUAL_WALLS:
                map_data.walls = MapDataParser.parse_walls(data, header)
            elif block_type == MapDataParser.NO_GO_AREAS:
                map_data.no_go_areas = MapDataParser.parse_area(header, data)
            elif block_type == MapDataParser.NO_MOPPING_AREAS:
                map_data.no_mopping_areas = MapDataParser.parse_area(header, data)
            elif block_type == MapDataParser.OBSTACLES:
                map_data.obstacles = MapDataParser.parse_obstacles(data, header)
            elif block_type == MapDataParser.BLOCKS:
                block_pairs = MapDataParser.get_int16(header, 0x08)
                map_data.blocks = MapDataParser.get_bytes(data, 0, block_pairs)
            block_start_position = block_start_position + block_data_length + (header[2] & 0xFF)
        if not map_data.image.is_empty:
            MapDataParser.draw_elements(colors, drawables, sizes, map_data)
            if len(map_data.rooms) > 0 and map_data.vacuum_position is not None:
                map_data.vacuum_room = MapDataParser.get_current_vacuum_room(img_start, raw, map_data.vacuum_position)
            ImageHandler.rotate(map_data.image)
            ImageHandler.draw_texts(map_data.image, texts)
        return map_data

    @staticmethod
    def get_current_vacuum_room(block_start_position, raw, vacuum_position):
        block_header_length = MapDataParser.get_int16(raw, block_start_position + 0x02)
        header = MapDataParser.get_bytes(raw, block_start_position, block_header_length)
        block_data_length = MapDataParser.get_int32(header, 0x04)
        block_data_start = block_start_position + block_header_length
        data = MapDataParser.get_bytes(raw, block_data_start, block_data_length)
        image_top = MapDataParser.get_int32(header, block_header_length - 16)
        image_left = MapDataParser.get_int32(header, block_header_length - 12)
        image_width = MapDataParser.get_int32(header, block_header_length - 4)
        x = round(vacuum_position.x / MapDataParser.MM - image_left)
        y = round(vacuum_position.y / MapDataParser.MM - image_top)
        room = ImageHandler.get_room_at_pixel(data, image_width, x, y)
        return room

    @staticmethod
    def parse_image(block_data_length, block_header_length, data, header, colors, image_config):
        image_size = block_data_length
        image_top = MapDataParser.get_int32(header, block_header_length - 16)
        image_left = MapDataParser.get_int32(header, block_header_length - 12)
        image_height = MapDataParser.get_int32(header, block_header_length - 8)
        image_width = MapDataParser.get_int32(header, block_header_length - 4)
        if image_width \
                - image_width * (image_config[CONF_TRIM][CONF_LEFT] + image_config[CONF_TRIM][CONF_RIGHT]) / 100 \
                < MINIMAL_IMAGE_WIDTH:
            image_config[CONF_TRIM][CONF_LEFT] = 0
            image_config[CONF_TRIM][CONF_RIGHT] = 0
        if image_height \
                - image_height * (image_config[CONF_TRIM][CONF_TOP] + image_config[CONF_TRIM][CONF_BOTTOM]) / 100 \
                < MINIMAL_IMAGE_HEIGHT:
            image_config[CONF_TRIM][CONF_TOP] = 0
            image_config[CONF_TRIM][CONF_BOTTOM] = 0
        image, rooms = ImageHandler.parse(data, image_width, image_height, colors, image_config)
        for number, room in rooms.items():
            rooms[number] = Zone((room[0] + image_left) * MapDataParser.MM,
                                 (room[1] + image_top) * MapDataParser.MM,
                                 (room[2] + image_left) * MapDataParser.MM,
                                 (room[3] + image_top) * MapDataParser.MM)
        return ImageData(image_size,
                         image_top,
                         image_left,
                         image_height,
                         image_width,
                         image_config,
                         image), rooms

    @staticmethod
    def parse_goto_target(data):
        x = MapDataParser.get_int16(data, 0x00)
        y = MapDataParser.get_int16(data, 0x02)
        return Point(x, y)

    @staticmethod
    def parse_vacuum_position(block_data_length, data):
        x = MapDataParser.get_int32(data, 0x00)
        y = MapDataParser.get_int32(data, 0x04)
        a = None
        if block_data_length > 8:
            a = MapDataParser.get_int32(data, 0x08)
        return Point(x, y, a)

    @staticmethod
    def parse_charger(block_start_position, raw):
        x = MapDataParser.get_int32(raw, block_start_position + 0x08)
        y = MapDataParser.get_int32(raw, block_start_position + 0x0C)
        return Point(x, y)

    @staticmethod
    def parse_walls(data, header):
        wall_pairs = MapDataParser.get_int16(header, 0x08)
        walls = []
        for wall_start in range(0, wall_pairs * 8, 8):
            x0 = MapDataParser.get_int16(data, wall_start + 0)
            y0 = MapDataParser.get_int16(data, wall_start + 2)
            x1 = MapDataParser.get_int16(data, wall_start + 4)
            y1 = MapDataParser.get_int16(data, wall_start + 6)
            walls.append(Wall(x0, y0, x1, y1))
        return walls

    @staticmethod
    def parse_obstacles(data, header):
        obstacle_pairs = MapDataParser.get_int16(header, 0x08)
        obstacles = []
        for obstacle_start in range(0, obstacle_pairs * 5, 5):
            x0 = MapDataParser.get_int16(data, obstacle_start + 0)
            y0 = MapDataParser.get_int16(data, obstacle_start + 2)
            u = data[obstacle_start + 0] & 0xFF
            obstacles.append({x0: x0, y0: y0, u: u})
        return obstacles

    @staticmethod
    def parse_zones(data, header):
        zone_pairs = MapDataParser.get_int16(header, 0x08)
        zones = []
        for zone_start in range(0, zone_pairs * 8, 8):
            x0 = MapDataParser.get_int16(data, zone_start + 0)
            y0 = MapDataParser.get_int16(data, zone_start + 2)
            x1 = MapDataParser.get_int16(data, zone_start + 4)
            y1 = MapDataParser.get_int16(data, zone_start + 6)
            zones.append(Zone(x0, y0, x1, y1))
        return zones

    @staticmethod
    def parse_path(block_start_position, header, raw):
        path_points = []
        end_pos = MapDataParser.get_int32(header, 0x04)
        point_length = MapDataParser.get_int32(header, 0x08)
        point_size = MapDataParser.get_int32(header, 0x0C)
        angle = MapDataParser.get_int32(header, 0x10)
        start_pos = block_start_position + 0x14
        for pos in range(start_pos, start_pos + end_pos, 4):
            x = MapDataParser.get_int16(raw, pos)
            y = MapDataParser.get_int16(raw, pos + 2)
            path_points.append(Point(x, y))
        return Path(point_length, point_size, angle, path_points)

    @staticmethod
    def parse_area(header, data):
        area_pairs = MapDataParser.get_int16(header, 0x08)
        areas = []
        for area_start in range(0, area_pairs * 16, 16):
            x0 = MapDataParser.get_int16(data, area_start + 0)
            y0 = MapDataParser.get_int16(data, area_start + 2)
            x1 = MapDataParser.get_int16(data, area_start + 4)
            y1 = MapDataParser.get_int16(data, area_start + 6)
            x2 = MapDataParser.get_int16(data, area_start + 8)
            y2 = MapDataParser.get_int16(data, area_start + 10)
            x3 = MapDataParser.get_int16(data, area_start + 12)
            y3 = MapDataParser.get_int16(data, area_start + 14)
            areas.append(Area(x0, y0, x1, y1, x2, y2, x3, y3))
        return areas

    @staticmethod
    def draw_elements(colors, drawables, sizes, map_data):
        if DRAWABLE_CHARGER in drawables and map_data.charger is not None:
            ImageHandler.draw_charger(map_data.image, map_data.charger, sizes[CONF_SIZE_CHARGER_RADIUS], colors)
        if DRAWABLE_VACUUM_POSITION in drawables and map_data.vacuum_position is not None:
            ImageHandler.draw_vacuum_position(map_data.image, map_data.vacuum_position, sizes[CONF_SIZE_VACUUM_RADIUS],
                                              colors)
        if DRAWABLE_PATH in drawables and map_data.path is not None:
            ImageHandler.draw_path(map_data.image, map_data.path, colors)
        if DRAWABLE_GOTO_PATH in drawables and map_data.goto_path is not None:
            ImageHandler.draw_goto_path(map_data.image, map_data.goto_path, colors)
        if DRAWABLE_PREDICTED_PATH in drawables and map_data.predicted_path is not None:
            ImageHandler.draw_predicted_path(map_data.image, map_data.predicted_path, colors)
        if DRAWABLE_NO_GO_AREAS in drawables and map_data.no_go_areas is not None:
            ImageHandler.draw_no_go_areas(map_data.image, map_data.no_go_areas, colors)
        if DRAWABLE_NO_MOPPING_AREAS in drawables and map_data.no_mopping_areas is not None:
            ImageHandler.draw_no_mopping_areas(map_data.image, map_data.no_mopping_areas, colors)
        if DRAWABLE_VIRTUAL_WALLS in drawables and map_data.walls is not None:
            ImageHandler.draw_walls(map_data.image, map_data.walls, colors)
        if DRAWABLE_ZONES in drawables and map_data.zones is not None:
            ImageHandler.draw_zones(map_data.image, map_data.zones, colors)
        if DRAWABLE_ZONES in drawables and map_data.zones is not None:
            ImageHandler.draw_zones(map_data.image, map_data.zones, colors)

    @staticmethod
    def get_bytes(data: bytes, start_index: int, size: int):
        return data[start_index:  start_index + size]

    @staticmethod
    def get_first_int16(data: bytes):
        return MapDataParser.get_int16(data, 0)

    @staticmethod
    def get_int16(data: bytes, address: int):
        return \
            ((data[address + 0] << 0) & 0xFF) | \
            ((data[address + 1] << 8) & 0xFFFF)

    @staticmethod
    def get_int32(data: bytes, address: int):
        return \
            ((data[address + 0] << 0) & 0xFF) | \
            ((data[address + 1] << 8) & 0xFFFF) | \
            ((data[address + 2] << 16) & 0xFFFFFF) | \
            ((data[address + 3] << 24) & 0xFFFFFFFF)


class MapData:
    def __init__(self):
        self.blocks = None
        self.charger: Optional[Point] = None
        self.goto: Optional[List[Point]] = None
        self.goto_path: Optional[List[Point]] = None
        self.image: Optional[ImageData] = None
        self.no_go_areas: Optional[List[Area]] = None
        self.no_mopping_areas: Optional[List[Area]] = None
        self.obstacles = None
        self.path: Optional[List[Point]] = None
        self.predicted_path: Optional[List[Point]] = None
        self.rooms: Optional[Dict[int, Zone]] = None
        self.vacuum_position: Optional[Point] = None
        self.vacuum_room: Optional[int] = None
        self.walls: Optional[List[Wall]] = None
        self.zones: Optional[List[Zone]] = None
        self.map_name: Optional[str] = None

    def calibration(self):
        calibration_points = []
        for point in [Point(25500, 25500), Point(26500, 25500), Point(26500, 26500)]:
            img_point = point.to_img(self.image.dimensions).rotated(self.image.dimensions)
            calibration_points.append({
                "vacuum": {"x": point.x, "y": point.y},
                "map": {"x": int(img_point.x), "y": int(img_point.y)}
            })
        return calibration_points


class Point:
    def __init__(self, x, y, a=None):
        self.x = x
        self.y = y
        self.a = a

    def __str__(self):
        if self.a is None:
            return f"({self.x}, {self.y})"
        return f"({self.x}, {self.y}, a = {self.a})"

    def as_dict(self):
        if self.a is None:
            return {
                ATTR_X: self.x,
                ATTR_Y: self.y
            }
        return {
            ATTR_X: self.x,
            ATTR_Y: self.y,
            ATTR_A: self.a
        }

    def to_img(self, image_dimensions):
        x = self.x / MapDataParser.MM - image_dimensions.left
        y = self.y / MapDataParser.MM - image_dimensions.top
        y = image_dimensions.height - y - 1
        return Point(x * image_dimensions.scale, y * image_dimensions.scale)

    def rotated(self, image_dimensions):
        alpha = image_dimensions.rotation
        w = int(image_dimensions.width * image_dimensions.scale)
        h = int(image_dimensions.height * image_dimensions.scale)
        x = self.x
        y = self.y
        while alpha > 0:
            tmp = y
            y = w - x
            x = tmp
            tmp = h
            h = w
            w = tmp
            alpha = alpha - 90
        return Point(x, y)


class ImageDimensions:
    def __init__(self, top, left, height, width, scale, rotation):
        self.top = top
        self.left = left
        self.height = height
        self.width = width
        self.scale = scale
        self.rotation = rotation


class ImageData:
    def __init__(self, size, top, left, height, width, image_config, data):
        trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * width / 100)
        trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * width / 100)
        trim_top = int(image_config[CONF_TRIM][CONF_TOP] * height / 100)
        trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * height / 100)
        scale = image_config[CONF_SCALE]
        rotation = image_config[CONF_ROTATE]
        self.size = size
        self.dimensions = ImageDimensions(top + trim_bottom,
                                          left + trim_left,
                                          height - trim_top - trim_bottom,
                                          width - trim_left - trim_right,
                                          scale,
                                          rotation)
        self.is_empty = height == 0 or width == 0
        self.data = data

    def as_dict(self):
        return {
            ATTR_SIZE: self.size,
            ATTR_OFFSET_Y: self.dimensions.top,
            ATTR_OFFSET_X: self.dimensions.left,
            ATTR_HEIGHT: self.dimensions.height,
            ATTR_SCALE: self.dimensions.scale,
            ATTR_ROTATION: self.dimensions.rotation,
            ATTR_WIDTH: self.dimensions.width
        }


class Path:
    def __init__(self, point_length, point_size, angle, path: list):
        self.point_length = point_length
        self.point_size = point_size
        self.angle = angle
        self.path = path

    def as_dict(self):
        return {
            ATTR_POINT_LENGTH: self.point_length,
            ATTR_POINT_SIZE: self.point_size,
            ATTR_ANGLE: self.angle,
            ATTR_PATH: self.path
        }


class Zone:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def __str__(self):
        return f"[{self.x0}, {self.y0}, {self.x1}, {self.y1}]"

    def as_dict(self):
        return {
            ATTR_X0: self.x0,
            ATTR_Y0: self.y0,
            ATTR_X1: self.x1,
            ATTR_Y1: self.y1
        }

    def as_area(self):
        return Area(self.x0, self.y0, self.x0, self.y1, self.x1, self.y1, self.x1, self.y0)


class Wall:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def __str__(self):
        return f"[{self.x0}, {self.y0}, {self.x1}, {self.y1}]"

    def as_dict(self):
        return {
            ATTR_X0: self.x0,
            ATTR_Y0: self.y0,
            ATTR_X1: self.x1,
            ATTR_Y1: self.y1
        }

    def to_img(self, image_dimensions):
        p0 = Point(self.x0, self.y0).to_img(image_dimensions)
        p1 = Point(self.x1, self.y1).to_img(image_dimensions)
        return Wall(p0.x, p0.y, p1.x, p1.y)

    def as_list(self):
        return [self.x0, self.y0, self.x1, self.y1]


class Area:
    def __init__(self, x0, y0, x1, y1, x2, y2, x3, y3):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.x3 = x3
        self.y3 = y3

    def __str__(self):
        return f"[{self.x0}, {self.y0}, {self.x1}, {self.y1}, {self.x2}, {self.y2}, {self.x3}, {self.y3}]"

    def as_dict(self):
        return {
            ATTR_X0: self.x0,
            ATTR_Y0: self.y0,
            ATTR_X1: self.x1,
            ATTR_Y1: self.y1,
            ATTR_X2: self.x2,
            ATTR_Y2: self.y2,
            ATTR_X3: self.x3,
            ATTR_Y3: self.y3
        }

    def as_list(self):
        return [self.x0, self.y0, self.x1, self.y1, self.x2, self.y2, self.x3, self.y3]

    def to_img(self, image_dimensions):
        p0 = Point(self.x0, self.y0).to_img(image_dimensions)
        p1 = Point(self.x1, self.y1).to_img(image_dimensions)
        p2 = Point(self.x2, self.y2).to_img(image_dimensions)
        p3 = Point(self.x3, self.y3).to_img(image_dimensions)
        return Area(p0.x, p0.y, p1.x, p1.y, p2.x, p2.y, p3.x, p3.y)

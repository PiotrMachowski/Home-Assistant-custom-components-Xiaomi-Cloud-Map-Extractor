import logging
from enum import IntEnum
from typing import Tuple

import numpy as numpy
from PIL import Image

from custom_components.xiaomi_cloud_map_extractor.common.image_handler import ImageHandler
from custom_components.xiaomi_cloud_map_extractor.common.map_data import Room
from custom_components.xiaomi_cloud_map_extractor.const import CONF_SCALE, CONF_TRIM, CONF_LEFT, CONF_RIGHT, CONF_TOP, \
    CONF_BOTTOM, COLOR_MAP_WALL, COLOR_ROOM_PREFIX

_LOGGER = logging.getLogger(__name__)


class ImageHandlerValetudo(ImageHandler):
    class PixelTypes(IntEnum):
        NONE = 0
        FLOOR = 1
        WALL = 2

    @staticmethod
    def draw_pixel(image, x: int, y: int, pixel_size: int, room_color):
        x_start = x * pixel_size
        x_end = x_start + pixel_size
        y_start = y * pixel_size
        y_end = y_start + pixel_size

        image[y_start:y_end, x_start:x_end] = room_color

    @staticmethod
    def draw(walls: list[int],
             rooms: list[Tuple[Room, list[int]]],
             image_width: int,
             image_height: int,
             colors,
             image_config,
             pixel_size: int,
             left: int,
             top: int) -> (Image, int, int):
        scale = image_config[CONF_SCALE]
        conf_trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * image_width / 100)
        conf_trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * image_width / 100)
        conf_trim_top = int(image_config[CONF_TRIM][CONF_TOP] * image_height / 100)
        conf_trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * image_height / 100)
        trimmed_height = image_height - conf_trim_top - conf_trim_bottom
        trimmed_width = image_width - conf_trim_left - conf_trim_right
        image = Image.new("RGBA", (trimmed_width * pixel_size, trimmed_height * pixel_size))
        image_data = numpy.array(image)
        if image_width == 0 or image_height == 0:
            return ImageHandler.create_empty_map_image(colors), left + conf_trim_left, top + conf_trim_top

        trim_left = conf_trim_left + left
        trim_top = conf_trim_top + top

        for room in rooms:
            room_data, px_room = room
            default = ImageHandler.ROOM_COLORS[room_data.number >> 1]
            room_color = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{room_data.number}", colors, default)
            if len(room_color) == 3:
                room_color = (room_color + (255,))

            for i in range(0, len(px_room), 2):
                x = px_room[i] - trim_left
                y = px_room[i + 1] - trim_top
                if 0 <= x <= trimmed_width and 0 <= y <= trimmed_height:
                    ImageHandlerValetudo.draw_pixel(image_data, x, y, pixel_size, room_color)

        wall_color = ImageHandler.__get_color__(COLOR_MAP_WALL, colors)
        if len(wall_color) == 3:
            wall_color = (wall_color + (255,))

        for i in range(0, len(walls), 2):
            x = walls[i] - trim_left
            y = walls[i + 1] - trim_top
            if 0 <= x <= trimmed_width and 0 <= y <= trimmed_height:
                ImageHandlerValetudo.draw_pixel(image_data, x, y, pixel_size, wall_color)

        image = Image.fromarray(image_data, "RGBA")

        if scale != 1 and image_width != 0 and image_height != 0:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)

        return image, trim_left, trim_top

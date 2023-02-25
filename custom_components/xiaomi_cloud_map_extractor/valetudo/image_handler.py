import logging
from enum import IntEnum
from typing import Tuple

from PIL import Image
from PIL.Image import Image as ImageType

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
    def draw_pixel(image: Image, x: int, y: int, pixel_size: int, room_color):
        x = x * pixel_size
        y = y * pixel_size
        for j in range(0, pixel_size):
            for k in range(0, pixel_size):
                image.putpixel((x + j, y + k), room_color)

    @staticmethod
    def draw(walls: list[int], rooms: list[Tuple[Room, list[int]]], image_width, image_height, colors, image_config,
             pixel_size) -> ImageType:
        scale = image_config[CONF_SCALE]
        trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * image_width / 100)
        trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * image_width / 100)
        trim_top = int(image_config[CONF_TRIM][CONF_TOP] * image_height / 100)
        trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * image_height / 100)
        trimmed_height = image_height - trim_top - trim_bottom
        trimmed_width = image_width - trim_left - trim_right
        image = Image.new("RGBA", (trimmed_width, trimmed_height))
        if image_width == 0 or image_height == 0:
            return ImageHandler.create_empty_map_image(colors)

        trimmed_x_max = trim_left + trimmed_width
        trimmed_y_max = trim_top + trimmed_height

        for room in rooms:
            room_data, px_room = room
            default = ImageHandler.ROOM_COLORS[room_data.number >> 1]
            room_color = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{room_data.number}", colors, default)

            for i in range(0, len(px_room), 2):
                x = px_room[i]
                y = px_room[i + 1]
                if trim_left <= x <= trimmed_x_max and trim_top <= y <= trimmed_y_max:
                    ImageHandlerValetudo.draw_pixel(image, x - trim_left, y + trim_top, pixel_size, room_color)

        wall_color = ImageHandler.__get_color__(COLOR_MAP_WALL, colors)

        for i in range(0, len(walls), 2):
            x = walls[i]
            y = walls[i + 1]
            if trim_left <= x <= trimmed_x_max and trim_top <= y <= trimmed_y_max:
                ImageHandlerValetudo.draw_pixel(image, x - trim_left, y + trim_top, pixel_size, wall_color)

        if scale != 1 and image_width != 0 and image_height != 0:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)

        return image

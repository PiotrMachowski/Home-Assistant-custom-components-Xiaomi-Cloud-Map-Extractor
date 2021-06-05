import logging
from typing import Tuple

from PIL import Image
from PIL.Image import Image as ImageType

from .const import *
from .image_handler import ImageHandler

_LOGGER = logging.getLogger(__name__)


class ImageHandlerV2(ImageHandler):
    MAP_OUTSIDE = 0x00
    MAP_WALL = 0xff
    MAP_SCAN = 0x01
    MAP_ROOM_MIN = 10
    MAP_ROOM_MAX = 59
    MAP_SELECTED_ROOM_MIN = 60
    MAP_SELECTED_ROOM_MAX = 109

    @staticmethod
    def parse(buf, width, height, colors, image_config) -> Tuple[ImageType, dict, dict]:
        rooms = {}
        areas = {}
        scale = image_config[CONF_SCALE]
        trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * width / 100)
        trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * width / 100)
        trim_top = int(image_config[CONF_TRIM][CONF_TOP] * height / 100)
        trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * height / 100)
        trimmed_height = height - trim_top - trim_bottom
        trimmed_width = width - trim_left - trim_right
        image = Image.new('RGBA', (trimmed_width, trimmed_height))
        if trimmed_width == 0 or trimmed_height == 0:
            return ImageHandler.create_empty_map(colors)
        pixels = image.load()
        buf.skip('trim_bottom', trim_bottom * width)
        u = set()
        for img_y in range(trimmed_height):
            buf.skip('trim_left', trim_left)
            for img_x in range(trimmed_width):
                pixel_type = buf.get_uint8('pixel')
                x = img_x
                y = trimmed_height - 1 - img_y
                if pixel_type == ImageHandlerV2.MAP_OUTSIDE:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_OUTSIDE, colors)
                elif pixel_type == ImageHandlerV2.MAP_WALL:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_WALL_V2, colors)
                elif pixel_type == ImageHandlerV2.MAP_SCAN:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_SCAN, colors)
                elif ImageHandlerV2.MAP_ROOM_MIN <= pixel_type <= ImageHandlerV2.MAP_SELECTED_ROOM_MAX:
                    room_x = img_x + trim_left
                    room_y = img_y + trim_bottom
                    if pixel_type < ImageHandlerV2.MAP_SELECTED_ROOM_MIN:
                        room_number = pixel_type
                    else:
                        room_number = pixel_type - ImageHandlerV2.MAP_SELECTED_ROOM_MIN + ImageHandlerV2.MAP_ROOM_MIN
                        if room_number not in areas:
                            areas[room_number] = (room_x, room_y, room_x, room_y)
                        else:
                            areas[room_number] = (min(areas[room_number][0], room_x),
                                                  min(areas[room_number][1], room_y),
                                                  max(areas[room_number][2], room_x),
                                                  max(areas[room_number][3], room_y))
                    if room_number not in rooms:
                        rooms[room_number] = (room_x, room_y, room_x, room_y)
                    else:
                        rooms[room_number] = (min(rooms[room_number][0], room_x),
                                              min(rooms[room_number][1], room_y),
                                              max(rooms[room_number][2], room_x),
                                              max(rooms[room_number][3], room_y))
                    default = ImageHandler.ROOM_COLORS[room_number % len(ImageHandler.ROOM_COLORS)]
                    pixels[x, y] = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{room_number}", colors, default)
                else:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_UNKNOWN, colors)
                    u.add(pixel_type)
            buf.skip('trim_right', trim_right)
        buf.skip('trim_top', trim_top * width)
        if image_config["scale"] != 1 and trimmed_width != 0 and trimmed_height != 0:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)
        if len(u) > 0:
            _LOGGER.warning('unknown pixel_types: %s', u)
        return image, rooms, areas

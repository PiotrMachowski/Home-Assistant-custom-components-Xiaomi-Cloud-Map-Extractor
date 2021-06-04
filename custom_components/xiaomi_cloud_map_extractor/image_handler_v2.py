import logging
from typing import Tuple

from PIL import Image
from PIL.Image import Image as ImageType

from .const import *
from .image_handler import ImageHandler

_LOGGER = logging.getLogger(__name__)


class ImageHandlerV2(ImageHandler):

    @staticmethod
    def parse(buf, width, height, colors, image_config) -> Tuple[ImageType, dict]:
        rooms = {}
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
        buf.skip('trim_top', trim_bottom * width)
        u = set()
        for img_y in range(trimmed_height):
            buf.skip('trim_left', trim_left)
            for img_x in range(trimmed_width):
                pixel_type = buf.get_uint8('pixel')
                x = img_x
                y = trimmed_height - 1 - img_y
                if pixel_type == 0:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_OUTSIDE, colors)
                elif pixel_type == 255:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_GREY_WALL, colors)
                elif pixel_type == 1:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_SCAN, colors)
                elif 10 <= pixel_type < 60:
                    room_number = pixel_type
                    room_x = x
                    room_y = y
                    if room_number not in rooms:
                        rooms[room_number] = (room_x, room_y, room_x, room_y)
                    else:
                        rooms[room_number] = (min(rooms[room_number][0], room_x),
                                              min(rooms[room_number][1], room_y),
                                              max(rooms[room_number][2], room_x),
                                              max(rooms[room_number][3], room_y))
                    default = ImageHandler.ROOM_COLORS[room_number >> 1]
                    pixels[x, y] = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{room_number}", colors, default)
                else:
                    u.add(pixel_type)
            buf.skip('trim_right', trim_right)
        buf.skip('trim_bottom', trim_top * width)
        if image_config["scale"] != 1 and trimmed_width != 0 and trimmed_height != 0:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)
        if len(u) > 0:
            _LOGGER.warning('unknown pixel_types: %s', u)
        return image, rooms

import logging
from enum import IntEnum
from typing import Dict, Tuple

from PIL import Image
from PIL.Image import Image as ImageType

from custom_components.xiaomi_cloud_map_extractor.common.image_handler import ImageHandler
from custom_components.xiaomi_cloud_map_extractor.common.map_data import Room
from custom_components.xiaomi_cloud_map_extractor.const import \
    CONF_SCALE, CONF_TRIM, CONF_LEFT, CONF_RIGHT, CONF_TOP, CONF_BOTTOM, \
    COLOR_MAP_OUTSIDE, COLOR_MAP_INSIDE, COLOR_MAP_WALL, COLOR_ROOM_PREFIX

_LOGGER = logging.getLogger(__name__)


class ImageHandlerDreame(ImageHandler):
    class PixelTypes(IntEnum):
        NONE = 0
        FLOOR = 1
        WALL = 2

    @staticmethod
    def parse(raw_data: bytes, header, colors, image_config, map_data_type: str) -> Tuple[ImageType, Dict[int, Room]]:
        scale = image_config[CONF_SCALE]
        trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * header.image_width / 100)
        trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * header.image_width / 100)
        trim_top = int(image_config[CONF_TRIM][CONF_TOP] * header.image_height / 100)
        trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * header.image_height / 100)
        trimmed_height = header.image_height - trim_top - trim_bottom
        trimmed_width = header.image_width - trim_left - trim_right
        image = Image.new('RGBA', (trimmed_width, trimmed_height))
        if header.image_width == 0 or header.image_height == 0:
            return ImageHandler.create_empty_map_image(colors), {}
        pixels = image.load()
        rooms = {}

        for img_y in range(trimmed_height):
            for img_x in range(trimmed_width):
                x = img_x
                y = trimmed_height - img_y - 1
                room_x = img_x + trim_left
                room_y = img_y + trim_bottom

                # TODO : use MapDataParserDreame.MapDataTypes enum
                if map_data_type == "regular":
                    px = raw_data[img_x + trim_left + header.image_width * (img_y + trim_bottom)]
                    segment_id = px >> 2
                    if 0 < segment_id < 62:
                        if segment_id not in rooms:
                            rooms[segment_id] = Room(segment_id, room_x, room_y, room_x, room_y)
                        rooms[segment_id] = Room(segment_id,
                                                 min(rooms[segment_id].x0, room_x), min(rooms[segment_id].y0, room_y),
                                                 max(rooms[segment_id].x1, room_x), max(rooms[segment_id].y1, room_y))
                        default = ImageHandler.ROOM_COLORS[segment_id >> 1]
                        pixels[x, y] = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{segment_id}", colors, default)
                    else:
                        masked_px = px & 0b00000011

                        if masked_px == ImageHandlerDreame.PixelTypes.NONE:
                            pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_OUTSIDE, colors)
                        elif masked_px == ImageHandlerDreame.PixelTypes.FLOOR:
                            pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_INSIDE, colors)
                        elif masked_px == ImageHandlerDreame.PixelTypes.WALL:
                            pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_WALL, colors)
                        else:
                            _LOGGER.warning(f'unhandled pixel type: {px}')
                elif map_data_type == "rism":
                    px = raw_data[img_x + trim_left + header.image_width * (img_y + trim_bottom)]
                    segment_id = px & 0b01111111
                    wall_flag = px >> 7

                    if wall_flag:
                        pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_WALL, colors)
                    elif segment_id > 0:
                        if segment_id not in rooms:
                            rooms[segment_id] = Room(segment_id, room_x, room_y, room_x, room_y)
                        rooms[segment_id] = Room(segment_id,
                                                 min(rooms[segment_id].x0, room_x), min(rooms[segment_id].y0, room_y),
                                                 max(rooms[segment_id].x1, room_x), max(rooms[segment_id].y1, room_y))
                        default = ImageHandler.ROOM_COLORS[segment_id >> 1]
                        pixels[x, y] = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{segment_id}", colors, default)

        if image_config["scale"] != 1 and header.image_width != 0 and header.image_height != 0:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)
        return image, rooms

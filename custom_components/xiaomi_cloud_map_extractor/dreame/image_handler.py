import logging
from enum import IntEnum

from PIL import Image
from PIL.Image import Image as ImageType

from custom_components.xiaomi_cloud_map_extractor.common.image_handler import ImageHandler
from custom_components.xiaomi_cloud_map_extractor.const import \
    CONF_SCALE, CONF_TRIM, CONF_LEFT, CONF_RIGHT, CONF_TOP, CONF_BOTTOM, \
    COLOR_MAP_OUTSIDE, COLOR_MAP_INSIDE, COLOR_MAP_WALL

_LOGGER = logging.getLogger(__name__)


class ImageHandlerDreame(ImageHandler):

    class PixelTypes(IntEnum):
        NONE = 0
        FLOOR = 1
        WALL = 2

    @staticmethod
    def parse(raw_data: bytes, header, colors, image_config, map_data_type: str) -> ImageType:
        scale = image_config[CONF_SCALE]
        trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * header.image_width / 100)
        trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * header.image_width / 100)
        trim_top = int(image_config[CONF_TRIM][CONF_TOP] * header.image_height / 100)
        trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * header.image_height / 100)
        trimmed_height = header.image_height - trim_top - trim_bottom
        trimmed_width = header.image_width - trim_left - trim_right
        image = Image.new('RGBA', (trimmed_width, trimmed_height))
        if header.image_width == 0 or header.image_height == 0:
            return ImageHandler.create_empty_map_image(colors)
        pixels = image.load()

        for i in range(trimmed_height):
            for j in range(trimmed_width):
                x = j
                y = header.image_height - i - 1

                # TODO : use MapDataParserDreame.MapDataTypes enum
                if map_data_type == "regular":
                    px = raw_data[(i * header.image_width) + j]
                    segment_id = px >> 2
                    if 0 < segment_id < 62:
                        pass
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
                    px = raw_data[(i * header.image_width) + j]
                    segment_id = px & 0b01111111
                    wall_flag = px >> 7

                    if wall_flag:
                        pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_WALL, colors)
                    elif segment_id > 0:
                        pass

        if image_config["scale"] != 1 and header.image_width != 0 and header.image_height != 0:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)
        return image

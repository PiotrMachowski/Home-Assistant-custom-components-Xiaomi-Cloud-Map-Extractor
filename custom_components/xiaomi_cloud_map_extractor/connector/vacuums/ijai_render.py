"""Rendering helpers for Ijai maps.

Ijai vacuums report a fixed size map canvas (e.g. 800x800) regardless of how
much of it has been explored, so with the default settings the floor plan ends
up as a small island in a large empty background, with tiny icons and room
names. These helpers adapt the image configuration and the element sizes to
each map before it is parsed and drawn. The map format parsing itself stays in
`vacuum_map_parser_ijai`.
"""
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from PIL import Image, ImageFont
from vacuum_map_parser_base.config.color import ColorsPalette, SupportedColor
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig, TrimConfig
from vacuum_map_parser_base.config.size import Size, Sizes
from vacuum_map_parser_base.config.text import Text
from vacuum_map_parser_base.image_generator import ImageGenerator
from vacuum_map_parser_base.map_data import ImageData, MapData
from vacuum_map_parser_ijai import RobotMap_pb2 as RobotMap
from vacuum_map_parser_ijai.image_parser import IjaiImageParser
from vacuum_map_parser_ijai.map_data_parser import IjaiMapDataParser

_LOGGER = logging.getLogger(__name__)

# Source pixels kept around the explored area when cropping to it.
AUTO_TRIM_PADDING = 15
# The cropped map is scaled up to at least this many pixels on its longer edge.
AUTO_SCALE_TARGET_DIMENSION = 960
# Vacuum icon radius as a fraction of the rendered image width.
VACUUM_RADIUS_RATIO = 0.022
# Room name font size as a fraction of the rendered image width.
ROOM_NAME_FONT_RATIO = 0.035
ROOM_NAME_MIN_FONT_SIZE = 10
# Pillow's default font has no Turkish characters and Home Assistant OS ships no
# system fonts, so a font is bundled with the integration.
FONT_PATH = Path(__file__).parent / "fonts" / "DejaVuSans.ttf"
TRANSPARENT = (255, 255, 255, 0)


def content_bounds(map_bytes: bytes, width: int, height: int) -> tuple[int, int, int, int] | None:
    """Return (left, top, right, bottom) of the explored pixels, right/bottom inclusive."""
    if width <= 0 or height <= 0 or len(map_bytes) != width * height:
        return None
    mask = Image.frombytes("L", (width, height), map_bytes).point(
        lambda value: 0 if value == IjaiImageParser.MAP_OUTSIDE else 255)
    box = mask.getbbox()
    if box is None:
        return None
    return box[0], box[1], box[2] - 1, box[3] - 1


def fit_image_config(image_config: ImageConfig, width: int, height: int,
                     bounds: tuple[int, int, int, int] | None) -> ImageConfig:
    """Tighten trim and scale to the explored area, never loosening what the user configured."""
    if bounds is None:
        return image_config
    min_x, min_y, max_x, max_y = bounds
    configured = image_config.trim
    trim = TrimConfig(
        left=max(configured.left, max(0, min_x - AUTO_TRIM_PADDING) / width * 100),
        right=max(configured.right, max(0, width - 1 - max_x - AUTO_TRIM_PADDING) / width * 100),
        # The map image is flipped vertically: its bottom is the lowest row index.
        bottom=max(configured.bottom, max(0, min_y - AUTO_TRIM_PADDING) / height * 100),
        top=max(configured.top, max(0, height - 1 - max_y - AUTO_TRIM_PADDING) / height * 100),
    )
    trimmed_width = width - int(trim.left * width / 100) - int(trim.right * width / 100)
    trimmed_height = height - int(trim.top * height / 100) - int(trim.bottom * height / 100)
    longer_edge = max(trimmed_width, trimmed_height)
    if longer_edge <= 0:
        return image_config
    return replace(image_config, trim=trim, scale=max(image_config.scale, AUTO_SCALE_TARGET_DIMENSION / longer_edge))


def fit_sizes(sizes: Sizes, rendered_width: float) -> Sizes:
    """Scale all element sizes so the vacuum icon takes a fixed share of the rendered image."""
    base_radius = sizes.get_size(Size.VACUUM_RADIUS)
    if not base_radius or rendered_width <= 0:
        return sizes
    factor = VACUUM_RADIUS_RATIO * rendered_width / base_radius
    return Sizes({size: sizes.get_size(size) * factor for size in Size})


class IjaiImageGenerator(ImageGenerator):
    """Image generator that draws room names with a bundled font sized relative to the map."""

    def _draw_room_names(self, map_data: MapData) -> None:
        if map_data.rooms is None or map_data.image is None:
            return
        color = self._get_color(SupportedColor.ROOM_NAMES)
        dims = map_data.image.dimensions
        font_size = max(ROOM_NAME_MIN_FONT_SIZE, int(dims.width * dims.scale * ROOM_NAME_FONT_RATIO))
        font: Any
        try:
            font = ImageFont.truetype(str(FONT_PATH), font_size)
        except OSError:
            _LOGGER.warning("Unable to load font %s, using the default font", FONT_PATH)
            font = ImageFont.load_default(size=font_size)
        for room in map_data.rooms.values():
            point = room.point()
            if point is None or room.name is None:
                continue
            position = point.to_img(dims)
            self._draw_name(map_data.image, room.name, position.x, position.y, font, color)

    @staticmethod
    def _draw_name(image: ImageData, text: str, x: float, y: float, font: Any, color: Any) -> None:
        def draw_func(draw: Any) -> None:
            left, top, right, bottom = draw.textbbox((0, 0), text, font)
            draw.text((x - (right - left) / 2, y - (bottom - top) / 2), text, font=font, fill=color)

        ImageGenerator._draw_on_new_layer(image, draw_func, ImageGenerator._use_transparency(color))


def create_parser(palette: ColorsPalette, sizes: Sizes, drawables: list[Drawable], image_config: ImageConfig,
                  texts: list[Text], decoded_map: bytes) -> IjaiMapDataParser:
    """Create a parser whose image configuration and sizes are fitted to this map."""
    robot_map = RobotMap.RobotMap()
    robot_map.ParseFromString(decoded_map)
    width, height = robot_map.mapHead.sizeX, robot_map.mapHead.sizeY
    fitted_config = fit_image_config(image_config, width, height,
                                     content_bounds(robot_map.mapData.mapData, width, height))
    trim = fitted_config.trim
    rendered_width = (width - int(trim.left * width / 100) - int(trim.right * width / 100)) * fitted_config.scale
    fitted_sizes = fit_sizes(sizes, rendered_width)
    parser = IjaiMapDataParser(palette, fitted_sizes, drawables, fitted_config, texts)
    # Draw the unexplored background transparent and the room names with the bundled font.
    parser._image_parser.color_map[IjaiImageParser.MAP_OUTSIDE] = TRANSPARENT  # pylint: disable=protected-access
    parser._image_generator = IjaiImageGenerator(  # pylint: disable=protected-access
        palette, fitted_sizes, drawables, fitted_config, texts)
    return parser

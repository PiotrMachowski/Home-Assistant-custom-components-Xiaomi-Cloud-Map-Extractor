import logging
import math
from typing import Callable, Dict, List

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as ImageType

from custom_components.xiaomi_cloud_map_extractor.common.map_data import Area, ImageData, Obstacle, Path, Point, Room, \
    Wall, Zone
from custom_components.xiaomi_cloud_map_extractor.const import *
from custom_components.xiaomi_cloud_map_extractor.types import Color, Colors, Sizes, Texts

_LOGGER = logging.getLogger(__name__)


class ImageHandler:
    COLORS = {
        COLOR_MAP_INSIDE: (32, 115, 185),
        COLOR_MAP_OUTSIDE: (19, 87, 148),
        COLOR_MAP_WALL: (100, 196, 254),
        COLOR_MAP_WALL_V2: (93, 109, 126),
        COLOR_GREY_WALL: (93, 109, 126),
        COLOR_CLEANED_AREA: (127, 127, 127, 127),
        COLOR_PATH: (147, 194, 238),
        COLOR_GOTO_PATH: (0, 255, 0),
        COLOR_PREDICTED_PATH: (255, 255, 0),
        COLOR_ZONES: (0xAD, 0xD8, 0xFF, 0x8F),
        COLOR_ZONES_OUTLINE: (0xAD, 0xD8, 0xFF),
        COLOR_VIRTUAL_WALLS: (255, 0, 0),
        COLOR_NEW_DISCOVERED_AREA: (64, 64, 64),
        COLOR_NO_GO_ZONES: (255, 33, 55, 127),
        COLOR_NO_GO_ZONES_OUTLINE: (255, 0, 0),
        COLOR_NO_MOPPING_ZONES: (163, 130, 211, 127),
        COLOR_NO_MOPPING_ZONES_OUTLINE: (163, 130, 211),
        COLOR_CHARGER: (0x66, 0xfe, 0xda, 0x7f),
        COLOR_CHARGER_OUTLINE: (0x66, 0xfe, 0xda, 0x7f),
        COLOR_ROBO: (0xff, 0xff, 0xff),
        COLOR_ROBO_OUTLINE: (0, 0, 0),
        COLOR_ROOM_NAMES: (0, 0, 0),
        COLOR_OBSTACLE: (0, 0, 0, 128),
        COLOR_IGNORED_OBSTACLE: (0, 0, 0, 128),
        COLOR_OBSTACLE_WITH_PHOTO: (0, 0, 0, 128),
        COLOR_IGNORED_OBSTACLE_WITH_PHOTO: (0, 0, 0, 128),
        COLOR_UNKNOWN: (0, 0, 0),
        COLOR_SCAN: (0xDF, 0xDF, 0xDF),
        COLOR_ROOM_1: (240, 178, 122),
        COLOR_ROOM_2: (133, 193, 233),
        COLOR_ROOM_3: (217, 136, 128),
        COLOR_ROOM_4: (52, 152, 219),
        COLOR_ROOM_5: (205, 97, 85),
        COLOR_ROOM_6: (243, 156, 18),
        COLOR_ROOM_7: (88, 214, 141),
        COLOR_ROOM_8: (245, 176, 65),
        COLOR_ROOM_9: (252, 212, 81),
        COLOR_ROOM_10: (72, 201, 176),
        COLOR_ROOM_11: (84, 153, 199),
        COLOR_ROOM_12: (133, 193, 233),
        COLOR_ROOM_13: (245, 176, 65),
        COLOR_ROOM_14: (82, 190, 128),
        COLOR_ROOM_15: (72, 201, 176),
        COLOR_ROOM_16: (165, 105, 189)
    }
    ROOM_COLORS = [COLOR_ROOM_1, COLOR_ROOM_2, COLOR_ROOM_3, COLOR_ROOM_4, COLOR_ROOM_5, COLOR_ROOM_6, COLOR_ROOM_7,
                   COLOR_ROOM_8, COLOR_ROOM_9, COLOR_ROOM_10, COLOR_ROOM_11, COLOR_ROOM_12, COLOR_ROOM_13,
                   COLOR_ROOM_14, COLOR_ROOM_15, COLOR_ROOM_16]

    @staticmethod
    def create_empty_map_image(colors: Colors, text: str = "NO MAP") -> ImageType:
        color = ImageHandler.__get_color__(COLOR_MAP_OUTSIDE, colors)
        image = Image.new('RGBA', (300, 200), color=color)
        if sum(color[0:3]) > 382:
            text_color = (0, 0, 0)
        else:
            text_color = (255, 255, 255)
        draw = ImageDraw.Draw(image, "RGBA")
        w, h = draw.textsize(text)
        draw.text(((image.size[0] - w) / 2, (image.size[1] - h) / 2), text, fill=text_color)
        return image

    @staticmethod
    def draw_path(image: ImageData, path: Path, sizes: Sizes, colors: Colors, scale: float):
        ImageHandler.__draw_path__(image, path, sizes, ImageHandler.__get_color__(COLOR_PATH, colors), scale)

    @staticmethod
    def draw_goto_path(image: ImageData, path: Path, sizes: Sizes, colors: Colors, scale: float):
        ImageHandler.__draw_path__(image, path, sizes, ImageHandler.__get_color__(COLOR_GOTO_PATH, colors), scale)

    @staticmethod
    def draw_predicted_path(image: ImageData, path: Path, sizes: Sizes, colors: Colors, scale: float):
        ImageHandler.__draw_path__(image, path, sizes, ImageHandler.__get_color__(COLOR_PREDICTED_PATH, colors), scale)

    @staticmethod
    def draw_no_go_areas(image: ImageData, areas: List[Area], colors: Colors):
        ImageHandler.__draw_areas__(image, areas,
                                    ImageHandler.__get_color__(COLOR_NO_GO_ZONES, colors),
                                    ImageHandler.__get_color__(COLOR_NO_GO_ZONES_OUTLINE, colors))

    @staticmethod
    def draw_no_mopping_areas(image: ImageData, areas: List[Area], colors: Colors):
        ImageHandler.__draw_areas__(image, areas,
                                    ImageHandler.__get_color__(COLOR_NO_MOPPING_ZONES, colors),
                                    ImageHandler.__get_color__(COLOR_NO_MOPPING_ZONES_OUTLINE, colors))

    @staticmethod
    def draw_walls(image: ImageData, walls: List[Wall], colors: Colors):
        draw = ImageDraw.Draw(image.data, 'RGBA')
        for wall in walls:
            draw.line(wall.to_img(image.dimensions).as_list(),
                      ImageHandler.__get_color__(COLOR_VIRTUAL_WALLS, colors), width=2)

    @staticmethod
    def draw_zones(image: ImageData, zones: List[Zone], colors: Colors):
        areas = [z.as_area() for z in zones]
        ImageHandler.__draw_areas__(image, areas,
                                    ImageHandler.__get_color__(COLOR_ZONES, colors),
                                    ImageHandler.__get_color__(COLOR_ZONES_OUTLINE, colors))

    @staticmethod
    def draw_charger(image: ImageData, charger: Point, sizes: Sizes, colors: Colors):
        color = ImageHandler.__get_color__(COLOR_CHARGER, colors)
        outline = ImageHandler.__get_color__(COLOR_CHARGER_OUTLINE, colors)
        radius = sizes[CONF_SIZE_CHARGER_RADIUS]
        ImageHandler.__draw_pieslice__(image, charger, radius, outline, color)

    @staticmethod
    def draw_obstacles(image: ImageData, obstacles, sizes: Sizes, colors: Colors):
        color = ImageHandler.__get_color__(COLOR_OBSTACLE, colors)
        radius = sizes[CONF_SIZE_OBSTACLE_RADIUS]
        ImageHandler.draw_all_obstacles(image, obstacles, radius, color)

    @staticmethod
    def draw_ignored_obstacles(image: ImageData, obstacles: List[Obstacle], sizes: Sizes, colors: Colors):
        color = ImageHandler.__get_color__(COLOR_IGNORED_OBSTACLE, colors)
        radius = sizes[CONF_SIZE_IGNORED_OBSTACLE_RADIUS]
        ImageHandler.draw_all_obstacles(image, obstacles, radius, color)

    @staticmethod
    def draw_obstacles_with_photo(image: ImageData, obstacles: List[Obstacle], sizes: Sizes, colors: Colors):
        color = ImageHandler.__get_color__(COLOR_OBSTACLE_WITH_PHOTO, colors)
        radius = sizes[CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS]
        ImageHandler.draw_all_obstacles(image, obstacles, radius, color)

    @staticmethod
    def draw_ignored_obstacles_with_photo(image: ImageData, obstacles: List[Obstacle], sizes: Sizes, colors: Colors):
        color = ImageHandler.__get_color__(COLOR_IGNORED_OBSTACLE_WITH_PHOTO, colors)
        radius = sizes[CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS]
        ImageHandler.draw_all_obstacles(image, obstacles, radius, color)

    @staticmethod
    def draw_all_obstacles(image: ImageData, obstacles: List[Obstacle], radius: float, color: Color):
        for obstacle in obstacles:
            ImageHandler.__draw_circle__(image, obstacle, radius, color, color)

    @staticmethod
    def draw_vacuum_position(image: ImageData, vacuum_position: Point, sizes: Sizes, colors: Colors):
        color = ImageHandler.__get_color__(COLOR_ROBO, colors)
        outline = ImageHandler.__get_color__(COLOR_ROBO_OUTLINE, colors)
        radius = sizes[CONF_SIZE_VACUUM_RADIUS]
        ImageHandler.__draw_vacuum__(image, vacuum_position, radius, outline, color)

    @staticmethod
    def draw_room_names(image: ImageData, rooms: Dict[int, Room], colors: Colors):
        color = ImageHandler.__get_color__(COLOR_ROOM_NAMES, colors)
        for room in rooms.values():
            p = room.point()
            if p is not None:
                point = p.to_img(image.dimensions)
                ImageHandler.__draw_text__(image, room.name, point.x, point.y, color)

    @staticmethod
    def rotate(image: ImageData):
        if image.dimensions.rotation == 90:
            image.data = image.data.transpose(Image.ROTATE_90)
        if image.dimensions.rotation == 180:
            image.data = image.data.transpose(Image.ROTATE_180)
        if image.dimensions.rotation == 270:
            image.data = image.data.transpose(Image.ROTATE_270)

    @staticmethod
    def draw_texts(image: ImageData, texts: Texts):
        for text_config in texts:
            x = text_config[CONF_X] * image.data.size[0] / 100
            y = text_config[CONF_Y] * image.data.size[1] / 100
            ImageHandler.__draw_text__(image, text_config[CONF_TEXT], x, y, text_config[CONF_COLOR],
                                       text_config[CONF_FONT], text_config[CONF_FONT_SIZE])

    @staticmethod
    def draw_layer(image: ImageData, layer_name: str):
        ImageHandler.__draw_layer__(image, image.additional_layers[layer_name])

    @staticmethod
    def __use_transparency__(*colors):
        return any(len(color) > 3 for color in colors)

    @staticmethod
    def __draw_vacuum__(image: ImageData, vacuum_pos, r, outline, fill):
        def draw_func(draw: ImageDraw):
            if vacuum_pos.a is None:
                vacuum_pos.a = 0
            point = vacuum_pos.to_img(image.dimensions)
            r_scaled = r / 16
            # main outline
            coords = [point.x - r, point.y - r, point.x + r, point.y + r]
            draw.ellipse(coords, outline=outline, fill=fill)
            if r >= 8:
                # secondary outline
                r2 = r_scaled * 14
                x = point.x
                y = point.y
                coords = [x - r2, y - r2, x + r2, y + r2]
                draw.ellipse(coords, outline=outline, fill=None)
            # bin cover
            a1 = (vacuum_pos.a + 104) / 180 * math.pi
            a2 = (vacuum_pos.a - 104) / 180 * math.pi
            r2 = r_scaled * 13
            x1 = point.x - r2 * math.cos(a1)
            y1 = point.y + r2 * math.sin(a1)
            x2 = point.x - r2 * math.cos(a2)
            y2 = point.y + r2 * math.sin(a2)
            draw.line([x1, y1, x2, y2], width=1, fill=outline)
            # lidar
            angle = vacuum_pos.a / 180 * math.pi
            r2 = r_scaled * 3
            x = point.x + r2 * math.cos(angle)
            y = point.y - r2 * math.sin(angle)
            r2 = r_scaled * 4
            coords = [x - r2, y - r2, x + r2, y + r2]
            draw.ellipse(coords, outline=outline, fill=fill)
            # button
            half_color = (
                (outline[0] + fill[0]) // 2,
                (outline[1] + fill[1]) // 2,
                (outline[2] + fill[2]) // 2
            )
            r2 = r_scaled * 10
            x = point.x + r2 * math.cos(angle)
            y = point.y - r2 * math.sin(angle)
            r2 = r_scaled * 2
            coords = [x - r2, y - r2, x + r2, y + r2]
            draw.ellipse(coords, outline=half_color, fill=half_color)

        ImageHandler.__draw_on_new_layer__(image, draw_func, 1, ImageHandler.__use_transparency__(outline, fill))

    @staticmethod
    def __draw_circle__(image: ImageData, center: Point, r: float, outline: Color, fill: Color):
        def draw_func(draw: ImageDraw):
            point = center.to_img(image.dimensions)
            coords = [point.x - r, point.y - r, point.x + r, point.y + r]
            draw.ellipse(coords, outline=outline, fill=fill)

        ImageHandler.__draw_on_new_layer__(image, draw_func, 1, ImageHandler.__use_transparency__(outline, fill))

    @staticmethod
    def __draw_pieslice__(image: ImageData, position, r, outline, fill):
        def draw_func(draw: ImageDraw):
            point = position.to_img(image.dimensions)
            angle = -position.a if position.a is not None else 0
            coords = [point.x - r, point.y - r, point.x + r, point.y + r]
            draw.pieslice(coords, angle + 90, angle - 90, outline="black", fill=fill)

        ImageHandler.__draw_on_new_layer__(image, draw_func, 1, ImageHandler.__use_transparency__(outline, fill))

    @staticmethod
    def __draw_areas__(image: ImageData, areas: List[Area], fill: Color, outline: Color):
        if len(areas) == 0:
            return

        use_transparency = ImageHandler.__use_transparency__(outline, fill)
        for area in areas:
            def draw_func(draw: ImageDraw):
                draw.polygon(area.to_img(image.dimensions).as_list(), fill, outline)

            ImageHandler.__draw_on_new_layer__(image, draw_func, 1, use_transparency)

    @staticmethod
    def __draw_path__(image: ImageData, path: Path, sizes: Sizes, color: Color, scale: float):
        if len(path.path) < 1:
            return

        path_width = sizes[CONF_SIZE_PATH_WIDTH]

        def draw_func(draw: ImageDraw):
            for current_path in path.path:
                if len(current_path) > 1:
                    s = current_path[0].to_img(image.dimensions)
                    for point in current_path[1:]:
                        e = point.to_img(image.dimensions)
                        draw.line([s.x * scale, s.y * scale, e.x * scale, e.y * scale],
                                  width=int(scale * path_width), fill=color)
                        s = e

        ImageHandler.__draw_on_new_layer__(image, draw_func, scale, ImageHandler.__use_transparency__(color))

    @staticmethod
    def __draw_text__(image: ImageData, text: str, x: float, y: float, color: Color, font_file=None, font_size=None):
        def draw_func(draw: ImageDraw):
            font = ImageFont.load_default()
            try:
                if font_file is not None and font_size > 0:
                    font = ImageFont.truetype(font_file, font_size)
            except OSError:
                _LOGGER.warning("Unable to find font file: %s", font_file)
            except ImportError:
                _LOGGER.warning("Unable to open font: %s", font_file)
            finally:
                w, h = draw.textsize(text, font)
                draw.text((x - w / 2, y - h / 2), text, font=font, fill=color)

        ImageHandler.__draw_on_new_layer__(image, draw_func, 1, ImageHandler.__use_transparency__(color))

    @staticmethod
    def __get_color__(name, colors: Colors, default_name: str = None) -> Color:
        if name in colors:
            return colors[name]
        if default_name is None:
            return ImageHandler.COLORS[name]
        return ImageHandler.COLORS[default_name]

    @staticmethod
    def __draw_on_new_layer__(image: ImageData, draw_function: Callable, scale: float = 1, use_transparency=False):
        if scale == 1 and not use_transparency:
            draw = ImageDraw.Draw(image.data, "RGBA")
            draw_function(draw)
        else:
            size = [int(image.data.size[0] * scale), int(image.data.size[1] * scale)]
            layer = Image.new("RGBA", size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(layer, "RGBA")
            draw_function(draw)
            if scale != 1:
                layer = layer.resize(image.data.size, resample=Image.BOX)
            ImageHandler.__draw_layer__(image, layer)

    @staticmethod
    def __draw_layer__(image: ImageData, layer: ImageType):
        image.data = Image.alpha_composite(image.data, layer)

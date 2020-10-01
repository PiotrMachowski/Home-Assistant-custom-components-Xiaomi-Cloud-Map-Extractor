from PIL import Image, ImageDraw
from .const import *


class ImageHandler:
    MAP_OUTSIDE = 0x00
    MAP_WALL = 0x01
    MAP_INSIDE = 0xFF
    MAP_SCAN = 0x07
    COLORS = {
        COLOR_MAP_INSIDE: (32, 115, 185),
        COLOR_MAP_OUTSIDE: (19, 87, 148),
        COLOR_MAP_WALL: (100, 196, 254),
        COLOR_MAP_WALL_V2: (93, 109, 126),
        COLOR_GREY_WALL: (93, 109, 126),
        COLOR_PATH: (147, 194, 238),
        COLOR_GOTO_PATH: (0, 255, 0),
        COLOR_PREDICTED_PATH: (255, 255, 0),
        COLOR_ZONES: (0xAD, 0xD8, 0xFF, 0x8F),
        COLOR_ZONES_OUTLINE: (0xAD, 0xD8, 0xFF),
        COLOR_VIRTUAL_WALLS: (255, 0, 0),
        COLOR_NO_GO_ZONES: (255, 33, 55, 127),
        COLOR_NO_GO_ZONES_OUTLINE: (255, 0, 0),
        COLOR_NO_MOPPING_ZONES: (163, 130, 211, 127),
        COLOR_NO_MOPPING_ZONES_OUTLINE: (163, 130, 211),
        COLOR_CHARGER: (0x66, 0xfe, 0xda, 0x7f),
        COLOR_ROBO: (75, 235, 149),
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
    def parse(raw_data: bytes, width, height, colors, image_config):
        scale = image_config[CONF_SCALE]
        trim_left = int(image_config[CONF_TRIM][CONF_LEFT] * width / 100)
        trim_right = int(image_config[CONF_TRIM][CONF_RIGHT] * width / 100)
        trim_top = int(image_config[CONF_TRIM][CONF_TOP] * height / 100)
        trim_bottom = int(image_config[CONF_TRIM][CONF_BOTTOM] * height / 100)
        trimmed_height = height - trim_top - trim_bottom
        trimmed_width = width - trim_left - trim_right
        image = Image.new('RGB', (trimmed_width, trimmed_height))
        pixels = image.load()
        for y in range(trimmed_height):
            for x in range(trimmed_width):
                pixel_type = raw_data[x + trim_left + width * (y + trim_bottom)]
                y = trimmed_height - y - 1
                if pixel_type == ImageHandler.MAP_OUTSIDE:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_OUTSIDE, colors)
                elif pixel_type == ImageHandler.MAP_WALL:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_WALL, colors)
                elif pixel_type == ImageHandler.MAP_INSIDE:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_INSIDE, colors)
                elif pixel_type == ImageHandler.MAP_SCAN:
                    pixels[x, y] = ImageHandler.__get_color__(COLOR_SCAN, colors)
                else:
                    obstacle = pixel_type & 0x07
                    if obstacle == 0:
                        pixels[x, y] = ImageHandler.__get_color__(COLOR_GREY_WALL, colors)
                    elif obstacle == 1:
                        pixels[x, y] = ImageHandler.__get_color__(COLOR_MAP_WALL_V2, colors)
                    elif obstacle == 7:
                        room_number = (pixel_type & 0xFF) >> 3
                        default = ImageHandler.ROOM_COLORS[room_number >> 1]
                        pixels[x, y] = ImageHandler.__get_color__(f"{COLOR_ROOM_PREFIX}{room_number}", colors, default)
                    else:
                        pixels[x, y] = ImageHandler.__get_color__(COLOR_UNKNOWN, colors)
        if image_config["scale"] != 1:
            image = image.resize((int(trimmed_width * scale), int(trimmed_height * scale)), resample=Image.NEAREST)
        return image

    @staticmethod
    def draw_path(image, path, colors):
        ImageHandler.__draw_path__(image, path, ImageHandler.__get_color__(COLOR_PATH, colors))

    @staticmethod
    def draw_goto_path(image, path, colors):
        ImageHandler.__draw_path__(image, path, ImageHandler.__get_color__(COLOR_GOTO_PATH, colors))

    @staticmethod
    def draw_predicted_path(image, path, colors):
        ImageHandler.__draw_path__(image, path, ImageHandler.__get_color__(COLOR_PREDICTED_PATH, colors))

    @staticmethod
    def draw_no_go_areas(image, areas, colors):
        ImageHandler.__draw_areas__(image, areas,
                                    ImageHandler.__get_color__(COLOR_NO_GO_ZONES, colors),
                                    ImageHandler.__get_color__(COLOR_NO_GO_ZONES_OUTLINE, colors))

    @staticmethod
    def draw_no_mopping_areas(image, areas, colors):
        ImageHandler.__draw_areas__(image, areas,
                                    ImageHandler.__get_color__(COLOR_NO_MOPPING_ZONES, colors),
                                    ImageHandler.__get_color__(COLOR_NO_MOPPING_ZONES_OUTLINE, colors))

    @staticmethod
    def draw_walls(image, walls, colors):
        draw = ImageDraw.Draw(image.data, 'RGBA')
        for wall in walls:
            draw.line(wall.to_img(image.dimensions).as_list(),
                      ImageHandler.__get_color__(COLOR_VIRTUAL_WALLS, colors), width=2)

    @staticmethod
    def draw_zones(image, zones, colors):
        areas = list(map(lambda z: z.as_area(), zones))
        ImageHandler.__draw_areas__(image, areas,
                                    ImageHandler.__get_color__(COLOR_ZONES, colors),
                                    ImageHandler.__get_color__(COLOR_ZONES_OUTLINE, colors))

    @staticmethod
    def draw_charger(image, charger, colors):
        color = ImageHandler.__get_color__(COLOR_CHARGER, colors)
        ImageHandler.__draw_circle__(image, charger, 4, color, color)

    @staticmethod
    def draw_vacuum_position(image, vacuum_position, colors):
        color = ImageHandler.__get_color__(COLOR_ROBO, colors)
        ImageHandler.__draw_circle__(image, vacuum_position, 4, color, color)

    @staticmethod
    def rotate(image):
        if image.dimensions.rotation == 90:
            image.data = image.data.transpose(Image.ROTATE_90)
        if image.dimensions.rotation == 180:
            image.data = image.data.transpose(Image.ROTATE_180)
        if image.dimensions.rotation == 270:
            image.data = image.data.transpose(Image.ROTATE_270)

    @staticmethod
    def __draw_circle__(image, center, r, outline, fill):
        point = center.to_img(image.dimensions)
        draw = ImageDraw.Draw(image.data, 'RGBA')
        coords = [point.x - r, point.y - r, point.x + r, point.y + r]
        draw.ellipse(coords, outline=outline, fill=fill)

    @staticmethod
    def __draw_areas__(image, areas, fill, outline):
        if len(areas) == 0:
            return
        draw = ImageDraw.Draw(image.data, 'RGBA')
        for area in areas:
            draw.polygon(area.to_img(image.dimensions).as_list(), fill, outline)

    @staticmethod
    def __draw_path__(image, path, color):
        if len(path.path) < 2:
            return
        draw = ImageDraw.Draw(image.data, 'RGBA')
        s = path.path[0].to_img(image.dimensions)
        for point in path.path[1:]:
            e = point.to_img(image.dimensions)
            draw.line([s.x, s.y, e.x, e.y], fill=color)
            s = e

    @staticmethod
    def __get_color__(name, colors, default_name=None):
        if name in colors:
            return colors[name]
        if default_name is None:
            return ImageHandler.COLORS[name]
        return ImageHandler.COLORS[default_name]

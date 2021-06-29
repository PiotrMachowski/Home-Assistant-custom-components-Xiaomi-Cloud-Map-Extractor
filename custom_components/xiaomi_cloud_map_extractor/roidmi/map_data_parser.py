import json
import logging
from typing import Dict, List, Tuple

from custom_components.xiaomi_cloud_map_extractor.common.map_data import ImageData, MapData, Room
from custom_components.xiaomi_cloud_map_extractor.common.map_data_parser import MapDataParser
from custom_components.xiaomi_cloud_map_extractor.roidmi.image_handler import ImageHandlerRoidmi

_LOGGER = logging.getLogger(__name__)


class MapDataParserRoidmi(MapDataParser):

    @staticmethod
    def parse(raw: bytes, colors, drawables, texts, sizes, image_config) -> MapData:
        map_image_size = raw.find(bytes([127, 123]))
        map_image = raw[16:map_image_size + 1]
        map_info = raw[map_image_size + 1:]
        map_json = json.loads(map_info)
        width = map_json["width"]
        height = map_json["height"]
        map_data = MapData(0, 1)
        room_numbers = []
        if "autoAreaValue" in map_json:
            room_numbers = list(map(lambda aav: aav["id"], map_json["autoAreaValue"]))
        elif "autoArea" in map_json:
            room_numbers = list(map(lambda aav: aav["id"], map_json["autoArea"]))
        image, rooms = MapDataParserRoidmi.parse_image(map_image, width, height, colors, image_config, room_numbers)
        map_data.image = image
        map_data.rooms = rooms
        return map_data

    @staticmethod
    def map_to_image(x):
        return x * 20 + 400

    @staticmethod
    def image_to_map(x):
        return (x - 400) / 20

    @staticmethod
    def parse_image(map_image: bytes, width: int, height: int, colors: Dict, image_config: Dict,
                    room_numbers: List[int]) -> Tuple[ImageData, Dict[int, Room]]:
        image_top = 0
        image_left = 0
        image, rooms_raw = ImageHandlerRoidmi.parse(map_image, width, height, colors, image_config, room_numbers)
        rooms = {}
        for number, room in rooms_raw.items():
            rooms[number] = Room(number, MapDataParserRoidmi.image_to_map(room[0] + image_left),
                                 MapDataParserRoidmi.image_to_map(room[1] + image_top),
                                 MapDataParserRoidmi.image_to_map(room[2] + image_left),
                                 MapDataParserRoidmi.image_to_map(room[3] + image_top))
        return ImageData(width * height, image_top, image_left, height, width, image_config,
                         image, MapDataParserRoidmi.map_to_image), rooms

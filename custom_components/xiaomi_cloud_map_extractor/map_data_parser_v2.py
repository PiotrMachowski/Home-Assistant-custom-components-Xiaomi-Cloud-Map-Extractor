import logging
from struct import unpack_from

from .image_handler_v2 import ImageHandlerV2
from .map_data import *
from .map_data_parser import MapDataParser

_LOGGER = logging.getLogger(__name__)


class ParsingBuffer:
    def __init__(self, name, data: bytes, start_offs, length):
        self._name = name
        self._data = data
        self._offs = start_offs
        self._length = length
        self._image_beginning = None

    def set_name(self, name):
        self._name = name
        _LOGGER.debug('SECTION %s: offset 0x%x', self._name, self._offs)

    def mark_as_image_beginning(self):
        self._image_beginning = self._offs

    def get_at_image(self, offset):
        return self._data[self._image_beginning + offset - 1]

    def skip(self, field, n):
        if self._length < n:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += n
        self._length -= n

    def get_uint8(self, field):
        if self._length < 1:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 1
        self._length -= 1
        return self._data[self._offs - 1]

    def get_uint16(self, field):
        if self._length < 2:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 2
        self._length -= 2
        return unpack_from('<H', self._data, self._offs - 2)[0]

    def get_uint32(self, field):
        if self._length < 4:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 4
        self._length -= 4
        return unpack_from('<L', self._data, self._offs - 4)[0]

    def get_float32(self, field):
        if self._length < 4:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += 4
        self._length -= 4
        return unpack_from('<f', self._data, self._offs - 4)[0]

    def get_string_len8(self, field):
        n = self.get_uint8(field + '.len')
        if self._length < n:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        self._offs += n
        self._length -= n
        return self._data[self._offs - n:self._offs].decode('UTF-8')

    def peek_uint32(self, field):
        if self._length < 4:
            raise ValueError(f"error parsing {self._name}.{field} at offset {self._offs:#x}: buffer underrun")
        return unpack_from('<L', self._data, self._offs)[0]


class MapDataParserV2(MapDataParser):
    FEATURE_ROBOT_STATUS = 0x00000001
    FEATURE_IMAGE = 0x00000002
    FEATURE_HISTORY = 0x00000004
    FEATURE_CHARGE_STATION = 0x00000008
    FEATURE_RESTRICTED_AREAS = 0x00000010
    FEATURE_CLEANING_AREAS = 0x00000020
    FEATURE_NAVIGATE = 0x00000040
    FEATURE_REALTIME = 0x00000080
    FEATURE_ROOMS = 0x00001000

    POSITION_UNKNOWN = 1100

    @staticmethod
    def parse(raw: bytes, colors, drawables, texts, sizes, image_config) -> MapData:
        map_data = MapData()
        buf = ParsingBuffer('header', raw, 0, len(raw))
        feature_flags = buf.get_uint32('feature_flags')
        map_id = buf.peek_uint32('map_id')
        _LOGGER.debug('feature_flags: 0x%x, map_id: %d', feature_flags, map_id)

        if feature_flags & MapDataParserV2.FEATURE_ROBOT_STATUS != 0:
            MapDataParserV2.parse_section(buf, 'robot_status', map_id)
            buf.skip('unknown1', 0x28)

        if feature_flags & MapDataParserV2.FEATURE_IMAGE != 0:
            MapDataParserV2.parse_section(buf, 'image', map_id)
            map_data.image, map_data.rooms, map_data.zones = MapDataParserV2.parse_image(buf, colors, image_config)

        if feature_flags & MapDataParserV2.FEATURE_HISTORY != 0:
            MapDataParserV2.parse_section(buf, 'history', map_id)
            map_data.path = MapDataParserV2.parse_history(buf)

        if feature_flags & MapDataParserV2.FEATURE_CHARGE_STATION != 0:
            MapDataParserV2.parse_section(buf, 'charge_station', map_id)
            map_data.charger = MapDataParserV2.parse_position(buf, 'pos')
            foo = buf.get_float32('foo')
            _LOGGER.debug('pos: %s, foo: %f', map_data.charger, foo)

        if feature_flags & MapDataParserV2.FEATURE_RESTRICTED_AREAS != 0:
            MapDataParserV2.parse_section(buf, 'restricted_areas', map_id)
            map_data.walls, map_data.no_go_areas = MapDataParserV2.parse_restricted_areas(buf)

        if feature_flags & MapDataParserV2.FEATURE_CLEANING_AREAS != 0:
            MapDataParserV2.parse_section(buf, 'cleaning_areas', map_id)
            MapDataParserV2.parse_cleaning_areas(buf, map_data.zones)

        if feature_flags & MapDataParserV2.FEATURE_NAVIGATE != 0:
            MapDataParserV2.parse_section(buf, 'navigate', map_id)
            buf.skip('unknown1', 4)
            map_data.goto = MapDataParserV2.parse_position(buf, 'pos')
            foo = buf.get_float32('foo')
            _LOGGER.debug('pos: %s, foo: %f', map_data.goto, foo)

        if feature_flags & MapDataParserV2.FEATURE_REALTIME != 0:
            MapDataParserV2.parse_section(buf, 'realtime', map_id)
            buf.skip('unknown1', 5)
            map_data.vacuum_position = MapDataParserV2.parse_position(buf, 'pos')
            foo = buf.get_float32('foo')
            _LOGGER.debug('pos: %s, foo: %f', map_data.vacuum_position, foo)

        if feature_flags & 0x00000800 != 0:
            MapDataParserV2.parse_section(buf, 'unknown1', map_id)
            buf.skip('unknown1', 4)

        if feature_flags & MapDataParserV2.FEATURE_ROOMS != 0:
            MapDataParserV2.parse_section(buf, 'rooms', map_id)
            MapDataParserV2.parse_rooms(buf, map_data.rooms)

        if feature_flags & 0x00002000 != 0:
            MapDataParserV2.parse_section(buf, 'unknown2', map_id)
            MapDataParserV2.parse_unknown_section(buf)

        if feature_flags & 0x00004000 != 0:
            MapDataParserV2.parse_section(buf, 'unknown3', map_id)
            MapDataParserV2.parse_unknown_section(buf)

        _LOGGER.debug('rooms: %s', [str(room) for number, room in map_data.rooms.items()])
        if not map_data.image.is_empty:
            MapDataParserV2.draw_elements(colors, drawables, sizes, map_data, image_config)
            if len(map_data.rooms) > 0 and map_data.vacuum_position is not None:
                map_data.vacuum_room = MapDataParserV2.get_current_vacuum_room(buf, map_data.vacuum_position)
                _LOGGER.debug('current vacuum room: %s', map_data.vacuum_room)
            #ImageHandlerV2.draw_zones(map_data.image, [room for number, room in map_data.rooms.items()], colors)
            ImageHandlerV2.rotate(map_data.image)
            ImageHandlerV2.draw_texts(map_data.image, texts)
        return map_data

    @staticmethod
    def get_current_vacuum_room(buf, vacuum_position):
        x = int(vacuum_position.x / MM)
        y = int(vacuum_position.y / MM)
        pixel_type = buf.get_at_image(y * 800 + x)
        if ImageHandlerV2.MAP_ROOM_MIN <= pixel_type <= ImageHandlerV2.MAP_ROOM_MAX:
            return pixel_type
        elif ImageHandlerV2.MAP_SELECTED_ROOM_MIN <= pixel_type <= ImageHandlerV2.MAP_SELECTED_ROOM_MAX:
            return pixel_type - ImageHandlerV2.MAP_SELECTED_ROOM_MIN + ImageHandlerV2.MAP_ROOM_MIN
        return None

    @staticmethod
    def parse_image(buf, colors, image_config):
        buf.skip('unknown1', 0x08)
        image_top = 0
        image_left = 0
        image_height = buf.get_uint32('image_height')
        image_width = buf.get_uint32('image_width')
        buf.skip('unknown2', 20)
        image_size = image_height * image_width
        _LOGGER.debug('width: %d, height: %d', image_width, image_height)
        if image_width \
                - image_width * (image_config[CONF_TRIM][CONF_LEFT] + image_config[CONF_TRIM][CONF_RIGHT]) / 100 \
                < MINIMAL_IMAGE_WIDTH:
            image_config[CONF_TRIM][CONF_LEFT] = 0
            image_config[CONF_TRIM][CONF_RIGHT] = 0
        if image_height \
                - image_height * (image_config[CONF_TRIM][CONF_TOP] + image_config[CONF_TRIM][CONF_BOTTOM]) / 100 \
                < MINIMAL_IMAGE_HEIGHT:
            image_config[CONF_TRIM][CONF_TOP] = 0
            image_config[CONF_TRIM][CONF_BOTTOM] = 0
        buf.mark_as_image_beginning()
        image, rooms, areas = ImageHandlerV2.parse(buf, image_width, image_height, colors, image_config)
        _LOGGER.debug('img: number of rooms: %d, numbers: %s', len(rooms), rooms.keys())
        for number, room in rooms.items():
            rooms[number] = Room(number, (room[0] + image_left) * MM,
                                 (room[1] + image_top) * MM,
                                 (room[2] + image_left) * MM,
                                 (room[3] + image_top) * MM)
        zones = []
        for number, area in areas.items():
            zones.append(Zone((area[0] + image_left) * MM,
                            (area[1] + image_top) * MM,
                            (area[2] + image_left) * MM,
                            (area[3] + image_top) * MM))
        return ImageData(image_size,
                         image_top,
                         image_left,
                         image_height,
                         image_width,
                         image_config,
                         image), rooms, zones

    @staticmethod
    def parse_history(buf):
        path_points = []
        buf.skip('unknown1', 4)
        history_count = buf.get_uint32('history_count')
        for _ in range(history_count):
            buf.skip('path.unknown1', 1)
            path_points.append(MapDataParserV2.parse_position(buf, 'path'))
            # buf.skip('path.unknown2', 9)
        return Path(len(path_points), 1, 0, path_points)

    @staticmethod
    def parse_restricted_areas(buf):
        walls = []
        areas = []
        buf.skip('unknown1', 4)
        area_count = buf.get_uint32('area_count')
        for _ in range(area_count):
            buf.skip('restricted.unknown1', 12)
            p1 = MapDataParserV2.parse_position(buf, 'p1')
            p2 = MapDataParserV2.parse_position(buf, 'p2')
            p3 = MapDataParserV2.parse_position(buf, 'p3')
            p4 = MapDataParserV2.parse_position(buf, 'p4')
            buf.skip('restricted.unknown2', 48)
            _LOGGER.debug('restricted: %s %s %s %s', p1, p2, p3, p4)
            if p1 == p2 and p3 == p4:
                walls.append(Wall(p1.x, p1.y, p3.x, p3.y))
            else:
                areas.append(Area(p1.x, p1.y, p2.x, p2.y, p3.x, p3.y, p4.x, p4.y))
        return walls, areas

    @staticmethod
    def parse_cleaning_areas(buf, zones):
        buf.skip('unknown1', 4)
        area_count = buf.get_uint32('area_count')
        for _ in range(area_count):
            buf.skip('area.unknown1', 12)
            p1 = MapDataParserV2.parse_position(buf, 'p1')
            p2 = MapDataParserV2.parse_position(buf, 'p2')
            p3 = MapDataParserV2.parse_position(buf, 'p3')
            p4 = MapDataParserV2.parse_position(buf, 'p4')
            buf.skip('area.unknown2', 48)
            zones.append(Zone(p1.x, p1.y, p3.x, p3.y))

    @staticmethod
    def parse_rooms(buf, map_data_rooms):
        map_name = buf.get_string_len8('map_name')
        map_arg = buf.get_uint32('map_arg')
        _LOGGER.debug('map#%d: %s', map_arg, map_name)
        while map_arg > 1:
            map_name = buf.get_string_len8('map_name')
            map_arg = buf.get_uint32('map_arg')
            _LOGGER.debug('map#%d: %s', map_arg, map_name)
        room_count = buf.get_uint32('room_count')
        for _ in range(room_count):
            room_id = buf.get_uint8('room.id')
            room_name = buf.get_string_len8('room.name')
            if map_data_rooms is not None and room_id in map_data_rooms:
                map_data_rooms[room_id].name = room_name
            buf.skip('room.unknown1', 1)
            room_text_pos = MapDataParserV2.parse_position(buf, 'room.text_pos')
            _LOGGER.debug('room#%d: %s %s', room_id, room_name, room_text_pos)
        buf.skip('unknown1', 6)

    @staticmethod
    def parse_section(buf, name, map_id):
        buf.set_name(name)
        magic = buf.get_uint32('magic')
        # if magic != map_id:
        #     raise ValueError(
        #         f"error parsing section {name} at offset {buf._offs - 4:#x}: magic check failed {magic:#x}")  # FIXME

    @staticmethod
    def parse_position(buf, name):
        x = buf.get_float32(name + '.x')
        y = buf.get_float32(name + '.y')
        if x == MapDataParserV2.POSITION_UNKNOWN or y == MapDataParserV2.POSITION_UNKNOWN:
            return None
        return Point(int(1000 * x + 20000), int(1000 * y + 20000))

    @staticmethod
    def parse_unknown_section(buf):
        n = buf._data[buf._offs:].find(buf._data[4:8])
        if n >= 0:
            buf._offs += n
            buf._length -= n
            return True
        else:
            return False

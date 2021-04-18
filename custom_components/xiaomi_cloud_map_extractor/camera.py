import io
import logging
import miio
import time
import voluptuous as vol
from datetime import timedelta

from homeassistant.helpers import config_validation as cv
from homeassistant.components.camera import PLATFORM_SCHEMA, ENTITY_ID_FORMAT, Camera
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.entity import generate_entity_id

from .const import *
from .xiaomi_cloud_connector import XiaomiCloudConnector

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

DEFAULT_TRIMS = {
    CONF_LEFT: 0,
    CONF_RIGHT: 0,
    CONF_TOP: 0,
    CONF_BOTTOM: 0
}

DEFAULT_SIZES = {
    CONF_SIZE_VACUUM_RADIUS: 4,
    CONF_SIZE_IGNORED_OBSTACLE_RADIUS: 3,
    CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS: 3,
    CONF_SIZE_OBSTACLE_RADIUS: 3,
    CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS: 3,
    CONF_SIZE_CHARGER_RADIUS: 4
}

COLOR_SCHEMA = vol.Or(
    vol.All(vol.Length(min=3, max=3), vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple)),
    vol.All(vol.Length(min=4, max=4), vol.ExactSequence((cv.byte, cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple))
)

PERCENT_SCHEMA = vol.All(vol.Coerce(float), vol.Range(min=0, max=100))

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_COUNTRY, default=None): vol.Or(vol.In(CONF_AVAILABLE_COUNTRIES), vol.Equal(None)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_AUTO_UPDATE, default=True): cv.boolean,
        vol.Optional(CONF_COLORS, default={}): vol.Schema({
            vol.In(CONF_AVAILABLE_COLORS): COLOR_SCHEMA
        }),
        vol.Optional(CONF_ROOM_COLORS, default={}): vol.Schema({
            cv.positive_int: COLOR_SCHEMA
        }),
        vol.Optional(CONF_DRAW, default=[]): vol.All(cv.ensure_list, [vol.In(CONF_AVAILABLE_DRAWABLES)]),
        vol.Optional(CONF_MAP_TRANSFORM, default={CONF_SCALE: 1, CONF_ROTATE: 0, CONF_TRIM: DEFAULT_TRIMS}):
            vol.Schema({
                vol.Optional(CONF_SCALE, default=1): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional(CONF_ROTATE, default=0): vol.In([0, 90, 180, 270]),
                vol.Optional(CONF_TRIM, default=DEFAULT_TRIMS): vol.Schema({
                    vol.Optional(CONF_LEFT, default=0): PERCENT_SCHEMA,
                    vol.Optional(CONF_RIGHT, default=0): PERCENT_SCHEMA,
                    vol.Optional(CONF_TOP, default=0): PERCENT_SCHEMA,
                    vol.Optional(CONF_BOTTOM, default=0): PERCENT_SCHEMA
                }),
            }),
        vol.Optional(CONF_ATTRIBUTES, default=[]): vol.All(cv.ensure_list, [vol.In(CONF_AVAILABLE_ATTRIBUTES)]),
        vol.Optional(CONF_TEXTS, default=[]):
            vol.All(cv.ensure_list, [vol.Schema({
                vol.Required(CONF_TEXT): cv.string,
                vol.Required(CONF_X): vol.Coerce(float),
                vol.Required(CONF_Y): vol.Coerce(float),
                vol.Optional(CONF_COLOR, default=(0, 0, 0)): COLOR_SCHEMA,
                vol.Optional(CONF_FONT, default=None): vol.Or(cv.string, vol.Equal(None)),
                vol.Optional(CONF_FONT_SIZE, default=0): cv.positive_int
            })]),
        vol.Optional(CONF_SIZES, default=DEFAULT_SIZES): vol.Schema({
            vol.Optional(CONF_SIZE_VACUUM_RADIUS, default=DEFAULT_SIZES[CONF_SIZE_VACUUM_RADIUS]):
                vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional(CONF_SIZE_IGNORED_OBSTACLE_RADIUS, default=DEFAULT_SIZES[CONF_SIZE_IGNORED_OBSTACLE_RADIUS]):
                vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional(CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS]):
                vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional(CONF_SIZE_OBSTACLE_RADIUS, default=DEFAULT_SIZES[CONF_SIZE_OBSTACLE_RADIUS]):
                vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional(CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS]):
                vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional(CONF_SIZE_CHARGER_RADIUS, default=DEFAULT_SIZES[CONF_SIZE_CHARGER_RADIUS]):
                vol.All(vol.Coerce(float), vol.Range(min=0))
        }),
        vol.Optional(CONF_STORE_MAP, default=False): cv.boolean
    })


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    host = config[CONF_HOST]
    token = config[CONF_TOKEN]
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    country = config[CONF_COUNTRY]
    name = config[CONF_NAME]
    should_poll = config[CONF_AUTO_UPDATE]
    image_config = config[CONF_MAP_TRANSFORM]
    colors = config[CONF_COLORS]
    room_colors = config[CONF_ROOM_COLORS]
    for room, color in room_colors.items():
        colors[f"{COLOR_ROOM_PREFIX}{room}"] = color
    drawables = config[CONF_DRAW]
    sizes = config[CONF_SIZES]
    texts = config[CONF_TEXTS]
    if DRAWABLE_ALL in drawables:
        drawables = CONF_AVAILABLE_DRAWABLES[1:]
    attributes = config[CONF_ATTRIBUTES]
    store_map = config[CONF_STORE_MAP]
    entity_id = generate_entity_id(ENTITY_ID_FORMAT, name, hass=hass)
    async_add_entities([VacuumCamera(entity_id, host, token, username, password, country, name, should_poll,
                                     image_config, colors, drawables, sizes, texts, attributes, store_map)])


class VacuumCamera(Camera):
    def __init__(self, entity_id, host, token, username, password, country, name, should_poll, image_config, colors,
                 drawables, sizes, texts, attributes, store_map):
        super().__init__()
        self.entity_id = entity_id
        self.content_type = CONTENT_TYPE
        self._vacuum = miio.Vacuum(host, token)
        self._connector = XiaomiCloudConnector(username, password)
        self._name = name
        self._should_poll = should_poll
        self._image_config = image_config
        self._colors = colors
        self._drawables = drawables
        self._sizes = sizes
        self._texts = texts
        self._attributes = attributes
        self._store_map = store_map
        self._map_saved = None
        self._image = None
        self._map_data = None
        self._logged_in = False
        self._logged_in_previously = True
        self._received_map_name_previously = True
        self._country = country

    async def async_added_to_hass(self) -> None:
        self.async_schedule_update_ha_state(True)

    @property
    def frame_interval(self):
        return 0.5

    def camera_image(self):
        return self._image

    @property
    def name(self):
        return self._name

    @property
    def device_state_attributes(self):
        attributes = {}
        if self._map_data is not None:
            for name, value in {
                ATTRIBUTE_CALIBRATION: self._map_data.calibration(),
                ATTRIBUTE_CHARGER: self._map_data.charger,
                ATTRIBUTE_COUNTRY: self._country,
                ATTRIBUTE_GOTO: self._map_data.goto,
                ATTRIBUTE_GOTO_PATH: self._map_data.goto_path,
                ATTRIBUTE_GOTO_PREDICTED_PATH: self._map_data.predicted_path,
                ATTRIBUTE_IGNORED_OBSTACLES: self._map_data.ignored_obstacles,
                ATTRIBUTE_IGNORED_OBSTACLES_WITH_PHOTO: self._map_data.ignored_obstacles_with_photo,
                ATTRIBUTE_IMAGE: self._map_data.image,
                ATTRIBUTE_IS_EMPTY: self._map_data.image.is_empty,
                ATTRIBUTE_MAP_NAME: self._map_data.map_name,
                ATTRIBUTE_NO_GO_AREAS: self._map_data.no_go_areas,
                ATTRIBUTE_NO_MOPPING_AREAS: self._map_data.no_mopping_areas,
                ATTRIBUTE_OBSTACLES: self._map_data.obstacles,
                ATTRIBUTE_OBSTACLES_WITH_PHOTO: self._map_data.obstacles_with_photo,
                ATTRIBUTE_PATH: self._map_data.path,
                ATTRIBUTE_ROOM_NUMBERS: list(self._map_data.rooms.keys()),
                ATTRIBUTE_ROOMS: self._map_data.rooms,
                ATTRIBUTE_VACUUM_POSITION: self._map_data.vacuum_position,
                ATTRIBUTE_VACUUM_ROOM: self._map_data.vacuum_room,
                ATTRIBUTE_WALLS: self._map_data.walls,
                ATTRIBUTE_ZONES: self._map_data.zones
            }.items():
                if name in self._attributes:
                    attributes[name] = value
        if self._store_map:
            attributes[ATTRIBUTE_MAP_SAVED] = self._map_saved
        return attributes

    @property
    def should_poll(self):
        return self._should_poll

    def update(self):
        counter = 10
        if not self._logged_in:
            self._logged_in = self._connector.login()
            if not self._logged_in and self._logged_in_previously:
                _LOGGER.error("Unable to log in, check credentials")
        if self._country is None and self._logged_in:
            self._country = self._connector.get_country_for_device(self._vacuum.ip, self._vacuum.token)
        map_name = "retry"
        while map_name == "retry" and counter > 0:
            time.sleep(0.1)
            try:
                map_name = self._vacuum.map()[0]
            except OSError as exc:
                _LOGGER.error("Got OSError while fetching the state: %s", exc)
            except miio.DeviceException as exc:
                if self._received_map_name_previously:
                    _LOGGER.warning("Got exception while fetching the state: %s", exc)
                self._received_map_name_previously = False
            finally:
                counter = counter - 1
        self._received_map_name_previously = map_name != "retry"
        if self._logged_in and map_name != "retry" and self._country is not None:
            map_data, map_stored = self._connector.get_map(self._country, map_name, self._colors, self._drawables,
                                                           self._texts, self._sizes, self._image_config,
                                                           self._store_map)
            if map_data is not None:
                # noinspection PyBroadException
                try:
                    img_byte_arr = io.BytesIO()
                    map_data.image.data.save(img_byte_arr, format='PNG')
                    self._image = img_byte_arr.getvalue()
                    self._map_data = map_data
                    self._map_saved = map_stored
                except:
                    _LOGGER.warning("Unable to retrieve map data")
            else:
                self._logged_in = False
                _LOGGER.warning("Unable to retrieve map data")
        self._logged_in_previously = self._logged_in

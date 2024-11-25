import io
import logging
from datetime import timedelta
from enum import StrEnum

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_base.config.text import Text
from vacuum_map_parser_base.image_generator import ImageGenerator
from vacuum_map_parser_base.map_data import ImageData

import PIL.Image as Image
import voluptuous as vol
from homeassistant.components.camera import Camera, ENTITY_ID_FORMAT, PLATFORM_SCHEMA, SUPPORT_ON_OFF
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.reload import async_setup_reload_service

from vacuum_map_parser_base.map_data import MapData

from .vacuum_platforms.xiaomi_cloud_connector import XiaomiCloudConnector
from .vacuum_platforms.vacuum_base import XiaomiCloudVacuum, VacuumConfig
from .vacuum_platforms.vacuum_dreame import DreameCloudVacuum
from .vacuum_platforms.vacuum_roborock import RoborockCloudVacuum
from .vacuum_platforms.vacuum_roidmi import RoidmiCloudVacuum
from .vacuum_platforms.vacuum_viomi import ViomiCloudVacuum
from .vacuum_platforms.vacuum_ijai import IjaiCloudVacuum
from .vacuum_platforms.vacuum_unsupported import UnsupportedCloudVacuum
from .initializer import from_dict
from .const import *


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

DEFAULT_TRIMS = {
    CONF_LEFT: 0,
    CONF_RIGHT: 0,
    CONF_TOP: 0,
    CONF_BOTTOM: 0
}

DEFAULT_SIZES = {
    CONF_SIZE_VACUUM_RADIUS: 6,
    CONF_SIZE_PATH_WIDTH: 1,
    CONF_SIZE_IGNORED_OBSTACLE_RADIUS: 3,
    CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS: 3,
    CONF_SIZE_OBSTACLE_RADIUS: 3,
    CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS: 3,
    CONF_SIZE_CHARGER_RADIUS: 6
}

COLOR_SCHEMA = vol.Or(
    vol.All(vol.Length(min=3, max=3), vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple)),
    vol.All(vol.Length(min=4, max=4), vol.ExactSequence((cv.byte, cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple))
)

PERCENT_SCHEMA = vol.All(vol.Coerce(float), vol.Range(min=0, max=100))

POSITIVE_FLOAT_SCHEMA = vol.All(vol.Coerce(float), vol.Range(min=0))

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
                vol.Optional(CONF_SCALE, default=1): POSITIVE_FLOAT_SCHEMA,
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
            vol.Optional(CONF_SIZE_VACUUM_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_VACUUM_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_PATH_WIDTH,
                         default=DEFAULT_SIZES[CONF_SIZE_PATH_WIDTH]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_MOP_PATH_WIDTH,
                         default=DEFAULT_SIZES[CONF_SIZE_VACUUM_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_IGNORED_OBSTACLE_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_IGNORED_OBSTACLE_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_OBSTACLE_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_OBSTACLE_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(CONF_SIZE_CHARGER_RADIUS,
                         default=DEFAULT_SIZES[CONF_SIZE_CHARGER_RADIUS]): POSITIVE_FLOAT_SCHEMA
        }),
        vol.Optional(CONF_STORE_MAP_RAW, default=False): cv.boolean,
        vol.Optional(CONF_STORE_MAP_IMAGE, default=False): cv.boolean,
        vol.Optional(CONF_STORE_MAP_PATH, default="/tmp"): cv.string,
        vol.Optional(CONF_FORCE_API, default=None): vol.Or(vol.In(CONF_AVAILABLE_APIS), vol.Equal(None))
    })

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    _LOGGER.debug(f"config={config}")
    host = config[CONF_HOST]
    token = config[CONF_TOKEN]
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    country = config[CONF_COUNTRY]
    name = config[CONF_NAME]
    should_poll = config[CONF_AUTO_UPDATE]
    image_config = from_dict(ImageConfig, config[CONF_MAP_TRANSFORM])
    colors = config[CONF_COLORS]
    room_colors = config[CONF_ROOM_COLORS]
    for room, color in room_colors.items():
        colors[f"{COLOR_ROOM_PREFIX}{room}"] = color
    drawables = config[CONF_DRAW]
    sizes = Sizes(config[CONF_SIZES])
    texts = from_dict(list, config[CONF_TEXTS])
    if DRAWABLE_ALL in drawables:
        drawables = CONF_AVAILABLE_DRAWABLES[1:]
    attributes = config[CONF_ATTRIBUTES]
    store_map_raw = config[CONF_STORE_MAP_RAW]
    store_map_image = config[CONF_STORE_MAP_IMAGE]
    store_map_path = config[CONF_STORE_MAP_PATH]
    force_api = config[CONF_FORCE_API]
    entity_id = generate_entity_id(ENTITY_ID_FORMAT, name, hass=hass)
    async_add_entities([VacuumCamera(entity_id, host, token, username, password, country, name, should_poll,
                                     image_config, ColorsPalette(colors, room_colors), drawables, sizes, texts, attributes, store_map_raw,
                                     store_map_image, store_map_path, force_api)])


class VacuumCamera(Camera):
    def __init__(self, entity_id: str, host: str, token: str, username: str, password: str, country: str, name: str,
                 should_poll: bool, image_config: ImageConfig, colors: ColorsPalette, drawables: list[Drawable],
                 sizes: Sizes, texts: list[Text], attributes: list[str], store_map_raw: bool, store_map_image: bool,
                 store_map_path: str, force_api: str):
        super().__init__()
        self.entity_id = entity_id
        self.content_type = CONTENT_TYPE
        self._host = host
        self._token = token
        self._connector = XiaomiCloudConnector(username, password)
        self._status = CameraStatus.INITIALIZING
        self._device: XiaomiCloudVacuum | None = None
        self._name = name
        self._should_poll = should_poll
        self._image_config = image_config
        self._colors = colors
        self._drawables = drawables
        self._sizes = sizes
        self._texts = texts
        self._attributes = attributes
        self._store_map_raw = store_map_raw
        self._store_map_image = store_map_image
        self._store_map_path = store_map_path
        self._forced_api = force_api
        self._used_api = None
        self._map_saved = None
        self._image = None
        self._map_data = None
        self._logged_in = False
        self._logged_in_previously = True
        self._country = country

    async def async_added_to_hass(self) -> None:
        self.async_schedule_update_ha_state(True)

    @property
    def frame_interval(self) -> float:
        return 1

    def camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return self._image

    @property
    def name(self) -> str:
        return self._name

    def turn_on(self):
        self._should_poll = True

    def turn_off(self):
        self._should_poll = False

    @property
    def supported_features(self) -> int:
        return SUPPORT_ON_OFF

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        attributes = {}
        if self._map_data is not None:
            attributes.update(self.extract_attributes(self._map_data, self._attributes, self._country))
        if self._store_map_raw:
            attributes[ATTRIBUTE_MAP_SAVED] = self._map_saved
        if self._device is not None:
            attributes[ATTR_MODEL] = self._device.model
            attributes[ATTR_USED_API] = self._used_api
        if self._connector.two_factor_auth_url is not None:
            attributes[ATTR_TWO_FACTOR_AUTH] = self._connector.two_factor_auth_url
        return attributes

    @property
    def should_poll(self) -> bool:
        return self._should_poll

    @staticmethod
    def extract_attributes(map_data: MapData, attributes_to_return: list[str], country) -> dict[str, any]:
        _LOGGER.debug(f"extract_attributes{map_data}, {attributes_to_return}, country")
        attributes = {}
        rooms = []
        if map_data.rooms is not None:
            rooms = dict(filter(lambda x: x[1] is not None, ((x[0], x[1].name) for x in map_data.rooms.items())))
            if len(rooms) == 0:
                rooms = list(map_data.rooms.keys())
        for name, value in {
            ATTRIBUTE_CALIBRATION: map_data.calibration(),
            ATTRIBUTE_CHARGER: map_data.charger,
            ATTRIBUTE_CLEANED_ROOMS: [*(map_data.cleaned_rooms or [])],
            ATTRIBUTE_COUNTRY: country,
            ATTRIBUTE_GOTO: map_data.goto,
            ATTRIBUTE_GOTO_PATH: map_data.goto_path,
            ATTRIBUTE_GOTO_PREDICTED_PATH: map_data.predicted_path,
            ATTRIBUTE_IGNORED_OBSTACLES: map_data.ignored_obstacles,
            ATTRIBUTE_IGNORED_OBSTACLES_WITH_PHOTO: map_data.ignored_obstacles_with_photo,
            ATTRIBUTE_IMAGE: map_data.image,
            ATTRIBUTE_IS_EMPTY: map_data.image.is_empty,
            ATTRIBUTE_MAP_NAME: map_data.map_name,
            ATTRIBUTE_MOP_PATH: map_data.mop_path,
            ATTRIBUTE_NO_CARPET_AREAS: map_data.no_carpet_areas,
            ATTRIBUTE_NO_GO_AREAS: map_data.no_go_areas,
            ATTRIBUTE_NO_MOPPING_AREAS: map_data.no_mopping_areas,
            ATTRIBUTE_OBSTACLES: map_data.obstacles,
            ATTRIBUTE_OBSTACLES_WITH_PHOTO: map_data.obstacles_with_photo,
            ATTRIBUTE_PATH: map_data.path,
            ATTRIBUTE_ROOM_NUMBERS: rooms,
            ATTRIBUTE_ROOMS: map_data.rooms,
            ATTRIBUTE_VACUUM_POSITION: map_data.vacuum_position,
            ATTRIBUTE_VACUUM_ROOM: map_data.vacuum_room,
            ATTRIBUTE_VACUUM_ROOM_NAME: map_data.vacuum_room_name,
            ATTRIBUTE_WALLS: map_data.walls,
            ATTRIBUTE_ZONES: map_data.zones
        }.items():
            if name in attributes_to_return:
                attributes[name] = value
        return attributes

    def update(self):
        if self._status != CameraStatus.TWO_FACTOR_AUTH_REQUIRED and not self._logged_in:
            self._login()
        if self._device is not None:
            if self._logged_in:
                #if we're logged in and the device is initialized - retrieve, parse and render map
                self._download_map_data()
                self._render_map()
                return
            #if the device is up and login failed (?) initialize map data
            self._map_data = MapData()
            self._map_data.image = ImageData.create_empty(self._image_generator.create_empty_map_image(str(self._status)))
            return
        #apparently we should initialize the device in case we haven't done it before
        self._initialize_device()

#        _LOGGER.debug("Unable to retrieve map, reasons: Logged in - %s, device retrieved - %s",
#                    self._logged_in, self._device is not None)

    def _login(self):
        _LOGGER.debug("Logging in...")
        self._logged_in = self._connector.login()
        if self._logged_in is None:
            _LOGGER.debug("2FA required")
            self._status = CameraStatus.TWO_FACTOR_AUTH_REQUIRED
        elif self._logged_in:
            _LOGGER.debug("Logged in")
            self._status = CameraStatus.LOGGED_IN
        else:
            _LOGGER.debug("Failed to log in")
            self._status = CameraStatus.FAILED_LOGIN
            if self._logged_in_previously:
                _LOGGER.error("Unable to log in, check credentials")
        self._logged_in_previously = self._logged_in

    def _render_map(self):
        if self._map_data is None or self._map_data.image is None or self._map_data.image.is_empty:
            return
        if not hasattr(self, "_image_generator") or self._image_generator is None:
            self._image_generator = ImageGenerator(self._colors, self._sizes, self._device.map_data_parser._image_parser._drawables, self._image_config, self._texts)
        self._image_generator.draw_map(self._map_data)
        img_byte_arr = io.BytesIO()
        self._map_data.image.data.save(img_byte_arr, format='PNG')
        self._image = img_byte_arr.getvalue()
        self._store_image()

    def _initialize_device(self):
        _LOGGER.debug("Retrieving device info, country: %s", self._country)
        country, user_id, device_id, model, mac = self._connector.get_device_details(self._token, self._country)
        if model is not None:
            self._country = country
            _LOGGER.debug("Retrieved device model: %s", model)
            self._device = self._create_device(user_id, device_id, model, mac)
            _LOGGER.debug("Created device, used api: %s", self._used_api)
        else:
            _LOGGER.error("Failed to retrieve model")
            self._status = CameraStatus.FAILED_TO_RETRIEVE_DEVICE

    def _download_map_data(self):
        _LOGGER.debug("Retrieving map from Xiaomi cloud")
        self._map_data, map_stored = self._device.get_map()
        if self._map_data is not None:
            # noinspection PyBroadException
            try:
                _LOGGER.debug("Map data retrieved")
                self._map_saved = map_stored
                if self._map_data.image.is_empty:
                    _LOGGER.debug("Map is empty")
                    self._status = CameraStatus.EMPTY_MAP
                else:
                    _LOGGER.debug("Map is ok")
                    self._status = CameraStatus.OK
            except:
                _LOGGER.warning("Unable to parse map data")
                self._status = CameraStatus.UNABLE_TO_PARSE_MAP
        else:
            self._logged_in = False
            _LOGGER.warning("Unable to retrieve map data")
            self._status = CameraStatus.UNABLE_TO_RETRIEVE_MAP

    def _create_device(self, user_id: str, device_id: str, model: str, mac: str) -> XiaomiCloudVacuum:
        self._used_api = self._detect_api(model)
        store_map_path = self._store_map_path if self._store_map_raw else None
        vacuum_config = VacuumConfig(
            connector=self._connector,
            country=self._country,
            user_id=user_id,
            device_id=device_id,
            host=self._host,
            token=self._token,
            model=model,
            _mac=mac,
            palette=self._colors,
            drawables=self._drawables,
            image_config=self._image_config,
            sizes=self._sizes,
            texts=self._texts,
            store_map_path=store_map_path
        )
        if self._used_api == CONF_AVAILABLE_API_XIAOMI:
            return RoborockCloudVacuum(vacuum_config)
        if self._used_api == CONF_AVAILABLE_API_VIOMI:
            return ViomiCloudVacuum(vacuum_config)
        if self._used_api == CONF_AVAILABLE_API_IJAI:
            return IjaiCloudVacuum(vacuum_config)
        if self._used_api == CONF_AVAILABLE_API_ROIDMI:
            return RoidmiCloudVacuum(vacuum_config)
        if self._used_api == CONF_AVAILABLE_API_DREAME:
            return DreameCloudVacuum(vacuum_config)
        return UnsupportedCloudVacuum(vacuum_config)

    def _detect_api(self, model: str) -> str | None:
        if self._forced_api is not None:
            return self._forced_api
        if model in API_EXCEPTIONS:
            return API_EXCEPTIONS[model]

        def list_contains_model(prefixes, model_to_check):
            return len(list(filter(lambda x: model_to_check.startswith(x), prefixes))) > 0

        filtered = list(filter(lambda x: list_contains_model(x[1], model), AVAILABLE_APIS.items()))
        if len(filtered) > 0:
            return filtered[0][0]
        return None

    def _store_image(self):
        if self._store_map_image:
            try:
                image = Image.open(io.BytesIO(self._image))
                image.save(f"{self._store_map_path}/map_image_{self._device.model}.png")
                _LOGGER.debug(f"image path = {self._store_map_path}/map_image_{self._device.model}.png")
            except:
                _LOGGER.warning("Error while saving image")


class CameraStatus(StrEnum):
    EMPTY_MAP = 'Empty map'
    FAILED_LOGIN = 'Failed to login'
    FAILED_TO_RETRIEVE_DEVICE = 'Failed to retrieve device'
    FAILED_TO_RETRIEVE_MAP_FROM_VACUUM = 'Failed to retrieve map from vacuum'
    INITIALIZING = 'Initializing'
    NOT_LOGGED_IN = 'Not logged in'
    OK = 'OK'
    LOGGED_IN = 'Logged in'
    TWO_FACTOR_AUTH_REQUIRED = 'Two factor auth required (see logs)'
    UNABLE_TO_PARSE_MAP = 'Unable to parse map'
    UNABLE_TO_RETRIEVE_MAP = 'Unable to retrieve map'

    def __str__(self):
        return str(self._value_)

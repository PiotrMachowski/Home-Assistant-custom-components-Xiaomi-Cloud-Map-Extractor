import time
import miio
import logging
import io
from datetime import timedelta
from .xiaomi_cloud_connector import XiaomiCloudConnector
from .const import *
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv
from homeassistant.components.camera import PLATFORM_SCHEMA, Camera

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

DEFAULT_TRIMS = {
    CONF_LEFT: 0,
    CONF_RIGHT: 0,
    CONF_TOP: 0,
    CONF_BOTTOM: 0
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
        vol.Required(CONF_COUNTRY): vol.In(CONF_AVAILABLE_COUNTRIES),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COLORS, default={}): vol.Schema({
            vol.In(CONF_AVAILABLE_COLORS): COLOR_SCHEMA
        }),
        vol.Optional(CONF_ROOM_COLORS, default={}): vol.Schema({
            cv.positive_int: COLOR_SCHEMA
        }),
        vol.Optional(CONF_DRAW, default=[]): vol.All(cv.ensure_list, [vol.In(CONF_AVAILABLE_DRAWABLES)]),
        vol.Optional(CONF_MAP_TRANSFORM, default={CONF_SCALE: 1, CONF_ROTATE: 0, CONF_TRIM: DEFAULT_TRIMS}): vol.Schema(
            {
                vol.Optional(CONF_SCALE, default=1): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional(CONF_ROTATE, default=0): vol.In([0, 90, 180, 270]),
                vol.Optional(CONF_TRIM, default=DEFAULT_TRIMS): vol.Schema({
                    vol.Optional(CONF_LEFT, default=0): PERCENT_SCHEMA,
                    vol.Optional(CONF_RIGHT, default=0): PERCENT_SCHEMA,
                    vol.Optional(CONF_TOP, default=0): PERCENT_SCHEMA,
                    vol.Optional(CONF_BOTTOM, default=0): PERCENT_SCHEMA
                }),
            }),
        vol.Optional(CONF_ATTRIBUTES, default=[]): vol.All(cv.ensure_list, [vol.In(CONF_AVAILABLE_ATTRIBUTES)])
    })


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    host = config[CONF_HOST]
    token = config[CONF_TOKEN]
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    country = config[CONF_COUNTRY]
    name = config[CONF_NAME]
    image_config = config[CONF_MAP_TRANSFORM]
    colors = config[CONF_COLORS]
    room_colors = config[CONF_ROOM_COLORS]
    for room, color in room_colors.items():
        colors[f"{COLOR_ROOM_PREFIX}{room}"] = color
    drawables = config[CONF_DRAW]
    if "all" in drawables:
        drawables = CONF_AVAILABLE_DRAWABLES[1:]
    attributes = config[CONF_ATTRIBUTES]
    async_add_entities([VacuumCamera(hass, host, token, username, password, country, name, image_config, colors,
                                     drawables, attributes)])


class VacuumCamera(Camera):
    def __init__(self, hass, host, token, username, password, country, name, image_config, colors, drawables,
                 attributes):
        super().__init__()
        self.hass = hass
        self._vacuum = miio.Vacuum(host, token)
        self._connector = XiaomiCloudConnector(username, password, country)
        self._name = name
        self._image_config = image_config
        self._colors = colors
        self._drawables = drawables
        self._attributes = attributes
        self._image = None
        self._map_data = None
        self._logged = False

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
                ATTRIBUTE_IMAGE: self._map_data.image,
                ATTRIBUTE_VACUUM_POSITION: self._map_data.vacuum_position,
                ATTRIBUTE_PATH: self._map_data.path,
                ATTRIBUTE_GOTO_PATH: self._map_data.goto_path,
                ATTRIBUTE_GOTO_PREDICTED_PATH: self._map_data.predicted_path,
                ATTRIBUTE_ZONES: self._map_data.zones,
                ATTRIBUTE_GOTO: self._map_data.goto,
                ATTRIBUTE_WALLS: self._map_data.walls,
                ATTRIBUTE_NO_GO_AREAS: self._map_data.no_go_areas,
                ATTRIBUTE_NO_MOPPING_AREAS: self._map_data.no_mopping_areas,
                ATTRIBUTE_OBSTACLES: self._map_data.obstacles
            }.items():
                if name in self._attributes:
                    attributes[name] = value
        return attributes

    @property
    def should_poll(self):
        return True

    def update(self):
        counter = 10
        if not self._logged:
            self._logged = self._connector.login()
        map_name = "retry"
        while map_name == "retry" and counter > 0:
            time.sleep(0.1)
            try:
                map_name = self._vacuum.map()[0]
            finally:
                counter = counter - 1
        if self._logged and map_name != "retry":
            self._map_data = self._connector.get_map(map_name, self._colors, self._drawables, self._image_config)
            if self._map_data is not None:
                img_byte_arr = io.BytesIO()
                self._map_data.image.data.save(img_byte_arr, format='PNG')
                self._image = img_byte_arr.getvalue()
                return
        _LOGGER.warning("Unable to retrieve map data")

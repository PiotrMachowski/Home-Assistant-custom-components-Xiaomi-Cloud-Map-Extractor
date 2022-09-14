import logging
import voluptuous as vol


from abc import ABC
from datetime import timedelta
from typing import Optional

from homeassistant.const import CONF_HOST, CONF_TOKEN, CONF_USERNAME, CONF_PASSWORD, CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from custom_components.xiaomi_cloud_map_extractor.vacuum_manager import VacuumManager

from homeassistant.components.camera import Camera, ENTITY_ID_FORMAT, PLATFORM_SCHEMA, SUPPORT_ON_OFF
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.reload import async_setup_reload_service

from custom_components.xiaomi_cloud_map_extractor.const import *

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

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

    manager = VacuumManager(config)

    async_add_entities([VacuumCamera(hass, manager)])


class VacuumCamera(Camera, ABC):
    def __init__(self, hass, manager: VacuumManager):
        super().__init__()

        self._hass = hass
        self._manager = manager
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, manager.name, hass=hass)

        self.content_type = CONTENT_TYPE

        self._remove_async_track_time = async_track_time_interval(
            self._hass, self._manager.update, SCAN_INTERVAL
        )

    async def async_added_to_hass(self) -> None:
        self.async_schedule_update_ha_state(True)

    @property
    def frame_interval(self):
        return 1

    def camera_image(self, width: Optional[int] = None, height: Optional[int] = None) -> Optional[bytes]:
        return self._manager.image

    @property
    def name(self):
        return self._manager.name

    def turn_on(self):
        self._manager.turn_on()

    def turn_off(self):
        self._manager.turn_off()

    @property
    def supported_features(self):
        return SUPPORT_ON_OFF

    @property
    def extra_state_attributes(self):
        return self._manager.attributes

    @property
    def should_poll(self):
        return self._manager.should_poll

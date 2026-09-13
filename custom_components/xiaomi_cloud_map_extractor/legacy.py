from typing import Mapping, Any, Callable

import logging
import voluptuous as vol
from aiohttp import ClientSession
from homeassistant.components.camera import PLATFORM_SCHEMA
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes, Size

from .const import (
    CONF_USED_MAP_API,
    CONF_SERVER,
    CONF_COLORS,
    CONF_IMAGE_CONFIG,
    CONF_ROOM_COLORS,
    CONF_DRAWABLES,
    CONF_SIZES,
    CONF_TEXTS,
    CONF_IMAGE_CONFIG_SCALE,
    CONF_IMAGE_CONFIG_ROTATE,
    CONF_IMAGE_CONFIG_TRIM_LEFT,
    CONF_IMAGE_CONFIG_TRIM_BOTTOM,
    CONF_IMAGE_CONFIG_TRIM_TOP,
    CONF_IMAGE_CONFIG_TRIM_RIGHT,
    DOMAIN,
    NAME,
)
from .connector.vacuums.base.model import VacuumApi
from .connector.xiaomi_cloud.connector import XiaomiCloudConnector, XiaomiCloudDeviceInfo


_LOGGER = logging.getLogger(__name__)

LEGACY_DEFAULT_NAME = NAME

LEGACY_CONF_ATTRIBUTES = "attributes"
LEGACY_CONF_AUTO_UPDATE = "auto_update"
LEGACY_CONF_AVAILABLE_API_DREAME = "dreame"
LEGACY_CONF_AVAILABLE_API_ROIDMI = "roidmi"
LEGACY_CONF_AVAILABLE_API_VIOMI = "viomi"
LEGACY_CONF_AVAILABLE_API_XIAOMI = "xiaomi"
LEGACY_CONF_AVAILABLE_COUNTRIES = ["cn", "de", "us", "ru", "tw", "sg", "in", "i2"]
LEGACY_CONF_BOTTOM = "bottom"
LEGACY_CONF_COLOR = "color"
LEGACY_CONF_COLORS = "colors"
LEGACY_CONF_COUNTRY = "country"
LEGACY_CONF_DRAW = "draw"
LEGACY_CONF_FORCE_API = "force_api"
LEGACY_CONF_FONT = "font"
LEGACY_CONF_FONT_SIZE = "font_size"
LEGACY_CONF_LEFT = "left"
LEGACY_CONF_MAP_TRANSFORM = "map_transformation"
LEGACY_CONF_RIGHT = "right"
LEGACY_CONF_ROOM_COLORS = "room_colors"
LEGACY_CONF_ROTATE = "rotate"
LEGACY_CONF_SCALE = "scale"
LEGACY_CONF_SIZES = "sizes"
LEGACY_CONF_SIZE_CHARGER_RADIUS = "charger_radius"
LEGACY_CONF_SIZE_IGNORED_OBSTACLE_RADIUS = "ignored_obstacle_radius"
LEGACY_CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS = "ignored_obstacle_with_photo_radius"
LEGACY_CONF_SIZE_MOP_PATH_WIDTH = "mop_path_width"
LEGACY_CONF_SIZE_OBSTACLE_RADIUS = "obstacle_radius"
LEGACY_CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS = "obstacle_with_photo_radius"
LEGACY_CONF_SIZE_VACUUM_RADIUS = "vacuum_radius"
LEGACY_CONF_SIZE_PATH_WIDTH = "path_width"
LEGACY_CONF_STORE_MAP_RAW = "store_map_raw"
LEGACY_CONF_STORE_MAP_IMAGE = "store_map_image"
LEGACY_CONF_STORE_MAP_PATH = "store_map_path"
LEGACY_CONF_TEXT = "text"
LEGACY_CONF_TEXTS = "texts"
LEGACY_CONF_TOP = "top"
LEGACY_CONF_TRIM = "trim"
LEGACY_CONF_X = "x"
LEGACY_CONF_Y = "y"

LEGACY_CONF_AVAILABLE_APIS = [
    LEGACY_CONF_AVAILABLE_API_XIAOMI,
    LEGACY_CONF_AVAILABLE_API_VIOMI,
    LEGACY_CONF_AVAILABLE_API_ROIDMI,
    LEGACY_CONF_AVAILABLE_API_DREAME,
]

LEGACY_CONF_AVAILABLE_SIZES = [
    LEGACY_CONF_SIZE_VACUUM_RADIUS,
    LEGACY_CONF_SIZE_PATH_WIDTH,
    LEGACY_CONF_SIZE_IGNORED_OBSTACLE_RADIUS,
    LEGACY_CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS,
    LEGACY_CONF_SIZE_MOP_PATH_WIDTH,
    LEGACY_CONF_SIZE_OBSTACLE_RADIUS,
    LEGACY_CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS,
    LEGACY_CONF_SIZE_CHARGER_RADIUS,
]


LEGACY_ATTRIBUTE_CALIBRATION = "calibration_points"
LEGACY_ATTRIBUTE_CARPET_MAP = "carpet_map"
LEGACY_ATTRIBUTE_CHARGER = "charger"
LEGACY_ATTRIBUTE_CLEANED_ROOMS = "cleaned_rooms"
LEGACY_ATTRIBUTE_COUNTRY = "country"
LEGACY_ATTRIBUTE_GOTO = "goto"
LEGACY_ATTRIBUTE_GOTO_PATH = "goto_path"
LEGACY_ATTRIBUTE_GOTO_PREDICTED_PATH = "goto_predicted_path"
LEGACY_ATTRIBUTE_IGNORED_OBSTACLES = "ignored_obstacles"
LEGACY_ATTRIBUTE_IGNORED_OBSTACLES_WITH_PHOTO = "ignored_obstacles_with_photo"
LEGACY_ATTRIBUTE_IMAGE = "image"
LEGACY_ATTRIBUTE_IS_EMPTY = "is_empty"
LEGACY_ATTRIBUTE_MAP_NAME = "map_name"
LEGACY_ATTRIBUTE_MOP_PATH = "mop_path"
LEGACY_ATTRIBUTE_MAP_SAVED = "map_saved"
LEGACY_ATTRIBUTE_NO_CARPET_AREAS = "no_carpet_areas"
LEGACY_ATTRIBUTE_NO_GO_AREAS = "no_go_areas"
LEGACY_ATTRIBUTE_NO_MOPPING_AREAS = "no_mopping_areas"
LEGACY_ATTRIBUTE_OBSTACLES = "obstacles"
LEGACY_ATTRIBUTE_OBSTACLES_WITH_PHOTO = "obstacles_with_photo"
LEGACY_ATTRIBUTE_PATH = "path"
LEGACY_ATTRIBUTE_ROOMS = "rooms"
LEGACY_ATTRIBUTE_ROOM_NUMBERS = "room_numbers"
LEGACY_ATTRIBUTE_VACUUM_POSITION = "vacuum_position"
LEGACY_ATTRIBUTE_VACUUM_ROOM = "vacuum_room"
LEGACY_ATTRIBUTE_VACUUM_ROOM_NAME = "vacuum_room_name"
LEGACY_ATTRIBUTE_WALLS = "walls"
LEGACY_ATTRIBUTE_ZONES = "zones"

LEGACY_CONF_AVAILABLE_ATTRIBUTES = [
    LEGACY_ATTRIBUTE_CALIBRATION,
    LEGACY_ATTRIBUTE_CARPET_MAP,
    LEGACY_ATTRIBUTE_NO_CARPET_AREAS,
    LEGACY_ATTRIBUTE_CHARGER,
    LEGACY_ATTRIBUTE_CLEANED_ROOMS,
    LEGACY_ATTRIBUTE_COUNTRY,
    LEGACY_ATTRIBUTE_GOTO,
    LEGACY_ATTRIBUTE_GOTO_PATH,
    LEGACY_ATTRIBUTE_GOTO_PREDICTED_PATH,
    LEGACY_ATTRIBUTE_IGNORED_OBSTACLES,
    LEGACY_ATTRIBUTE_IGNORED_OBSTACLES_WITH_PHOTO,
    LEGACY_ATTRIBUTE_IMAGE,
    LEGACY_ATTRIBUTE_IS_EMPTY,
    LEGACY_ATTRIBUTE_MAP_NAME,
    LEGACY_ATTRIBUTE_MOP_PATH,
    LEGACY_ATTRIBUTE_NO_GO_AREAS,
    LEGACY_ATTRIBUTE_NO_MOPPING_AREAS,
    LEGACY_ATTRIBUTE_OBSTACLES,
    LEGACY_ATTRIBUTE_OBSTACLES_WITH_PHOTO,
    LEGACY_ATTRIBUTE_PATH,
    LEGACY_ATTRIBUTE_ROOMS,
    LEGACY_ATTRIBUTE_ROOM_NUMBERS,
    LEGACY_ATTRIBUTE_VACUUM_POSITION,
    LEGACY_ATTRIBUTE_VACUUM_ROOM,
    LEGACY_ATTRIBUTE_VACUUM_ROOM_NAME,
    LEGACY_ATTRIBUTE_WALLS,
    LEGACY_ATTRIBUTE_ZONES,
]


LEGACY_COLOR_CARPETS = "color_carpets"
LEGACY_COLOR_CHARGER = "color_charger"
LEGACY_COLOR_CHARGER_OUTLINE = "color_charger_outline"
LEGACY_COLOR_CLEANED_AREA = "color_cleaned_area"
LEGACY_COLOR_GOTO_PATH = "color_goto_path"
LEGACY_COLOR_GREY_WALL = "color_grey_wall"
LEGACY_COLOR_IGNORED_OBSTACLE = "color_ignored_obstacle"
LEGACY_COLOR_IGNORED_OBSTACLE_WITH_PHOTO = "color_ignored_obstacle_with_photo"
LEGACY_COLOR_MAP_INSIDE = "color_map_inside"
LEGACY_COLOR_MAP_OUTSIDE = "color_map_outside"
LEGACY_COLOR_MAP_WALL = "color_map_wall"
LEGACY_COLOR_MAP_WALL_V2 = "color_map_wall_v2"
LEGACY_COLOR_MOP_PATH = "color_mop_path"
LEGACY_COLOR_NEW_DISCOVERED_AREA = "color_new_discovered_area"
LEGACY_COLOR_NO_CARPET_ZONES = "color_no_carpet_zones"
LEGACY_COLOR_NO_CARPET_ZONES_OUTLINE = "color_no_carpet_zones_outline"
LEGACY_COLOR_NO_GO_ZONES = "color_no_go_zones"
LEGACY_COLOR_NO_GO_ZONES_OUTLINE = "color_no_go_zones_outline"
LEGACY_COLOR_NO_MOPPING_ZONES = "color_no_mop_zones"
LEGACY_COLOR_NO_MOPPING_ZONES_OUTLINE = "color_no_mop_zones_outline"
LEGACY_COLOR_OBSTACLE = "color_obstacle"
LEGACY_COLOR_OBSTACLE_WITH_PHOTO = "color_obstacle_with_photo"
LEGACY_COLOR_PATH = "color_path"
LEGACY_COLOR_PREDICTED_PATH = "color_predicted_path"
LEGACY_COLOR_ROBO = "color_robo"
LEGACY_COLOR_ROBO_OUTLINE = "color_robo_outline"
LEGACY_COLOR_ROOM_NAMES = "color_room_names"
LEGACY_COLOR_SCAN = "color_scan"
LEGACY_COLOR_UNKNOWN = "color_unknown"
LEGACY_COLOR_VIRTUAL_WALLS = "color_virtual_walls"
LEGACY_COLOR_ZONES = "color_zones"
LEGACY_COLOR_ZONES_OUTLINE = "color_zones_outline"

LEGACY_CONF_AVAILABLE_COLORS = [
    LEGACY_COLOR_CARPETS,
    LEGACY_COLOR_CHARGER,
    LEGACY_COLOR_CHARGER_OUTLINE,
    LEGACY_COLOR_CLEANED_AREA,
    LEGACY_COLOR_GOTO_PATH,
    LEGACY_COLOR_GREY_WALL,
    LEGACY_COLOR_IGNORED_OBSTACLE,
    LEGACY_COLOR_IGNORED_OBSTACLE_WITH_PHOTO,
    LEGACY_COLOR_MAP_INSIDE,
    LEGACY_COLOR_MAP_OUTSIDE,
    LEGACY_COLOR_MAP_WALL,
    LEGACY_COLOR_MAP_WALL_V2,
    LEGACY_COLOR_MOP_PATH,
    LEGACY_COLOR_NEW_DISCOVERED_AREA,
    LEGACY_COLOR_NO_CARPET_ZONES,
    LEGACY_COLOR_NO_CARPET_ZONES_OUTLINE,
    LEGACY_COLOR_NO_GO_ZONES,
    LEGACY_COLOR_NO_GO_ZONES_OUTLINE,
    LEGACY_COLOR_NO_MOPPING_ZONES,
    LEGACY_COLOR_NO_MOPPING_ZONES_OUTLINE,
    LEGACY_COLOR_OBSTACLE,
    LEGACY_COLOR_OBSTACLE_WITH_PHOTO,
    LEGACY_COLOR_PATH,
    LEGACY_COLOR_PREDICTED_PATH,
    LEGACY_COLOR_ROBO,
    LEGACY_COLOR_ROBO_OUTLINE,
    LEGACY_COLOR_ROOM_NAMES,
    LEGACY_COLOR_SCAN,
    LEGACY_COLOR_UNKNOWN,
    LEGACY_COLOR_VIRTUAL_WALLS,
    LEGACY_COLOR_ZONES,
    LEGACY_COLOR_ZONES_OUTLINE,
]

LEGACY_DRAWABLE_ALL = "all"
LEGACY_DRAWABLE_CHARGER = "charger"
LEGACY_DRAWABLE_CLEANED_AREA = "cleaned_area"
LEGACY_DRAWABLE_GOTO_PATH = "goto_path"
LEGACY_DRAWABLE_IGNORED_OBSTACLES = "ignored_obstacles"
LEGACY_DRAWABLE_IGNORED_OBSTACLES_WITH_PHOTO = "ignored_obstacles_with_photo"
LEGACY_DRAWABLE_MOP_PATH = "mop_path"
LEGACY_DRAWABLE_NO_CARPET_AREAS = "no_carpet_zones"
LEGACY_DRAWABLE_NO_GO_AREAS = "no_go_zones"
LEGACY_DRAWABLE_NO_MOPPING_AREAS = "no_mopping_zones"
LEGACY_DRAWABLE_OBSTACLES = "obstacles"
LEGACY_DRAWABLE_OBSTACLES_WITH_PHOTO = "obstacles_with_photo"
LEGACY_DRAWABLE_PATH = "path"
LEGACY_DRAWABLE_PREDICTED_PATH = "predicted_path"
LEGACY_DRAWABLE_ROOM_NAMES = "room_names"
LEGACY_DRAWABLE_VACUUM_POSITION = "vacuum_position"
LEGACY_DRAWABLE_VIRTUAL_WALLS = "virtual_walls"
LEGACY_DRAWABLE_ZONES = "zones"

LEGACY_CONF_AVAILABLE_DRAWABLES = [
    LEGACY_DRAWABLE_ALL,
    LEGACY_DRAWABLE_CLEANED_AREA,
    LEGACY_DRAWABLE_CHARGER,
    LEGACY_DRAWABLE_GOTO_PATH,
    LEGACY_DRAWABLE_IGNORED_OBSTACLES,
    LEGACY_DRAWABLE_IGNORED_OBSTACLES_WITH_PHOTO,
    LEGACY_DRAWABLE_MOP_PATH,
    LEGACY_DRAWABLE_NO_CARPET_AREAS,
    LEGACY_DRAWABLE_NO_GO_AREAS,
    LEGACY_DRAWABLE_NO_MOPPING_AREAS,
    LEGACY_DRAWABLE_OBSTACLES,
    LEGACY_DRAWABLE_OBSTACLES_WITH_PHOTO,
    LEGACY_DRAWABLE_PATH,
    LEGACY_DRAWABLE_PREDICTED_PATH,
    LEGACY_DRAWABLE_ROOM_NAMES,
    LEGACY_DRAWABLE_VACUUM_POSITION,
    LEGACY_DRAWABLE_VIRTUAL_WALLS,
    LEGACY_DRAWABLE_ZONES,
]

DEFAULT_TRIMS = {
    LEGACY_CONF_LEFT: 0,
    LEGACY_CONF_RIGHT: 0,
    LEGACY_CONF_TOP: 0,
    LEGACY_CONF_BOTTOM: 0
}

DEFAULT_SIZES = {
    LEGACY_CONF_SIZE_VACUUM_RADIUS: 6,
    LEGACY_CONF_SIZE_PATH_WIDTH: 1,
    LEGACY_CONF_SIZE_IGNORED_OBSTACLE_RADIUS: 3,
    LEGACY_CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS: 3,
    LEGACY_CONF_SIZE_OBSTACLE_RADIUS: 3,
    LEGACY_CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS: 3,
    LEGACY_CONF_SIZE_CHARGER_RADIUS: 6
}

COLOR_SCHEMA = vol.Or(
    vol.All(vol.Length(min=3, max=3), vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple)),
    vol.All(vol.Length(min=4, max=4), vol.ExactSequence((cv.byte, cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple))
)

PERCENT_SCHEMA = vol.All(vol.Coerce(float), vol.Range(min=0, max=100))

POSITIVE_FLOAT_SCHEMA = vol.All(vol.Coerce(float), vol.Range(min=0))

LEGACY_PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(LEGACY_CONF_COUNTRY, default=None): vol.Or(vol.In(LEGACY_CONF_AVAILABLE_COUNTRIES), vol.Equal(None)),
        vol.Optional(CONF_NAME, default=LEGACY_DEFAULT_NAME): cv.string,
        vol.Optional(LEGACY_CONF_AUTO_UPDATE, default=True): cv.boolean,
        vol.Optional(LEGACY_CONF_COLORS, default={}): vol.Schema({
            vol.In(LEGACY_CONF_AVAILABLE_COLORS): COLOR_SCHEMA
        }),
        vol.Optional(LEGACY_CONF_ROOM_COLORS, default={}): vol.Schema({
            cv.positive_int: COLOR_SCHEMA
        }),
        vol.Optional(LEGACY_CONF_DRAW, default=[]): vol.All(cv.ensure_list, [vol.In(LEGACY_CONF_AVAILABLE_DRAWABLES)]),
        vol.Optional(LEGACY_CONF_MAP_TRANSFORM, default={LEGACY_CONF_SCALE: 1, LEGACY_CONF_ROTATE: 0, LEGACY_CONF_TRIM: DEFAULT_TRIMS}):
            vol.Schema({
                vol.Optional(LEGACY_CONF_SCALE, default=1): POSITIVE_FLOAT_SCHEMA,
                vol.Optional(LEGACY_CONF_ROTATE, default=0): vol.In([0, 90, 180, 270]),
                vol.Optional(LEGACY_CONF_TRIM, default=DEFAULT_TRIMS): vol.Schema({
                    vol.Optional(LEGACY_CONF_LEFT, default=0): PERCENT_SCHEMA,
                    vol.Optional(LEGACY_CONF_RIGHT, default=0): PERCENT_SCHEMA,
                    vol.Optional(LEGACY_CONF_TOP, default=0): PERCENT_SCHEMA,
                    vol.Optional(LEGACY_CONF_BOTTOM, default=0): PERCENT_SCHEMA
                }),
            }),
        vol.Optional(LEGACY_CONF_ATTRIBUTES, default=[]): vol.All(cv.ensure_list, [vol.In(LEGACY_CONF_AVAILABLE_ATTRIBUTES)]),
        vol.Optional(LEGACY_CONF_TEXTS, default=[]):
            vol.All(cv.ensure_list, [vol.Schema({
                vol.Required(LEGACY_CONF_TEXT): cv.string,
                vol.Required(LEGACY_CONF_X): vol.Coerce(float),
                vol.Required(LEGACY_CONF_Y): vol.Coerce(float),
                vol.Optional(LEGACY_CONF_COLOR, default=(0, 0, 0)): COLOR_SCHEMA,
                vol.Optional(LEGACY_CONF_FONT, default=None): vol.Or(cv.string, vol.Equal(None)),
                vol.Optional(LEGACY_CONF_FONT_SIZE, default=0): cv.positive_int
            })]),
        vol.Optional(LEGACY_CONF_SIZES, default=DEFAULT_SIZES): vol.Schema({
            vol.Optional(LEGACY_CONF_SIZE_VACUUM_RADIUS,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_VACUUM_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_PATH_WIDTH,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_PATH_WIDTH]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_MOP_PATH_WIDTH,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_VACUUM_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_IGNORED_OBSTACLE_RADIUS,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_IGNORED_OBSTACLE_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_OBSTACLE_RADIUS,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_OBSTACLE_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS]): POSITIVE_FLOAT_SCHEMA,
            vol.Optional(LEGACY_CONF_SIZE_CHARGER_RADIUS,
                         default=DEFAULT_SIZES[LEGACY_CONF_SIZE_CHARGER_RADIUS]): POSITIVE_FLOAT_SCHEMA
        }),
        vol.Optional(LEGACY_CONF_STORE_MAP_RAW, default=False): cv.boolean,
        vol.Optional(LEGACY_CONF_STORE_MAP_IMAGE, default=False): cv.boolean,
        vol.Optional(LEGACY_CONF_STORE_MAP_PATH, default=""): cv.string,
        vol.Optional(LEGACY_CONF_FORCE_API, default=None): vol.Or(vol.In(LEGACY_CONF_AVAILABLE_APIS), vol.Equal(None))
    })


def handle_old_config(hass: HomeAssistant, config: ConfigType) -> None:
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={**config},
        )
    )

    async_create_issue(
        hass,
        DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": NAME,
        },
    )


async def create_config_entry_data_from_yaml(
    import_info: Mapping[str, Any], session_creator: Callable[[], ClientSession]
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    device_id = None
    model = None
    mac = None
    name = None
    server = import_info.get(LEGACY_CONF_COUNTRY, None)
    connector = XiaomiCloudConnector(session_creator)
    try:
        await connector.login_with_credentials(import_info[CONF_USERNAME], import_info[CONF_PASSWORD])
        devices = await connector.get_devices(server)
        device: XiaomiCloudDeviceInfo | None = next(filter(lambda d: d.token == import_info[CONF_TOKEN], devices), None)
        if device is not None:
            device_id = device.device_id
            model = device.model
            mac = format_mac(device.mac)
            name = device.name
            server = device.server
    except BaseException as e:
        _LOGGER.error("Failed to connect to Xiaomi Cloud", exc_info=e)

    used_map_api = import_info.get(LEGACY_CONF_FORCE_API)
    if model is not None and used_map_api is None:
        detected_api = VacuumApi.detect(model)
        used_map_api = detected_api.value if detected_api is not None else None

    data = {
        CONF_HOST: import_info[CONF_HOST],
        CONF_TOKEN: import_info[CONF_TOKEN],
        CONF_DEVICE_ID: device_id,
        CONF_MODEL: model,
        CONF_MAC: mac,
        CONF_NAME: import_info.get(CONF_NAME) or name,
        CONF_USERNAME: import_info[CONF_USERNAME],
        CONF_PASSWORD: import_info[CONF_PASSWORD],
        CONF_SERVER: server,
        CONF_USED_MAP_API: used_map_api,
    }
    options = {
        CONF_IMAGE_CONFIG: {
            **default_image_config(),
            CONF_IMAGE_CONFIG_SCALE: import_info[LEGACY_CONF_MAP_TRANSFORM][LEGACY_CONF_SCALE],
            CONF_IMAGE_CONFIG_ROTATE: import_info[LEGACY_CONF_MAP_TRANSFORM][LEGACY_CONF_ROTATE],
            CONF_IMAGE_CONFIG_TRIM_LEFT: import_info[LEGACY_CONF_MAP_TRANSFORM][LEGACY_CONF_TRIM][LEGACY_CONF_LEFT],
            CONF_IMAGE_CONFIG_TRIM_RIGHT: import_info[LEGACY_CONF_MAP_TRANSFORM][LEGACY_CONF_TRIM][LEGACY_CONF_RIGHT],
            CONF_IMAGE_CONFIG_TRIM_TOP: import_info[LEGACY_CONF_MAP_TRANSFORM][LEGACY_CONF_TRIM][LEGACY_CONF_TOP],
            CONF_IMAGE_CONFIG_TRIM_BOTTOM: import_info[LEGACY_CONF_MAP_TRANSFORM][LEGACY_CONF_TRIM][LEGACY_CONF_BOTTOM],
        },
        CONF_COLORS: {
            **map_colors_map(ColorsPalette.COLORS),
            **map_colors_map(import_info[LEGACY_CONF_COLORS]),
        },
        CONF_ROOM_COLORS: {},
        CONF_DRAWABLES: [
            e.value
            for e in Drawable
            if e not in [
                Drawable.ROOM_NAMES,
                Drawable.NO_CARPET_AREAS,
                Drawable.IGNORED_OBSTACLES,
                Drawable.IGNORED_OBSTACLES_WITH_PHOTO,
            ]
        ],
        CONF_SIZES: {
            **{k.value: v for k, v in Sizes.SIZES.items()},
            Size.VACUUM_RADIUS.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_VACUUM_RADIUS],
            Size.PATH_WIDTH.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_PATH_WIDTH],
            Size.IGNORED_OBSTACLE_RADIUS.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_IGNORED_OBSTACLE_RADIUS],
            Size.IGNORED_OBSTACLE_WITH_PHOTO_RADIUS.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_IGNORED_OBSTACLE_WITH_PHOTO_RADIUS],
            Size.MOP_PATH_WIDTH.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_MOP_PATH_WIDTH],
            Size.OBSTACLE_RADIUS.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_OBSTACLE_RADIUS],
            Size.OBSTACLE_WITH_PHOTO_RADIUS.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_OBSTACLE_WITH_PHOTO_RADIUS],
            Size.CHARGER_RADIUS.value: import_info[LEGACY_CONF_SIZES][LEGACY_CONF_SIZE_CHARGER_RADIUS],
        },
        CONF_TEXTS: [],
    }
    return data, options


def default_image_config() -> dict[str, float]:
    image_config = ImageConfig()
    return {
        CONF_IMAGE_CONFIG_SCALE: image_config.scale,
        CONF_IMAGE_CONFIG_ROTATE: image_config.rotate,
        CONF_IMAGE_CONFIG_TRIM_LEFT: image_config.trim.left,
        CONF_IMAGE_CONFIG_TRIM_RIGHT: image_config.trim.right,
        CONF_IMAGE_CONFIG_TRIM_TOP: image_config.trim.top,
        CONF_IMAGE_CONFIG_TRIM_BOTTOM: image_config.trim.bottom,
    }


def default_colors() -> dict[str, tuple[int, int, int, int]]:
    return map_colors_map(ColorsPalette.COLORS)


def map_colors_map(
    data: dict[str, tuple[int, int, int] | tuple[int, int, int, int]],
) -> dict[str, tuple[int, int, int, int]]:
    return {
        k: ((v[0], v[1], v[2], v[3]) if len(v) == 4 else (v[0], v[1], v[2], 255))
        for k, v in data.items()
    }

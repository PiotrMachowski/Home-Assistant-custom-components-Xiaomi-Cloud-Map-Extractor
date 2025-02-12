from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

NAME: Final = "Xiaomi Cloud Map Extractor"

DOMAIN: Final = "xiaomi_cloud_map_extractor"

PLATFORMS: list[Platform] = [
    Platform.CAMERA,
    Platform.IMAGE,
]

CONTENT_TYPE: Final = "image/png"
DEFAULT_UPDATE_INTERVAL: Final = timedelta(seconds=10)

CONF_USED_MAP_API: Final = "used_map_api"
CONF_SERVER: Final = "server"

CONF_IMAGE_CONFIG: Final = "image_config"
CONF_IMAGE_CONFIG_SCALE: Final = "scale"
CONF_IMAGE_CONFIG_ROTATE: Final = "rotate"
CONF_IMAGE_CONFIG_TRIM_LEFT: Final = "trim_left"
CONF_IMAGE_CONFIG_TRIM_RIGHT: Final = "trim_right"
CONF_IMAGE_CONFIG_TRIM_TOP: Final = "trim_top"
CONF_IMAGE_CONFIG_TRIM_BOTTOM: Final = "trim_bottom"

CONF_COLORS: Final = "colors"

CONF_ROOM_COLORS = "room_colors"

CONF_DRAWABLES: Final = "drawables"

CONF_SIZES: Final = "sizes"

CONF_TEXTS: Final = "texts"
CONF_TEXT_VALUE: Final = "text"
CONF_TEXT_X: Final = "x"
CONF_TEXT_Y: Final = "y"
CONF_TEXT_COLOR: Final = "color"
CONF_TEXT_FONT: Final = "font"
CONF_TEXT_FONT_SIZE: Final = "font_size"

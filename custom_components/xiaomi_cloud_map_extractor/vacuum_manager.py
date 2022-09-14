import io
import logging
import time
from typing import List, Optional

from custom_components.xiaomi_cloud_map_extractor.common.map_data import MapData
from custom_components.xiaomi_cloud_map_extractor.types import Colors, Drawables, ImageConfig, Sizes, Texts

try:
    from miio import RoborockVacuum, DeviceException
except ImportError:
    from miio import Vacuum as RoborockVacuum, DeviceException

import PIL.Image as Image

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME

from custom_components.xiaomi_cloud_map_extractor.common.map_data_parser import MapDataParser
from custom_components.xiaomi_cloud_map_extractor.common.xiaomi_cloud_connector import XiaomiCloudConnector
from custom_components.xiaomi_cloud_map_extractor.const import *
from custom_components.xiaomi_cloud_map_extractor.dreame.vacuum import DreameVacuum
from custom_components.xiaomi_cloud_map_extractor.enums import CameraStatus
from custom_components.xiaomi_cloud_map_extractor.roidmi.vacuum import RoidmiVacuum
from custom_components.xiaomi_cloud_map_extractor.unsupported.vacuum import UnsupportedVacuum
from custom_components.xiaomi_cloud_map_extractor.viomi.vacuum import ViomiVacuum
from custom_components.xiaomi_cloud_map_extractor.xiaomi.vacuum import XiaomiVacuum


_LOGGER = logging.getLogger(__name__)

DEVICE_MAPPING = {
    CONF_AVAILABLE_API_XIAOMI: XiaomiVacuum,
    CONF_AVAILABLE_API_VIOMI: ViomiVacuum,
    CONF_AVAILABLE_API_ROIDMI: RoidmiVacuum,
    CONF_AVAILABLE_API_DREAME: DreameVacuum,
}

STATUS_LOG_LEVEL = {
    CameraStatus.FAILED_TO_RETRIEVE_DEVICE: _LOGGER.error,
    CameraStatus.UNABLE_TO_PARSE_MAP: _LOGGER.warning,
    CameraStatus.UNABLE_TO_RETRIEVE_MAP: _LOGGER.warning
}


class VacuumManager:
    def __init__(self, config):

        host: str = config[CONF_HOST]
        token: str = config[CONF_TOKEN]
        username: str = config[CONF_USERNAME]
        password: str = config[CONF_PASSWORD]

        drawables = config.get(CONF_DRAW, [])
        room_colors = config.get(CONF_ROOM_COLORS, {})
        colors: Colors = config.get(CONF_COLORS, {})

        for room, color in room_colors.items():
            colors[f"{COLOR_ROOM_PREFIX}{room}"] = color

        self._vacuum = RoborockVacuum(host, token)
        self._connector = XiaomiCloudConnector(username, password)

        self._name: str = config.get(CONF_NAME, DEFAULT_NAME)
        self._should_poll: bool = config.get(CONF_AUTO_UPDATE, True)
        self._image_config: ImageConfig = config.get(CONF_MAP_TRANSFORM, DEFAULT_MAP_TRANSFORM)
        self._colors: Colors = colors
        self._drawables: Drawables = CONF_AVAILABLE_DRAWABLES[1:] if DRAWABLE_ALL in drawables else drawables
        self._sizes: Sizes = config.get(CONF_SIZES, DEFAULT_SIZES)
        self._texts: Texts = config.get(CONF_TEXTS, [])
        self._country: str = config.get(CONF_COUNTRY)
        self._allowed_attributes: List[str] = config.get(CONF_ATTRIBUTES, [])
        self._store_map_raw: bool = config.get(CONF_STORE_MAP_RAW, False)
        self._store_map_image: bool = config.get(CONF_STORE_MAP_IMAGE)
        self._store_map_path: str = config.get(CONF_STORE_MAP_PATH, DEFAULT_STORE_MAP_PATH)
        self._forced_api: str = config.get(CONF_FORCE_API)

        self._device = None
        self._used_api = None
        self._map_saved = None
        self._image = None
        self._map_data = None
        self._logged_in = False

        self._logged_in_previously = True
        self._received_map_name_previously = True

        self._attributes = {}

        self._status = CameraStatus.INITIALIZING

    @property
    def image(self) -> Optional[bytes]:
        return self._image

    @property
    def name(self):
        return self._name

    @property
    def attributes(self):
        return self._attributes

    @property
    def should_poll(self):
        return self._should_poll

    def turn_on(self):
        self._should_poll = True

    def turn_off(self):
        self._should_poll = False

    def _get_attributes_data(self):
        map_data = self._map_data

        rooms = []
        if self._map_data.rooms is not None:
            rooms = dict(
                filter(lambda x: x[0] is not None, map(lambda x: (x[0], x[1].name), self._map_data.rooms.items())))
            if len(rooms) == 0:
                rooms = list(self._map_data.rooms.keys())

        attributes = {
            ATTRIBUTE_CALIBRATION: map_data.calibration(),
            ATTRIBUTE_CHARGER: map_data.charger,
            ATTRIBUTE_CLEANED_ROOMS: map_data.cleaned_rooms,
            ATTRIBUTE_COUNTRY: self._country,
            ATTRIBUTE_GOTO: map_data.goto,
            ATTRIBUTE_GOTO_PATH: map_data.goto_path,
            ATTRIBUTE_GOTO_PREDICTED_PATH: map_data.predicted_path,
            ATTRIBUTE_IGNORED_OBSTACLES: map_data.ignored_obstacles,
            ATTRIBUTE_IGNORED_OBSTACLES_WITH_PHOTO: map_data.ignored_obstacles_with_photo,
            ATTRIBUTE_IMAGE: map_data.image,
            ATTRIBUTE_IS_EMPTY: map_data.image.is_empty,
            ATTRIBUTE_MAP_NAME: map_data.map_name,
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
        }

        return attributes

    def _update_attributes(self):
        attributes = {}
        if self._map_data is not None:
            data = self._get_attributes_data()

            for name, value in data.items():
                if name in self._allowed_attributes:
                    attributes[name] = value

        if self._store_map_raw:
            attributes[ATTRIBUTE_MAP_SAVED] = self._map_saved

        if self._device is not None:
            attributes[ATTR_MODEL] = self._device.model
            attributes[ATTR_USED_API] = self._used_api

        if self._connector.two_factor_auth_url is not None:
            attributes[ATTR_TWO_FACTOR_AUTH] = self._connector.two_factor_auth_url

        self._attributes = attributes

    def update(self, now):
        counter = 10

        if self._status != CameraStatus.TWO_FACTOR_AUTH_REQUIRED and not self._logged_in:
            self._handle_login()

        if self._device is None and self._logged_in:
            self._handle_device()

        map_name = self._handle_map_name(counter)
        if map_name == "retry" and self._device is not None:
            self._set_status(CameraStatus.FAILED_TO_RETRIEVE_MAP_FROM_VACUUM)

        self._received_map_name_previously = map_name != "retry"
        if self._logged_in and map_name != "retry" and self._device is not None:
            self._handle_map_data(map_name)

        else:
            exists = self._device is not None

            _LOGGER.debug(
                f"Unable to retrieve map ({now}), "
                f"Logged in: {self._logged_in} | "
                f"Map name: {map_name} | "
                f"Device retrieved: {exists}"
            )

            message = str(self._status)
            map_data = MapDataParser.create_empty(self._colors, message)
            self._set_map_data(map_data)

        self._logged_in_previously = self._logged_in

        self._update_attributes()

    def _handle_login(self):
        _LOGGER.debug("Logging in...")

        self._logged_in = self._connector.login()
        if self._logged_in is None:
            self._set_status(CameraStatus.TWO_FACTOR_AUTH_REQUIRED)

        elif self._logged_in:
            self._set_status(CameraStatus.LOGGED_IN)

        else:
            self._set_status(CameraStatus.FAILED_LOGIN)

            if self._logged_in_previously:
                _LOGGER.error("Unable to log in, check credentials")

    def _handle_device(self):
        _LOGGER.debug(f"Retrieving device info, country: {self._country}")

        country, user_id, device_id, model = self._connector.get_device_details(self._vacuum.token, self._country)
        if model is not None:
            self._country = country
            _LOGGER.debug(f"Retrieved device model: {model}")

            self._used_api = self._detect_api(model)

            device_init = DEVICE_MAPPING.get(self._used_api, UnsupportedVacuum)
            self._device = device_init(self._connector, self._country, user_id, device_id, model)
            _LOGGER.debug(f"Created device, used api: {self._used_api}")

        else:
            self._set_status(CameraStatus.FAILED_TO_RETRIEVE_DEVICE)

    def _handle_map_name(self, counter):
        map_name = "retry"
        if self._device is not None and not self._device.should_get_map_from_vacuum():
            map_name = "0"

        while map_name == "retry" and counter > 0:
            _LOGGER.debug("Retrieving map name from device")
            time.sleep(0.1)

            try:
                map_name = self._vacuum.map()[0]
                _LOGGER.debug("Map name %s", map_name)

            except OSError as exc:
                _LOGGER.error(f"Got OSError while fetching the state: {str(exc)}")

            except DeviceException as exc:
                if self._received_map_name_previously:
                    _LOGGER.warning(f"Got exception while fetching the state: {str(exc)}")

                self._received_map_name_previously = False

            finally:
                counter = counter - 1

        return map_name

    def _handle_map_data(self, map_name):
        _LOGGER.debug("Retrieving map from Xiaomi cloud")
        store_map_path = self._store_map_path if self._store_map_raw else None
        map_data, map_stored = self._device.get_map(map_name, self._colors, self._drawables, self._texts,
                                                    self._sizes, self._image_config, store_map_path)
        if map_data is not None:
            # noinspection PyBroadException
            try:
                _LOGGER.debug("Map data retrieved")
                self._set_map_data(map_data)
                self._map_saved = map_stored

                if self._map_data.image.is_empty:
                    self._set_status(CameraStatus.EMPTY_MAP)

                    if self._map_data is None or self._map_data.image.is_empty:
                        self._set_map_data(map_data)

                else:
                    self._set_map_data(map_data)

                    self._set_status(CameraStatus.OK)

            except Exception as ex:
                self._set_status(CameraStatus.UNABLE_TO_PARSE_MAP, ex)

        else:
            self._logged_in = False
            self._set_status(CameraStatus.UNABLE_TO_RETRIEVE_MAP)

    def _set_status(self, status, ex: Optional[Exception] = None):
        log = STATUS_LOG_LEVEL.get(status, _LOGGER.debug)

        log_message = status
        if ex is not None:
            log_message = f"{status}, Error: {str(ex)}"

        self._status = status
        log(log_message)

    def _set_map_data(self, map_data: MapData):
        img_byte_arr = io.BytesIO()
        map_data.image.data.save(img_byte_arr, format='PNG')
        self._image = img_byte_arr.getvalue()
        self._map_data = map_data
        self._store_image()

    def _detect_api(self, model: str):
        if self._forced_api is not None:
            return self._forced_api
        if model in API_EXCEPTIONS:
            return API_EXCEPTIONS[model]

        def list_contains_model(prefixes):
            return len(list(filter(lambda x: model.startswith(x), prefixes))) > 0

        filtered = list(filter(lambda x: list_contains_model(x[1]), AVAILABLE_APIS.items()))
        if len(filtered) > 0:
            return filtered[0][0]

        return CONF_AVAILABLE_API_XIAOMI

    def _store_image(self):
        if self._store_map_image:
            try:
                if self._image is not None:
                    image = Image.open(io.BytesIO(self._image))
                    image.save(f"{self._store_map_path}/map_image_{self._device.model}.png")

            except Exception as ex:
                _LOGGER.warning(f"Error while saving image, Error: {str(ex)}")

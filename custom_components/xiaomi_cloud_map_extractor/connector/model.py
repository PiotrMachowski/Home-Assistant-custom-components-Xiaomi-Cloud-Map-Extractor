import base64
import enum
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import IntEnum
from typing import Self, Any

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_base.config.text import Text
from vacuum_map_parser_base.map_data import MapData

from .vacuums.base.model import VacuumApi


class XiaomiCloudMapExtractorConnectorStatus(IntEnum):
    UNKNOWN = enum.auto()
    UNINITIALIZED = enum.auto()
    OK = enum.auto()
    FAILED_LOGIN = enum.auto()
    INVALID_CREDENTIALS = enum.auto()
    TWO_FACTOR_REQUIRED = enum.auto()
    DEVICE_NOT_FOUND = enum.auto()
    INVALID_TOKEN = enum.auto()
    FAILED_MAP_DOWNLOAD = enum.auto()
    FAILED_MAP_PARSING = enum.auto()


@dataclass
class XiaomiCloudMapExtractorConnectorConfiguration:
    host: str
    token: str
    username: str
    password: str
    server: str
    used_api: VacuumApi
    device_id: str
    mac: str
    model: str
    image_config: ImageConfig
    colors: ColorsPalette
    drawables: list[Drawable]
    sizes: Sizes
    texts: list[Text]
    store_map_raw: bool
    store_map_image: bool
    store_map_path: str


@dataclass
class XiaomiCloudMapExtractorData:
    map_data: MapData | None = None
    map_data_raw: bytes | None = None
    map_image: bytes | None = None
    map_saved: bool = False
    two_factor_url: str | None = None
    last_update_timestamp: datetime | None = None
    last_successful_update_timestamp: datetime | None = None
    status: XiaomiCloudMapExtractorConnectorStatus = XiaomiCloudMapExtractorConnectorStatus.UNKNOWN

    def as_dict(self: Self) -> dict[str, Any]:
        map_image_dict = self.map_data and self.map_data.image and {
            **self.map_data.image.as_dict(),
            "image_bytes": base64.b64encode(self.map_data.image.data.tobytes()).decode()
        }

        map_data_dict = self.map_data and {
            "blocks": self.map_data.blocks,
            "charger": self.map_data.charger and asdict(self.map_data.charger),
            "goto": self.map_data.goto and asdict(self.map_data.goto),
            "goto_path": self.map_data.goto_path and asdict(self.map_data.goto_path),
            "image": map_image_dict,
            "no_go_areas": list(map(lambda a: asdict(a), self.map_data.no_go_areas or [])),
            "no_mopping_areas": list(map(lambda a: asdict(a), self.map_data.no_mopping_areas or [])),
            "no_carpet_areas": list(map(lambda a: asdict(a), self.map_data.no_carpet_areas or [])),
            "carpet_map": list(map(lambda a: asdict(a), self.map_data.carpet_map or [])),
            "obstacles": list(map(lambda a: asdict(a), self.map_data.obstacles or [])),
            "ignored_obstacles": list(map(lambda a: asdict(a), self.map_data.ignored_obstacles or [])),
            "obstacles_with_photo": list(map(lambda a: asdict(a), self.map_data.obstacles_with_photo or [])),
            "ignored_obstacles_with_photo": list(
                map(lambda a: asdict(a), self.map_data.ignored_obstacles_with_photo or [])),
            "path": self.map_data.path and asdict(self.map_data.path),
            "predicted_path": self.map_data.predicted_path and asdict(self.map_data.predicted_path),
            "mop_path": self.map_data.mop_path and asdict(self.map_data.mop_path),
            "rooms": list(map(lambda a: asdict(a), self.map_data.rooms or [])),
            "vacuum_position": self.map_data.vacuum_position and asdict(self.map_data.vacuum_position),
            "vacuum_room": self.map_data.vacuum_room,
            "vacuum_room_name": self.map_data.vacuum_room_name,
            "walls": list(map(lambda a: asdict(a), self.map_data.walls or [])),
            "zones": list(map(lambda a: asdict(a), self.map_data.zones or [])),
            "cleaned_rooms": list(map(lambda a: asdict(a), self.map_data.cleaned_rooms or [])),
            "map_name": self.map_data.map_name,
            "additional_parameters": self.map_data.additional_parameters,
            "calibration": self.map_data.calibration()
        }
        return {
            'map_data': map_data_dict,
            'map_data_raw': self.map_data_raw and base64.b64encode(self.map_data_raw).decode(),
            'map_image': self.map_image and base64.b64encode(self.map_image).decode(),
            'map_saved': self.map_saved,
            'last_update_timestamp': self.last_update_timestamp and self.last_update_timestamp.strftime(
                '%Y-%m-%d %H:%M:%S'),
            'last_successful_update_timestamp': self.last_successful_update_timestamp and self.last_successful_update_timestamp.strftime(
                '%Y-%m-%d %H:%M:%S'),
            'status': self.status,
        }

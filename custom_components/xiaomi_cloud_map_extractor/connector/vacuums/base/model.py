from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_base.config.text import Text

from ...xiaomi_cloud.connector import XiaomiCloudConnector, XiaomiCloudDeviceInfo


@dataclass
class VacuumConfig:
    connector: XiaomiCloudConnector
    device_info: XiaomiCloudDeviceInfo
    server: str
    device_id: str
    host: str
    token: str
    model: str
    palette: ColorsPalette
    drawables: list[Drawable]
    image_config: ImageConfig
    sizes: Sizes
    texts: list[Text]
    store_map_path: str | None


class VacuumApi(StrEnum):
    ROBOROCK = "ROBOROCK"
    VIOMI = "VIOMI"
    ROIDMI = "ROIDMI"
    DREAME = "DREAME"
    UNSUPPORTED = "UNSUPPORTED"

    @staticmethod
    def detect(vacuum_model: str) -> VacuumApi | None:
        if vacuum_model in API_EXCEPTIONS:
            return API_EXCEPTIONS[vacuum_model]

        def list_contains_model(prefixes, model_to_check):
            return len(list(filter(lambda x: model_to_check.startswith(x), prefixes))) > 0

        filtered = list(filter(lambda x: list_contains_model(x[1], vacuum_model), AVAILABLE_APIS.items()))
        if len(filtered) > 0:
            return filtered[0][0]
        return VacuumApi.UNSUPPORTED


AVAILABLE_APIS = {
    VacuumApi.DREAME: ["dreame.vacuum."],
    VacuumApi.ROIDMI: ["roidmi.vacuum.", "zhimi.vacuum.", "chuangmi.vacuum."],
    VacuumApi.VIOMI: ["viomi.vacuum."],
    VacuumApi.ROBOROCK: ["roborock.vacuum", "rockrobo.vacuum"]
}

API_EXCEPTIONS = {
    "viomi.vacuum.v18": VacuumApi.ROIDMI,
    "viomi.vacuum.v23": VacuumApi.ROIDMI,
    "viomi.vacuum.v38": VacuumApi.ROIDMI,
}

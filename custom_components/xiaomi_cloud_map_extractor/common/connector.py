import logging
from typing import Any, Dict, Optional, Tuple

_LOGGER = logging.getLogger(__name__)


# noinspection PyBroadException
class Connector:

    def login(self) -> bool:
        return False

    def get_raw_map_data(self, map_url) -> Optional[bytes]:
        return None

    def get_device_details(self, token: str,
                           country: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        return None, None, None, None

    def execute_api_call_encrypted(self, url: str, params: Dict[str, str]) -> Any:
        return None
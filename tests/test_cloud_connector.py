"""Xiaomi cloud connector: device discovery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.xiaomi_cloud_map_extractor.connector.utils.exceptions import FailedConnectionException
from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.connector import XiaomiCloudConnector


@pytest.mark.parametrize(
    "error", [TimeoutError(), FailedConnectionException(OSError("reset"))], ids=lambda error: type(error).__name__
)
async def test_home_device_list_failure_skips_that_home(error: Exception) -> None:
    """A home whose device list cannot be fetched yields no devices instead of crashing discovery.

    Upstream wrote `except FailedConnectionException | TimeoutError`, which Python rejects with
    TypeError the moment an exception reaches it, so one slow home aborted the whole config flow.
    """
    connector = XiaomiCloudConnector(MagicMock())
    connector.execute_api_call_encrypted = AsyncMock(side_effect=error)

    assert await connector._get_devices_from_home("de", 1, 2) == []

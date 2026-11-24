"""Shared fixtures.

The Xiaomi cloud and the vacuum are never contacted: the config flow talks to a mocked
`XiaomiCloudConnector`, and setup uses a mocked `XiaomiCloudMapExtractorConnector`.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.xiaomi_cloud_map_extractor.connector.model import (
    XiaomiCloudMapExtractorConnectorStatus,
    XiaomiCloudMapExtractorData,
)
from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.connector import (
    XiaomiCloudDeviceInfo,
)

from .const import VACUUM_DEVICE


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


def make_device(**overrides) -> XiaomiCloudDeviceInfo:
    return XiaomiCloudDeviceInfo(**{**VACUUM_DEVICE, **overrides})


@pytest.fixture
def cloud_connector() -> Generator[MagicMock]:
    """The cloud connector the config flow creates, logged in with one vacuum."""
    with patch(
        "custom_components.xiaomi_cloud_map_extractor.config_flow.XiaomiCloudConnector",
        autospec=True,
    ) as connector_class:
        connector = connector_class.return_value
        connector.login_with_credentials = AsyncMock(return_value="user_id")
        connector.get_devices = AsyncMock(return_value=[make_device()])
        connector.to_config = MagicMock(return_value=None)
        yield connector


@pytest.fixture
def no_store() -> Generator[AsyncMock]:
    """Skip persisting the cloud session; the flow tests do not read it back."""
    with patch(
        "custom_components.xiaomi_cloud_map_extractor.config_flow.save_connector_config",
        new=AsyncMock(),
    ) as save:
        yield save


@pytest.fixture
def map_connector() -> Generator[MagicMock]:
    """The runtime connector used by the coordinator; returns an empty, healthy map."""
    with patch(
        "custom_components.xiaomi_cloud_map_extractor.XiaomiCloudMapExtractorConnector",
        autospec=True,
    ) as connector_class:
        connector = connector_class.return_value
        connector.get_data = AsyncMock(
            return_value=XiaomiCloudMapExtractorData(status=XiaomiCloudMapExtractorConnectorStatus.OK)
        )
        connector.is_auto_updating = MagicMock(return_value=True)
        yield connector

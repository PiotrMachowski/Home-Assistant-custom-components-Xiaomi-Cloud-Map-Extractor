"""Setup and the coordinator: which connector errors ask for re-authentication."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_cloud_map_extractor.config_flow import XiaomiCloudMapExtractorFlowHandler
from custom_components.xiaomi_cloud_map_extractor.connector.utils.exceptions import (
    CaptchaRequiredException,
    DeviceNotFoundException,
    FailedLoginException,
    FailedMapDownloadException,
    FailedMapParseException,
    InvalidCredentialsException,
    InvalidDeviceTokenException,
    TwoFactorAuthRequiredException,
)
from custom_components.xiaomi_cloud_map_extractor.const import DOMAIN

from .const import ENTRY_DATA, MAC


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    flow = XiaomiCloudMapExtractorFlowHandler
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        title="Living room vacuum",
        data=ENTRY_DATA,
        options={
            "image_config": flow._default_image_config(),
            "colors": flow._default_colors(),
            "room_colors": {},
            "drawables": ["charger", "path"],
            "sizes": {},
            "texts": [],
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_and_unload(hass: HomeAssistant, map_connector: MagicMock) -> None:
    entry = _entry(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    map_connector.get_data.assert_awaited()
    assert hass.states.get("image.living_room_vacuum_live_map") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    "error",
    [
        FailedLoginException(),
        InvalidCredentialsException(),
        InvalidDeviceTokenException(),
        TwoFactorAuthRequiredException("https://2fa", {}, "context"),
        CaptchaRequiredException("https://captcha", b"png"),
        DeviceNotFoundException(),
    ],
    ids=lambda error: type(error).__name__,
)
async def test_auth_errors_start_reauth(hass: HomeAssistant, map_connector: MagicMock, error: Exception) -> None:
    map_connector.get_data.side_effect = error
    entry = _entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


@pytest.mark.parametrize(
    "error", [FailedMapDownloadException(), FailedMapParseException()], ids=lambda error: type(error).__name__
)
async def test_map_errors_retry_without_reauth(
    hass: HomeAssistant, map_connector: MagicMock, error: Exception
) -> None:
    map_connector.get_data.side_effect = error
    entry = _entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []


async def test_entry_without_device_id_asks_for_reauth(hass: HomeAssistant, map_connector: MagicMock) -> None:
    """Entries imported from YAML have no cloud device id until the user logs in."""
    entry = _entry(hass)
    hass.config_entries.async_update_entry(entry, data={**ENTRY_DATA, "device_id": None})

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    map_connector.get_data.assert_not_awaited()

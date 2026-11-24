"""What the user sees when the background session can't be kept alive."""

from __future__ import annotations

import logging
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
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
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_cloud_map_extractor.connector.utils.exceptions import (
    CaptchaRequiredException,
    FailedConnectionException,
    TwoFactorAuthRequiredException,
)
from custom_components.xiaomi_cloud_map_extractor.const import (
    CONF_COLORS,
    CONF_DRAWABLES,
    CONF_IMAGE_CONFIG,
    CONF_ROOM_COLORS,
    CONF_SERVER,
    CONF_SIZES,
    CONF_TEXTS,
    CONF_TWO_FACTOR_CODE,
    CONF_USED_MAP_API,
    DOMAIN,
)

PACKAGE = "custom_components.xiaomi_cloud_map_extractor"
CAPTCHA_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00captcha"
VERIFY_URL = "https://account.xiaomi.com/fe/service/identity/authStart?sid=xiaomiio&context=ctx123"


def make_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        source=config_entries.SOURCE_IMPORT,
        title="Xiaomi Cloud Map Extractor",
        unique_id="60:1d:9d:3b:87:37",
        data={
            CONF_HOST: "192.168.1.14",
            CONF_TOKEN: "0" * 32,
            CONF_DEVICE_ID: "428789378",
            CONF_MODEL: "viomi.vacuum.v8",
            CONF_MAC: "60:1d:9d:3b:87:37",
            CONF_NAME: "Viomi V8",
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "stored-password",
            CONF_SERVER: "de",
            CONF_USED_MAP_API: "VIOMI",
        },
        options={
            CONF_IMAGE_CONFIG: {
                "scale": 1, "rotate": 0, "trim_left": 0, "trim_right": 0, "trim_top": 0, "trim_bottom": 0,
            },
            CONF_COLORS: {},
            CONF_ROOM_COLORS: {},
            CONF_DRAWABLES: [],
            CONF_SIZES: {},
            CONF_TEXTS: [],
        },
    )


@pytest.fixture
def background_failure() -> Generator[AsyncMock]:
    """The map connector's update, as run by the coordinator."""
    with (
        patch(f"{PACKAGE}.restore_connector_config", return_value=None),
        patch(f"{PACKAGE}.connector.XiaomiCloudMapExtractorConnector.get_data") as get_data,
    ):
        yield get_data


async def setup_failing_entry(hass: HomeAssistant, error: Exception, get_data: AsyncMock) -> MockConfigEntry:
    get_data.side_effect = error
    entry = make_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def reauth_flows(hass: HomeAssistant) -> list[dict]:
    return [f for f in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
            if f["context"]["source"] == config_entries.SOURCE_REAUTH]


async def test_network_failure_does_not_ask_user_to_reauthenticate(
    hass: HomeAssistant, background_failure: AsyncMock
) -> None:
    entry = await setup_failing_entry(hass, FailedConnectionException(TimeoutError()), background_failure)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert reauth_flows(hass) == []


async def test_captcha_in_background_starts_reauth_without_logging_image_bytes(
    hass: HomeAssistant, background_failure: AsyncMock, caplog
) -> None:
    with caplog.at_level(logging.DEBUG):
        entry = await setup_failing_entry(
            hass, CaptchaRequiredException("https://account.xiaomi.com/pass/getCode", CAPTCHA_BYTES), background_failure
        )

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert "\\xff" not in caplog.text and "JFIF" not in caplog.text
    [flow] = reauth_flows(hass)
    assert flow["step_id"] == "reauth_captcha"


async def test_reauth_after_captcha_offers_login_with_saved_credentials(
    hass: HomeAssistant, background_failure: AsyncMock
) -> None:
    await setup_failing_entry(
        hass, CaptchaRequiredException("https://account.xiaomi.com/pass/getCode", CAPTCHA_BYTES), background_failure
    )
    [flow] = reauth_flows(hass)

    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"][0] == "auth_saved_credentials"

    with patch(f"{PACKAGE}.config_flow.XiaomiCloudConnector", autospec=True) as connector_cls:
        connector_cls.return_value.login_with_credentials = AsyncMock(
            side_effect=CaptchaRequiredException("https://account.xiaomi.com/pass/getCode", CAPTCHA_BYTES)
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"next_step_id": "auth_saved_credentials"}
        )

    connector_cls.return_value.login_with_credentials.assert_awaited_once_with("user@example.com", "stored-password")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth_captcha"


async def test_identity_verification_in_background_shows_the_link_in_reauth(
    hass: HomeAssistant, background_failure: AsyncMock
) -> None:
    await setup_failing_entry(
        hass, TwoFactorAuthRequiredException(VERIFY_URL, {"User-Agent": "x"}, "ctx123"), background_failure
    )
    [flow] = reauth_flows(hass)

    assert flow["step_id"] == "reauth_verification"
    # Re-render the current step to read its placeholders.
    result = await hass.config_entries.flow.async_configure(flow["flow_id"])
    assert result["step_id"] == "reauth_verification"
    assert result["description_placeholders"]["verification_url"] == VERIFY_URL


async def test_two_factor_step_shows_the_link_and_can_retry_after_browser_verification(
    hass: HomeAssistant,
) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch(f"{PACKAGE}.config_flow.XiaomiCloudConnector", autospec=True) as connector_cls:
        connector = connector_cls.return_value
        connector.login_with_credentials = AsyncMock(
            side_effect=[
                TwoFactorAuthRequiredException(VERIFY_URL, {"User-Agent": "x"}, "ctx123"),
                CaptchaRequiredException("https://account.xiaomi.com/pass/getCode", CAPTCHA_BYTES),
            ]
        )
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "auth_saved_credentials"}
        )
        assert result["step_id"] == "auth_two_factor"
        assert result["description_placeholders"]["verification_url"] == VERIFY_URL

        # The user verified in the browser instead of typing a code: submitting empty retries the login.
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TWO_FACTOR_CODE: ""})

    assert connector.login_with_credentials.await_count == 2
    connector.continue_login_with_two_factor.assert_not_called()
    assert result["step_id"] == "auth_captcha"


def test_translations_cover_new_steps() -> None:
    import json
    from pathlib import Path

    translations = json.loads(
        (Path(__file__).parents[1] / "custom_components/xiaomi_cloud_map_extractor/translations/en.json").read_text()
    )
    steps = translations["config"]["step"]
    for step in ("reauth_captcha", "reauth_verification", "reauth_confirm"):
        assert step in steps
    assert "{verification_url}" in steps["reauth_verification"]["description"]
    assert "{verification_url}" in steps["auth_two_factor"]["description"]
    assert "auth_saved_credentials" in steps["auth_method_selection"]["menu_options"]
    for key in ("captcha_required", "verification_required", "invalid_credentials", "session_expired"):
        assert key in translations["exceptions"]

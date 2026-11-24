"""Config flow: cloud login, vacuum selection and entry creation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_cloud_map_extractor.config_flow import XiaomiCloudMapExtractorFlowHandler
from custom_components.xiaomi_cloud_map_extractor.connector.utils.exceptions import (
    CaptchaRequiredException,
    FailedLoginException,
    TwoFactorAuthRequiredException,
)
from custom_components.xiaomi_cloud_map_extractor.const import (
    CONF_CAPTCHA_CODE,
    CONF_COLORS,
    CONF_DRAWABLES,
    CONF_IMAGE_CONFIG,
    CONF_TWO_FACTOR_CODE,
    CONF_USED_MAP_API,
    DOMAIN,
)

from .conftest import make_device
from .const import ENTRY_DATA, HOST, MAC, PASSWORD, TOKEN, USERNAME

pytestmark = pytest.mark.usefixtures("no_store")


async def _start_credentials_login(hass: HomeAssistant) -> dict:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["auth_credentials", "auth_qr"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "auth_credentials"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth_credentials"
    return result


async def _submit_credentials(hass: HomeAssistant, result: dict) -> dict:
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": USERNAME, "password": PASSWORD}
    )


async def _confirm(hass: HomeAssistant, result: dict, used_map_api: str = "VIOMI") -> dict:
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm_data"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": HOST, "token": TOKEN, CONF_USED_MAP_API: used_map_api}
    )


async def test_credentials_login_creates_entry(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    result = await _submit_credentials(hass, await _start_credentials_login(hass))
    cloud_connector.login_with_credentials.assert_awaited_once_with(USERNAME, PASSWORD)

    result = await _confirm(hass, result)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living room vacuum"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == MAC
    options = result["options"]
    assert {CONF_IMAGE_CONFIG, CONF_COLORS, CONF_DRAWABLES} <= options.keys()
    assert "room_names" not in options[CONF_DRAWABLES]


async def test_confirm_data_suggests_cloud_values_and_detected_api(
    hass: HomeAssistant, cloud_connector: MagicMock
) -> None:
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    defaults = {str(key): key.default() for key in result["data_schema"].schema}
    assert defaults == {"host": HOST, "token": TOKEN, CONF_USED_MAP_API: "VIOMI"}


async def test_failed_login_shows_error_and_allows_retry(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.login_with_credentials.side_effect = [FailedLoginException(), "user_id"]
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cloud_login_error"}

    result = await _submit_credentials(hass, result)
    assert result["step_id"] == "confirm_data"


async def test_login_returning_none_shows_error(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.login_with_credentials.return_value = None
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cloud_login_error"}


async def test_unexpected_login_error_aborts(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.login_with_credentials.side_effect = RuntimeError("boom")
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_captcha_then_login(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.login_with_credentials.side_effect = CaptchaRequiredException("https://captcha", b"png")
    cloud_connector.continue_login_with_captcha = AsyncMock(return_value="user_id")
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth_captcha"
    assert result["description_placeholders"] == {"captcha_image_b64": "cG5n"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_CAPTCHA_CODE: "abcd"})
    cloud_connector.continue_login_with_captcha.assert_awaited_once_with("abcd")
    result = await _confirm(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_wrong_captcha_shows_new_captcha(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.login_with_credentials.side_effect = CaptchaRequiredException("https://captcha", b"one")
    cloud_connector.continue_login_with_captcha = AsyncMock(
        side_effect=CaptchaRequiredException("https://captcha", b"two")
    )
    result = await _submit_credentials(hass, await _start_credentials_login(hass))
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_CAPTCHA_CODE: "wrong"})

    assert result["step_id"] == "auth_captcha"
    assert result["errors"] == {CONF_CAPTCHA_CODE: "invalid_captcha"}
    assert result["description_placeholders"] == {"captcha_image_b64": "dHdv"}


async def test_two_factor_then_login(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    two_factor = TwoFactorAuthRequiredException("https://2fa", {}, "context")
    cloud_connector.login_with_credentials.side_effect = two_factor
    cloud_connector.continue_login_with_two_factor = AsyncMock(return_value=True)
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth_two_factor"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TWO_FACTOR_CODE: "123456"})
    cloud_connector.continue_login_with_two_factor.assert_awaited_once_with("123456", two_factor)
    result = await _confirm(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_no_vacuums_in_account_aborts(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.get_devices.return_value = [make_device(spec_type="urn:miot-spec-v2:device:light:0000A001")]
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cloud_no_devices"


async def test_several_vacuums_ask_which_one(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    second = make_device(device_id="987", name="Upstairs", mac="11:22:33:44:55:66", local_ip="192.168.1.51")
    cloud_connector.get_devices.return_value = [make_device(), second]
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_vacuum"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"select_vacuum": "de_987"})
    assert result["step_id"] == "confirm_data"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.168.1.51", "token": TOKEN, CONF_USED_MAP_API: "VIOMI"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Upstairs"
    assert result["result"].unique_id == "11:22:33:44:55:66"


async def test_same_vacuum_twice_aborts(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=MAC, data={**ENTRY_DATA, "host": "192.168.1.99"}).add_to_hass(hass)
    result = await _confirm(hass, await _submit_credentials(hass, await _start_credentials_login(hass)))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_roborock_unreachable_shows_error(
    hass: HomeAssistant, cloud_connector: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(XiaomiCloudMapExtractorFlowHandler, "_validate_vacuum", AsyncMock(return_value=False))
    result = await _submit_credentials(hass, await _start_credentials_login(hass))
    result = await _confirm(hass, result, used_map_api="ROBOROCK")

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_vacuum"}


async def test_device_list_error_aborts(hass: HomeAssistant, cloud_connector: MagicMock) -> None:
    cloud_connector.get_devices.side_effect = RuntimeError("boom")
    result = await _submit_credentials(hass, await _start_credentials_login(hass))

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"

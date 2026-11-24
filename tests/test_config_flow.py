"""Config flow tests."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
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

from custom_components.xiaomi_cloud_map_extractor import config_flow  # noqa: F401
from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.connector import (
    XiaomiCloudDeviceInfo,
)
from custom_components.xiaomi_cloud_map_extractor.const import (
    CONF_SERVER,
    CONF_USED_MAP_API,
    DOMAIN,
)

FLOW_MODULE = "custom_components.xiaomi_cloud_map_extractor.config_flow"

CLOUD_VACUUM = XiaomiCloudDeviceInfo(
    device_id="123456789",
    name="Roborock S7",
    model="roborock.vacuum.a15",
    token="0123456789abcdef0123456789abcdef",
    spec_type="urn:miot-spec-v2:device:vacuum:0000A006:roborock-a15:1",
    local_ip="192.168.1.50",
    mac="AA:BB:CC:DD:EE:FF",
    server="de",
    home_id=1,
    user_id=2,
)


@pytest.fixture
def mock_connector() -> Generator[MagicMock]:
    """Replace the Xiaomi Cloud connector used by the config flow."""
    with patch(f"{FLOW_MODULE}.XiaomiCloudConnector", autospec=True) as connector_cls:
        connector = connector_cls.return_value
        connector.login_with_credentials = AsyncMock(return_value=True)
        connector.get_devices = AsyncMock(return_value=[CLOUD_VACUUM])
        yield connector


@pytest.fixture
def mock_flow_side_effects() -> Generator[dict[str, MagicMock]]:
    """Skip local vacuum validation, storage writes and the real entry setup."""
    with (
        patch(
            f"{FLOW_MODULE}.XiaomiCloudMapExtractorFlowHandler._validate_vacuum",
            return_value=True,
        ) as validate,
        patch(f"{FLOW_MODULE}.save_connector_config") as save,
        patch(
            "custom_components.xiaomi_cloud_map_extractor.async_setup_entry",
            return_value=True,
        ) as setup_entry,
    ):
        yield {"validate": validate, "save": save, "setup_entry": setup_entry}


def _imported_entry(host: str) -> MockConfigEntry:
    """A config entry as created by the YAML import (no unique_id)."""
    return MockConfigEntry(
        domain=DOMAIN,
        source=config_entries.SOURCE_IMPORT,
        title="Xiaomi Cloud Map Extractor",
        unique_id=None,
        data={
            CONF_HOST: host,
            CONF_TOKEN: CLOUD_VACUUM.token,
            CONF_DEVICE_ID: CLOUD_VACUUM.device_id,
            CONF_MODEL: CLOUD_VACUUM.model,
            CONF_MAC: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: CLOUD_VACUUM.name,
            CONF_USERNAME: "old-user",
            CONF_PASSWORD: "old-password",
            CONF_SERVER: "de",
            CONF_USED_MAP_API: "ROBOROCK",
        },
        options={"keep": "me"},
    )


async def _login_with_credentials(hass: HomeAssistant, flow_id: str) -> dict:
    """Drive the flow from the auth method menu up to the confirm_data form."""
    result = await hass.config_entries.flow.async_configure(
        flow_id, {"next_step_id": "auth_credentials"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth_credentials"

    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_USERNAME: "user@example.com", CONF_PASSWORD: "new-password"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm_data"
    return result


async def test_reauth_imported_entry_with_different_host(
    hass: HomeAssistant,
    mock_connector: MagicMock,
    mock_flow_side_effects: dict[str, MagicMock],
) -> None:
    """Reauth must update the entry being reauthenticated, even when the host changed.

    Regression: the entry was looked up by the host typed in confirm_data, so a
    YAML-imported entry with a different stored host made the flow crash with
    AttributeError: 'NoneType' object has no attribute 'data'.
    """
    entry = _imported_entry(host="192.168.1.10")
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "auth_method_selection"

    await _login_with_credentials(hass, result["flow_id"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.50",
            CONF_TOKEN: CLOUD_VACUUM.token,
            CONF_USED_MAP_API: "ROBOROCK",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert entry.data[CONF_HOST] == "192.168.1.50"
    assert entry.data[CONF_USERNAME] == "user@example.com"
    assert entry.data[CONF_PASSWORD] == "new-password"
    assert entry.data[CONF_MAC] == "aa:bb:cc:dd:ee:ff"
    assert entry.options == {"keep": "me"}
    # The imported entry gets the vacuum's MAC as unique_id from now on.
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1

    mock_flow_side_effects["save"].assert_awaited_once()
    # The entry was reloaded with the new data.
    mock_flow_side_effects["setup_entry"].assert_called_once()


async def test_reauth_with_a_different_vacuum_aborts(
    hass: HomeAssistant,
    mock_connector: MagicMock,
    mock_flow_side_effects: dict[str, MagicMock],
) -> None:
    """Picking another vacuum during reauth must not rewrite the entry."""
    entry = _imported_entry(host="192.168.1.10")
    entry.add_to_hass(hass)
    mock_connector.get_devices.return_value = [
        replace(CLOUD_VACUUM, mac="11:22:33:44:55:66", device_id="987")
    ]

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await _login_with_credentials(hass, result["flow_id"])
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.60", CONF_TOKEN: CLOUD_VACUUM.token, CONF_USED_MAP_API: "ROBOROCK"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_wrong_vacuum"
    assert entry.data[CONF_HOST] == "192.168.1.10"
    assert entry.data[CONF_USERNAME] == "old-user"
    mock_flow_side_effects["save"].assert_not_called()


async def _run_user_flow(hass: HomeAssistant, host: str) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    await _login_with_credentials(hass, result["flow_id"])
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: host, CONF_TOKEN: CLOUD_VACUUM.token, CONF_USED_MAP_API: "ROBOROCK"},
    )
    await hass.async_block_till_done()
    return result


async def test_user_flow_creates_entry(
    hass: HomeAssistant,
    mock_connector: MagicMock,
    mock_flow_side_effects: dict[str, MagicMock],
) -> None:
    result = await _run_user_flow(hass, "192.168.1.50")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "aa:bb:cc:dd:ee:ff"
    assert result["data"][CONF_HOST] == "192.168.1.50"


async def test_user_flow_adopts_imported_entry_with_same_host(
    hass: HomeAssistant,
    mock_connector: MagicMock,
    mock_flow_side_effects: dict[str, MagicMock],
) -> None:
    """A YAML-imported entry (no unique_id) on the same host is updated, not duplicated."""
    entry = _imported_entry(host="192.168.1.50")
    entry.add_to_hass(hass)

    result = await _run_user_flow(hass, "192.168.1.50")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff"
    assert entry.data[CONF_USERNAME] == "user@example.com"


async def test_user_flow_aborts_when_vacuum_already_configured(
    hass: HomeAssistant,
    mock_connector: MagicMock,
    mock_flow_side_effects: dict[str, MagicMock],
) -> None:
    """The unique_id (MAC) decides, whatever host the existing entry has."""
    entry = _imported_entry(host="192.168.1.10")
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, unique_id="aa:bb:cc:dd:ee:ff")

    result = await _run_user_flow(hass, "192.168.1.50")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "192.168.1.10"
    mock_flow_side_effects["save"].assert_not_called()

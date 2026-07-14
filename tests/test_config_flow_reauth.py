from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import CONF_HOST, CONF_TOKEN

from custom_components.xiaomi_cloud_map_extractor import config_flow
from custom_components.xiaomi_cloud_map_extractor.config_flow import (
    XiaomiCloudMapExtractorFlowHandler,
)
from custom_components.xiaomi_cloud_map_extractor.const import CONF_USED_MAP_API
from custom_components.xiaomi_cloud_map_extractor.connector.vacuums.base.model import (
    VacuumApi,
)
from custom_components.xiaomi_cloud_map_extractor.connector.xiaomi_cloud.connector import (
    XiaomiCloudDeviceInfo,
)


def test_reauth_uses_entry_from_flow_context_when_host_changed(monkeypatch) -> None:
    async def run_test() -> None:
        old_host = "0.0.0.0"
        new_host = "192.0.2.10"
        mac = "aa:bb:cc:dd:ee:ff"
        existing_entry = SimpleNamespace(data={CONF_HOST: old_host})
        connector = SimpleNamespace(
            server=None,
            to_config=Mock(return_value={"service_token": "token"}),
        )
        flow = SimpleNamespace(
            source=SOURCE_REAUTH,
            hass=object(),
            _cloud_vacuum=XiaomiCloudDeviceInfo(
                device_id="1234567890",
                name="Test Vacuum",
                model="xiaomi.vacuum.test",
                token="1" * 32,
                spec_type="urn:miot-spec-v2:device:vacuum:0000A006:test:1",
                local_ip=new_host,
                mac=mac,
                server="ru",
                home_id=1,
                user_id=1,
            ),
            _connector=connector,
            _username=None,
            _password=None,
            _validate_vacuum=AsyncMock(return_value=True),
            _get_reauth_entry=Mock(return_value=existing_entry),
            _async_current_entries=Mock(return_value=[]),
            async_set_unique_id=AsyncMock(),
            _abort_if_unique_id_configured=Mock(),
            async_update_reload_and_abort=Mock(
                return_value={"type": "abort", "reason": "reauth_successful"}
            ),
        )
        save_connector_config = AsyncMock()
        monkeypatch.setattr(config_flow, "save_connector_config", save_connector_config)

        result = await XiaomiCloudMapExtractorFlowHandler.async_step_confirm_data(
            flow,
            {
                CONF_HOST: new_host,
                CONF_TOKEN: "2" * 32,
                CONF_USED_MAP_API: VacuumApi.XIAOMI,
            },
        )

        assert result == {"type": "abort", "reason": "reauth_successful"}
        flow._get_reauth_entry.assert_called_once_with()
        flow._async_current_entries.assert_not_called()
        flow.async_update_reload_and_abort.assert_called_once()
        (entry,) = flow.async_update_reload_and_abort.call_args.args
        assert entry is existing_entry
        assert (
            flow.async_update_reload_and_abort.call_args.kwargs["unique_id"] == mac
        )
        assert (
            flow.async_update_reload_and_abort.call_args.kwargs["data"][CONF_HOST]
            == new_host
        )
        save_connector_config.assert_awaited_once()

    asyncio.run(run_test())

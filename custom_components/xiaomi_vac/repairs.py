"""Repairs flow: nudge cloud entries to link MIoT OAuth for the live map."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir

from .cloud.oauth import (
    XiaomiOAuthError,
    build_authorize_url,
    exchange_code,
    generate_oauth_device_id,
    oauth_entry_updates,
    resolve_region_from_code,
)
from .const import CONF_OAUTH_DEVICE_ID, CONF_SERVER, DOMAIN

OAUTH_CODE_SCHEMA = vol.Schema({vol.Required("code"): cv.string})


def oauth_missing_issue_id(entry_id: str) -> str:
    return f"oauth_missing_{entry_id}"


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    return MiotOAuthRepairFlow(str((data or {}).get("entry_id", "")))


class MiotOAuthRepairFlow(RepairsFlow):
    """Paste-the-code flow launched from the Repairs 'Fix' button."""

    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._device_id: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self.async_step_link()

    async def async_step_link(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_gone")

        data = dict(entry.data)
        # Generate once and reuse across form-show and submit: the auth code is
        # bound to the device_id shown in the authorize URL.
        if self._device_id is None:
            self._device_id = str(
                data.get(CONF_OAUTH_DEVICE_ID) or generate_oauth_device_id()
            )
        device_id = self._device_id

        if user_input is not None:
            code = user_input["code"].strip()
            region = resolve_region_from_code(code, data.get(CONF_SERVER))
            if region is None:
                errors["base"] = "oauth_region_failed"
            else:
                try:
                    tokens = await self.hass.async_add_executor_job(
                        exchange_code, code, device_id, region
                    )
                except XiaomiOAuthError:
                    errors["base"] = "oauth_failed"
                else:
                    data.update(oauth_entry_updates(tokens, device_id))
                    self.hass.config_entries.async_update_entry(entry, data=data)
                    ir.async_delete_issue(
                        self.hass, DOMAIN, oauth_missing_issue_id(self._entry_id)
                    )
                    await self.hass.config_entries.async_reload(self._entry_id)
                    return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="link",
            data_schema=OAUTH_CODE_SCHEMA,
            errors=errors,
            description_placeholders={"authorize_url": build_authorize_url(device_id)},
        )

"""Config flow for Xiaomi Vacuum.

See docs/dev/module-notes.md for design rationale.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers import config_validation as cv

from .captcha_view import IMG_URL, ensure_registered, set_image
from .cloud.connector import XiaomiCloud
from .cloud.oauth import (
    OAUTH_REDIRECT_URI,
    XiaomiOAuthError,
    build_authorize_url,
    exchange_code,
    generate_oauth_device_id,
    oauth_entry_updates,
    resolve_region_from_code,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_OAUTH_DEVICE_ID,
    CONF_PASS_TOKEN,
    CONF_PASSWORD,
    CONF_SERVER,
    CONF_SERVICE_TOKEN,
    CONF_SSECURITY,
    CONF_TOKEN,
    CONF_USER_ID,
    CONF_USERNAME,
    CONF_WIFI_SN,
    DOMAIN,
)
from .device import IjaiVacuumDevice
from .oauth_flow import OAuthCodeLink
from .spec.registry import is_supported

_LOGGER = logging.getLogger(__name__)

CRED_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)
CODE_SCHEMA = vol.Schema({vol.Required("code"): cv.string})
LOCAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    }
)
OAUTH_CHOICE_SCHEMA = vol.Schema(
    {vol.Required("enable_miot_oauth", default=True): cv.boolean}
)
OAUTH_CODE_SCHEMA = vol.Schema({vol.Required("code"): cv.string})


def _probe(host: str, token: str) -> dict[str, str]:
    from miio import Device

    info = Device(host, token).info()
    return {"model": info.model, "mac": info.mac_address or ""}


async def _async_exchange_linked_oauth(
    hass,
    link: OAuthCodeLink,
    data: Mapping[str, Any],
    device_id: str,
) -> dict[str, Any]:
    result = await link.async_wait_code()
    region = resolve_region_from_code(result.code, data.get(CONF_SERVER))
    if region is None:
        raise XiaomiOAuthError("Could not resolve OAuth region")
    tokens = await hass.async_add_executor_job(
        partial(
            exchange_code,
            result.code,
            device_id,
            region,
            redirect_uri=result.redirect_uri,
        )
    )
    return oauth_entry_updates(tokens, device_id, result.redirect_uri)


async def _async_exchange_manual_oauth(
    hass,
    code: str,
    data: Mapping[str, Any],
    device_id: str,
) -> dict[str, Any]:
    region = resolve_region_from_code(code, data.get(CONF_SERVER))
    if region is None:
        raise XiaomiOAuthError("Could not resolve OAuth region")
    tokens = await hass.async_add_executor_job(
        partial(
            exchange_code,
            code,
            device_id,
            region,
            redirect_uri=OAUTH_REDIRECT_URI,
        )
    )
    return oauth_entry_updates(tokens, device_id, OAUTH_REDIRECT_URI)


class XiaomiVacuumConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 2

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return XiaomiVacuumOptionsFlow()

    def __init__(self) -> None:
        self._cloud: XiaomiCloud | None = None
        self._devices: list[dict] = []
        self._selected: dict | None = None
        self._cap_n = 0
        self._data: dict[str, Any] = {}
        self._title = ""
        self._oauth_link: OAuthCodeLink | None = None
        self._oauth_task: asyncio.Task[dict[str, Any]] | None = None
        self._oauth_error: str | None = None

    # --- entry: pick login method ---------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=["credentials", "local"]
        )


    # --- local IP + token (control only, no cloud map) ------------------
    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host, token = user_input[CONF_HOST], user_input[CONF_TOKEN]
            try:
                info = await self.hass.async_add_executor_job(_probe, host, token)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                if not is_supported(info["model"]):
                    errors["base"] = "unsupported_model"
                else:
                    await self.async_set_unique_id(
                        info["mac"] or f'{info["model"]}-{host}'
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=info["model"],
                        data={
                            CONF_HOST: host,
                            CONF_TOKEN: token,
                            CONF_MODEL: info["model"],
                            CONF_MAC: info["mac"],
                        },
                    )
        return self.async_show_form(
            step_id="local", data_schema=LOCAL_SCHEMA, errors=errors
        )

    # --- reauth: cloud session died and passToken renewal failed --------
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Triggered when the integration raises ConfigEntryAuthFailed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-enter credentials, log in again, swap the tokens in place."""
        if user_input is not None:
            self._cloud = XiaomiCloud(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            self._data[CONF_USERNAME] = user_input[CONF_USERNAME]
            # Password is used only to mint fresh tokens below; never persisted.
            state = await self.hass.async_add_executor_job(self._cloud.begin_login)
            return await self._branch(state)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                CRED_SCHEMA,
                {CONF_USERNAME: self._get_reauth_entry().data.get(CONF_USERNAME, "")},
            ),
        )

    def _finish_reauth(self) -> ConfigFlowResult:
        """Write the fresh session onto the existing entry and reload it.

        We don't re-discover the device here (the entry already knows it); if
        the user logs into the wrong account the new tokens simply won't work
        for this device and reauth fires again.
        """
        cloud = self._cloud
        return self.async_update_reload_and_abort(
            self._get_reauth_entry(),
            data_updates={
                CONF_USERNAME: self._data[CONF_USERNAME],
                CONF_USER_ID: str(cloud.user_id),
                CONF_SSECURITY: cloud.ssecurity,
                CONF_SERVICE_TOKEN: cloud.service_token,
                CONF_PASS_TOKEN: cloud.pass_token or "",
            },
        )

    # --- email + password -----------------------------------------------
    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="credentials", data_schema=CRED_SCHEMA)
        self._cloud = XiaomiCloud(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
        self._data[CONF_USERNAME] = user_input[CONF_USERNAME]
        # Password is consumed by begin_login to mint tokens; never persisted.
        state = await self.hass.async_add_executor_job(self._cloud.begin_login)
        return await self._branch(state)

    async def async_step_captcha(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            state = await self.hass.async_add_executor_job(
                self._cloud.submit_captcha, user_input["code"]
            )
            return await self._branch(state)
        ensure_registered(self.hass)
        set_image(self.hass, "captcha", self._cloud.captcha_image)
        self._cap_n += 1
        return self.async_show_form(
            step_id="captcha",
            data_schema=CODE_SCHEMA,
            description_placeholders={"captcha_url": f"{IMG_URL}?n=captcha&t={self._cap_n}"},
        )

    async def async_step_twofa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            state = await self.hass.async_add_executor_job(
                self._cloud.submit_2fa, user_input["code"]
            )
            return await self._branch(state)
        return self.async_show_form(step_id="twofa", data_schema=CODE_SCHEMA)

    async def _branch(self, state: str) -> ConfigFlowResult:
        if state == "captcha":
            return await self.async_step_captcha()
        if state == "2fa":
            return await self.async_step_twofa()
        if state == "ok":
            if self.source == SOURCE_REAUTH:
                return self._finish_reauth()
            return await self.async_step_devices()
        # 登录验证失败 = Xiaomi blocked the sign-in pending account verification,
        # not bad credentials. Point the user at Xiaomi's own sign-in first.
        reason_text = getattr(self._cloud, "login_error", "")
        if not isinstance(reason_text, str):
            reason_text = ""
        if "登录验证失败" in reason_text:
            return self.async_abort(reason="login_verification_required")
        return self.async_abort(
            reason="login_failed",
            description_placeholders={"reason": reason_text or "unknown"},
        )

    # --- device discovery + pick ----------------------------------------
    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not self._devices:
            all_vacuums = await self.hass.async_add_executor_job(
                self._cloud.list_vacuums
            )
            self._devices = [d for d in all_vacuums if is_supported(d["model"])]
            if not self._devices:
                reason = "no_devices" if not all_vacuums else "unsupported_model"
                return self.async_abort(reason=reason)
        if len(self._devices) == 1:
            self._selected = self._devices[0]
            return await self._finalize()
        if user_input is not None:
            self._selected = next(
                d for d in self._devices if d["did"] == user_input["device"]
            )
            return await self._finalize()
        options = {d["did"]: f'{d["name"]} ({d["model"]})' for d in self._devices}
        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema({vol.Required("device"): vol.In(options)}),
        )

    async def _finalize(self) -> ConfigFlowResult:
        d = self._selected
        cloud = self._cloud
        if not is_supported(d["model"]):
            return self.async_abort(reason="unsupported_model")

        wifi_sn = await self.hass.async_add_executor_job(
            self._get_wifi_sn, d["localip"], d["token"], d["model"], cloud.user_id
        )
        await self.async_set_unique_id(d["mac"] or f'{d["model"]}-{d["did"]}')
        self._abort_if_unique_id_configured()

        self._data.update(
            {
                CONF_HOST: d["localip"],
                CONF_TOKEN: d["token"],
                CONF_MODEL: d["model"],
                CONF_MAC: d["mac"],
                CONF_SERVER: d["server"],
                CONF_USER_ID: str(cloud.user_id),
                CONF_DEVICE_ID: str(d["did"]),
                CONF_SSECURITY: cloud.ssecurity,
                CONF_SERVICE_TOKEN: cloud.service_token,
                CONF_PASS_TOKEN: cloud.pass_token or "",
                CONF_WIFI_SN: wifi_sn or "",
            }
        )
        self._title = d["name"] or d["model"]
        return await self.async_step_miot_oauth()

    async def async_step_miot_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer optional MIoT OAuth for future MQTT live-map support."""
        if user_input is not None:
            if user_input["enable_miot_oauth"]:
                return await self.async_step_miot_oauth_auth()
            return self._create_entry()
        return self.async_show_form(
            step_id="miot_oauth", data_schema=OAUTH_CHOICE_SCHEMA
        )

    async def async_step_miot_oauth_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Link Xiaomi OAuth through a HA webhook callback."""
        device_id = str(
            self._data.setdefault(CONF_OAUTH_DEVICE_ID, generate_oauth_device_id())
        )
        if self._oauth_task is None:
            self._oauth_link = OAuthCodeLink(self.hass, device_id)
            self._oauth_link.register()
            self._oauth_task = self.hass.async_create_task(
                _async_exchange_linked_oauth(
                    self.hass, self._oauth_link, self._data, device_id
                )
            )

        if self._oauth_task.done():
            try:
                self._data.update(self._oauth_task.result())
            except XiaomiOAuthError as err:
                if "region" in str(err):
                    self._oauth_error = "oauth_region_failed"
                else:
                    _LOGGER.exception("Xiaomi OAuth exchange failed")
                    self._oauth_error = "oauth_failed"
                self._oauth_task = None
                self._oauth_link = None
                return self.async_show_progress_done(
                    next_step_id="miot_oauth_code"
                )
            self._oauth_task = None
            self._oauth_link = None
            return self.async_show_progress_done(next_step_id="miot_oauth_finish")

        return self.async_show_progress(
            step_id="miot_oauth_auth",
            progress_action="miot_oauth_auth",
            progress_task=self._oauth_task,
            description_placeholders={
                "authorize_url": self._oauth_link.authorize_url
            },
        )

    async def async_step_miot_oauth_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Finish entry creation after automatic OAuth completes."""
        return self._create_entry()

    async def async_step_miot_oauth_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fallback paste-code flow for browsers that cannot reach HA."""
        errors: dict[str, str] = {}
        if self._oauth_error:
            errors["base"] = self._oauth_error
            self._oauth_error = None
        device_id = str(
            self._data.setdefault(CONF_OAUTH_DEVICE_ID, generate_oauth_device_id())
        )
        if user_input is not None:
            code = user_input["code"].strip()
            try:
                self._data.update(
                    await _async_exchange_manual_oauth(
                        self.hass, code, self._data, device_id
                    )
                )
            except XiaomiOAuthError as err:
                if "region" in str(err):
                    errors["base"] = "oauth_region_failed"
                else:
                    _LOGGER.exception("Xiaomi OAuth exchange failed")
                    errors["base"] = "oauth_failed"
            else:
                return self._create_entry()
            if errors.get("base") is None:
                errors["base"] = "oauth_region_failed"
        return self.async_show_form(
            step_id="miot_oauth_code",
            data_schema=OAUTH_CODE_SCHEMA,
            errors=errors,
            description_placeholders={
                "authorize_url": build_authorize_url(str(device_id))
            },
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry after optional OAuth handling."""
        return self.async_create_entry(title=self._title, data=self._data)

    @staticmethod
    def _get_wifi_sn(host, token, model, user_id) -> str | None:
        try:
            return IjaiVacuumDevice(host, token, model).get_wifi_sn(user_id)
        except Exception:  # noqa: BLE001
            return None


class XiaomiVacuumOptionsFlow(OptionsFlow):
    """Add/refresh MIoT OAuth (MQTT live-map) on an existing entry.

    Lets users who upgraded to the MQTT version enable OAuth without deleting
    and re-adding the integration.
    """

    def __init__(self) -> None:
        self._oauth_device_id: str | None = None
        self._oauth_link: OAuthCodeLink | None = None
        self._oauth_task: asyncio.Task[dict[str, Any]] | None = None
        self._oauth_error: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        # OAuth needs a cloud session (server/user); local-only entries can't.
        if not self.config_entry.data.get(CONF_SERVER):
            return self.async_abort(reason="oauth_local_only")
        return await self.async_step_miot_oauth_auth()

    async def async_step_miot_oauth_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        data = dict(self.config_entry.data)
        if self._oauth_device_id is None:
            self._oauth_device_id = str(
                data.get(CONF_OAUTH_DEVICE_ID) or generate_oauth_device_id()
            )
        device_id = self._oauth_device_id

        if self._oauth_task is None:
            self._oauth_link = OAuthCodeLink(self.hass, device_id)
            self._oauth_link.register()
            self._oauth_task = self.hass.async_create_task(
                _async_exchange_linked_oauth(
                    self.hass, self._oauth_link, data, device_id
                )
            )

        if self._oauth_task.done():
            try:
                updates = self._oauth_task.result()
            except XiaomiOAuthError as err:
                if "region" in str(err):
                    self._oauth_error = "oauth_region_failed"
                else:
                    _LOGGER.exception("Xiaomi OAuth exchange failed")
                    self._oauth_error = "oauth_failed"
                self._oauth_task = None
                self._oauth_link = None
                return self.async_show_progress_done(
                    next_step_id="miot_oauth_code"
                )
            data.update(updates)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=data
            )
            await self.hass.config_entries.async_reload(
                self.config_entry.entry_id
            )
            self._oauth_task = None
            self._oauth_link = None
            return self.async_show_progress_done(next_step_id="miot_oauth_finish")

        return self.async_show_progress(
            step_id="miot_oauth_auth",
            progress_action="miot_oauth_auth",
            progress_task=self._oauth_task,
            description_placeholders={
                "authorize_url": self._oauth_link.authorize_url
            },
        )

    async def async_step_miot_oauth_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_create_entry(title="", data={})

    async def async_step_miot_oauth_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if self._oauth_error:
            errors["base"] = self._oauth_error
            self._oauth_error = None
        data = dict(self.config_entry.data)
        if self._oauth_device_id is None:
            self._oauth_device_id = str(
                data.get(CONF_OAUTH_DEVICE_ID) or generate_oauth_device_id()
            )
        device_id = self._oauth_device_id
        if user_input is not None:
            code = user_input["code"].strip()
            try:
                data.update(
                    await _async_exchange_manual_oauth(
                        self.hass, code, data, device_id
                    )
                )
            except XiaomiOAuthError as err:
                if "region" in str(err):
                    errors["base"] = "oauth_region_failed"
                else:
                    _LOGGER.exception("Xiaomi OAuth exchange failed")
                    errors["base"] = "oauth_failed"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=data
                )
                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )
                return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="miot_oauth_code",
            data_schema=OAUTH_CODE_SCHEMA,
            errors=errors,
            description_placeholders={
                "authorize_url": build_authorize_url(device_id)
            },
        )

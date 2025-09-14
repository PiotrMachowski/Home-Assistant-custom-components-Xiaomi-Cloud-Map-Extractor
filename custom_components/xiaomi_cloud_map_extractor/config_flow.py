from __future__ import annotations

import logging
import base64
import uuid
import time
from typing import Any, Self, Mapping

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (CONF_HOST, CONF_TOKEN, CONF_MAC, CONF_USERNAME, CONF_PASSWORD, CONF_MODEL,
                                 CONF_DEVICE_ID, CONF_NAME)
from homeassistant.core import callback
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from miio import RoborockVacuum
from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes

from .connector.utils.exceptions import XiaomiCloudMapExtractorException, TwoFactorAuthRequiredException, InvalidCredentialsException, FailedLoginException, CaptchaRequiredException
from .connector.vacuums.base.model import VacuumApi
from .connector.xiaomi_cloud.connector import XiaomiCloudConnector, XiaomiCloudDeviceInfo
from .connector.xiaomi_cloud.const import AVAILABLE_SERVERS
from .const import (
    DOMAIN,
    CONF_USED_MAP_API,
    CONF_SERVER,
    CONF_COLORS,
    CONF_IMAGE_CONFIG,
    CONF_ROOM_COLORS,
    CONF_DRAWABLES,
    CONF_SIZES,
    CONF_TEXTS,
    CONF_IMAGE_CONFIG_SCALE,
    CONF_IMAGE_CONFIG_ROTATE,
    CONF_IMAGE_CONFIG_TRIM_LEFT,
    CONF_IMAGE_CONFIG_TRIM_BOTTOM,
    CONF_IMAGE_CONFIG_TRIM_TOP,
    CONF_IMAGE_CONFIG_TRIM_RIGHT,
    CONF_MI_SSECURITY,
    CONF_MI_SERVICE_TOKEN,
    CONF_MI_USER_ID,
    CONF_MI_CUSER_ID,
)
from .options_flow import XiaomiCloudMapExtractorOptionsFlowHandler
from .types import XiaomiCloudMapExtractorConfigEntry

_LOGGER = logging.getLogger(__name__)

CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_SERVER, default='de'): vol.In(
            AVAILABLE_SERVERS
        )
    }
)

TWO_FACTOR_SCHEMA = vol.Schema(
    {
        vol.Required("verification_code"): str,
    }
)

CAPTCHA_SCHEMA = vol.Schema(
    {
        vol.Required("captcha_code"): str,
    }
)


# noinspection PyTypeChecker,PyBroadException
class XiaomiCloudMapExtractorFlowHandler(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self.username = None
        self.password = None
        self.server = None
        self.cloud_vacuums: list[XiaomiCloudDeviceInfo] = []
        self.cloud_vacuum: XiaomiCloudDeviceInfo | None = None
        self.two_factor_url = None
        self.session_data = None
        # Avoid clashing with ConfigFlow.context (dict). Store Xiaomi context separately.
        self.mi_context = None
        self.connector = None
        # Captcha-related state
        self._captcha_sign = None
        self._captcha_url = None
        self._captcha_token = None

    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: XiaomiCloudMapExtractorConfigEntry) -> XiaomiCloudMapExtractorOptionsFlowHandler:
        """Get the options flow."""
        return XiaomiCloudMapExtractorOptionsFlowHandler()

    async def async_step_reauth(
            self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an authentication error or missing cloud credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is not None:
            return await self.async_step_cloud()
        return self.async_show_form(step_id="reauth_confirm")

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return await self.async_step_cloud()

    async def async_step_cloud(
            self: Self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        _LOGGER.error("STEP_CLOUD_CALLED: Method started with user_input=%s", user_input is not None)
        errors = {}
        if user_input is not None:
            _LOGGER.error("STEP_CLOUD_PROCESSING: Processing user input")

            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            server = user_input.get(CONF_SERVER)
            session_creator = lambda: async_create_clientsession(self.hass)

            connector = XiaomiCloudConnector(session_creator, username, password, server)
            two_factor_url = None
            try:
                _LOGGER.error("DEBUG: Config flow starting login attempt - THIS IS A TEST MESSAGE")
                _LOGGER.debug("About to call connector.login()")
                login_result = await connector.login()
                _LOGGER.debug("Login completed with result: %s", login_result)
                if login_result is None:
                    _LOGGER.error("Login returned None - authentication failed")
                    errors["base"] = "TESTING_LOGIN_RETURNED_NULL"
            except CaptchaRequiredException as e:
                _LOGGER.error("CaptchaRequiredException caught - redirecting to CAPTCHA input step")
                # Preserve auth inputs and connector to reuse the same session
                self.username = username
                self.password = password
                self.server = server
                self.connector = connector
                # Store sign needed to retry step 2
                self._captcha_sign = e.sign
                # Build absolute captcha URL for display
                self._captcha_url = e.captcha_url
                # Fetch the exact CAPTCHA image bytes using the same session and expose via a local HTTP view
                try:
                    r = await self.connector._session_data.get(self._captcha_url)
                    if r.status == 200:
                        img_bytes = await r.read()
                        content_type = r.headers.get("Content-Type", "image/jpeg")
                        store = self.hass.data.setdefault(DOMAIN, {}).setdefault("captcha_store", {})
                        # Cleanup old entries (older than 5 minutes)
                        now = time.time()
                        for k in list(store.keys()):
                            if now - store[k].get("ts", 0) > 300:
                                store.pop(k, None)
                        token = uuid.uuid4().hex
                        store[token] = {"bytes": img_bytes, "content_type": content_type, "ts": now}
                        self._captcha_token = token
                        # Ensure view is registered once
                        if not self.hass.data.setdefault(DOMAIN, {}).get("captcha_view_registered"):
                            class XiaomiCloudCaptchaView(HomeAssistantView):
                                url = "/api/xiaomi_cloud_map_extractor/captcha"
                                name = "xiaomi_cloud_map_extractor:captcha"
                                requires_auth = True

                                def __init__(self, hass):
                                    self.hass = hass

                                async def get(self, request):
                                    token = request.query.get("token")
                                    store = self.hass.data.get(DOMAIN, {}).get("captcha_store", {})
                                    entry = store.get(token)
                                    if not entry:
                                        from aiohttp import web
                                        return web.Response(status=404, text="Not Found")
                                    from aiohttp import web
                                    return web.Response(body=entry["bytes"], content_type=entry["content_type"])

                            self.hass.http.register_view(XiaomiCloudCaptchaView(self.hass))
                            self.hass.data[DOMAIN]["captcha_view_registered"] = True
                except Exception:
                    pass
                return self.async_show_form(
                    step_id="captcha",
                    data_schema=CAPTCHA_SCHEMA,
                    errors={},
                    description_placeholders={
                        "captcha_url": "/api/xiaomi_cloud_map_extractor/captcha?token=" + (self._captcha_token or ""),
                    },
                )
            except TwoFactorAuthRequiredException as e:
                _LOGGER.error("TwoFactorAuthRequiredException caught - redirecting to 2FA input step")
                _LOGGER.error("Exception details: url=%s, session_data=%s, context=%s", e.url, e.session_data, e.context)
                # Store data for 2FA step
                self.username = username
                self.password = password  
                self.server = server
                self.connector = connector
                self.two_factor_url = e.url
                self.session_data = e.session_data
                self.mi_context = e.context
                _LOGGER.error("2FA_REDIRECT: Stored session data, showing simple 2FA form")
                try:
                    form_result = self.async_show_form(
                        step_id="two_factor",
                        data_schema=vol.Schema({vol.Required("verification_code"): str}),
                        errors={},
                        description_placeholders={"two_factor_url": self.two_factor_url}
                    )
                    _LOGGER.error("2FA_REDIRECT: 2FA form created successfully")
                    return form_result
                except Exception as form_error:
                    _LOGGER.error("2FA_REDIRECT: Error creating 2FA form: %s", form_error, exc_info=True)
                    # Fall back to error message
                    errors["base"] = "two_factor_auth_required"
                    two_factor_url = e.url
            except InvalidCredentialsException as e:
                _LOGGER.error("InvalidCredentialsException during login: %s", str(e))
                errors["base"] = "TESTING_INVALID_CREDENTIALS"
            except FailedLoginException as e:
                _LOGGER.error("FailedLoginException during login: %s", str(e))
                errors["base"] = "TESTING_FAILED_LOGIN"
            except XiaomiCloudMapExtractorException as e:
                _LOGGER.error("Other XiaomiCloudMapExtractorException during login: %s (type: %s)", str(e), type(e).__name__)
                errors["base"] = f"TESTING_XIAOMI_EXCEPTION_{type(e).__name__}"
            except Exception as e:
                _LOGGER.error("Unexpected exception type: %s", type(e).__name__)
                _LOGGER.error("Unexpected exception message: %s", str(e))
                _LOGGER.error("Exception details:", exc_info=True)
                # Show the actual error in the UI for debugging
                errors["base"] = f"DEBUGGING_ERROR_{type(e).__name__}_{str(e)[:50]}"

            if errors:
                _LOGGER.error("FINAL_ERROR_CHECK: Found errors, showing cloud form with errors: %s", errors)
                _LOGGER.error("FINAL_ERROR_CHECK: two_factor_url value: %s", two_factor_url)
                placeholders = {}
                if two_factor_url:
                    placeholders["two_factor_url"] = two_factor_url
                return self.async_show_form(
                    step_id="cloud", data_schema=CLOUD_SCHEMA, errors=errors,
                    description_placeholders=placeholders
                )

            try:
                devices_raw = await connector.get_devices(server)
            except Exception as e:
                _LOGGER.error("Unexpected exception while attempting to Miio cloud get devices: %s", str(e))
                _LOGGER.error(e, exc_info=True)
                errors["base"] = f"DEVICE_DISCOVERY_ERROR_{type(e).__name__}"
                return self.async_show_form(
                    step_id="cloud", data_schema=CLOUD_SCHEMA, errors=errors
                )

            if not devices_raw:
                errors[CONF_SERVER] = "cloud_no_devices"
                return self.async_show_form(
                    step_id="cloud", data_schema=CLOUD_SCHEMA, errors=errors
                )

            self.username = username
            self.password = password
            self.server = server
            self.cloud_vacuums = [device for device in devices_raw if "vacuum" in device.spec_type]

            if len(self.cloud_vacuums) == 1:
                self.cloud_vacuum = self.cloud_vacuums[0]
                return await self.async_step_confirm_data()

            return await self.async_step_select_vacuum()

        return self.async_show_form(
            step_id="cloud", data_schema=CLOUD_SCHEMA, errors=errors
        )

    async def async_step_two_factor(
        self: Self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle 2FA verification step."""
        _LOGGER.error("2FA_STEP: async_step_two_factor called")
        errors = {}
        
        if user_input is not None:
            _LOGGER.error("2FA_STEP: Processing verification code")
            verification_code = user_input.get("verification_code")
            
            if verification_code:
                try:
                    # Continue the 2FA flow with the provided code
                    _LOGGER.error("2FA_STEP: Calling continue_2fa_email_flow with code")
                    success = await self.connector.continue_2fa_email_flow(
                        verification_code, self.session_data, self.mi_context
                    )
                    
                    if success:
                        _LOGGER.error("2FA_STEP: 2FA completed successfully, proceeding to device discovery")
                        # Persist Xiaomi session artifacts to the entry once we finish device selection
                        return await self._complete_login()
                    else:
                        _LOGGER.error("2FA_STEP: Invalid verification code")
                        errors["base"] = "two_factor_invalid_code"
                        
                except Exception as e:
                    _LOGGER.error("2FA_STEP: Error during verification: %s", e, exc_info=True)
                    errors["base"] = "two_factor_error"
            else:
                errors["base"] = "two_factor_invalid_code"
        
        _LOGGER.error("2FA_STEP: Showing 2FA form with URL: %s", self.two_factor_url)
        return self.async_show_form(
            step_id="two_factor",
            data_schema=TWO_FACTOR_SCHEMA,
            errors=errors,
            description_placeholders={"two_factor_url": self.two_factor_url}
        )

    async def async_step_captcha(
        self: Self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle CAPTCHA step when Xiaomi requests captchaUrl in login step 2."""
        errors: dict[str, str] = {}
        if user_input is not None:
            captcha_code = user_input.get("captcha_code")
            if captcha_code:
                try:
                    # Retry step 2 with captcha and continue the normal flow
                    location = await self.connector.continue_login_with_captcha(self._captcha_sign or "", captcha_code)
                    if location:
                        await self.connector._login_step_3(location)
                        return await self._complete_login()
                except TwoFactorAuthRequiredException as e:
                    # Switch into 2FA step
                    self.two_factor_url = e.url
                    self.session_data = e.session_data
                    self.mi_context = e.context
                    return self.async_show_form(
                        step_id="two_factor",
                        data_schema=TWO_FACTOR_SCHEMA,
                        errors={},
                        description_placeholders={"two_factor_url": self.two_factor_url}
                    )
                except InvalidCredentialsException:
                    errors["base"] = "captcha_invalid"
                except Exception as e:
                    _LOGGER.error("CAPTCHA_STEP: Unexpected error: %s", e, exc_info=True)
                    errors["base"] = "captcha_error"
            else:
                errors["base"] = "captcha_invalid"

        # Prefetch captcha image to establish required cookies in our session,
        # and embed the image as a data URL so it matches our session challenge.
        captcha_image_data_url = ""
        try:
            if getattr(self, "_captcha_url", None) and getattr(self, "connector", None) and getattr(self.connector, "_session_data", None):
                r = await self.connector._session_data.get(self._captcha_url)
                if r.status == 200:
                    img_bytes = await r.read()
                    captcha_image_data_url = "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("ascii")
        except Exception:
            pass

        return self.async_show_form(
            step_id="captcha",
            data_schema=CAPTCHA_SCHEMA,
            errors=errors,
            description_placeholders={
                "captcha_url": getattr(self, "_captcha_url", ""),
                "captcha_image": captcha_image_data_url,
            },
        )

    
    async def _complete_login(self) -> ConfigFlowResult:
        """Complete login after 2FA and discover devices."""
        try:
            cloud_vacuums = await self.connector.get_devices(self.server)
            if len(cloud_vacuums) == 0:
                return self.async_abort(reason="cloud_no_devices")
            
            self.cloud_vacuums = cloud_vacuums
            
            if len(cloud_vacuums) == 1:
                self.cloud_vacuum = cloud_vacuums[0]
                return await self.async_step_confirm_data()
            else:
                return await self.async_step_select_vacuum()
                
        except Exception as e:
            _LOGGER.error("Error during device discovery: %s", e, exc_info=True)
            return self.async_abort(reason="cloud_login_error")

    async def async_step_select_vacuum(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle multiple cloud devices found."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.cloud_vacuum = next(filter(lambda v: v.device_id == user_input["select_vacuum"], self.cloud_vacuums))
            return await self.async_step_confirm_data()

        options: list[SelectOptionDict] = [
            SelectOptionDict(value=cloud_vacuum.device_id,
                             label=f"{cloud_vacuum.name} - {cloud_vacuum.model} ({cloud_vacuum.mac})")
            for cloud_vacuum in self.cloud_vacuums
        ]

        select_schema = vol.Schema(
            {vol.Required("select_vacuum"): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    custom_value=False,
                    sort=True,
                    mode=SelectSelectorMode.LIST,
                ))}
        )

        return self.async_show_form(
            step_id="select_vacuum", data_schema=select_schema, errors=errors
        )

    async def async_step_confirm_data(
            self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input.get(CONF_HOST)
            token = user_input.get(CONF_TOKEN)
            used_map_api = user_input.get(CONF_USED_MAP_API)

            if not await self._validate_vacuum(host, token, VacuumApi(used_map_api)):
                errors["base"] = "invalid_vacuum"
            else:
                unique_id = format_mac(self.cloud_vacuum.mac)
                existing_entry = await self.async_set_unique_id(
                    unique_id, raise_on_progress=False
                )
                if existing_entry:
                    data = existing_entry.data.copy()
                    data[CONF_HOST] = host
                    data[CONF_TOKEN] = token
                    data[CONF_DEVICE_ID] = self.cloud_vacuum.device_id,
                    data[CONF_MODEL] = self.cloud_vacuum.model
                    data[CONF_MAC] = format_mac(self.cloud_vacuum.mac)
                    data[CONF_NAME] = self.cloud_vacuum.name
                    data[CONF_USERNAME] = self.username
                    data[CONF_PASSWORD] = self.password
                    data[CONF_SERVER] = self.server
                    data[CONF_USED_MAP_API] = used_map_api
                    # Persist Xiaomi session artifacts gathered during 2FA
                    try:
                        artifacts = self.connector.get_session_artifacts()
                        if artifacts:
                            data[CONF_MI_SSECURITY] = artifacts.get("ssecurity")
                            data[CONF_MI_SERVICE_TOKEN] = artifacts.get("serviceToken")
                            data[CONF_MI_USER_ID] = artifacts.get("userId")
                            data[CONF_MI_CUSER_ID] = artifacts.get("cUserId")
                    except Exception:
                        pass
                    return self.async_update_reload_and_abort(existing_entry, data=data)
                else:
                    return self.async_create_entry(
                        title=self.cloud_vacuum.name,
                        data={
                            CONF_HOST: host,
                            CONF_TOKEN: token,
                            CONF_DEVICE_ID: self.cloud_vacuum.device_id,
                            CONF_MODEL: self.cloud_vacuum.model,
                            CONF_MAC: format_mac(self.cloud_vacuum.mac),
                            CONF_NAME: self.cloud_vacuum.name,
                            CONF_USERNAME: self.username,
                            CONF_PASSWORD: self.password,
                            CONF_SERVER: self.server,
                            CONF_USED_MAP_API: used_map_api,
                            # Persist Xiaomi session artifacts gathered during 2FA
                            CONF_MI_SSECURITY: self.connector.get_session_artifacts() and self.connector.get_session_artifacts().get("ssecurity"),
                            CONF_MI_SERVICE_TOKEN: self.connector.get_session_artifacts() and self.connector.get_session_artifacts().get("serviceToken"),
                            CONF_MI_USER_ID: self.connector.get_session_artifacts() and self.connector.get_session_artifacts().get("userId"),
                            CONF_MI_CUSER_ID: self.connector.get_session_artifacts() and self.connector.get_session_artifacts().get("cUserId"),
                        },
                        options={
                            CONF_IMAGE_CONFIG: self._default_image_config(),
                            CONF_COLORS: self._default_colors(),
                            CONF_ROOM_COLORS: {},
                            CONF_DRAWABLES: [
                                e.value for e in Drawable if
                                e != Drawable.ROOM_NAMES and "ignored" not in e
                            ],
                            CONF_SIZES: {k.value: v for k, v in Sizes.SIZES.items()},
                            CONF_TEXTS: [],
                        }
                    )

        detected_api = VacuumApi.detect(self.cloud_vacuum.model)
        api_options: list[SelectOptionDict] = [
            SelectOptionDict(value=v, label=v.title() + (" *" if v == detected_api else "")) for v in VacuumApi
        ]
        confirm_data_schema = vol.Schema({
            vol.Required(CONF_HOST, default=self.cloud_vacuum.local_ip): str,
            vol.Required(CONF_TOKEN, default=self.cloud_vacuum.token): vol.All(str, vol.Length(min=32, max=32)),
            vol.Required(CONF_USED_MAP_API, default=detected_api): SelectSelector(
                SelectSelectorConfig(
                    options=api_options,
                    custom_value=False,
                    sort=False,
                    mode=SelectSelectorMode.LIST,
                ))
        })

        return self.async_show_form(
            step_id="confirm_data", data_schema=confirm_data_schema, errors=errors, last_step=True
        )

    async def _validate_vacuum(self: Self, host: str, token: str, used_map_api: VacuumApi) -> bool:
        if used_map_api != VacuumApi.ROBOROCK:
            return True
        roborock_vacuum = RoborockVacuum(host, token)
        try:
            status = await self.hass.async_add_executor_job(roborock_vacuum.status)
            return status is not None
        except Exception as e:
            _LOGGER.error(e, exc_info=True)
            return False

    def _default_image_config(self: Self) -> dict[str, float]:
        image_config = ImageConfig()
        return {
            CONF_IMAGE_CONFIG_SCALE: image_config.scale,
            CONF_IMAGE_CONFIG_ROTATE: image_config.rotate,
            CONF_IMAGE_CONFIG_TRIM_LEFT: image_config.trim.left,
            CONF_IMAGE_CONFIG_TRIM_RIGHT: image_config.trim.right,
            CONF_IMAGE_CONFIG_TRIM_TOP: image_config.trim.top,
            CONF_IMAGE_CONFIG_TRIM_BOTTOM: image_config.trim.bottom,
        }

    @staticmethod
    def _default_colors() -> dict[str, tuple[int, int, int, int]]:
        return {k: ([*v] if len(v) == 4 else [*v, 255]) for k, v in ColorsPalette.COLORS.items()}

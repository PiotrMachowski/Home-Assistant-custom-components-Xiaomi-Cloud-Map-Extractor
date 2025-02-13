from __future__ import annotations

import logging
from typing import Any, Self, Mapping

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (CONF_HOST, CONF_TOKEN, CONF_MAC, CONF_USERNAME, CONF_PASSWORD, CONF_MODEL,
                                 CONF_DEVICE_ID, CONF_NAME)
from homeassistant.core import callback
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

from .connector.utils.exceptions import XiaomiCloudMapExtractorException, TwoFactorAuthRequiredException
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
    CONF_IMAGE_CONFIG_TRIM_RIGHT
)
from .options_flow import XiaomiCloudMapExtractorOptionsFlowHandler
from .types import XiaomiCloudMapExtractorConfigEntry

_LOGGER = logging.getLogger(__name__)

CLOUD_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_SERVER, default='de'): vol.In(
            AVAILABLE_SERVERS
        )
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
        errors = {}
        if user_input is not None:

            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            server = user_input.get(CONF_SERVER)
            session_creator = lambda: async_create_clientsession(self.hass)

            connector = XiaomiCloudConnector(session_creator, username, password, server)
            two_factor_url = None
            try:
                if await connector.login() is None:
                    errors["base"] = "cloud_login_error"
            except TwoFactorAuthRequiredException as e:
                errors["base"] = "two_factor_auth_required"  # todo 2fa
                two_factor_url = e.url
            except XiaomiCloudMapExtractorException:
                errors["base"] = "cloud_login_error"
            except Exception as e:
                _LOGGER.error("Unexpected exception while attempting Miio cloud login")
                _LOGGER.error(e, exc_info=True)
                return self.async_abort(reason="unknown")

            if errors:
                return self.async_show_form(
                    step_id="cloud", data_schema=CLOUD_SCHEMA, errors=errors,
                    description_placeholders={"two_factor_url": two_factor_url}
                )

            try:
                devices_raw = await connector.get_devices(server)
            except Exception as e:
                _LOGGER.error("Unexpected exception while attempting to Miio cloud get devices")
                _LOGGER.error(e, exc_info=True)
                return self.async_abort(reason="unknown")

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

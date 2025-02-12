from typing import Self, Any

import voluptuous as vol
from homeassistant.config_entries import OptionsFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    ColorRGBSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelectorConfig,
    SelectSelector,
    SelectSelectorMode
)
from vacuum_map_parser_base.config.color import SupportedColor, ColorsPalette
from vacuum_map_parser_base.config.drawable import Drawable
from vacuum_map_parser_base.config.size import Size, Sizes

from .const import (
    CONF_IMAGE_CONFIG_SCALE,
    CONF_IMAGE_CONFIG_ROTATE,
    CONF_IMAGE_CONFIG_TRIM_LEFT,
    CONF_IMAGE_CONFIG_TRIM_RIGHT,
    CONF_IMAGE_CONFIG_TRIM_TOP,
    CONF_IMAGE_CONFIG_TRIM_BOTTOM,
    CONF_COLORS,
    CONF_IMAGE_CONFIG,
    CONF_SIZES,
    CONF_DRAWABLES,
    CONF_ROOM_COLORS
)
from .types import XiaomiCloudMapExtractorConfigEntry


class XiaomiCloudMapExtractorOptionsFlowHandler(OptionsFlow):
    """Options for the component."""
    _room_color_ids: list[str]
    _changed_options: dict[str, Any]

    def __init__(self: Self) -> None:
        self._changed_options = {}
        self._room_color_ids = []

    @property
    def config_entry(self: Self) -> XiaomiCloudMapExtractorConfigEntry:
        return super().config_entry

    async def async_step_init(self: Self, user_input=None) -> ConfigFlowResult:  # pylint: disable=unused-argument
        """Manage the options."""

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "image_config",
                "colors",
                "room_colors_step1",
                "drawables",
                "sizes",
                # "texts"
            ],
        )

    async def async_step_image_config(self: Self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            if user_input[CONF_IMAGE_CONFIG_TRIM_LEFT] + user_input[CONF_IMAGE_CONFIG_TRIM_RIGHT] >= 100:
                errors[CONF_IMAGE_CONFIG_TRIM_LEFT] = "left_and_right_sum_over_100"
                errors[CONF_IMAGE_CONFIG_TRIM_RIGHT] = "left_and_right_sum_over_100"
            if user_input[CONF_IMAGE_CONFIG_TRIM_TOP] + user_input[CONF_IMAGE_CONFIG_TRIM_BOTTOM] >= 100:
                errors[CONF_IMAGE_CONFIG_TRIM_TOP] = "top_and_bottom_sum_over_100"
                errors[CONF_IMAGE_CONFIG_TRIM_BOTTOM] = "top_and_bottom_sum_over_100"
            if len(errors) == 0:
                self._changed_options[CONF_IMAGE_CONFIG] = user_input
                return await self._update_entry()

        schema = vol.Schema({
            vol.Required(CONF_IMAGE_CONFIG_SCALE): NumberSelector(
                config=NumberSelectorConfig(min=0.1, max=20, step=0.1, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_IMAGE_CONFIG_ROTATE): NumberSelector(
                config=NumberSelectorConfig(min=0, max=359, step=1, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_IMAGE_CONFIG_TRIM_LEFT): NumberSelector(
                config=NumberSelectorConfig(min=0, max=100, step=0.1, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_IMAGE_CONFIG_TRIM_RIGHT): NumberSelector(
                config=NumberSelectorConfig(min=0, max=100, step=0.1, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_IMAGE_CONFIG_TRIM_TOP): NumberSelector(
                config=NumberSelectorConfig(min=0, max=100, step=0.1, mode=NumberSelectorMode.BOX)),
            vol.Required(CONF_IMAGE_CONFIG_TRIM_BOTTOM): NumberSelector(
                config=NumberSelectorConfig(min=0, max=100, step=0.1, mode=NumberSelectorMode.BOX))
        })
        data_schema = self.add_suggested_values_to_schema(
            schema, {**self.config_entry.options[CONF_IMAGE_CONFIG], **(user_input or {})}
        )
        return self.async_show_form(step_id="image_config", data_schema=data_schema, errors=errors, last_step=True)

    async def async_step_colors(self: Self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._changed_options[CONF_COLORS] = {
                v.value: [*user_input[v.value], int(user_input[v.value + "_alpha"])] for v in SupportedColor
            }
            return await self._update_entry()

        supported_colors = [v.value for v in SupportedColor]
        field_schemas = {}

        for color in supported_colors:
            field_schemas[vol.Required(color)] = ColorRGBSelector()
            field_schemas[vol.Required(color + "_alpha")] = NumberSelector(
                config=NumberSelectorConfig(min=0, max=255, step=1, mode=NumberSelectorMode.SLIDER))

        schema = vol.Schema(field_schemas)
        data_schema = self.add_suggested_values_to_schema(
            schema, self._default_values_colors()
        )
        return self.async_show_form(step_id="colors", data_schema=data_schema, last_step=True)

    def _default_values_colors(self: Self) -> dict[str, Any]:
        defaults = {}
        for k, v in ColorsPalette.COLORS.items():
            defaults[k] = v[0:3]
            defaults[k + "_alpha"] = 255 if len(v) == 3 else v[3]
        for k, v in self.config_entry.options[CONF_COLORS].items():
            defaults[k] = v[0:3]
            defaults[k + "_alpha"] = v[3]
        return defaults

    async def async_step_room_colors_step1(self: Self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            invalid_room_ids = list(filter(lambda i: not i.isdigit(), user_input["room_color_ids"]))

            if len(invalid_room_ids) > 0:
                errors["room_color_ids"] = "some_room_ids_are_not_integers"
            else:
                self._room_color_ids = user_input["room_color_ids"]
            return await self.async_step_room_colors_step2()

        schema = vol.Schema(
            {vol.Required("room_color_ids"): SelectSelector(
                SelectSelectorConfig(
                    options=[*ColorsPalette.ROOM_COLORS.keys()],
                    custom_value=True,
                    sort=False,
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                ))}
        )

        if len(self.config_entry.options[CONF_ROOM_COLORS]) > 0:
            data_schema = self.add_suggested_values_to_schema(
                schema, {"room_color_ids": list(self.config_entry.options[CONF_ROOM_COLORS].keys())}
            )
        else:
            data_schema = schema
        return self.async_show_form(step_id="room_colors_step1", data_schema=data_schema)

    async def async_step_room_colors_step2(self: Self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._changed_options[CONF_ROOM_COLORS] = user_input
            return await self._update_entry()

        schema = vol.Schema({vol.Required(room_id): ColorRGBSelector() for room_id in self._room_color_ids})
        configured_colors = self.config_entry.options[CONF_ROOM_COLORS]
        palette = ColorsPalette()
        data_schema = self.add_suggested_values_to_schema(
            schema,
            {
                room_id: (
                    configured_colors[room_id]
                    if room_id in configured_colors
                    else palette.get_room_color(room_id)
                )
                for room_id in self._room_color_ids
            }
        )
        return self.async_show_form(step_id="room_colors_step2", data_schema=data_schema, last_step=True)

    async def async_step_drawables(self: Self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._changed_options[CONF_DRAWABLES] = user_input[CONF_DRAWABLES]
            return await self._update_entry()

        schema = vol.Schema(
            {vol.Required(CONF_DRAWABLES): SelectSelector(
                SelectSelectorConfig(
                    options=[v.value for v in Drawable],
                    custom_value=False,
                    sort=True,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_DRAWABLES
                ))}
        )
        data_schema = self.add_suggested_values_to_schema(
            schema, {CONF_DRAWABLES: self.config_entry.options[CONF_DRAWABLES]}
        )
        return self.async_show_form(step_id="drawables", data_schema=data_schema, last_step=True)

    async def async_step_sizes(self: Self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._changed_options[CONF_SIZES] = user_input
            return await self._update_entry()

        selector = NumberSelector(
            config=NumberSelectorConfig(min=0, max=50, step=0.1, unit_of_measurement="px", mode=NumberSelectorMode.BOX))
        schema = vol.Schema({vol.Required(s.value): selector for s in Size})
        data_schema = self.add_suggested_values_to_schema(
            schema, self.config_entry.options[CONF_SIZES]
        )
        return self.async_show_form(step_id="sizes", data_schema=data_schema, last_step=True)

    def _default_values_sizes(self: Self) -> dict[str, Any]:
        defaults = {k.value: v for k, v in Sizes.SIZES.items()}
        for k, v in self.config_entry.options[CONF_SIZES]:
            defaults[k] = v
        return defaults

    # async def async_step_texts(self: Self, user_input=None) -> ConfigFlowResult:
    #     schema = vol.All(cv.ensure_list, [vol.Schema({
    #         vol.Required(CONF_TEXT_VALUE): cv.string,
    #         vol.Required(CONF_TEXT_X): vol.Coerce(float),
    #         vol.Required(CONF_TEXT_Y): vol.Coerce(float),
    #         vol.Optional(CONF_TEXT_COLOR, default=(0, 0, 0)): COLOR_SCHEMA,
    #         vol.Optional(CONF_TEXT_FONT, default=None): vol.Or(cv.string, vol.Equal(None)),
    #         vol.Optional(CONF_TEXT_FONT_SIZE, default=0): cv.positive_int
    #     })])
    #     return self.async_show_form(step_id="texts", data_schema=schema, last_step=True)

    async def _update_entry(self: Self) -> ConfigFlowResult:
        updated_options = {
            **self.config_entry.options,
            **self._changed_options
        }
        return self.async_create_entry(title="", data=updated_options)

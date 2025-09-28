from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from . import DOMAIN


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    This function can also be extended later to attempt a quick connection
    test to the WebSocket endpoint if desired.
    """
    host: str = data.get("host", "").strip()
    password: str = data.get("password", "")

    errors: dict[str, str] = {}

    if not host:
        errors["host"] = "required"
    if not password:
        errors["password"] = "required"

    if errors:
        raise vol.Invalid(errors)

    # Return info that you want to store in the config entry.
    return {"title": host}


class TibberWebsocketConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tibber WebSocket."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except vol.Invalid as err:
                # err.error_message may not be structured; map our own
                for field, code in getattr(err, "error", {}) or {}:
                    errors[field] = code
            else:
                await self.async_set_unique_id(user_input["host"])  # one entry per host
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data={
                    "host": user_input["host"],
                    # The password will be stored by Home Assistant as part of the
                    # config entry data. It will be treated as a sensitive field in
                    # the UI and redacted in logs. Home Assistant stores credentials
                    # in its secure storage backend.
                    "password": user_input["password"],
                })

        data_schema = vol.Schema({
            vol.Required("host"): TextSelector(TextSelectorConfig(type="text")),
            vol.Required("password"): TextSelector(TextSelectorConfig(type="password")),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class TibberWebsocketOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow to allow editing settings later."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Save options; for now we mirror data to options
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required("host", default=self.config_entry.data.get("host")): TextSelector(TextSelectorConfig(type="text")),
            vol.Required("password", default=self.config_entry.data.get("password", "")): TextSelector(TextSelectorConfig(type="password")),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> TibberWebsocketOptionsFlowHandler:
    return TibberWebsocketOptionsFlowHandler(config_entry)

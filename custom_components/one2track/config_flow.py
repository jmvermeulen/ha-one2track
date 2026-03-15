"""Config flow for One2Track."""

import logging

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import voluptuous as vol

from .api import One2TrackApiClient, AuthenticationError
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_ACCOUNT_ID

_LOGGER = logging.getLogger(__name__)


class One2TrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for One2Track."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input:
            try:
                session = async_create_clientsession(self.hass)
                client = One2TrackApiClient(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=session,
                )
                account_id = await client.authenticate()

                user_input[CONF_ACCOUNT_ID] = account_id
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"One2Track ({account_id})",
                    data=user_input,
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

"""Config flow for Cast4All Energy."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Cast4AllApiClient, Cast4AllAuthError, Cast4AllConnectionError
from .const import DOMAIN, CONF_INSTALLATION_ID

_LOGGER = logging.getLogger(__name__)


class Cast4AllConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cast4All Energy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = Cast4AllApiClient(
                session=session,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )

            try:
                valid = await api.validate_credentials()
                if not valid:
                    errors["base"] = "invalid_auth"
                else:
                    # Discover installation
                    installations = await api.get_installations()
                    if not installations:
                        errors["base"] = "no_installation"
                    else:
                        installation = installations[0]
                        # Extract ID from resourceUri
                        resource_uri = installation.get("resourceUri", "")
                        installation_id = resource_uri.rstrip("/").split("/")[-1]
                        address = f"{installation.get('street', '')} {installation.get('houseNumber', '')}, {installation.get('zipCode', '')} {installation.get('city', '')}".strip()

                        # Check for duplicates
                        await self.async_set_unique_id(installation_id)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=address or "Cast4All Energy",
                            data={
                                CONF_USERNAME: user_input[CONF_USERNAME],
                                CONF_PASSWORD: user_input[CONF_PASSWORD],
                                CONF_INSTALLATION_ID: installation_id,
                            },
                        )
            except Cast4AllConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when credentials expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = Cast4AllApiClient(
                session=session,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            try:
                valid = await api.validate_credentials()
                if valid:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data_updates={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                errors["base"] = "invalid_auth"
            except Cast4AllConnectionError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

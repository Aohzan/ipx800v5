"""Config flow to configure the ipx800v5 integration."""

from collections.abc import Mapping
from itertools import groupby
import logging
from typing import Any

from aiohttp import ClientSession
from pypx800v5 import (
    API_CONFIG_NAME,
    EXT_X8R,
    IPX,
    IPX800,
    IPX800CannotConnectError,
    IPX800InvalidAuthError,
    IPX800RequestError,
)
import voluptuous as vol
from voluptuous.util import Upper

from homeassistant.config_entries import (
    SOURCE_IMPORT,
    SOURCE_REAUTH,
    SOURCE_USER,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_DEVICES,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_COMPONENT,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_PUSH_PASSWORD,
    DEFAULT_IPX_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import IpxConfigEntry
from .helpers import get_device_in_devices_config, get_entry_config

_LOGGER = logging.getLogger(__name__)

BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_IPX_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=80): int,
        vol.Required(CONF_API_KEY): str,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})
RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT): int,
    }
)


def _unique_id(host: str) -> str:
    """Return the unique ID of the config entry of an IPX800."""
    return f"{DOMAIN}, {host}"


class IpxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a IPX800 config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize class variables."""
        self.base_config: dict[str, Any] = {}
        self.params_schema: dict = {}

    async def async_step_import(self, import_info) -> ConfigFlowResult:
        """Import an advanced configuration from YAML config."""
        entry = await self.async_set_unique_id(_unique_id(import_info[CONF_HOST]))

        if entry:
            if entry.source == SOURCE_USER:
                _LOGGER.error(
                    "The IPX800 V5 on %s is already configured from the UI. Delete it first if you want to configure it from configuration.yaml",
                    import_info[CONF_HOST],
                )
                return self.async_abort(reason="already_configured")
            self.hass.config_entries.async_update_entry(entry, data=import_info)
            self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{import_info[CONF_NAME]} (from yaml)", data=import_info
        )

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Get configuration from the user."""
        errors: dict[str, str] = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=BASE_SCHEMA, errors=errors
            )

        await self.async_set_unique_id(_unique_id(user_input[CONF_HOST]))
        self._abort_if_unique_id_configured()

        session = async_get_clientsession(self.hass, verify_ssl=False)

        # Read the IPX800 configuration here to show the errors in this step
        schema, errors = await _async_get_param_schema(session, user_input, SOURCE_USER)

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=BASE_SCHEMA, errors=errors
            )

        self.base_config = user_input
        self.params_schema = schema
        return await self.async_step_params()

    async def async_step_params(self, user_input=None) -> ConfigFlowResult:
        """Handle the param flow to customize according to device config."""
        if user_input is None:
            return self.async_show_form(
                step_id="params", data_schema=vol.Schema(self.params_schema)
            )

        return self.async_create_entry(
            title=self.base_config[CONF_HOST],
            data=self.base_config | config_organizer(user_input, SOURCE_USER),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a rejected API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API key."""
        return await self._async_step_update_entry(
            "reauth_confirm", REAUTH_SCHEMA, user_input
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the address of the IPX800."""
        return await self._async_step_update_entry(
            "reconfigure", RECONFIGURE_SCHEMA, user_input
        )

    async def _async_step_update_entry(
        self, step_id: str, schema: vol.Schema, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Update the connection settings of the entry after testing them."""
        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
        else:
            entry = self._get_reconfigure_entry()
        if entry.source == SOURCE_IMPORT:
            # configuration.yaml replaces the entry data at each startup
            return self.async_abort(reason="yaml_entry")
        config = get_entry_config(entry)
        errors: dict[str, str] = {}

        if user_input is not None:
            new_config = config | user_input
            unique_id = _unique_id(new_config[CONF_HOST])
            if unique_id != entry.unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
            errors = await _test_connection(
                async_get_clientsession(self.hass, verify_ssl=False), new_config
            )
            if not errors:
                # An API key changed here replaces the one of the options
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    data_updates=user_input,
                    options={
                        key: value
                        for key, value in entry.options.items()
                        if key not in user_input
                    },
                )

        if self.source != SOURCE_REAUTH:
            # The rejected API key is not suggested
            schema = self.add_suggested_values_to_schema(schema, user_input or config)
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: IpxConfigEntry,
    ) -> IpxOptionsFlowHandler:
        """Define the config flow to handle options."""
        return IpxOptionsFlowHandler()


class IpxOptionsFlowHandler(OptionsFlowWithReload):
    """Handle a IPX800 options flow."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self.schema: dict | None = None

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None and self.schema is not None:
            return self.async_create_entry(
                data=config_organizer(user_input, self.config_entry.source)
            )

        # Without the IPX800 configuration, the form only shows the error and
        # submitting it tries again
        session = async_get_clientsession(self.hass, verify_ssl=False)
        schema, errors = await _async_get_param_schema(
            session, get_entry_config(self.config_entry), self.config_entry.source
        )
        if not errors:
            self.schema = schema
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )


async def _test_connection(session: ClientSession, config: dict) -> dict[str, str]:
    """Return the errors of a request to the IPX800."""
    controller = IPX800(
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        api_key=config[CONF_API_KEY],
        session=session,
    )
    try:
        await controller.ping()
    except IPX800InvalidAuthError:
        return {"base": "invalid_auth"}
    except IPX800CannotConnectError, IPX800RequestError:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected error while connecting to the IPX800")
        return {"base": "unknown"}
    return {}


async def _async_get_param_schema(
    session: ClientSession, config: dict, entry_source: str
) -> tuple[dict, dict[str, str]]:
    """Return the params schema, or the errors when the IPX800 can't be read."""
    try:
        return await _build_param_schema(session, config, entry_source), {}
    except IPX800InvalidAuthError:
        return {}, {"base": "invalid_auth"}
    except IPX800CannotConnectError, IPX800RequestError:
        return {}, {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected error while reading the IPX800 configuration")
        return {}, {"base": "unknown"}


async def _build_param_schema(
    session,
    config,
    entry_source,
):
    """Build schema for params and options flow according to the IPX800 config."""
    # options for ui and yaml entry
    schema = {
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): int,
    }

    # if entry created with config_flow, add options
    if entry_source == SOURCE_USER:
        _LOGGER.debug("Add options for user entry")
        devices_config = config.get(CONF_DEVICES, {})
        schema.update(
            {
                vol.Required(
                    CONF_API_KEY,
                    default=config.get(CONF_API_KEY),
                ): str,
                vol.Optional(
                    CONF_PUSH_PASSWORD,
                    default=config.get(CONF_PUSH_PASSWORD, ""),
                ): str,
            }
        )

        _LOGGER.debug("Connect to the IPX to get its configuration")
        ipx = IPX800(
            host=config[CONF_HOST],
            port=config[CONF_PORT],
            api_key=config[CONF_API_KEY],
            session=session,
        )
        await ipx.init_config()

        _LOGGER.debug("Build schema according to the IPX configuration")
        for i in range(8):
            device = get_device_in_devices_config(
                devices_config,
                {
                    CONF_NAME: f"{DEFAULT_IPX_NAME} Relais {i + 1}",
                    CONF_COMPONENT: "switch",
                    CONF_EXT_TYPE: IPX,
                    CONF_EXT_NUMBER: 0,
                    CONF_IO_NUMBER: i + 1,
                },
            )
            schema.update(
                {
                    vol.Required(
                        f"ipx_0_{i + 1}",
                        default=device.get(CONF_COMPONENT, "switch"),
                    ): vol.All(str, vol.Lower, vol.In(["switch", "light"])),
                }
            )

        _LOGGER.debug("Build schema according to the extensions found")
        for ext_type, extensions in groupby(ipx.extensions_config, lambda x: x["type"]):
            _LOGGER.debug("Found %s", ext_type)
            ext_number = 0
            for extension in extensions:
                if ext_type == EXT_X8R:
                    _LOGGER.debug("Add X8R N°%s to the params", ext_number)
                    for i in range(8):
                        device = get_device_in_devices_config(
                            devices_config,
                            {
                                CONF_NAME: f"{extension[API_CONFIG_NAME]} Relais {i + 1}",
                                CONF_COMPONENT: "switch",
                                CONF_EXT_TYPE: ext_type,
                                CONF_EXT_NUMBER: ext_number,
                                CONF_IO_NUMBER: i + 1,
                            },
                        )
                        schema.update(
                            {
                                vol.Required(
                                    f"{ext_type}_{ext_number}_{i + 1}",
                                    description=f"{extension[API_CONFIG_NAME]} N°{i}",
                                    default=device.get(CONF_COMPONENT, "switch"),
                                ): vol.All(str, vol.Lower, vol.In(["switch", "light"])),
                            }
                        )
                ext_number += 1  # noqa: SIM113

    return schema


def config_organizer(user_input, entry_source):
    """Organize params input to options, with devices config as a yaml-like list."""
    user_input = dict(user_input)
    config = {}

    # For user and yaml entry
    config[CONF_SCAN_INTERVAL] = user_input.pop(CONF_SCAN_INTERVAL)

    # Only for user entry, devices of yaml entries come from configuration.yaml
    if entry_source != SOURCE_USER:
        return config

    if CONF_API_KEY in user_input:
        config[CONF_API_KEY] = user_input.pop(CONF_API_KEY)

    if CONF_PUSH_PASSWORD in user_input:
        config[CONF_PUSH_PASSWORD] = user_input.pop(CONF_PUSH_PASSWORD)

    config[CONF_DEVICES] = []
    for device_config in user_input.items():
        ident = device_config[0].split("_")
        config[CONF_DEVICES].append(
            {
                CONF_NAME: f"{Upper(ident[0])} N°{ident[1]} Relais {ident[2]}",
                CONF_EXT_TYPE: str(ident[0]),
                CONF_EXT_NUMBER: int(ident[1]),
                CONF_EXT_NAME: f"{Upper(ident[0])} N°{ident[1]}",
                CONF_IO_NUMBER: int(ident[2]),
                CONF_COMPONENT: str(device_config[1]),
            }
        )
    return config

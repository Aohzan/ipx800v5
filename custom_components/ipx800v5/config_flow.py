"""Config flow to configure the ipx800v5 integration."""
from itertools import groupby
import logging

from pypx800v5 import IPX800, IPX800CannotConnectError, IPX800InvalidAuthError
from pypx800v5.const import API_CONFIG_NAME, EXT_X8R, IPX
import voluptuous as vol
from voluptuous.util import Upper

from homeassistant import config_entries
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
from .tools_entities import get_device_in_devices_config

_LOGGER = logging.getLogger(__name__)

BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_IPX_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=80): int,
        vol.Required(CONF_API_KEY): str,
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class IpxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a IPX800 config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize class variables."""
        self.base_config = {}

    async def async_step_import(self, import_info):
        """Import an advanced configuration from YAML config."""
        entry = await self.async_set_unique_id(f"{DOMAIN}, {import_info[CONF_HOST]}")

        if entry:
            if entry.source == "user":
                _LOGGER.error(
                    "The IPX800 V5 on %s is already configured from the UI. Delete it first if you want to configure it from configuration.yaml",
                    import_info[CONF_HOST],
                )
                return self.async_abort(reason="single_instance_allowed")
            self.hass.config_entries.async_update_entry(entry, data=import_info)
            self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{import_info[CONF_NAME]} (from yaml)", data=import_info
        )

    async def async_step_user(self, user_input=None):
        """Get configuration from the user."""
        errors = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=BASE_SCHEMA, errors=errors
            )

        entry = await self.async_set_unique_id(f"{DOMAIN}, {user_input[CONF_HOST]}")
        if entry:
            self._abort_if_unique_id_configured()

        session = async_get_clientsession(self.hass, False)

        errors = await _test_connection(session, user_input)

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=BASE_SCHEMA, errors=errors
            )

        self.base_config = user_input
        return await self.async_step_params()

    async def async_step_params(self, user_input=None):
        """Handle the param flow to customize according to device config."""
        if user_input is None:
            session = async_get_clientsession(self.hass, False)
            return self.async_show_form(
                step_id="params",
                data_schema=vol.Schema(
                    await _build_param_schema(session, self.base_config, {}, "user")
                ),
            )

        return self.async_create_entry(
            title=self.base_config[CONF_HOST],
            data=config_organizer(self.base_config, user_input),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return IpxOptionsFlowHandler(config_entry)


class IpxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a IPX800 options flow."""

    def __init__(self, config_entry):
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict = None):
        """Manage the options."""
        if user_input is None:
            session = async_get_clientsession(self.hass, False)
            config = self.config_entry.data
            options = self.config_entry.options

            schema = await _build_param_schema(
                session, config, options, self.config_entry.source
            )

            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(schema),
            )

        return self.async_create_entry(
            title=self.config_entry.data[CONF_HOST],
            data=config_organizer(self.config_entry.data, user_input),
        )


async def _test_connection(session, base_config):
    errors = {}

    controller = IPX800(
        host=base_config[CONF_HOST],
        port=base_config[CONF_PORT],
        api_key=base_config[CONF_API_KEY],
        session=session,
    )

    try:
        await controller.ping()
    except IPX800InvalidAuthError:
        errors["base"] = "invalid_auth"
    except IPX800CannotConnectError:
        errors["base"] = "cannot_connect"

    return errors


async def _build_param_schema(
    session, base_config: dict, options: dict, entry_source: str
):
    """Build schema for params and options flow according to the IPX800 config."""
    config = {**base_config, **options}
    # options for ui and yaml entry
    schema = {
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): int,
    }

    # if entry created with config_flow, add options
    if entry_source == "user":
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

        ipx = IPX800(
            host=base_config[CONF_HOST],
            port=base_config[CONF_PORT],
            api_key=base_config[CONF_API_KEY],
            session=session,
        )
        await ipx.init_config()

        # Build schema according to needed options for the IPX configuration
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
        # Extensions
        for ext_type, extensions in groupby(ipx.extensions_config, lambda x: x["type"]):
            ext_number = 1
            for extension in extensions:
                if ext_type == EXT_X8R:
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
                                    f"{ext_type}_{ext_number}_{i + 1}",
                                    description=f"{extension[API_CONFIG_NAME]} N°{i + 1}",
                                    default=device.get(CONF_COMPONENT, "switch"),
                                ): vol.All(str, vol.Lower, vol.In(["switch", "light"])),
                            }
                        )
                ext_number += 1

    return schema


def config_organizer(base_config: dict, user_input: dict):
    """Organize devices config to be a list like yaml schema."""
    config = dict(base_config)

    # For user and yaml entry
    config[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
    user_input.pop(CONF_SCAN_INTERVAL)

    # Only for user entry
    if CONF_API_KEY in user_input:
        config[CONF_API_KEY] = user_input[CONF_API_KEY]
        user_input.pop(CONF_API_KEY)

    if CONF_PUSH_PASSWORD in user_input:
        config[CONF_PUSH_PASSWORD] = user_input[CONF_PUSH_PASSWORD]
        user_input.pop(CONF_PUSH_PASSWORD)

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

"""Support for the GCE IPX800 V5."""

from datetime import timedelta
import logging

from pypx800v5 import IPX800, IPX800CannotConnectError, IPX800InvalidAuthError
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_COMPONENT,
    CONF_DEFAULT_BRIGHTNESS,
    CONF_DEVICES,
    CONF_DEVICES_AUTO,
    CONF_DIAG_SENSORS,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    CONF_PUSH_PASSWORD,
    CONF_TRANSITION,
    CONTROLLER,
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRANSITION,
    DOMAIN,
    PLATFORMS,
    REQUEST_REFRESH_DELAY,
    UNDO_UPDATE_LISTENER,
)
from .helpers import (
    build_extensions_entities,
    build_ipx_entities,
    build_ipx_system_entities,
    build_objects_entities,
    filter_entities_by_platform,
    remove_duplicate_entities,
)
from .request_views import IpxRequestDataView, IpxRequestRefreshView, IpxRequestView

_LOGGER = logging.getLogger(__name__)

IPX800_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_COMPONENT): cv.string,
        vol.Required(CONF_EXT_TYPE): cv.string,
        vol.Optional(CONF_EXT_NUMBER, default=0): cv.positive_int,
        vol.Optional(CONF_TYPE): cv.string,
        vol.Optional(CONF_IO_NUMBER): cv.positive_int,
        vol.Optional(CONF_IO_NUMBERS): cv.ensure_list,
        vol.Optional(CONF_DEFAULT_BRIGHTNESS): cv.positive_int,
        vol.Optional(CONF_ID): cv.positive_int,
        vol.Optional(CONF_ICON): cv.icon,
        vol.Optional(CONF_TRANSITION, default=DEFAULT_TRANSITION): vol.Coerce(float),
        vol.Optional(CONF_DEVICE_CLASS): cv.string,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    }
)

IPX800_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_DEVICES_AUTO, default=[]): cv.ensure_list,
        vol.Optional(CONF_DEVICES, default=[]): vol.All(
            cv.ensure_list, [IPX800_DEVICES_SCHEMA]
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [IPX800_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the IPX800 from config file."""
    if DOMAIN in config:
        for ipx800_config in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": SOURCE_IMPORT}, data=ipx800_config
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the IPX800v5."""
    hass.data.setdefault(DOMAIN, {})

    config = entry.options | entry.data

    session = async_get_clientsession(hass, False)

    ipx = IPX800(
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        api_key=config[CONF_API_KEY],
        session=session,
    )

    try:
        await ipx.ping()
    except IPX800CannotConnectError as exception:
        _LOGGER.error(
            "Cannot connect to the %s IPX800 V5, check host and port",
            config[CONF_HOST],
        )
        raise ConfigEntryNotReady from exception
    except IPX800InvalidAuthError:
        _LOGGER.error("Authentication error, check API Key")
        return False

    await ipx.init_config()

    async def async_update_data():
        """Fetch data from API."""
        try:
            return await ipx.global_get()
        except IPX800InvalidAuthError as err:
            raise UpdateFailed("Authentication error on IPX800") from err
        except IPX800CannotConnectError as err:
            raise UpdateFailed(f"Failed to communicating with API: {err}") from err

    scan_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    if scan_interval < 10:
        _LOGGER.warning(
            "A scan interval too low has been set, you will send too many requests to your IPX800"
        )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=config[CONF_NAME],
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
        request_refresh_debouncer=Debouncer(
            hass,
            _LOGGER,
            cooldown=REQUEST_REFRESH_DELAY,
            immediate=False,
        ),
    )

    undo_listener = entry.add_update_listener(_async_update_listener)

    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_NAME: config[CONF_NAME],
        CONTROLLER: ipx,
        COORDINATOR: coordinator,
        CONF_DEVICES: {},
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    # Parse devices config is correct and supported
    # devices = check_devices_list(devices)

    # build list of entities according to the configuration and discovered extensions and objects
    auto_entities = []
    auto_entities.extend(
        build_ipx_entities(
            entry.source, config[CONF_DEVICES], config.get(CONF_DEVICES_AUTO, [])
        )
    )
    auto_entities.extend(
        build_ipx_system_entities(ipx, config.get(CONF_DIAG_SENSORS, False))
    )
    auto_entities.extend(
        build_extensions_entities(
            entry.source, ipx, config[CONF_DEVICES], config.get(CONF_DEVICES_AUTO, [])
        )
    )
    auto_entities.extend(
        build_objects_entities(
            entry.source, ipx, config[CONF_DEVICES], config.get(CONF_DEVICES_AUTO, [])
        )
    )
    entities = list(config[CONF_DEVICES])
    entities.extend(remove_duplicate_entities(auto_entities, config[CONF_DEVICES]))

    for platform in PLATFORMS:
        _LOGGER.debug("Load platform %s", platform)
        hass.data[DOMAIN][entry.entry_id][CONF_DEVICES][platform] = (
            filter_entities_by_platform(entities, platform)
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Provide endpoints for the IPX to call to push states
    if CONF_PUSH_PASSWORD in config:
        hass.http.register_view(
            IpxRequestView(
                config[CONF_HOST], config[CONF_PUSH_PASSWORD], config[CONF_NAME]
            )
        )
        hass.http.register_view(
            IpxRequestDataView(
                config[CONF_HOST], config[CONF_PUSH_PASSWORD], config[CONF_NAME]
            )
        )

        hass.http.register_view(
            IpxRequestRefreshView(
                config[CONF_HOST],
                config[CONF_PUSH_PASSWORD],
                config[CONF_NAME],
                coordinator,
            )
        )
    else:
        _LOGGER.info(
            "No %s parameter provided in configuration, skip API call handling for IPX800 PUSH",
            CONF_PUSH_PASSWORD,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

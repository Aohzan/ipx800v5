"""Support for the GCE IPX800 V5."""

import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_API_KEY,
    CONF_DEVICE_CLASS,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    CONF_TYPE,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceEntry,
    DeviceIdentifierCollisionError,
    async_entries_for_config_entry,
    async_get as async_get_device_registry,
)
from homeassistant.helpers.entity_registry import (
    async_entries_for_device,
    async_get as async_get_entity_registry,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_COMPONENT,
    CONF_DEFAULT_BRIGHTNESS,
    CONF_DEVICES,
    CONF_DEVICES_AUTO,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    CONF_PUSH_PASSWORD,
    CONF_TRANSITION,
    DEFAULT_TRANSITION,
    DOMAIN,
    PLATFORMS,
    PUSH_VIEWS,
)
from .coordinator import IpxConfigEntry, IpxCoordinator
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


async def async_setup_entry(hass: HomeAssistant, entry: IpxConfigEntry) -> bool:
    """Set up the IPX800v5."""
    coordinator = IpxCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    ipx = coordinator.ipx
    config = coordinator.config
    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(CONNECTION_NETWORK_MAC, str(ipx.mac_address))},
        identifiers={(DOMAIN, ipx.mac_address)},
        manufacturer="GCE Electronics",
        model="IPX800 V5",
        name=config[CONF_NAME],
        sw_version=ipx.firmware_version,
        configuration_url=f"http://{config[CONF_HOST]}:{config[CONF_PORT]}/",
    )
    _async_migrate_extension_devices(hass, entry, ipx.mac_address)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Provide endpoints for the IPX to call to push states
    if CONF_PUSH_PASSWORD in config:
        # Views can't be unregistered: register each URL once and point it to
        # the current entry, so it keeps working after a reload
        push_views = hass.data.setdefault(PUSH_VIEWS, {})
        for view in (
            IpxRequestView(entry.entry_id, config[CONF_NAME]),
            IpxRequestDataView(entry.entry_id, config[CONF_NAME]),
            IpxRequestRefreshView(entry.entry_id, config[CONF_NAME]),
        ):
            if view.url in push_views:
                push_views[view.url].entry_id = entry.entry_id
            else:
                hass.http.register_view(view)
                push_views[view.url] = view
    else:
        _LOGGER.info(
            "No %s parameter provided in configuration, skip API call handling for IPX800 PUSH",
            CONF_PUSH_PASSWORD,
        )

    return True


@callback
def _async_migrate_extension_devices(
    hass: HomeAssistant, entry: IpxConfigEntry, mac_address: str
) -> None:
    """Prefix the extension device identifiers with the IPX800 MAC address.

    Extension devices were identified by their name only, which merged the
    devices of extensions having the same name on several IPX800. Home
    Assistant 2026.8 split the devices shared between entries, so each entry
    migrates its own copy.
    """
    device_registry = async_get_device_registry(hass)
    for device in async_entries_for_config_entry(device_registry, entry.entry_id):
        identifiers = {
            (domain, identifier)
            if domain != DOMAIN
            or identifier == mac_address
            or identifier.startswith(f"{mac_address}_")
            else (domain, f"{mac_address}_{identifier}")
            for domain, identifier in device.identifiers
        }
        if identifiers == device.identifiers:
            continue
        try:
            device_registry.async_update_device(device.id, new_identifiers=identifiers)
        except DeviceIdentifierCollisionError:
            _LOGGER.warning("Cannot migrate the identifiers of device %s", device.name)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: IpxConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow removing devices left without entities, like the merged ones."""
    return not async_entries_for_device(
        async_get_entity_registry(hass),
        device_entry.id,
        include_disabled_entities=True,
    )


async def async_unload_entry(hass: HomeAssistant, entry: IpxConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
    return True

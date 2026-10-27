"""Diagnostics support for the GCE IPX800 V5 integration."""

from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import CONF_PUSH_PASSWORD
from .coordinator import IpxConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_PUSH_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IpxConfigEntry
) -> dict[str, Any]:
    """Return the diagnostics of a config entry."""
    coordinator = entry.runtime_data
    ipx = coordinator.ipx
    return {
        "entry": {
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "ipx": {
            "firmware_version": ipx.firmware_version,
            "config": ipx.ipx_config,
            "extensions": ipx.extensions_config,
            "objects": ipx.objects_config,
        },
        "devices": coordinator.devices,
        "data": {
            # The text values are the last codes of the access controls
            key: {**value, "value": REDACTED} if key in coordinator.str_ids else value
            for key, value in coordinator.data.items()
        },
    }

"""Support for IPX800 V5 button."""
import logging
from typing import List

from pypx800v5.const import IPX

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICES, CONF_EXT_TYPE, CONTROLLER, COORDINATOR, DOMAIN
from .tools_ipx_entity import IpxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the IPX800 switches."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["button"]

    entities: List[ButtonEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == IPX:
            entities.append(RebootButton(device, controller, coordinator))

    async_add_entities(entities, True)


class RebootButton(IpxEntity, ButtonEntity):
    """Representation of a IPX Counter as a number entity."""

    async def async_press(self) -> None:
        """Handle the button press."""
        self.ipx.reboot()

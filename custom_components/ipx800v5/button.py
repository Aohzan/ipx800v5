"""Support for IPX800 V5 button."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pypx800v5 import IPX

from .const import CONF_DEVICES, CONF_EXT_TYPE, CONTROLLER, COORDINATOR, DOMAIN
from .entity import IpxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPX800 buttons."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["button"]

    entities: list[ButtonEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == IPX:
            entities.append(RebootButton(device, controller, coordinator))  # noqa: PERF401

    async_add_entities(entities)


class RebootButton(IpxEntity, ButtonEntity):
    """Representation of a reboot IPX button entity."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.ipx.reboot()

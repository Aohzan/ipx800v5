"""Support for IPX800 V5 button."""

import logging

from pypx800v5 import IPX

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_EXT_TYPE
from .coordinator import IpxConfigEntry
from .entity import IpxEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IpxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the IPX800 buttons."""
    coordinator = entry.runtime_data
    controller = coordinator.ipx
    devices = coordinator.devices[Platform.BUTTON]

    entities: list[ButtonEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == IPX:
            entities.append(RebootButton(device, controller, coordinator))

    async_add_entities(entities)


class RebootButton(IpxEntity, ButtonEntity):
    """Representation of a reboot IPX button entity."""

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.ipx.reboot()

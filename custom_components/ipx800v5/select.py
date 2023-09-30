"""Support for IPX800 V5 select."""
from collections.abc import Mapping
import logging
from typing import Any

from pypx800v5 import EXT_XDISPLAY, IPX800, XDisplay

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_DEVICES, CONF_EXT_TYPE, CONTROLLER, COORDINATOR, DOMAIN
from .tools_ipx_entity import IpxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPX800 switches."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["select"]

    entities: list[SelectEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == EXT_XDISPLAY:
            entities.append(XDisplayScreenSelect(device, controller, coordinator))

    async_add_entities(entities, True)


class XDisplayScreenSelect(IpxEntity, SelectEntity):
    """Representation of an X-Display screen select."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the X-Display screen select."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Current screen")
        self.control = XDisplay(ipx, self._ext_number)
        self._attr_icon = "mdi:overscan"

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        return [s.name for s in self.control.screens]

    @property
    def current_option(self) -> str | None:
        """Return the current screen."""
        return self.control.screens[
            self.coordinator.data[self.control.ana_current_screen_id]["value"]
        ].name

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra attributes about current screen."""
        return {
            "type": self.control.screens[
                self.coordinator.data[self.control.ana_current_screen_id]["value"]
            ].type
        }

    async def async_select_option(self, option: str) -> None:
        """Change the current screen."""
        screen = next(s for s in self.control.screens if s.name == option)
        await self.control.set_screen(screen.id)

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await self.control.refresh_screens()
        await super().async_added_to_hass()

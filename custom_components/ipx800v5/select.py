"""Support for IPX800 V5 select."""

from collections.abc import Mapping
import logging
from typing import Any

from pypx800v5 import EXT_XDISPLAY, IPX800, XDisplay

from homeassistant.components.select import SelectEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_EXT_TYPE
from .coordinator import IpxConfigEntry, IpxCoordinator
from .entity import IpxEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IpxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the IPX800 switches."""
    coordinator = entry.runtime_data
    controller = coordinator.ipx
    devices = coordinator.devices[Platform.SELECT]

    entities: list[SelectEntity] = [
        XDisplayScreenSelect(device, controller, coordinator)
        for device in devices
        if device[CONF_EXT_TYPE] == EXT_XDISPLAY
    ]

    async_add_entities(entities)


class XDisplayScreenSelect(IpxEntity, SelectEntity):
    """Representation of an X-Display screen select."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the X-Display screen select."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Current screen",
            translation_key="current_screen",
        )
        self.control = XDisplay(ipx, self._ext_number)

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        return [s.name for s in self.control.screens]

    @property
    def current_option(self) -> str | None:
        """Return the current screen."""
        screen_id = int(
            self.coordinator.data[self.control.ana_current_screen_id]["value"]
        )
        if len(self.control.screens) < screen_id + 1:
            _LOGGER.warning(
                "X-Display current screen #%s is not recognized, please reload the integration to refresh screens, or update if it's persist",
                screen_id,
            )
            return None
        return self.control.screens[screen_id].name

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra attributes about current screen."""
        screen_id = int(
            self.coordinator.data[self.control.ana_current_screen_id]["value"]
        )
        if len(self.control.screens) < screen_id + 1:
            return None
        return {"type": self.control.screens[screen_id].type}

    async def async_select_option(self, option: str) -> None:
        """Change the current screen."""
        screen = next(s for s in self.control.screens if s.name == option)
        await self.control.set_screen(screen.id)
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await self.control.refresh_screens()
        await super().async_added_to_hass()

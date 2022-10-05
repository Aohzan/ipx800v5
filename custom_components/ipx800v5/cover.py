"""Support for IPX800 V5 covers."""
import logging
from typing import Any

from pypx800v5 import IPX800, X4VR
from pypx800v5.const import EXT_X4VR

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
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
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["cover"]

    entities: list[CoverEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == EXT_X4VR:
            entities.append(X4VRCover(device, controller, coordinator))

    async_add_entities(entities, True)


class X4VRCover(IpxEntity, CoverEntity):
    """Representation of a IPX Cover through relay."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the X4VR Cover."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X4VR(ipx, self._ext_number, self._io_number)
        self._attr_device_class = CoverDeviceClass.SHUTTER
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        if self.control.mode in [2, 3]:
            self._attr_supported_features += (
                CoverEntityFeature.CLOSE_TILT | CoverEntityFeature.OPEN_TILT
            )

    @property
    def is_closed(self) -> bool:
        """Return the state."""
        return int(self.coordinator.data[self.control.ana_position_id]["value"]) == 100

    @property
    def current_cover_position(self) -> int:
        """Return the current cover position."""
        return 100 - int(self.coordinator.data[self.control.ana_position_id]["value"])

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        await self.control.open()
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.control.close()
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.control.stop()
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover to a specific position."""
        await self.control.set_position(kwargs[ATTR_POSITION])
        await self.coordinator.async_request_refresh()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        await self.control.open_bso()
        await self.coordinator.async_request_refresh()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        await self.control.close_bso()
        await self.coordinator.async_request_refresh()

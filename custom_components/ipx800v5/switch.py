"""Support for IPX800 V5 switches."""
import logging
from typing import Any

from pypx800v5 import (
    EXT_X8R,
    EXT_XDISPLAY,
    IPX,
    IPX800,
    OBJECT_TEMPO,
    TYPE_IO,
    X8R,
    IPX800OpenColl,
    IPX800Relay,
    Tempo,
    XDisplay,
)

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEVICES,
    CONF_EXT_TYPE,
    CONTROLLER,
    COORDINATOR,
    DOMAIN,
    TYPE_IPX_OPENCOLL,
)
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
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["switch"]

    entities: list[SwitchEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_IO:
            entities.append(IOSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == IPX:
            if device.get(CONF_TYPE) == TYPE_IPX_OPENCOLL:
                entities.append(IpxOpenCollSwitch(device, controller, coordinator))
            else:
                entities.append(IpxSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_X8R:
            entities.append(X8RSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_XDISPLAY:
            entities.append(XDisplayScreenStateSwitch(device, controller, coordinator))
            entities.append(XDisplayScreenLockSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_TEMPO:
            entities.append(TempoEnableSwitch(device, controller, coordinator))

    async_add_entities(entities, True)


class IOSwitch(IpxEntity, SwitchEntity):
    """Representation of a IO value as a switch."""

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self._io_id]["on"] is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.ipx.update_io(self._io_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.ipx.update_io(self._io_id, False)
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        await self.ipx.update_io(self._io_id, True, "toggle")
        await self.coordinator.async_request_refresh()


class IpxSwitch(IpxEntity, SwitchEntity):
    """Representation of a IPX Relay Switch through relay."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800Relay(ipx, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        await self.control.toggle()
        await self.coordinator.async_request_refresh()


class IpxOpenCollSwitch(IpxEntity, SwitchEntity):
    """Representation of a IPX Open Collector Switch through relay."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800OpenColl(ipx, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        await self.control.toggle()
        await self.coordinator.async_request_refresh()


class X8RSwitch(IpxEntity, SwitchEntity):
    """Representation of a X-8R Switch through relay."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X8R(ipx, self._ext_number, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        await self.control.toggle()
        await self.coordinator.async_request_refresh()


class XDisplayScreenStateSwitch(IpxEntity, SwitchEntity):
    """Representation of a X-Display screen state switch."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Screen state")
        self.control = XDisplay(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_on_screen_id]["on"] is not True

    @property
    def icon(self) -> str:
        """Return icon according to state."""
        if self.is_on:
            return "mdi:television"
        return "mdi:television-off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.control.screen_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.control.screen_off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        await self.control.screen_toggle()
        await self.coordinator.async_request_refresh()


class XDisplayScreenLockSwitch(IpxEntity, SwitchEntity):
    """Representation of a X-Display screen lock switch."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Screen lock")
        self.control = XDisplay(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_lock_screen_id]["on"] is True

    @property
    def icon(self) -> str:
        """Return icon according to state."""
        if self.is_on:
            return "mdi:lock"
        return "mdi:lock-open-variant"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.control.screen_lock()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.control.screen_unlock()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch."""
        await self.control.screen_toggle_lock()
        await self.coordinator.async_request_refresh()


class TempoEnableSwitch(IpxEntity, SwitchEntity):
    """Representation of a enable tempo as a switch."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Enable")
        self.control = Tempo(ipx, self._ext_number)
        self._attr_icon = "mdi:toggle-switch"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_enabled_id]["on"] is True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

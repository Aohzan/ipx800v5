"""Support for IPX800 V5 switches."""

import logging
from typing import Any

from pypx800v5 import (
    EXT_X8R,
    EXT_XDISPLAY,
    IPX,
    IPX800,
    OBJECT_TEMPO,
    OBJECT_THERMOSTAT,
    TYPE_IO,
    X8R,
    IPX800OpenColl,
    IPX800Relay,
    Tempo,
    Thermostat,
    XDisplay,
)

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_TYPE, EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_EXT_TYPE, TYPE_IPX_OPENCOLL
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
    devices = coordinator.devices[Platform.SWITCH]

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
        elif device[CONF_EXT_TYPE] == OBJECT_THERMOSTAT:
            entities.append(
                ThermostatCoolingModeSwitch(device, controller, coordinator)
            )

    async_add_entities(entities)


class IOSwitch(IpxEntity, SwitchEntity):
    """Representation of a IO value as a switch."""

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self._io_id]["on"] is True  # type: ignore[index]

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
        coordinator: IpxCoordinator,
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
        coordinator: IpxCoordinator,
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
        coordinator: IpxCoordinator,
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
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Screen state",
            translation_key="screen_state",
        )
        self.control = XDisplay(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_on_screen_id]["on"] is not True

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
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Screen lock",
            translation_key="screen_lock",
        )
        self.control = XDisplay(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.data[self.control.io_lock_screen_id]["on"] is True

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
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Enable",
            translation_key="tempo_enable",
        )
        self.control = Tempo(ipx, self._ext_number)
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


class ThermostatCoolingModeSwitch(IpxEntity, SwitchEntity):
    """Representation of the thermostat inverted output, to drive a cooling device."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Cooling Mode",
            translation_key="cooling_mode",
        )
        self.control = Thermostat(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return if the thermostat output is inverted."""
        return self.control.inverted_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Invert the thermostat output to drive a cooling device."""
        await self._async_set_inverted_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Restore the thermostat output to drive a heating device."""
        await self._async_set_inverted_mode(False)

    async def _async_set_inverted_mode(self, inverted: bool) -> None:
        """Update the thermostat inverted mode."""
        await self.control.update_params(invMode=inverted)
        self.async_write_ha_state()
        # The thermostat climate entity reads it to show the heat or cool mode
        await self.coordinator.async_request_refresh()

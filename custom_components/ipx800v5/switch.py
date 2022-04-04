"""Support for IPX800 V5 switches."""
import logging

from pypx800v5 import IPX800, X8R, IPX800Relay, Tempo
from pypx800v5.const import EXT_X8R, IPX, OBJECT_TEMPO, TYPE_IO

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["switch"]

    entities: list[SwitchEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_IO:
            entities.append(IOSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == IPX:
            entities.append(IpxSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_X8R:
            entities.append(X8RSwitch(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_TEMPO:
            entities.append(TempoEnableSwitch(device, controller, coordinator))

    async_add_entities(entities, True)


class IOSwitch(IpxEntity, SwitchEntity):
    """Representation of a IO value as a switch."""

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self._io_id]["on"] is True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        await self.ipx.update_io(self._io_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        await self.ipx.update_io(self._io_id, False)
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs) -> None:
        """Toggle the switch."""
        await self.ipx.update_io(self._io_id, True, "toggle")
        await self.coordinator.async_request_refresh()


class IpxSwitch(IpxEntity, SwitchEntity):
    """Representation of a IPX Switch through relay."""

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

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs) -> None:
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

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs) -> None:
        """Toggle the switch."""
        await self.control.toggle()
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

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

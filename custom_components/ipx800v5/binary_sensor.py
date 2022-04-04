"""Support for IPX800 V5 binary sensors."""
import logging

from pypx800v5 import IPX800, X8D, X8R, X24D, IPX800DigitalInput, Tempo, Thermostat
from pypx800v5.const import (
    EXT_X8D,
    EXT_X8R,
    EXT_X24D,
    IPX,
    OBJECT_TEMPO,
    OBJECT_THERMOSTAT,
    TYPE_IO,
)

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
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
    """Set up the IPX800 sensors."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["binary_sensor"]

    entities: list[BinarySensorEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_IO:
            entities.append(IOBinarySensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == IPX:
            entities.append(
                IpxDigitalInputBinarySensor(device, controller, coordinator)
            )
        elif device[CONF_EXT_TYPE] == EXT_X8R:
            entities.append(X8RLongPushBinarySensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_X24D:
            entities.append(X24DBinarySensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_X8D:
            entities.append(X8DBinarySensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_TEMPO:
            entities.append(TempoStateBinarySensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_THERMOSTAT:
            entities.append(
                ThermostatFaultStateBinarySensor(device, controller, coordinator)
            )

    async_add_entities(entities, True)


class IOBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a IO value as a binary sensor."""

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self._io_id]["on"] is True


class IpxDigitalInputBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a IPX digital input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the digital input sensor of the IPX800."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800DigitalInput(ipx, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class X24DBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a X24D digital input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the digital input sensor of the X-24D."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X24D(ipx, self._ext_number, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class X8DBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a X8D digital input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the digital input sensor of the X-8D."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X8D(ipx, self._ext_number, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class TempoStateBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation the tempo state as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the sensor of the tempo."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Tempo(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class X8RLongPushBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a X8R long push as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the long push sensor of the X-8R."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Long Push")
        self.control = X8R(ipx, self._ext_number, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_longpush_id]["on"] is True


class ThermostatFaultStateBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation the thermostat error state as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the sensor of the tempo."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Fault")
        self.control = Thermostat(ipx, self._ext_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_fault_id]["on"] is True

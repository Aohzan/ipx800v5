"""Support for IPX800 V5 binary sensors."""

import logging

from pypx800v5 import (
    EXT_X8D,
    EXT_X8R,
    EXT_X24D,
    IPX,
    IPX800,
    OBJECT_ACCESS_CONTROL,
    OBJECT_TEMPO,
    OBJECT_THERMOSTAT,
    TYPE_IO,
    X8D,
    X8R,
    X24D,
    AccessControl,
    IPX800DigitalInput,
    IPX800OptoInput,
    Tempo,
    Thermostat,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_TYPE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_EXT_TYPE, TYPE_IPX_OPTO
from .coordinator import IpxConfigEntry, IpxCoordinator
from .entity import IpxEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IpxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the IPX800 sensors."""
    coordinator = entry.runtime_data
    controller = coordinator.ipx
    devices = coordinator.devices[Platform.BINARY_SENSOR]

    entities: list[BinarySensorEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_IO:
            entities.append(IOBinarySensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == IPX:
            if device.get(CONF_TYPE) == TYPE_IPX_OPTO:
                entities.append(
                    IpxOptoInputBinarySensor(device, controller, coordinator)
                )
            else:
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
        elif device[CONF_EXT_TYPE] == OBJECT_ACCESS_CONTROL:
            entities.append(
                AccessControlBinarySensor(
                    device_config=device,
                    coordinator=coordinator,
                    ipx=controller,
                    id_name="io_out_id",
                    suffix_name="Success",
                    translation_key="access_success",
                    device_class=BinarySensorDeviceClass.LOCK,
                )
            )
            entities.append(
                AccessControlBinarySensor(
                    device_config=device,
                    coordinator=coordinator,
                    ipx=controller,
                    id_name="io_fault_id",
                    suffix_name="Fail",
                    translation_key="access_fail",
                    device_class=BinarySensorDeviceClass.SAFETY,
                )
            )

    async_add_entities(entities)


class IOBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a IO value as a binary sensor."""

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.io_id]["on"] is True


class IpxDigitalInputBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a IPX digital input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the digital input sensor of the IPX800."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800DigitalInput(ipx, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class IpxOptoInputBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a IPX Opto input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the opto input sensor of the IPX800."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800OptoInput(ipx, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class X24DBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a X24D digital input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the digital input sensor of the X-24D."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X24D(ipx, self._ext_number, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class X8DBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation of a X8D digital input as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the digital input sensor of the X-8D."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X8D(ipx, self._ext_number, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_state_id]["on"] is True


class TempoStateBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation the tempo state as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
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
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the long push sensor of the X-8R."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Long Push",
            translation_key="long_push",
        )
        self.control = X8R(ipx, self._ext_number, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_longpush_id]["on"] is True


class ThermostatFaultStateBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation the thermostat error state as a binary sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the sensor of the tempo."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Fault",
            translation_key="fault",
        )
        self.control = Thermostat(ipx, self._ext_number)
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[self.control.io_fault_id]["on"] is True


class AccessControlBinarySensor(IpxEntity, BinarySensorEntity):
    """Representation the Access Control state as a binary sensor."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
        id_name: str,
        suffix_name: str,
        translation_key: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        """Initialize the sensor of the access control."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name=suffix_name,
            translation_key=translation_key,
        )
        self.control = AccessControl(ipx, self._ext_number)
        self._attr_device_class = device_class
        self._id_name = id_name

    @property
    def is_on(self) -> bool:
        """Return the current value."""
        return self.coordinator.data[getattr(self.control, self._id_name)]["on"] is True

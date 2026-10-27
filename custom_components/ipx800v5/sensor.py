"""Support for IPX800 V5 sensors."""

import logging

import pypx800v5
from pypx800v5 import (
    EXT_X400,
    EXT_XDISPLAY,
    EXT_XTHL,
    IPX,
    IPX800,
    OBJECT_ACCESS_CONTROL,
    TYPE_ANA,
    X400,
    XTHL,
    IPX800AnalogInput,
    XDisplay,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_TYPE,
    LIGHT_LUX,
    EntityCategory,
    Platform,
    UnitOfElectricCurrent,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

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
    """Set up the IPX800 sensors."""
    coordinator = entry.runtime_data
    controller = coordinator.ipx
    devices = coordinator.devices[Platform.SENSOR]

    entities: list[SensorEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_ANA:
            entities.append(AnalogSensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == IPX:
            entities.append(IpxAnalogInputSensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_XTHL:
            entities.append(
                XTHLSensor(
                    device,
                    controller,
                    coordinator,
                    SensorDeviceClass.TEMPERATURE,
                    UnitOfTemperature.CELSIUS,
                    "TEMP",
                    "Temperature",
                    device[CONF_NAME],
                )
            )
            entities.append(
                XTHLSensor(
                    device,
                    controller,
                    coordinator,
                    SensorDeviceClass.HUMIDITY,
                    UnitOfRatio.PERCENTAGE,
                    "HUM",
                    "Humidity",
                    device[CONF_NAME],
                )
            )
            entities.append(
                XTHLSensor(
                    device,
                    controller,
                    coordinator,
                    SensorDeviceClass.ILLUMINANCE,
                    LIGHT_LUX,
                    "LUM",
                    "Luminance",
                    device[CONF_NAME],
                )
            )
        elif device[CONF_EXT_TYPE] == EXT_X400:
            entities.append(X400Sensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_XDISPLAY:
            entities.append(XDisplayAutoOffSensor(device, controller, coordinator))
            entities.append(XDisplaySensitiveSensor(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_ACCESS_CONTROL:
            entities.append(
                GenericAnalogSensor(
                    device,
                    controller,
                    coordinator,
                    pypx_object_name="AccessControl",
                    pypx_property_name="str_last_code_id",
                )
            )
    async_add_entities(entities)


class GenericAnalogSensor(IpxEntity, SensorEntity):
    """Representation of a generic analog sensor."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
        pypx_object_name: str,
        pypx_property_name: str,
        device_class: SensorDeviceClass | None = None,
    ) -> None:
        """Initialize the analog sensor."""
        super().__init__(device_config, ipx, coordinator)
        pypx_object = getattr(pypx800v5, pypx_object_name)
        self.control = pypx_object(ipx, self._ext_number)
        self._pypx_property_name = pypx_property_name
        self._attr_device_class = device_class

    @property
    def native_value(self) -> StateType:
        """Return the current value."""
        return self.coordinator.data[getattr(self.control, self._pypx_property_name)][
            "value"
        ]


class AnalogSensor(IpxEntity, SensorEntity):
    """Representation of an analog as a sensor."""

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data[self._io_id]["value"]  # type: ignore[index]


class IpxAnalogInputSensor(IpxEntity, SensorEntity):
    """Representation of a IPX analog input as a sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the analog input sensor of the IPX800."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800AnalogInput(ipx, self._io_number)

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data[self.control.ana_state_id]["value"]


class XTHLSensor(IpxEntity, SensorEntity):
    """Representation of a X-THL sensor."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
        device_class: SensorDeviceClass,
        unit_of_measurement: str,
        req_type: str,
        suffix_name: str,
        device_name: str,
    ) -> None:
        """Initialize the X-THL sensor."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name=suffix_name,
            device_name=device_name,
            translation_key=suffix_name.lower(),
        )
        self.control = XTHL(ipx, self._ext_number)
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_state_class = SensorStateClass.MEASUREMENT
        if req_type == "TEMP":
            self._state_id = self.control.temp_state_id
        elif req_type == "HUM":
            self._state_id = self.control.hum_state_id
        elif req_type == "LUM":
            self._state_id = self.control.lum_state_id

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return round(self.coordinator.data[self._state_id]["value"], 1)


class X400Sensor(IpxEntity, SensorEntity):
    """Representation of a X-400 input, current clamp (CT) or analog sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the X-400 sensor."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X400(ipx, self._ext_number, self._io_number)
        if self.control.is_current_clamp:
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
            self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data[self.control.ana_value_id]["value"]


class XDisplayAutoOffSensor(IpxEntity, SensorEntity):
    """Representation of a X-Display auto off sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Auto off",
            translation_key="auto_off",
        )
        self.control = XDisplay(ipx, self._ext_number)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.control.autoOff


class XDisplaySensitiveSensor(IpxEntity, SensorEntity):
    """Representation of a X-Display sensitivity sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: IpxCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Sensitive",
            translation_key="sensitive",
        )
        self.control = XDisplay(ipx, self._ext_number)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.control.sensitive

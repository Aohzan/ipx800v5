"""Support for IPX800 V5 sensors."""
import logging

from pypx800v5 import (
    EXT_XDISPLAY,
    EXT_XTHL,
    IPX,
    IPX800,
    TYPE_ANA,
    XTHL,
    IPX800AnalogInput,
    XDisplay,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_TYPE,
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)
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
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["sensor"]

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
                    PERCENTAGE,
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
        elif device[CONF_EXT_TYPE] == EXT_XDISPLAY:
            entities.append(XDisplayAutoOffSensor(device, controller, coordinator))
            entities.append(XDisplaySensitiveSensor(device, controller, coordinator))
    async_add_entities(entities, True)


class AnalogSensor(IpxEntity, SensorEntity):
    """Representation of an analog as a sensor."""

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.data[self._io_id]["value"]


class IpxAnalogInputSensor(IpxEntity, SensorEntity):
    """Representation of a IPX analog input as a sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
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
        coordinator: DataUpdateCoordinator,
        device_class: SensorDeviceClass,
        unit_of_measurement: str,
        req_type: str,
        suffix_name: str,
        device_name: str,
    ) -> None:
        """Initialize the X-THL sensor."""
        super().__init__(device_config, ipx, coordinator, suffix_name, device_name)
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


class XDisplayAutoOffSensor(IpxEntity, SensorEntity):
    """Representation of a X-Display auto off sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Auto off")
        self.control = XDisplay(ipx, self._ext_number)
        self._attr_icon = "mdi:timer"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.control.autoOff


class XDisplaySensitiveSensor(IpxEntity, SensorEntity):
    """Representation of a X-Display auto off sensor."""

    def __init__(
        self, device_config: dict, ipx: IPX800, coordinator: DataUpdateCoordinator
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Sensitive")
        self.control = XDisplay(ipx, self._ext_number)
        self._attr_icon = "mdi:fingerprint"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.control.sensitive

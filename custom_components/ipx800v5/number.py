"""Support for IPX800 V5 numbers."""

import logging

from pypx800v5 import (
    IPX800,
    OBJECT_COUNTER,
    OBJECT_TEMPO,
    OBJECT_THERMOSTAT,
    TYPE_ANA,
    Counter,
    Tempo,
    Thermostat,
)

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import (
    CONF_TYPE,
    EntityCategory,
    Platform,
    UnitOfTemperature,
    UnitOfTime,
)
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
    devices = coordinator.devices[Platform.NUMBER]

    entities: list[NumberEntity] = []

    for device in devices:
        if device.get(CONF_TYPE) == TYPE_ANA:
            entities.append(AnalogNumber(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_COUNTER:
            entities.append(CounterNumber(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_THERMOSTAT:
            entities.append(
                ThermostatParamNumber(device, controller, coordinator, param="Comfort")
            )
            entities.append(
                ThermostatParamNumber(device, controller, coordinator, param="Eco")
            )
            entities.append(
                ThermostatParamNumber(device, controller, coordinator, param="NoFrost")
            )
        elif device[CONF_EXT_TYPE] == OBJECT_TEMPO:
            entities.append(TempoDelayNumber(device, controller, coordinator))

    async_add_entities(entities)


class AnalogNumber(IpxEntity, NumberEntity):
    """Representation of an analog as a number."""

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return float(self.coordinator.data[self.io_id]["value"])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.ipx.update_ana(self.io_id, value)
        await self.coordinator.async_request_refresh()


class CounterNumber(IpxEntity, NumberEntity):
    """Representation of a IPX Counter as a number entity."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = -21474836
    _attr_native_max_value = 21474836

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Counter(ipx, self._ext_number)

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return float(self.coordinator.data[self.control.ana_state_id]["value"])

    @property
    def native_step(self) -> float:
        """Return the step value."""
        return float(self.coordinator.data[self.control.ana_step_id]["value"])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.control.set_value(value)
        await self.coordinator.async_request_refresh()


class ThermostatParamNumber(IpxEntity, NumberEntity):
    """Representation of a IPX Counter as a number entity."""

    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 35
    _attr_native_step = 0.1
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
        param: str,
    ) -> None:
        """Initialize the ThermostatParamNumber."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name=f"{param} Temperature",
            translation_key=f"{param.lower()}_temperature",
        )
        self.control = Thermostat(ipx, self._ext_number)
        self._param = param
        self._value = self.control.init_config[f"setPoint{param}"]

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if self._param == "Comfort":
            await self.control.update_params(comfortTemp=value)
        elif self._param == "Eco":
            await self.control.update_params(ecoTemp=value)
        elif self._param == "NoFrost":
            await self.control.update_params(noFrostTemp=value)
        self._value = value
        self.async_write_ha_state()


class TempoDelayNumber(IpxEntity, NumberEntity):
    """Representation of a Tempo delay as a number entity."""

    _attr_native_min_value = 0
    _attr_native_max_value = 36000
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            device_config,
            ipx,
            coordinator,
            suffix_name="Delay",
            translation_key="tempo_delay",
        )
        self.control = Tempo(ipx, self._ext_number)

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return int(self.coordinator.data[self.control.ana_time_id]["value"])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.control.set_time(int(value))
        await self.coordinator.async_request_refresh()

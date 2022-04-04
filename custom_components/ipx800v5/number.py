"""Support for IPX800 V5 numbers."""
import logging

from pypx800v5 import IPX800, Counter, Tempo, Thermostat
from pypx800v5.const import OBJECT_COUNTER, OBJECT_TEMPO, OBJECT_THERMOSTAT, TYPE_ANA

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE, DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS
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
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["number"]

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

    async_add_entities(entities, True)


class AnalogNumber(IpxEntity, NumberEntity):
    """Representation of an analog as a number."""

    @property
    def native_value(self):
        """Return the current value."""
        return self.coordinator.data[self._io_id]["value"]

    async def async_set_value(self, value) -> None:
        """Update the current value."""
        await self.ipx.update_ana(self._io_id, value)


class CounterNumber(IpxEntity, NumberEntity):
    """Representation of a IPX Counter as a number entity."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Counter(ipx, self._ext_number)
        self._attr_mode = NumberMode.BOX
        self._attr_min_value = -21474836
        self._attr_max_value = 21474836

    @property
    def value(self) -> float:
        """Return the current value."""
        return float(self.coordinator.data[self.control.ana_state_id]["value"])

    @property
    def step(self) -> float:
        """Return the step value."""
        return float(self.coordinator.data[self.control.ana_step_id]["value"])

    async def async_set_value(self, value: float) -> None:
        """Update the current value."""
        await self.control.set_value(value)


class ThermostatParamNumber(IpxEntity, NumberEntity):
    """Representation of a IPX Counter as a number entity."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
        param: str,
    ) -> None:
        """Initialize the RelaySwitch."""
        super().__init__(
            device_config, ipx, coordinator, suffix_name=f"{param} Temperature"
        )
        self.control = Thermostat(ipx, self._ext_number)
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_class = DEVICE_CLASS_TEMPERATURE
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._param = param
        self._value = self.control._config[f"setPoint{param}"]
        self._attr_mode = NumberMode.BOX
        self._attr_min_value = 0
        self._attr_max_value = 35
        self._attr_step = 0.1

    @property
    def value(self) -> float:
        """Return the current value."""
        return self._value

    async def async_set_value(self, value: float) -> None:
        """Update the current value."""
        if self._param == "Comfort":
            await self.control.update_params(comfortTemp=value)
        elif self._param == "Eco":
            await self.control.update_params(ecoTemp=value)
        elif self._param == "NoFrost":
            await self.control.update_params(noFrostTemp=value)
        self._value = value


class TempoDelayNumber(IpxEntity, NumberEntity):
    """Representation of a Tempo delay as a number entity."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        super().__init__(device_config, ipx, coordinator, suffix_name="Delay")
        self.control = Tempo(ipx, self._ext_number)
        self._attr_min_value = 0
        self._attr_max_value = 36000
        self._attr_step = 1
        self._attr_unit_of_measurement = "s"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:clock-time-two"

    @property
    def value(self) -> int:
        """Return the current value."""
        return int(self.coordinator.data[self.control.ana_time_id]["value"])

    async def async_set_value(self, value: float) -> None:
        """Update the current value."""
        await self.control.set_time(value)

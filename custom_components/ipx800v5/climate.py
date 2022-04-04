"""Support for IPX800 V5 climates."""
import logging

from pypx800v5 import IPX800, X4FP, X8R, IPX800Relay, Thermostat, X4FPMode
from pypx800v5.const import EXT_X4FP, EXT_X8R, IPX, OBJECT_THERMOSTAT

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
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
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["climate"]

    entities: list[ClimateEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == EXT_X4FP:
            entities.append(X4FPClimate(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] in [IPX, EXT_X8R]:
            entities.append(RelayClimate(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == OBJECT_THERMOSTAT:
            entities.append(ThermostatClimate(device, controller, coordinator))

    async_add_entities(entities, True)


class X4FPClimate(IpxEntity, ClimateEntity):
    """Representation of a IPX Climate through X4FP."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the X4FPClimate."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X4FP(ipx, self._ext_number, self._io_number)

        self._attr_supported_features = ClimateEntityFeature.PRESET_MODE
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
        self._attr_preset_modes = [
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_NONE,
            f"{PRESET_COMFORT} -1",
            f"{PRESET_COMFORT} -2",
        ]

    @property
    def _mode(self) -> X4FPMode:
        """Return the current mode enabled."""
        if self.coordinator.data[self.control.io_stop_id] == "on":
            return X4FPMode.STOP
        if self.coordinator.data[self.control.io_eco_id] == "on":
            return X4FPMode.ECO
        if self.coordinator.data[self.control.io_comfort_id] == "on":
            return X4FPMode.COMFORT
        if self.coordinator.data[self.control.io_comfort_1_id] == "on":
            return X4FPMode.COMFORT_1
        if self.coordinator.data[self.control.io_comfort_2_id] == "on":
            return X4FPMode.COMFORT_2
        if self.coordinator.data[self.control.io_anti_freeze_id] == "on":
            return X4FPMode.ANTIFREEZE

    @property
    def hvac_mode(self):
        """Return current mode if heating or not."""
        if self._mode == X4FPMode.STOP:
            return HVAC_MODE_OFF
        return HVAC_MODE_HEAT

    @property
    def hvac_action(self):
        """Return current action if heating or not."""
        if self._mode == X4FPMode.STOP:
            return CURRENT_HVAC_OFF
        return CURRENT_HVAC_HEAT

    @property
    def preset_mode(self):
        """Return current preset mode."""
        switcher = {
            X4FPMode.STOP: PRESET_NONE,
            X4FPMode.ECO: PRESET_ECO,
            X4FPMode.ANTIFREEZE: PRESET_AWAY,
            X4FPMode.COMFORT: PRESET_COMFORT,
            X4FPMode.COMFORT_1: f"{PRESET_COMFORT} -1",
            X4FPMode.COMFORT_2: f"{PRESET_COMFORT} -2",
        }
        return switcher.get(self._mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target preset mode."""
        switcher = {
            PRESET_COMFORT: X4FPMode.COMFORT,
            PRESET_ECO: X4FPMode.ECO,
            PRESET_AWAY: X4FPMode.ANTIFREEZE,
            PRESET_NONE: X4FPMode.STOP,
            f"{PRESET_COMFORT} -1": X4FPMode.COMFORT_1,
            f"{PRESET_COMFORT} -2": X4FPMode.COMFORT_2,
        }
        await self.control.set_mode(switcher.get(preset_mode))
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            await self.control.set_mode(X4FPMode.COMFORT)
        elif hvac_mode == HVAC_MODE_OFF:
            await self.control.set_mode(X4FPMode.STOP)
        await self.coordinator.async_request_refresh()


class RelayClimate(IpxEntity, ClimateEntity):
    """Representation of a IPX Climate through 2 relais."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelayClimate."""
        super().__init__(device_config, ipx, coordinator)
        if device_config[CONF_EXT_TYPE] == IPX:
            self.control_minus = IPX800Relay(ipx, self._io_numbers[0])
            self.control_plus = IPX800Relay(ipx, self._io_numbers[1])
        elif device_config[CONF_EXT_TYPE] == EXT_X8R:
            self.control_minus = X8R(ipx, self._ext_number, self._io_numbers[0])
            self.control_plus = X8R(ipx, self._ext_number, self._io_numbers[1])
        self._attr_supported_features = ClimateEntityFeature.PRESET_MODE
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
        self._attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, PRESET_NONE]

    @property
    def hvac_mode(self):
        """Return current mode if heating or not."""
        if (
            self.coordinator.data[self.control_minus.io_state_id]["on"] is False
            and self.coordinator.data[self.control_plus.io_state_id]["on"] is True
        ):
            return HVAC_MODE_OFF
        return HVAC_MODE_HEAT

    @property
    def hvac_action(self):
        """Return current action if heating or not."""
        if (
            self.coordinator.data[self.control_minus.io_state_id]["on"] is False
            and self.coordinator.data[self.control_plus.io_state_id]["on"] is True
        ):
            return CURRENT_HVAC_OFF
        return CURRENT_HVAC_HEAT

    @property
    def preset_mode(self):
        """Return current preset mode from 2 relay states."""
        state_minus = (
            self.coordinator.data[self.control_minus.io_state_id]["on"] is True
        )
        state_plus = self.coordinator.data[self.control_plus.io_state_id]["on"] is True
        switcher = {
            (False, False): PRESET_COMFORT,
            (False, True): PRESET_NONE,
            (True, False): PRESET_AWAY,
            (True, True): PRESET_ECO,
        }
        return switcher.get((state_minus, state_plus))

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            await self.control_minus.off()
            await self.control_plus.off()
        elif hvac_mode == HVAC_MODE_OFF:
            await self.control_minus.off()
            await self.control_plus.on()
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set target preset mode."""
        if preset_mode == PRESET_COMFORT:
            await self.control_minus.off()
            await self.control_plus.off()
        elif preset_mode == PRESET_ECO:
            await self.control_minus.on()
            await self.control_plus.on()
        elif preset_mode == PRESET_AWAY:
            await self.control_minus.on()
            await self.control_plus.off()
        else:
            await self.control_minus.off()
            await self.control_plus.on()
        await self.coordinator.async_request_refresh()


class ThermostatClimate(IpxEntity, ClimateEntity):
    """Representation of a IPX Thermostat."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the IPX800 thermostat."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Thermostat(ipx, self._ext_number)

        self._attr_target_temperature_step = 0.1
        self._attr_supported_features = (
            ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TARGET_TEMPERATURE
        )
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
        self._attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, PRESET_NONE]

    @property
    def current_temperature(self):
        """Get current temperature."""
        return float(self.coordinator.data[self.control.ana_measure_id]["value"])

    @property
    def target_temperature(self):
        """Get target temperature."""
        return float(self.coordinator.data[self.control.ana_consigne_id]["value"])

    @property
    def hvac_mode(self):
        """Return current mode if heating or not."""
        if self.coordinator.data[self.control.io_onoff_id]["on"] is True:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def hvac_action(self):
        """Return current action if heating or not."""
        if self.coordinator.data[self.control.io_state_id]["on"] is True:
            return CURRENT_HVAC_HEAT
        if self.coordinator.data[self.control.io_onoff_id]["on"] is False:
            return CURRENT_HVAC_OFF
        return CURRENT_HVAC_IDLE

    @property
    def preset_mode(self):
        """Return current preset mode from 2 relay states."""
        if self.coordinator.data[self.control.io_comfort_id]["on"] is True:
            return PRESET_COMFORT
        if self.coordinator.data[self.control.io_eco_id]["on"] is True:
            return PRESET_ECO
        if self.coordinator.data[self.control.io_nofrost_id]["on"] is True:
            return PRESET_AWAY
        if self.coordinator.data[self.control.io_onoff_id]["on"] is False:
            return PRESET_NONE

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        await self.control.set_target_temperature(kwargs[ATTR_TEMPERATURE])

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            await self.control.on()
            await self.control.set_mode_comfort()
        elif hvac_mode == HVAC_MODE_OFF:
            await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set target preset mode."""
        if preset_mode == PRESET_COMFORT:
            await self.control.on()
            await self.control.set_mode_comfort()
        elif preset_mode == PRESET_ECO:
            await self.control.on()
            await self.control.set_mode_eco()
        elif preset_mode == PRESET_AWAY:
            await self.control.on()
            await self.control.set_mode_nofrost()
        else:
            await self.control.off()
        await self.coordinator.async_request_refresh()

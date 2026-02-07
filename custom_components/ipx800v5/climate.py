"""Support for IPX800 V5 climates."""

import logging
from typing import Any

from pypx800v5 import (
    EXT_X4FP,
    EXT_X8R,
    IPX,
    IPX800,
    OBJECT_THERMOSTAT,
    X4FP,
    X8R,
    IPX800Relay,
    Thermostat,
    X4FPMode,
)

from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEVICES,
    CONF_EXT_TYPE,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP_STEP,
    CONTROLLER,
    COORDINATOR,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_TARGET_TEMP_STEP,
    DOMAIN,
)
from .entity import IpxEntity

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

    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _enable_turn_on_off_backwards_compatibility = False
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = [
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_AWAY,
        PRESET_NONE,
        f"{PRESET_COMFORT} -1",
        f"{PRESET_COMFORT} -2",
    ]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the X4FPClimate."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X4FP(ipx, self._ext_number, self._io_number)

    @property
    def _mode(self) -> X4FPMode:
        """Return the current mode enabled."""
        if self.coordinator.data[self.control.io_eco_id]["on"] is True:
            return X4FPMode.ECO
        if self.coordinator.data[self.control.io_comfort_id]["on"] is True:
            return X4FPMode.COMFORT
        if self.coordinator.data[self.control.io_comfort_1_id]["on"] is True:
            return X4FPMode.COMFORT_1
        if self.coordinator.data[self.control.io_comfort_2_id]["on"] is True:
            return X4FPMode.COMFORT_2
        if self.coordinator.data[self.control.io_anti_freeze_id]["on"] is True:
            return X4FPMode.ANTIFREEZE
        if self.coordinator.data[self.control.io_stop_id]["on"] is True:
            return X4FPMode.STOP
        _LOGGER.warning("The X4FP doesn't return a known mode, set to stop by default")
        return X4FPMode.STOP

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current mode if heating or not."""
        if self._mode == X4FPMode.STOP:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        """Return current action if heating or not."""
        if self._mode == X4FPMode.STOP:
            return HVACAction.OFF
        return HVACAction.HEATING

    @property
    def preset_mode(self) -> str:
        """Return current preset mode."""
        switcher = {
            X4FPMode.STOP: PRESET_NONE,
            X4FPMode.ECO: PRESET_ECO,
            X4FPMode.ANTIFREEZE: PRESET_AWAY,
            X4FPMode.COMFORT: PRESET_COMFORT,
            X4FPMode.COMFORT_1: f"{PRESET_COMFORT} -1",
            X4FPMode.COMFORT_2: f"{PRESET_COMFORT} -2",
        }
        return switcher[self._mode]

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

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            await self.control.set_mode(X4FPMode.COMFORT)
        elif hvac_mode == HVACMode.OFF:
            await self.control.set_mode(X4FPMode.STOP)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)


class RelayClimate(IpxEntity, ClimateEntity):
    """Representation of a IPX Climate through 2 relais."""

    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _enable_turn_on_off_backwards_compatibility = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, PRESET_NONE]

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

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current mode if heating or not."""
        if (
            self.coordinator.data[self.control_minus.io_state_id]["on"] is False
            and self.coordinator.data[self.control_plus.io_state_id]["on"] is True
        ):
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        """Return current action if heating or not."""
        if (
            self.coordinator.data[self.control_minus.io_state_id]["on"] is False
            and self.coordinator.data[self.control_plus.io_state_id]["on"] is True
        ):
            return HVACAction.OFF
        return HVACAction.HEATING

    @property
    def preset_mode(self) -> str:
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
        return switcher[(state_minus, state_plus)]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            await self.control_minus.off()
            await self.control_plus.off()
        elif hvac_mode == HVACMode.OFF:
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

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)


class ThermostatClimate(IpxEntity, ClimateEntity):
    """Representation of a IPX Thermostat."""

    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _enable_turn_on_off_backwards_compatibility = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_AWAY, PRESET_NONE]

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the IPX800 thermostat."""
        super().__init__(device_config, ipx, coordinator)
        self.control = Thermostat(ipx, self._ext_number)
        
        # min_temp is NEVER configurable - always read from IPX800 NoFrost for safety
        # max_temp and target_temp_step can be configured in YAML or use defaults
        self._config_max_temp = device_config.get(CONF_MAX_TEMP)
        self._config_target_temp_step = device_config.get(CONF_TARGET_TEMP_STEP)
        
        _LOGGER.info(
            "Thermostat %s initialized - min_temp=NoFrost (dynamic), max_temp=%s, step=%s",
            self._attr_name,
            self._config_max_temp or DEFAULT_MAX_TEMP,
            self._config_target_temp_step or DEFAULT_TARGET_TEMP_STEP,
        )

    def _get_nofrost_temp(self) -> float | None:
        """Get NoFrost temperature from IPX800 config."""
        try:
            ipx_config = self.control.init_config
            if ipx_config and "setPointNoFrost" in ipx_config:
                nofrost = float(ipx_config["setPointNoFrost"])
                _LOGGER.debug(
                    "Thermostat %s - Read NoFrost from IPX800: %s°C",
                    self._attr_name,
                    nofrost,
                )
                return nofrost
        except (AttributeError, KeyError, ValueError, TypeError) as err:
            _LOGGER.debug(
                "Could not read NoFrost from IPX800 for %s: %s",
                self._attr_name,
                err,
            )
        return None

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature - ALWAYS read from IPX800 NoFrost (safety)."""
        # min_temp is NEVER configurable in YAML - always synchronized with IPX800 NoFrost
        # This ensures safety: the minimum temperature in HA matches the anti-freeze setting
        nofrost = self._get_nofrost_temp()
        if nofrost is not None:
            return nofrost
        # Fallback to safe default if NoFrost cannot be read
        _LOGGER.warning(
            "Could not read NoFrost from IPX800 for %s, using default min_temp=%s",
            self._attr_name,
            DEFAULT_MIN_TEMP,
        )
        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature - configurable in YAML or default."""
        # max_temp has no equivalent in IPX800
        # User can configure it in YAML or we use a reasonable default (22°C)
        return self._config_max_temp or DEFAULT_MAX_TEMP

    @property
    def target_temperature_step(self) -> float:
        """Return the target temperature step - configurable in YAML or default."""
        # target_temp_step has no equivalent in IPX800
        # User can configure it in YAML or we use 0.5°C (more practical than 0.1°C)
        return self._config_target_temp_step or DEFAULT_TARGET_TEMP_STEP

    @property
    def current_temperature(self) -> float:
        """Get current temperature."""
        return float(self.coordinator.data[self.control.ana_measure_id]["value"])

    @property
    def target_temperature(self) -> float:
        """Get target temperature."""
        return float(self.coordinator.data[self.control.ana_consigne_id]["value"])

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current mode if heating or not."""
        if self.coordinator.data[self.control.io_onoff_id]["on"] is True:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current action if heating or not."""
        if self.coordinator.data[self.control.io_state_id]["on"] is True:
            return HVACAction.HEATING
        if self.coordinator.data[self.control.io_onoff_id]["on"] is False:
            return HVACAction.OFF
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str:
        """Return current preset mode from 2 relay states."""
        if self.coordinator.data[self.control.io_comfort_id]["on"] is True:
            return PRESET_COMFORT
        if self.coordinator.data[self.control.io_eco_id]["on"] is True:
            return PRESET_ECO
        if self.coordinator.data[self.control.io_nofrost_id]["on"] is True:
            return PRESET_AWAY
        if self.coordinator.data[self.control.io_onoff_id]["on"] is False:
            return PRESET_NONE
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await self.control.set_target_temperature(kwargs[ATTR_TEMPERATURE])
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            await self.control.on()
            await self.control.set_mode_comfort()
        elif hvac_mode == HVACMode.OFF:
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

    async def async_turn_off(self) -> None:
        """Turn off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        """Turn on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

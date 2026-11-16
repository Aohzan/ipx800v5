"""Support for IPX800 V5 lights."""

from asyncio import gather as async_gather
from collections.abc import Coroutine
import logging
from typing import Any

from pypx800v5 import (
    EXT_X010V,
    EXT_X8R,
    EXT_XDIMMER,
    EXT_XPWM,
    IPX,
    IPX800,
    X010V,
    X8R,
    XPWM,
    IPX800Relay,
    XDimmer,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_TYPE, Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_DEFAULT_BRIGHTNESS,
    CONF_EXT_TYPE,
    TYPE_XPWM_RGB,
    TYPE_XPWM_RGBW,
)
from .coordinator import IpxConfigEntry, IpxCoordinator
from .entity import IpxEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Seconds the commanded levels are shown when the IPX800 doesn't report them
COMMANDED_LEVELS_TIMEOUT = 5


def scalefrom100to255(value):
    """Scale from classic value to Home-Assistant value."""
    return max(0, min(255, round((value * 255.0) / 100.0)))


def scaleto100(value):
    """Scale to IPX800 value."""
    return max(0, min(100, round((value * 100.0) / 255.0)))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IpxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the IPX800 lights."""
    coordinator = entry.runtime_data
    controller = coordinator.ipx
    devices = coordinator.devices[Platform.LIGHT]

    entities: list[LightEntity] = []

    for device in devices:
        if device[CONF_EXT_TYPE] == IPX:
            entities.append(IpxLight(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_X8R:
            entities.append(X8RLight(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_XDIMMER:
            entities.append(XDimmerLight(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_XPWM and CONF_TYPE not in device:
            entities.append(XPWMLight(device, controller, coordinator))
        elif (
            device[CONF_EXT_TYPE] == EXT_XPWM and device.get(CONF_TYPE) == TYPE_XPWM_RGB
        ):
            entities.append(XPWMRGBLight(device, controller, coordinator))
        elif (
            device[CONF_EXT_TYPE] == EXT_XPWM
            and device.get(CONF_TYPE) == TYPE_XPWM_RGBW
        ):
            entities.append(XPWMRGBWLight(device, controller, coordinator))
        elif device[CONF_EXT_TYPE] == EXT_X010V:
            entities.append(X010VLight(device, controller, coordinator))

    async_add_entities(entities)


class IpxLight(IpxEntity, LightEntity):
    """Representation of a IPX light through relay."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the RelayLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800Relay(ipx, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self.coordinator.data[self.control.io_state_id]["on"] == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        await self.control.toggle()
        await self.coordinator.async_request_refresh()


class X8RLight(IpxEntity, LightEntity):
    """Representation of a X-8R light through relay."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the RelayLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X8R(ipx, self._ext_number, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self.coordinator.data[self.control.io_state_id]["on"] == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        await self.control.toggle()
        await self.coordinator.async_request_refresh()


class IpxDimmableLight(IpxEntity, LightEntity):
    """Light showing its commanded levels until the IPX800 reports them.

    Home Assistant computes brightness_step from the brightness of the entity,
    and the IPX800 reports a new level only at the next refresh: without
    this, the steps sent before it start from the same stale level.
    """

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the light."""
        super().__init__(device_config, ipx, coordinator)
        # Levels from 0 to 100 by ID of the analog value reporting them
        self._commanded_levels: dict[int, int] = {}
        self._cancel_commanded_timeout: CALLBACK_TYPE | None = None

    def _level(self, ana_id: int) -> int:
        """Return the level of an analog value, the commanded one first."""
        if ana_id in self._commanded_levels:
            return self._commanded_levels[ana_id]
        return self.coordinator.data[ana_id]["value"]

    async def _async_set_levels(
        self, levels: dict[int, int], *commands: Coroutine[Any, Any, None]
    ) -> None:
        """Send the commands of the levels, shown before the IPX800 reports them.

        The levels are set before the requests, so that a concurrent
        brightness step starts from them.
        """
        self._commanded_levels.update(levels)
        if self._cancel_commanded_timeout is not None:
            self._cancel_commanded_timeout()
        self._cancel_commanded_timeout = async_call_later(
            self.hass, COMMANDED_LEVELS_TIMEOUT, self._async_commanded_timeout
        )
        self.async_write_ha_state()
        try:
            await async_gather(*commands)
        except Exception:
            self._clear_commanded_levels()
            self.async_write_ha_state()
            raise
        await self.coordinator.async_request_refresh()

    async def _async_command(self, command: Coroutine[Any, Any, None]) -> None:
        """Send a command leading to a level only the IPX800 knows."""
        self._clear_commanded_levels()
        await command
        await self.coordinator.async_request_refresh()

    @callback
    def _async_commanded_timeout(self, _now: Any) -> None:
        """Show the levels reported by the IPX800, even if not the commanded ones."""
        self._cancel_commanded_timeout = None
        self._clear_commanded_levels()
        self.async_write_ha_state()

    def _clear_commanded_levels(self) -> None:
        """Forget the commanded levels."""
        self._commanded_levels.clear()
        if self._cancel_commanded_timeout is not None:
            self._cancel_commanded_timeout()
            self._cancel_commanded_timeout = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Forget the commanded levels reported by the IPX800."""
        for ana_id, level in list(self._commanded_levels.items()):
            if self.coordinator.data[ana_id]["value"] == level:
                del self._commanded_levels[ana_id]
        if not self._commanded_levels:
            self._clear_commanded_levels()
        super()._handle_coordinator_update()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the timeout of the commanded levels."""
        self._clear_commanded_levels()
        await super().async_will_remove_from_hass()


class IpxOutputLight(IpxDimmableLight):
    """Light of an output with an on state and a level: X-Dimmer or X-010V."""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    control: XDimmer | X010V
    # ID of the analog value reporting the level
    _level_id: int

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        if self._level_id in self._commanded_levels:
            return self._commanded_levels[self._level_id] > 0
        return self.coordinator.data[self.control.io_state_id]["on"] == 1

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return scalefrom100to255(self._level(self._level_id))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_BRIGHTNESS not in kwargs:
            # Back to the last commanded level
            await self._async_command(self.control.on())
            return
        level = scaleto100(kwargs[ATTR_BRIGHTNESS])
        await self._async_set_levels(
            {self._level_id: level},
            self._async_set_level(level, turn_on=not self.is_on and level > 0),
        )

    async def _async_set_level(self, level: int, turn_on: bool) -> None:
        """Set the level of the output, turning it on if needed."""
        await self.control.set_level(level)
        if turn_on:
            # An output that is off stays off when its command is the level
            await self.control.on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._async_set_levels({self._level_id: 0}, self.control.off())

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        await self._async_command(self.control.toggle())


class XDimmerLight(IpxOutputLight):
    """Representation of a IPX Light through X-Dimmer."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the class XDimmerLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = XDimmer(ipx, self._ext_number, self.io_number)
        # Position during the transition set on the X-Dimmer
        self._level_id = self.control.ana_state_id


class XPWMLight(IpxDimmableLight):
    """Representation of a IPX Light through X-PWM single channel."""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the XPWMLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = XPWM(ipx, self._ext_number, self.io_number)

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self._level(self.control.ana_state_id) > 0

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return scalefrom100to255(self._level(self.control.ana_state_id))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        level = scaleto100(kwargs.get(ATTR_BRIGHTNESS, 255))
        await self._async_set_levels(
            {self.control.ana_state_id: level}, self.control.set_level(level)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._async_set_levels({self.control.ana_state_id: 0}, self.control.off())

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        if self.is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()


class XPWMColorLight(IpxDimmableLight):
    """Representation of a color light through several X-PWM channels."""

    _channel_count: int
    _color_attr: str

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the light."""
        super().__init__(device_config, ipx, coordinator)
        self._channels = [
            XPWM(ipx, self._ext_number, io_number)
            for io_number in self._io_numbers[: self._channel_count]
        ]
        self._default_brightness = device_config.get(CONF_DEFAULT_BRIGHTNESS, 255)

    @property
    def _white_channels(self) -> list[XPWM]:
        """Return the channels turned on from off without a color."""
        return self._channels

    @property
    def _levels(self) -> tuple[int, ...]:
        """Return the levels of the channels, from 0 to 255."""
        return tuple(
            scalefrom100to255(self._level(channel.ana_state_id))
            for channel in self._channels
        )

    @property
    def is_on(self) -> bool:
        """Return if at least a level in on."""
        return any(level > 0 for level in self._levels)

    @property
    def brightness(self) -> int:
        """Return the brightness from levels."""
        return max(self._levels)

    async def _async_set_channels(self, levels: dict[XPWM, float]) -> None:
        """Set the levels of channels, from 0 to 255."""
        levels_100 = {channel: scaleto100(level) for channel, level in levels.items()}
        await self._async_set_levels(
            {channel.ana_state_id: level for channel, level in levels_100.items()},
            *(channel.set_level(level) for channel, level in levels_100.items()),
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if self._color_attr in kwargs:
            await self._async_set_channels(
                dict(zip(self._channels, kwargs[self._color_attr], strict=True))
            )
        elif ATTR_BRIGHTNESS in kwargs and self.is_on:
            ratio = kwargs[ATTR_BRIGHTNESS] / self.brightness
            await self._async_set_channels(
                {
                    channel: level * ratio
                    for channel, level in zip(self._channels, self._levels, strict=True)
                }
            )
        else:
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._default_brightness)
            await self._async_set_channels(
                dict.fromkeys(self._white_channels, brightness)
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._async_set_channels(dict.fromkeys(self._channels, 0))


class XPWMRGBLight(XPWMColorLight):
    """Representation of a RGB light through 3 X-PWM channels."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _channel_count = 3
    _color_attr = ATTR_RGB_COLOR

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the RGB color from RGB levels."""
        red, green, blue = self._levels
        return (red, green, blue)


class XPWMRGBWLight(XPWMColorLight):
    """Representation of a RGBW light through 4 X-PWM channels."""

    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_color_mode = ColorMode.RGBW
    _channel_count = 4
    _color_attr = ATTR_RGBW_COLOR

    @property
    def _white_channels(self) -> list[XPWM]:
        """Return the white channel."""
        return self._channels[3:]

    @property
    def rgbw_color(self) -> tuple[int, int, int, int]:
        """Return the RGBW color from RGBW levels."""
        red, green, blue, white = self._levels
        return (red, green, blue, white)


class X010VLight(IpxOutputLight):
    """Representation of a X-010V output as a light."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
    ) -> None:
        """Initialize the class X010VLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X010V(ipx, self._ext_number, self.io_number)
        self._level_id = self.control.ana_level_id

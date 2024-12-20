"""Support for IPX800 V5 lights."""

from asyncio import gather as async_gather
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
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEFAULT_BRIGHTNESS,
    CONF_DEVICES,
    CONF_EXT_TYPE,
    CONF_TRANSITION,
    CONTROLLER,
    COORDINATOR,
    DEFAULT_TRANSITION,
    DOMAIN,
    TYPE_XPWM_RGB,
    TYPE_XPWM_RGBW,
)
from .entity import IpxEntity

_LOGGER = logging.getLogger(__name__)


def scalefrom100to255(value):
    """Scale from classic value to Home-Assistant value."""
    return max(0, min(255, round((value * 255.0) / 100.0)))


def scaleto100(value):
    """Scale to IPX800 value."""
    return max(0, min(100, round((value * 100.0) / 255.0)))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPX800 lights."""
    controller = hass.data[DOMAIN][entry.entry_id][CONTROLLER]
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    devices = hass.data[DOMAIN][entry.entry_id][CONF_DEVICES]["light"]

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

    async_add_entities(entities, True)


class IpxLight(IpxEntity, LightEntity):
    """Representation of a IPX light through relay."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelayLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = IPX800Relay(ipx, self._io_number)

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
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the RelayLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X8R(ipx, self._ext_number, self._io_number)

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


class XDimmerLight(IpxEntity, LightEntity):
    """Representation of a IPX Light through X-Dimmer."""

    _attr_supported_features = LightEntityFeature.TRANSITION
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the class XDimmerLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = XDimmer(ipx, self._ext_number, self._io_number)
        self._transition = device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION)

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self.coordinator.data[self.control.io_state_id]["on"] == 1

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return scalefrom100to255(
            self.coordinator.data[self.control.ana_state_id]["value"]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        if ATTR_BRIGHTNESS in kwargs:
            await self.control.set_level(
                scaleto100(kwargs[ATTR_BRIGHTNESS]), self._transition * 1000
            )
        else:
            await self.control.on(self._transition * 1000)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        await self.control.off(self._transition * 1000)
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        await self.control.toggle(self._transition * 1000)
        await self.coordinator.async_request_refresh()


class XPWMLight(IpxEntity, LightEntity):
    """Representation of a IPX Light through X-PWM single channel."""

    _attr_supported_features = LightEntityFeature.TRANSITION
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the XPWMLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = XPWM(ipx, self._ext_number, self._io_number)

        self._default_brightness = scaleto100(
            device_config.get(CONF_DEFAULT_BRIGHTNESS, 255)
        )
        self._transition = device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION)

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self.coordinator.data[self.control.ana_state_id]["value"] > 0

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return scalefrom100to255(
            self.coordinator.data[self.control.ana_state_id]["value"]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        if ATTR_BRIGHTNESS in kwargs:
            await self.control.set_level(
                scaleto100(kwargs[ATTR_BRIGHTNESS]), self._transition * 1000
            )
        else:
            await self.control.on(self._transition * 1000)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        await self.control.off(self._transition * 1000)
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        await self.control.toggle(self._transition * 1000)
        await self.coordinator.async_request_refresh()


class XPWMRGBLight(IpxEntity, LightEntity):
    """Representation of a RGB light through 3 X-PWM channels."""

    _attr_supported_features = LightEntityFeature.TRANSITION
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the XPWMRGBLight."""
        super().__init__(device_config, ipx, coordinator)
        self.xpwm_rgb_r = XPWM(ipx, self._ext_number, self._io_numbers[0])
        self.xpwm_rgb_g = XPWM(ipx, self._ext_number, self._io_numbers[1])
        self.xpwm_rgb_b = XPWM(ipx, self._ext_number, self._io_numbers[2])

        self._default_brightness = scaleto100(
            device_config.get(CONF_DEFAULT_BRIGHTNESS, 255)
        )
        self._transition = device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION)

    @property
    def is_on(self) -> bool:
        """Return if at least a level in on."""
        return any(i > 0 for i in self.rgb_color)

    @property
    def brightness(self) -> int:
        """Return the brightness from levels."""
        return max(self.rgb_color)

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the RGB color from RGB levels."""
        level_r = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgb_r.ana_state_id]["value"]
        )
        level_g = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgb_g.ana_state_id]["value"]
        )
        level_b = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgb_b.ana_state_id]["value"]
        )
        return (level_r, level_g, level_b)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        if ATTR_RGB_COLOR in kwargs:
            colors = kwargs[ATTR_RGB_COLOR]
            await async_gather(
                self.xpwm_rgb_r.set_level(
                    scaleto100(colors[0]), self._transition * 1000
                ),
                self.xpwm_rgb_g.set_level(
                    scaleto100(colors[1]), self._transition * 1000
                ),
                self.xpwm_rgb_b.set_level(
                    scaleto100(colors[2]), self._transition * 1000
                ),
            )
        elif ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if self.is_on:
                await async_gather(
                    self.xpwm_rgb_r.set_level(
                        scaleto100(self.rgb_color[0] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgb_g.set_level(
                        scaleto100(self.rgb_color[1] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgb_b.set_level(
                        scaleto100(self.rgb_color[2] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                )
            else:
                await async_gather(
                    self.xpwm_rgb_r.set_level(
                        scaleto100(brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgb_g.set_level(
                        scaleto100(brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgb_b.set_level(
                        scaleto100(brightness),
                        self._transition * 1000,
                    ),
                )
        else:
            await async_gather(
                self.xpwm_rgb_r.set_level(
                    scaleto100(self._default_brightness),
                    self._transition * 1000,
                ),
                self.xpwm_rgb_g.set_level(
                    scaleto100(self._default_brightness),
                    self._transition * 1000,
                ),
                self.xpwm_rgb_b.set_level(
                    scaleto100(self._default_brightness),
                    self._transition * 1000,
                ),
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        await async_gather(
            self.xpwm_rgb_r.off(self._transition * 1000),
            self.xpwm_rgb_g.off(self._transition * 1000),
            self.xpwm_rgb_b.off(self._transition * 1000),
        )
        await self.coordinator.async_request_refresh()


class XPWMRGBWLight(IpxEntity, LightEntity):
    """Representation of a RGBW light through 4 X-PWM channels."""

    _attr_supported_features = LightEntityFeature.TRANSITION
    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_color_mode = ColorMode.RGBW

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the XPWMRGBWLight."""
        super().__init__(device_config, ipx, coordinator)
        self.xpwm_rgbw_r = XPWM(ipx, self._ext_number, self._io_numbers[0])
        self.xpwm_rgbw_g = XPWM(ipx, self._ext_number, self._io_numbers[1])
        self.xpwm_rgbw_b = XPWM(ipx, self._ext_number, self._io_numbers[2])
        self.xpwm_rgbw_w = XPWM(ipx, self._ext_number, self._io_numbers[3])

        self._default_brightness = scaleto100(
            device_config.get(CONF_DEFAULT_BRIGHTNESS, 255)
        )
        self._transition = device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION)

    @property
    def is_on(self) -> bool:
        """Return if at least a level in on."""
        return any(i > 0 for i in self.rgbw_color)

    @property
    def brightness(self) -> int:
        """Return the brightness from levels."""
        return max(self.rgbw_color)

    @property
    def rgbw_color(self) -> tuple[int, int, int, int]:
        """Return the RGB color from RGB levels."""
        level_r = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgbw_r.ana_state_id]["value"]
        )
        level_g = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgbw_g.ana_state_id]["value"]
        )
        level_b = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgbw_b.ana_state_id]["value"]
        )
        level_w = scalefrom100to255(
            self.coordinator.data[self.xpwm_rgbw_w.ana_state_id]["value"]
        )
        return (level_r, level_g, level_b, level_w)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]

        if ATTR_RGBW_COLOR in kwargs:
            colors = kwargs[ATTR_RGBW_COLOR]
            # if only rgb color have been set
            await async_gather(
                self.xpwm_rgbw_r.set_level(
                    scaleto100(colors[0]), self._transition * 1000
                ),
                self.xpwm_rgbw_g.set_level(
                    scaleto100(colors[1]), self._transition * 1000
                ),
                self.xpwm_rgbw_b.set_level(
                    scaleto100(colors[2]), self._transition * 1000
                ),
                self.xpwm_rgbw_w.set_level(
                    scaleto100(colors[3]), self._transition * 1000
                ),
            )
        elif ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if self.is_on:
                await async_gather(
                    self.xpwm_rgbw_r.set_level(
                        scaleto100(self.rgbw_color[0] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgbw_g.set_level(
                        scaleto100(self.rgbw_color[1] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgbw_b.set_level(
                        scaleto100(self.rgbw_color[2] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                    self.xpwm_rgbw_w.set_level(
                        scaleto100(self.rgbw_color[3] * brightness / self.brightness),
                        self._transition * 1000,
                    ),
                )
            else:
                await self.xpwm_rgbw_w.set_level(
                    scaleto100(brightness),
                    self._transition * 1000,
                )
        else:
            await self.xpwm_rgbw_w.set_level(
                self._default_brightness, self._transition * 1000
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        if ATTR_TRANSITION in kwargs:
            self._transition = kwargs[ATTR_TRANSITION]
        await async_gather(
            self.xpwm_rgbw_w.off(self._transition * 1000),
            self.xpwm_rgbw_r.off(self._transition * 1000),
            self.xpwm_rgbw_g.off(self._transition * 1000),
            self.xpwm_rgbw_b.off(self._transition * 1000),
        )
        await self.coordinator.async_request_refresh()


class X010VLight(IpxEntity, LightEntity):
    """Representation of a X-010V output as a light."""

    _attr_supported_features = LightEntityFeature.TRANSITION
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Initialize the class XDimmerLight."""
        super().__init__(device_config, ipx, coordinator)
        self.control = X010V(ipx, self._ext_number, self._io_number)

    @property
    def is_on(self) -> bool:
        """Return if the output is on."""
        return self.coordinator.data[self.control.io_state_id]["on"] == 1

    @property
    def brightness(self) -> int:
        """Return the brightness of the output."""
        return scalefrom100to255(
            self.coordinator.data[self.control.ana_level_id]["value"]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the output."""
        if ATTR_BRIGHTNESS in kwargs:
            await self.control.set_level(scaleto100(kwargs[ATTR_BRIGHTNESS]))
        else:
            await self.control.on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the output."""
        await self.control.off()
        await self.coordinator.async_request_refresh()

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the output."""
        await self.control.toggle()
        await self.coordinator.async_request_refresh()

"""Represent the IPX800V5 base entity."""
from pypx800v5 import EXTENSIONS, IPX, IPX800
from voluptuous.util import Upper

from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITY_CATEGORY,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import slugify

from .const import (
    CONF_COMPONENT,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    CONF_TRANSITION,
    DEFAULT_TRANSITION,
    DOMAIN,
)


class IpxEntity(CoordinatorEntity):
    """Representation of a IPX800 generic device entity."""

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: DataUpdateCoordinator,
        suffix_name=None,
        device_name=None,
    ) -> None:
        """Initialize the device."""
        super().__init__(coordinator)

        self.ipx = ipx
        self._transition = int(
            device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION) * 1000
        )
        self._component = device_config[CONF_COMPONENT]
        self._ext_type = device_config[CONF_EXT_TYPE]
        self._ext_number = device_config.get(CONF_EXT_NUMBER)
        self._io_number = device_config.get(CONF_IO_NUMBER)
        self._io_numbers = device_config.get(CONF_IO_NUMBERS, [])
        self._io_id = device_config.get(CONF_ID)

        self._attr_name: str = device_config[CONF_NAME]
        if suffix_name:
            self._attr_name = f"{self._attr_name} {suffix_name}"
        self._attr_device_class = device_config.get(CONF_DEVICE_CLASS)
        self._attr_native_unit_of_measurement = device_config.get(
            CONF_UNIT_OF_MEASUREMENT
        )
        self._attr_icon = device_config.get(CONF_ICON)
        self._attr_entity_category = device_config.get(CONF_ENTITY_CATEGORY)
        self._attr_unique_id = "_".join(
            [DOMAIN, self.ipx.host, self._component, slugify(self._attr_name)]
        )

        if device_name:
            self._device_name = device_name
        elif self._ext_type == IPX:
            self._device_name = coordinator.name
        else:
            self._device_name = device_config.get(
                CONF_EXT_NAME, f"{Upper(self._ext_type)} N°{self._ext_number}"
            )

        configuration_url = f"http://{self.ipx.host}:{self.ipx.port}/"

        model = Upper(self._ext_type) if self._ext_type in EXTENSIONS else "IPX800 V5"
        sw_version = self.ipx.firmware_version if self._ext_type == IPX else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, slugify(self._device_name))},
            via_device=(DOMAIN, coordinator.name),
            name=self._device_name,
            manufacturer="GCE Electronics",
            model=model,
            configuration_url=configuration_url,
            sw_version=sw_version,
            connections={(CONNECTION_NETWORK_MAC, str(self.ipx.mac_address))},
        )

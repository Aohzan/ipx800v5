"""Represent the IPX800V5 base entity."""

from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_ENTITY_CATEGORY,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    async_get as async_get_device_registry,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import slugify
from pypx800v5 import EXTENSIONS, IPX, IPX800
from voluptuous.util import Upper

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
        self._device_config = device_config
        self._transition = int(
            device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION) * 1000
        )
        self._component: str = device_config[CONF_COMPONENT]
        self._ext_type: str = device_config[CONF_EXT_TYPE]
        self._ext_number: int | None = device_config.get(CONF_EXT_NUMBER)
        self._io_number: int | None = device_config.get(CONF_IO_NUMBER)
        self._io_numbers: list[int] = device_config.get(CONF_IO_NUMBERS, [])
        self._io_id: int | None = device_config.get(CONF_ID)

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
            [
                DOMAIN,
                self.ipx.mac_address,
                self._ext_type,
                str(self._ext_number),
                self._component,
                slugify(self._attr_name),
            ]
        )
        self._attr_extra_state_attributes = {
            "extension_type": self._ext_type,
            "extension_number": self._ext_number,
            "io": self._io_number or self._io_numbers or self._io_id,
        }

        self._device_name = device_name
        self._device_info: DeviceInfo | None = None

        configuration_url = f"http://{self.ipx.host}:{self.ipx.port}/"

        self._device_model = (
            Upper(self._ext_type[:1] + "-" + self._ext_type[1:])
            if self._ext_type in EXTENSIONS
            else "IPX800 V5"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info, resolving via_device_id from the device registry."""
        if self._device_info is not None:
            return self._device_info

        configuration_url = f"http://{self.ipx.host}:{self.ipx.port}/"

        if self._ext_type == IPX:
            self._device_info = DeviceInfo(
                identifiers={(DOMAIN, self.ipx.mac_address)},
                manufacturer="GCE Electronics",
                model=self._device_model,
                name=self.coordinator.name,
                configuration_url=configuration_url,
                sw_version=self.ipx.firmware_version,
                connections={(CONNECTION_NETWORK_MAC, str(self.ipx.mac_address))},
            )
        else:
            device_name = self._device_name or self._device_config.get(
                CONF_EXT_NAME, f"{Upper(self._ext_type)} N°{self._ext_number}"
            )
            dev_reg = async_get_device_registry(self.hass)
            parent_device = dev_reg.async_get_device(
                identifiers={(DOMAIN, self.ipx.mac_address)},
                connections=None,
            )
            self._device_info = DeviceInfo(
                identifiers={(DOMAIN, slugify(device_name))},
                manufacturer="GCE Electronics",
                model=self._device_model,
                name=device_name,
                configuration_url=configuration_url,
                via_device_id=parent_device.id if parent_device else None,
            )

        return self._device_info

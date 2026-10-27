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
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    async_get_device_id_by_identifier,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    CONF_COMPONENT,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    CONF_TRANSITION,
    CONF_TRANSLATION_KEY,
    DEFAULT_TRANSITION,
    DOMAIN,
)
from .coordinator import IpxCoordinator


def _remove_device_name(name: str, device_name: str) -> str | None:
    """Return the name without the device name, or None when it's the same.

    Same rules as Home Assistant for the friendly names of the entities
    without has_entity_name (_async_strip_prefix_from_entity_name of the
    entity registry): the prefix is case insensitive and followed by a
    separator, which is removed, and a lowercase first word is capitalized.
    """
    prefix = device_name.casefold()
    candidate = name[: len(prefix)]
    prefix_len = len(candidate)
    candidate = candidate.casefold()
    if not candidate.startswith(prefix):
        return name
    # Casefolded strings can be longer
    prefix_diff = len(candidate) - len(prefix)
    while prefix_diff > 0:
        prefix_len -= 1
        prefix_diff -= len(name[prefix_len].casefold())
    if prefix_diff < 0:
        return name
    unprefixed = name[prefix_len:].lstrip(" -:")
    if not unprefixed:
        return None
    if len(unprefixed) == len(name) - prefix_len:
        # Not followed by a separator
        return name
    if not unprefixed.partition(" ")[0].islower():
        return unprefixed
    return unprefixed[0].upper() + unprefixed[1:]


class IpxEntity(CoordinatorEntity[IpxCoordinator]):
    """Representation of a IPX800 generic device entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device_config: dict,
        ipx: IPX800,
        coordinator: IpxCoordinator,
        suffix_name: str | None = None,
        device_name: str | None = None,
        translation_key: str | None = None,
    ) -> None:
        """Initialize the device.

        suffix_name is the English name of the secondary entities of a
        device, translated with translation_key when the entity is named
        after its device.
        """
        super().__init__(coordinator)

        self.ipx = ipx
        self._transition = int(
            device_config.get(CONF_TRANSITION, DEFAULT_TRANSITION) * 1000
        )
        self._component: str = device_config[CONF_COMPONENT]
        self._ext_type: str = device_config[CONF_EXT_TYPE]
        self._ext_number: int | None = device_config.get(CONF_EXT_NUMBER)
        self._io_number: int | None = device_config.get(CONF_IO_NUMBER)
        self._io_numbers: list[int] = device_config.get(CONF_IO_NUMBERS, [])
        self._io_id: int | None = device_config.get(CONF_ID)

        name: str = device_config[CONF_NAME]
        full_name = f"{name} {suffix_name}" if suffix_name else name
        # Only override the defaults set by the entity classes when configured
        if (device_class := device_config.get(CONF_DEVICE_CLASS)) is not None:
            self._attr_device_class = device_class
        if (unit := device_config.get(CONF_UNIT_OF_MEASUREMENT)) is not None:
            self._attr_native_unit_of_measurement = unit
        if (icon := device_config.get(CONF_ICON)) is not None:
            self._attr_icon = icon
        if (entity_category := device_config.get(CONF_ENTITY_CATEGORY)) is not None:
            self._attr_entity_category = entity_category
        # Built from the full name, which was the entity name before
        # has_entity_name
        self._attr_unique_id = "_".join(
            [
                DOMAIN,
                self.ipx.mac_address,
                self._ext_type,
                str(self._ext_number),
                self._component,
                slugify(full_name),
            ]
        )
        self._attr_extra_state_attributes = {
            "extension_type": self._ext_type,
            "extension_number": self._ext_number,
            "io": self._io_number or self._io_numbers or self._io_id,
        }

        configuration_url = f"http://{self.ipx.host}:{self.ipx.port}/"

        device_model = (
            Upper(self._ext_type[:1] + "-" + self._ext_type[1:])
            if self._ext_type in EXTENSIONS
            else "IPX800 V5"
        )
        if self._ext_type == IPX:
            device_name = coordinator.name
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self.ipx.mac_address)},
                manufacturer="GCE Electronics",
                model=device_model,
                name=device_name,
                configuration_url=configuration_url,
                sw_version=self.ipx.firmware_version,
                connections={(CONNECTION_NETWORK_MAC, str(self.ipx.mac_address))},
            )
        else:
            device_name = device_name or device_config.get(
                CONF_EXT_NAME, f"{Upper(self._ext_type)} N°{self._ext_number}"
            )
            self._attr_device_info = DeviceInfo(
                identifiers={
                    (DOMAIN, f"{self.ipx.mac_address}_{slugify(device_name)}")
                },
                manufacturer="GCE Electronics",
                model=device_model,
                name=device_name,
                configuration_url=configuration_url,
                # The parent IPX device is registered in async_setup_entry
                # before the platforms are set up, so it always resolves.
                via_device_id=async_get_device_id_by_identifier(
                    coordinator.hass,
                    (DOMAIN, self.ipx.mac_address),
                    config_entry_id=coordinator.config_entry.entry_id,
                ),
            )

        self._set_name(
            name,
            device_name,
            suffix_name,
            translation_key or device_config.get(CONF_TRANSLATION_KEY),
        )

    def _set_name(
        self,
        name: str,
        device_name: str,
        suffix_name: str | None,
        translation_key: str | None,
    ) -> None:
        """Name the entity without the name of its device.

        The names come from the user configuration or the IPX800 and often
        start with the device name, which Home Assistant adds to the friendly
        name: it's removed from the entity name, so the friendly names don't
        change.
        """
        if translation_key is not None:
            # Also gives the icon of the entity
            self._attr_translation_key = translation_key
            if suffix_name is None:
                # Entity of the IPX800 itself, named by the integration
                return

        # None for the main entity of its device
        entity_name = _remove_device_name(name, device_name)

        if suffix_name is None:
            self._attr_name = entity_name
        elif entity_name is not None:
            self._attr_name = f"{entity_name} {suffix_name}"
        elif translation_key is None:
            self._attr_name = suffix_name

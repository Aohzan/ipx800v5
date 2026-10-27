"""Tests of the friendly names of the GCE IPX800 V5 entities.

The entities were named with has_entity_name=False before Home Assistant
2026.10. Home Assistant shows those legacy entities as "<device name> <name
without the device name>", so the names given with has_entity_name=True must
give the same friendly names.
"""

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ipx800v5 import CONFIG_SCHEMA
from custom_components.ipx800v5.const import (
    CONF_COMPONENT,
    CONF_DEVICES,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    DOMAIN,
)
from custom_components.ipx800v5.entity import IpxEntity, _remove_device_name
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_API_KEY, CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import (
    _async_strip_prefix_from_entity_name,
)

from .conftest import API_KEY, ENTRY_DATA, HOST

# configuration.yaml of an IPX800 named by the user, with custom names
YAML_CONFIG = {
    CONF_NAME: "Maison",
    CONF_HOST: HOST,
    CONF_API_KEY: API_KEY,
    CONF_DEVICES: [
        # Not prefixed by the device name
        {
            CONF_NAME: "Lumiere cuisine",
            CONF_COMPONENT: "light",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 1,
        },
        # Prefixed by the device name
        {
            CONF_NAME: "Maison Lumiere salon",
            CONF_COMPONENT: "light",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 2,
        },
        # Prefixed with another case, then a lowercase word
        {
            CONF_NAME: "maison lumiere couloir",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 3,
        },
        # Prefixed with a separator
        {
            CONF_NAME: "Maison - Prise bureau",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 4,
        },
        # Starting with the device name, without a separator
        {
            CONF_NAME: "Maisonnette",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 5,
        },
        # Same name as the device
        {
            CONF_NAME: "Maison",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 6,
        },
        # Extension with its default device name
        {
            CONF_NAME: "Prise garage",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "x8r",
            CONF_EXT_NUMBER: 0,
            CONF_IO_NUMBER: 3,
        },
        {
            CONF_NAME: "X8R N°0 Prise cellier",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "x8r",
            CONF_EXT_NUMBER: 0,
            CONF_IO_NUMBER: 4,
        },
        # Extension without the name of the IPX800
        {
            CONF_NAME: "Radiateur chambre",
            CONF_COMPONENT: "climate",
            CONF_EXT_TYPE: "x4fp",
            CONF_EXT_NUMBER: 0,
            CONF_IO_NUMBER: 2,
        },
        # Several relays
        {
            CONF_NAME: "Sèche-serviettes",
            CONF_COMPONENT: "climate",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBERS: [7, 8],
        },
    ],
}

# UI entry of an IPX800 named by the user, with an extension named by the user
UI_ENTRY_DATA = ENTRY_DATA | {
    CONF_NAME: "Garage",
    CONF_DEVICES: [
        *ENTRY_DATA[CONF_DEVICES],
        {
            CONF_NAME: "X8R N°0 Relais 3",
            CONF_EXT_TYPE: "x8r",
            CONF_EXT_NUMBER: 0,
            CONF_EXT_NAME: "Relais garage",
            CONF_IO_NUMBER: 3,
            CONF_COMPONENT: "switch",
        },
    ],
}


def _legacy_set_name(
    self: IpxEntity,
    name: str,
    device_name: str,
    suffix_name: str | None,
    translation_key: str | None,
) -> None:
    """Name the entity like the integration did before has_entity_name."""
    self._attr_has_entity_name = False
    self._attr_name = f"{name} {suffix_name}" if suffix_name else name


async def _async_friendly_names(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    data: dict[str, Any],
    source: str,
) -> dict[str, str]:
    """Set up an entry and return the friendly names by unique ID.

    The entities named by the integration are left out: their names are
    translated now, so they are expected to change.
    """
    entry = MockConfigEntry(domain=DOMAIN, data=data, source=source)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    names = {
        registry_entry.unique_id: hass.states.get(registry_entry.entity_id).attributes[
            ATTR_FRIENDLY_NAME
        ]
        for registry_entry in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        )
        if registry_entry.translation_key is None and not registry_entry.disabled_by
    }
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    return names


@pytest.mark.usefixtures("mock_ipx")
@pytest.mark.parametrize(
    ("data", "source", "expected"),
    [
        (
            ENTRY_DATA,
            "user",
            {
                "IPX800 V5 IPX N°0 Relais 1",
                "IPX800 V5 Relais 2",
                "IPX800 V5 Digital Input 1",
                "X8R N°0 Relais 1",
                "X8R N°0 Relais 2",
                "Radiateurs FP 1",
                "Volets VR 1",
                "Thermostat",
                "Compteur",
                "Tempo Garage",
            },
        ),
        (
            UI_ENTRY_DATA,
            "user",
            {
                "Garage IPX N°0 Relais 1",
                "Garage IPX800 V5 Relais 2",
                "Garage IPX800 V5 Digital Input 1",
                "Relais garage X8R N°0 Relais 3",
            },
        ),
        (
            CONFIG_SCHEMA({DOMAIN: [YAML_CONFIG]})[DOMAIN][0],
            SOURCE_IMPORT,
            {
                "Maison Lumiere cuisine",
                "Maison Lumiere salon",
                "Maison Lumiere couloir",
                "Maison Prise bureau",
                "Maison Maisonnette",
                "Maison",
                "X8R N°0 Prise garage",
                "X8R N°0 Prise cellier",
                "X4FP N°0 Radiateur chambre",
                "Maison Sèche-serviettes",
            },
        ),
    ],
    ids=["ui_default_names", "ui_custom_names", "yaml_custom_names"],
)
async def test_friendly_names_unchanged(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    data: dict[str, Any],
    source: str,
    expected: set[str],
) -> None:
    """Test the friendly names are the ones of the legacy entity names."""
    names = await _async_friendly_names(hass, entity_registry, data, source)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(IpxEntity, "_set_name", _legacy_set_name)
        legacy_names = await _async_friendly_names(hass, entity_registry, data, source)

    assert names == {unique_id: legacy_names[unique_id] for unique_id in names}
    assert expected <= set(names.values())


@pytest.mark.parametrize(
    ("name", "device_name"),
    [
        ("Maison Lumiere", "Maison"),
        ("maison lumiere", "Maison"),
        ("Maison: lumiere", "Maison"),
        ("Maison -", "Maison"),
        ("MAISON", "Maison"),
        ("Maisonnette", "Maison"),
        ("Mai", "Maison"),
        ("Lumiere", "Maison"),
        ("Straße Licht", "STRASSE"),
        ("STRASSE Licht", "Straße"),
        ("Strass Licht", "Straße"),
        ("ß Licht", "S"),
    ],
)
def test_remove_device_name(name: str, device_name: str) -> None:
    """Test the device name is removed like Home Assistant does it."""
    unprefixed = _async_strip_prefix_from_entity_name(name, device_name)
    if unprefixed is None:
        expected = name
    elif not unprefixed:
        expected = None
    else:
        expected = unprefixed

    assert _remove_device_name(name, device_name) == expected

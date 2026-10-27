"""Tests of the setup of the GCE IPX800 V5 integration."""

from freezegun.api import FrozenDateTimeFactory
from pypx800v5 import IPX800CannotConnectError, IPX800InvalidAuthError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.ipx800v5 import async_remove_config_entry_device
from custom_components.ipx800v5.const import (
    CONF_COMPONENT,
    CONF_DEVICES,
    CONF_DEVICES_AUTO,
    CONF_DIAG_SENSORS,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    CONF_TYPE,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import API_KEY, HOST, MAC, PORT, FakeIpxApi

YAML_CONFIG = {
    CONF_NAME: "IPX800 V5",
    CONF_HOST: HOST,
    CONF_PORT: PORT,
    CONF_API_KEY: API_KEY,
    CONF_DIAG_SENSORS: True,
    CONF_DEVICES_AUTO: ["xthl"],
    CONF_DEVICES: [
        {
            CONF_NAME: "VMC",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBER: 3,
        },
        {
            CONF_NAME: "Mon Virtual IO",
            CONF_COMPONENT: "switch",
            CONF_EXT_TYPE: "ipx",
            CONF_TYPE: "io",
            CONF_ID: 150,
        },
        {
            CONF_NAME: "Digicode",
            CONF_COMPONENT: "sensor",
            CONF_EXT_TYPE: "access_control",
            CONF_EXT_NUMBER: 0,
        },
        {
            CONF_NAME: "Sèche-serviettes",
            CONF_COMPONENT: "climate",
            CONF_EXT_TYPE: "ipx",
            CONF_IO_NUMBERS: [7, 8],
        },
    ],
}


async def test_setup_and_unload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the setup and unload of an entry."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.ipx.mac_address == MAC

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_cannot_connect(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the setup is retried when the IPX800 is unreachable."""
    mock_ipx.error = IPX800CannotConnectError("Timeout")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_invalid_auth(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test a rejected API key starts a reauth flow."""
    mock_ipx.error = IPX800InvalidAuthError()
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_setup_invalid_auth_yaml(
    hass: HomeAssistant, mock_ipx: FakeIpxApi
) -> None:
    """Test a rejected API key of configuration.yaml doesn't start a reauth flow."""
    mock_ipx.error = IPX800InvalidAuthError()
    entry = MockConfigEntry(domain=DOMAIN, source=SOURCE_IMPORT, data=YAML_CONFIG)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)


@pytest.mark.parametrize(
    ("error", "reauth"),
    [(IPX800CannotConnectError("Timeout"), False), (IPX800InvalidAuthError(), True)],
)
async def test_update_errors(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
    error: Exception,
    reauth: bool,
) -> None:
    """Test the entities are unavailable when the update fails."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = "switch.ipx800_v5_relais_2"
    assert hass.states.get(entity_id).state == "off"

    mock_ipx.error = error
    freezer.tick(20)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert bool(flows) is reauth


async def test_yaml_import(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test the configuration of configuration.yaml is imported and set up."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [YAML_CONFIG]})
    await hass.async_block_till_done()

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.source == SOURCE_IMPORT
    assert entry.title == "IPX800 V5 (from yaml)"
    assert entry.unique_id == f"{DOMAIN}, {HOST}"
    assert entry.state is ConfigEntryState.LOADED

    entities = {
        entity.entity_id: entity
        for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    }
    # Configured devices and the automatic ones of devices_auto only
    assert hass.states.get("switch.ipx800_v5_vmc").attributes["friendly_name"] == (
        "IPX800 V5 VMC"
    )
    assert "switch.ipx800_v5_mon_virtual_io" in entities
    assert "climate.ipx800_v5_seche_serviettes" in entities
    assert "sensor.salon_temperature" in entities
    # Last code of the access control, a text value
    code_id = mock_ipx.objects["access_control"][0]["bindCurrentCode_id"]
    assert (
        hass.states.get("sensor.access_control_ndeg0_digicode").state
        == f"text {code_id}"
    )
    assert "switch.ipx800_v5_relais_2" not in entities
    # Diagnostic sensors, named by the integration when they are known
    assert entities["sensor.ipx800_v5_heap_free"].translation_key == "heap_free"
    assert entities["sensor.ipx800_v5_ipx_clock"].translation_key == "clock"
    assert entities["sensor.ipx800_v5_ipxnewcounter"].original_name == "IPXNewCounter"

    # A new import updates the entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=YAML_CONFIG | {"port": 8080}
    )
    assert result["reason"] == "already_configured"
    assert entry.data["port"] == 8080


async def test_migrate_extension_devices(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test the extension devices are identified with the MAC address."""
    mock_config_entry.add_to_hass(hass)
    old_device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id, identifiers={(DOMAIN, "salon")}
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device = device_registry.async_get(old_device.id)
    assert device.identifiers == {(DOMAIN, f"{MAC}_salon")}


async def test_remove_device(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test only the devices without entities can be removed."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    orphan = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id, identifiers={(DOMAIN, "orphan")}
    )
    salon = device_registry.async_get_device_by_identifier(
        (DOMAIN, f"{MAC}_salon"), mock_config_entry.entry_id
    )

    assert await async_remove_config_entry_device(hass, mock_config_entry, orphan)
    assert not await async_remove_config_entry_device(hass, mock_config_entry, salon)

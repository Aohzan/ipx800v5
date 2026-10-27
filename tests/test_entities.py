"""Tests of the entities of the GCE IPX800 V5 integration."""

from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.ipx800v5.const import (
    CONF_COMPONENT,
    CONF_DEVICES,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBERS,
    DOMAIN,
    PLATFORMS,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_API_KEY,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_TYPE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import API_KEY, HOST, FakeIpxApi


@pytest.mark.parametrize("platform", PLATFORMS)
async def test_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
    platform: Platform,
) -> None:
    """Test the entities and their states."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("custom_components.ipx800v5.PLATFORMS", [platform])
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("domain", "service", "entity_id", "data"),
    [
        ("button", "press", "button.ipx800_v5_reboot", {}),
        (
            "climate",
            "set_preset_mode",
            "climate.radiateurs_fp_1",
            {"preset_mode": "eco"},
        ),
        ("climate", "set_hvac_mode", "climate.radiateurs_fp_1", {"hvac_mode": "off"}),
        ("climate", "set_hvac_mode", "climate.radiateurs_fp_1", {"hvac_mode": "heat"}),
        ("climate", "turn_on", "climate.radiateurs_fp_2", {}),
        ("climate", "turn_off", "climate.radiateurs_fp_1", {}),
        ("climate", "set_temperature", "climate.thermostat", {"temperature": 19}),
        ("climate", "set_hvac_mode", "climate.thermostat", {"hvac_mode": "off"}),
        ("climate", "turn_on", "climate.thermostat", {}),
        ("climate", "turn_off", "climate.thermostat", {}),
        (
            "climate",
            "set_preset_mode",
            "climate.thermostat",
            {"preset_mode": "comfort"},
        ),
        ("climate", "set_preset_mode", "climate.thermostat", {"preset_mode": "eco"}),
        ("climate", "set_preset_mode", "climate.thermostat", {"preset_mode": "away"}),
        ("climate", "set_preset_mode", "climate.thermostat", {"preset_mode": "none"}),
        ("cover", "open_cover", "cover.volets_vr_1", {}),
        ("cover", "close_cover", "cover.volets_vr_1", {}),
        ("cover", "stop_cover", "cover.volets_vr_1", {}),
        ("cover", "set_cover_position", "cover.volets_vr_1", {"position": 40}),
        ("cover", "open_cover_tilt", "cover.volets_vr_1", {}),
        ("cover", "close_cover_tilt", "cover.volets_vr_1", {}),
        ("light", "turn_on", "light.ipx800_v5_ipx_ndeg0_relais_1", {}),
        ("light", "turn_off", "light.ipx800_v5_ipx_ndeg0_relais_1", {}),
        ("light", "toggle", "light.ipx800_v5_ipx_ndeg0_relais_1", {}),
        ("light", "turn_on", "light.x8r_ndeg0_relais_1", {}),
        ("light", "turn_off", "light.x8r_ndeg0_relais_1", {}),
        ("light", "toggle", "light.x8r_ndeg0_relais_1", {}),
        ("light", "turn_on", "light.variateur_sortie_1", {"brightness": 128}),
        ("light", "turn_on", "light.variateur_sortie_1", {}),
        ("light", "turn_off", "light.variateur_sortie_1", {}),
        ("light", "toggle", "light.variateur_sortie_1", {}),
        ("light", "turn_on", "light.pwm_sortie_1", {"brightness": 128}),
        ("light", "turn_on", "light.pwm_sortie_1", {}),
        ("light", "turn_off", "light.pwm_sortie_1", {}),
        ("light", "toggle", "light.pwm_sortie_1", {}),
        ("light", "turn_on", "light.sorties_0_10v_sortie_1", {"brightness": 128}),
        ("light", "turn_on", "light.sorties_0_10v_sortie_2", {}),
        ("light", "turn_off", "light.sorties_0_10v_sortie_1", {}),
        ("light", "toggle", "light.sorties_0_10v_sortie_1", {}),
        ("number", "set_value", "number.compteur", {"value": 12}),
        ("number", "set_value", "number.tempo_garage_delay", {"value": 60}),
        (
            "select",
            "select_option",
            "select.ecran_current_screen",
            {"option": "Screen 1"},
        ),
        ("switch", "turn_on", "switch.ipx800_v5_relais_2", {}),
        ("switch", "turn_off", "switch.ipx800_v5_relais_3", {}),
        ("switch", "toggle", "switch.ipx800_v5_relais_2", {}),
        ("switch", "turn_on", "switch.ipx800_v5_open_collector_2", {}),
        ("switch", "turn_off", "switch.ipx800_v5_open_collector_1", {}),
        ("switch", "toggle", "switch.ipx800_v5_open_collector_1", {}),
        ("switch", "turn_on", "switch.x8r_ndeg0_relais_2", {}),
        ("switch", "turn_off", "switch.x8r_ndeg0_relais_2", {}),
        ("switch", "toggle", "switch.x8r_ndeg0_relais_2", {}),
        ("switch", "turn_on", "switch.ecran_screen_state", {}),
        ("switch", "turn_off", "switch.ecran_screen_state", {}),
        ("switch", "toggle", "switch.ecran_screen_state", {}),
        ("switch", "turn_on", "switch.ecran_screen_lock", {}),
        ("switch", "turn_off", "switch.ecran_screen_lock", {}),
        ("switch", "toggle", "switch.ecran_screen_lock", {}),
        ("switch", "turn_on", "switch.tempo_garage_enable", {}),
        ("switch", "turn_off", "switch.tempo_garage_enable", {}),
    ],
)
async def test_actions(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
    domain: str,
    service: str,
    entity_id: str,
    data: dict[str, Any],
) -> None:
    """Test the actions send a request to the IPX800."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )

    assert mock_ipx.requests


async def test_thermostat_params(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test the parameters of a thermostat, and its cooling mode."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    for param, key in (
        ("comfort", "setPointComfort"),
        ("eco", "setPointEco"),
        ("nofrost", "setPointNoFrost"),
    ):
        await hass.services.async_call(
            "number",
            "set_value",
            {ATTR_ENTITY_ID: f"number.thermostat_{param}_temperature", "value": 15},
            blocking=True,
        )
        assert mock_ipx.requests[-1] == ("PUT", "object/thermostat/11", {key: 15})
        assert (
            float(hass.states.get(f"number.thermostat_{param}_temperature").state) == 15
        )

    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: "switch.thermostat_cooling_mode"},
        blocking=True,
    )
    # The climate entity is updated by the refresh requested by the switch
    freezer.tick(1)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert mock_ipx.requests[-1] == ("PUT", "object/thermostat/11", {"invMode": True})
    state = hass.states.get("climate.thermostat")
    assert state.state == "cool"
    assert state.attributes["max_temp"] == 35

    await hass.services.async_call(
        "switch",
        "turn_off",
        {ATTR_ENTITY_ID: "switch.thermostat_cooling_mode"},
        blocking=True,
    )
    freezer.tick(1)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("climate.thermostat").state == "heat"


YAML_DEVICES = [
    {
        CONF_NAME: "Bandeau RGB",
        CONF_COMPONENT: "light",
        CONF_EXT_TYPE: "xpwm",
        CONF_EXT_NUMBER: 0,
        CONF_TYPE: "xpwm_rgb",
        CONF_IO_NUMBERS: [1, 2, 3],
    },
    {
        CONF_NAME: "Bandeau RGBW",
        CONF_COMPONENT: "light",
        CONF_EXT_TYPE: "xpwm",
        CONF_EXT_NUMBER: 0,
        CONF_TYPE: "xpwm_rgbw",
        CONF_IO_NUMBERS: [4, 5, 6, 7],
    },
    {
        CONF_NAME: "Sèche-serviettes",
        CONF_COMPONENT: "climate",
        CONF_EXT_TYPE: "ipx",
        CONF_IO_NUMBERS: [7, 8],
    },
    {
        CONF_NAME: "Radiateur X-8R",
        CONF_COMPONENT: "climate",
        CONF_EXT_TYPE: "x8r",
        CONF_EXT_NUMBER: 0,
        CONF_IO_NUMBERS: [1, 2],
    },
    {
        CONF_NAME: "Virtual IO",
        CONF_COMPONENT: "switch",
        CONF_EXT_TYPE: "ipx",
        CONF_TYPE: "io",
        CONF_ID: 150,
    },
    {
        CONF_NAME: "Virtual ANA",
        CONF_COMPONENT: "number",
        CONF_EXT_TYPE: "ipx",
        CONF_TYPE: "ana",
        CONF_ID: 151,
    },
]


@pytest.mark.parametrize(
    ("domain", "service", "entity_id", "data"),
    [
        (
            "light",
            "turn_on",
            "light.xpwm_ndeg0_bandeau_rgb",
            {"rgb_color": [255, 0, 0]},
        ),
        ("light", "turn_on", "light.xpwm_ndeg0_bandeau_rgb", {"brightness": 100}),
        ("light", "turn_on", "light.xpwm_ndeg0_bandeau_rgb", {}),
        ("light", "turn_off", "light.xpwm_ndeg0_bandeau_rgb", {}),
        (
            "light",
            "turn_on",
            "light.xpwm_ndeg0_bandeau_rgbw",
            {"rgbw_color": [255, 0, 0, 10]},
        ),
        ("light", "turn_on", "light.xpwm_ndeg0_bandeau_rgbw", {"brightness": 100}),
        ("light", "turn_on", "light.xpwm_ndeg0_bandeau_rgbw", {}),
        ("light", "turn_off", "light.xpwm_ndeg0_bandeau_rgbw", {}),
        (
            "climate",
            "set_hvac_mode",
            "climate.ipx800_v5_seche_serviettes",
            {"hvac_mode": "off"},
        ),
        ("climate", "turn_on", "climate.ipx800_v5_seche_serviettes", {}),
        ("climate", "turn_off", "climate.ipx800_v5_seche_serviettes", {}),
        (
            "climate",
            "set_preset_mode",
            "climate.x8r_ndeg0_radiateur_x_8r",
            {"preset_mode": "comfort"},
        ),
        (
            "climate",
            "set_preset_mode",
            "climate.x8r_ndeg0_radiateur_x_8r",
            {"preset_mode": "eco"},
        ),
        (
            "climate",
            "set_preset_mode",
            "climate.x8r_ndeg0_radiateur_x_8r",
            {"preset_mode": "away"},
        ),
        (
            "climate",
            "set_preset_mode",
            "climate.x8r_ndeg0_radiateur_x_8r",
            {"preset_mode": "none"},
        ),
        ("switch", "turn_on", "switch.ipx800_v5_virtual_io", {}),
        ("switch", "turn_off", "switch.ipx800_v5_virtual_io", {}),
        ("switch", "toggle", "switch.ipx800_v5_virtual_io", {}),
        ("number", "set_value", "number.ipx800_v5_virtual_ana", {"value": 12}),
    ],
)
async def test_yaml_actions(
    hass: HomeAssistant,
    mock_ipx: FakeIpxApi,
    domain: str,
    service: str,
    entity_id: str,
    data: dict[str, Any],
) -> None:
    """Test the actions of the entities only available from configuration.yaml."""
    config = {
        CONF_NAME: "IPX800 V5",
        CONF_HOST: HOST,
        CONF_API_KEY: API_KEY,
        CONF_DEVICES: YAML_DEVICES,
    }
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [config]})
    await hass.async_block_till_done()

    await hass.services.async_call(
        domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True
    )

    assert mock_ipx.requests

"""Tests of the lights of the GCE IPX800 V5 integration."""

from freezegun.api import FrozenDateTimeFactory
from pypx800v5 import IPX800RequestError
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.ipx800v5.const import (
    CONF_COMPONENT,
    CONF_DEVICES,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_TRANSITION,
    DOMAIN,
)
from custom_components.ipx800v5.light import COMMANDED_LEVELS_TIMEOUT
from homeassistant.const import ATTR_ENTITY_ID, CONF_API_KEY, CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import API_KEY, HOST, FakeIpxApi

DIMMER = "light.variateur_sortie_1"


@pytest.fixture
async def dimmer_ids(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> tuple[int, int]:
    """Set up the IPX800 with the X-Dimmer output 1 on at 50%.

    Return the IDs of its position and its command.
    """
    dimmer = mock_ipx.extensions["xdimmer"][0]
    position_id = dimmer["anaPosition_id"][0]
    mock_ipx.values[dimmer["ioOn_id"][0]]["on"] = True
    mock_ipx.values[position_id]["value"] = 50
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return position_id, dimmer["anaCommand_id"][0]


async def _step(hass: HomeAssistant, step_pct: int) -> None:
    """Change the brightness of the X-Dimmer light by a step."""
    await hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: DIMMER, "brightness_step_pct": step_pct},
        blocking=True,
    )


def _brightness_pct(hass: HomeAssistant) -> int:
    """Return the brightness of the X-Dimmer light in percent."""
    return round(hass.states.get(DIMMER).attributes["brightness"] / 255 * 100)


async def _tick(hass: HomeAssistant, freezer: FrozenDateTimeFactory, delay: float):
    """Move the time forward."""
    freezer.tick(delay)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_brightness_steps_before_refresh(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_ipx: FakeIpxApi,
    dimmer_ids: tuple[int, int],
) -> None:
    """Test the brightness steps start from the commanded level."""
    _, command_id = dimmer_ids

    await _step(hass, 10)
    await _step(hass, 10)

    assert [
        data["value"]
        for _, path, data in mock_ipx.requests
        if path == f"core/ana/{command_id}"
    ] == [60, 70]
    assert _brightness_pct(hass) == 70

    # The refresh doesn't report the level yet: the X-Dimmer is in transition
    await _tick(hass, freezer, 1)
    assert _brightness_pct(hass) == 70

    # Never reported: the IPX800 is right
    await _tick(hass, freezer, COMMANDED_LEVELS_TIMEOUT)
    assert _brightness_pct(hass) == 50


async def test_commanded_level_reported(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
    dimmer_ids: tuple[int, int],
) -> None:
    """Test the levels of the IPX800 are shown once it reported the command."""
    position_id, _ = dimmer_ids

    await _step(hass, 10)
    mock_ipx.values[position_id]["value"] = 60
    await _tick(hass, freezer, 1)
    assert _brightness_pct(hass) == 60

    # Changed on the IPX800, before the timeout of the commanded level
    mock_ipx.values[position_id]["value"] = 20
    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert _brightness_pct(hass) == 20


async def test_command_error(
    hass: HomeAssistant, mock_ipx: FakeIpxApi, dimmer_ids: tuple[int, int]
) -> None:
    """Test the levels of the IPX800 are shown when a command fails."""
    mock_ipx.error = IPX800RequestError("Error")

    with pytest.raises(IPX800RequestError):
        await _step(hass, 10)

    assert _brightness_pct(hass) == 50


async def test_turn_off_then_on(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    dimmer_ids: tuple[int, int],
) -> None:
    """Test turning on an X-Dimmer shows the level reported by the IPX800."""
    await hass.services.async_call(
        "light", "turn_off", {ATTR_ENTITY_ID: DIMMER}, blocking=True
    )
    assert hass.states.get(DIMMER).state == "off"

    # Back to a level only the IPX800 knows
    await hass.services.async_call(
        "light", "turn_on", {ATTR_ENTITY_ID: DIMMER}, blocking=True
    )
    await _tick(hass, freezer, 1)
    assert hass.states.get(DIMMER).state == "on"
    assert _brightness_pct(hass) == 50


async def test_rgb_brightness(hass: HomeAssistant, mock_ipx: FakeIpxApi) -> None:
    """Test the brightness of a RGB light keeps its color."""
    channel_ids = mock_ipx.extensions["xpwm"][0]["anaCommand_id"][:3]
    for channel_id, level in zip(channel_ids, (100, 50, 0), strict=True):
        mock_ipx.values[channel_id]["value"] = level
    config = {
        CONF_NAME: "IPX800 V5",
        CONF_HOST: HOST,
        CONF_API_KEY: API_KEY,
        CONF_DEVICES: [
            {
                CONF_NAME: "Bandeau RGB",
                CONF_COMPONENT: "light",
                CONF_EXT_TYPE: "xpwm",
                CONF_EXT_NUMBER: 0,
                "type": "xpwm_rgb",
                "io_numbers": [1, 2, 3],
            }
        ],
    }
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [config]})
    await hass.async_block_till_done()
    entity_id = "light.xpwm_ndeg0_bandeau_rgb"

    await hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: entity_id, "brightness_step_pct": -50},
        blocking=True,
    )

    assert [data["value"] for _, _, data in mock_ipx.requests] == [50, 25, 0]
    assert hass.states.get(entity_id).attributes["rgb_color"] == (128, 64, 0)
    assert hass.states.get(entity_id).attributes["brightness"] == 128


async def test_yaml_transition_ignored(
    hass: HomeAssistant, mock_ipx: FakeIpxApi, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the removed transition option still validates."""
    config = {
        CONF_NAME: "IPX800 V5",
        CONF_HOST: HOST,
        CONF_API_KEY: API_KEY,
        CONF_DEVICES: [
            {
                CONF_NAME: "Lumière",
                CONF_COMPONENT: "light",
                CONF_EXT_TYPE: "xdimmer",
                CONF_EXT_NUMBER: 0,
                CONF_IO_NUMBER: 1,
                CONF_TRANSITION: 1,
            }
        ],
    }

    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [config]})
    await hass.async_block_till_done()

    assert "transition" in caplog.text
    assert hass.states.get("light.xdimmer_ndeg0_lumiere") is not None


async def test_turn_on_level_from_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test a level turns on an X-Dimmer even when it's its command already."""
    dimmer = mock_ipx.extensions["xdimmer"][0]
    io_id = dimmer["ioOn_id"][0]
    mock_ipx.values[io_id]["on"] = False
    mock_ipx.values[dimmer["anaPosition_id"][0]]["value"] = 0
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: DIMMER, "brightness_pct": 20},
        blocking=True,
    )
    await hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: DIMMER, "brightness_pct": 30},
        blocking=True,
    )

    assert mock_ipx.requests == [
        ("PUT", f"core/ana/{dimmer['anaCommand_id'][0]}", {"value": 20}),
        ("PUT", f"core/io/{io_id}", {"on": True}),
        # Already on
        ("PUT", f"core/ana/{dimmer['anaCommand_id'][0]}", {"value": 30}),
    ]

"""Tests of the diagnostics of the GCE IPX800 V5 integration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion

from custom_components.ipx800v5.const import DOMAIN
from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import FakeIpxApi
from .test_init import YAML_CONFIG


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test the diagnostics redact the API key, push password and codes."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        await get_diagnostics_for_config_entry(hass, hass_client, mock_config_entry)
        == snapshot
    )


async def test_diagnostics_codes(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test the last code of an access control is redacted."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [YAML_CONFIG]})
    await hass.async_block_till_done()
    (entry,) = hass.config_entries.async_entries(DOMAIN)

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    code_id = mock_ipx.objects["access_control"][0]["bindCurrentCode_id"]
    assert diagnostics["data"][str(code_id)]["value"] == REDACTED

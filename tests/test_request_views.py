"""Tests of the push requests of the IPX800 V5."""

from base64 import b64encode
from http import HTTPStatus

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.ipx800v5.const import DOMAIN
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .conftest import ENTRY_DATA, PUSH_PASSWORD, FakeIpxApi

# Requests of the test client come from the local host
LOCAL_HOST = "127.0.0.1"


def _auth(password: str = PUSH_PASSWORD) -> dict[str, str]:
    """Return the authorization header of a push request."""
    token = b64encode(f"ipx800:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
async def push_entry(hass: HomeAssistant, mock_ipx: FakeIpxApi) -> MockConfigEntry:
    """Set up an entry with push requests from the local host."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA | {CONF_HOST: LOCAL_HOST})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.usefixtures("push_entry")
async def test_push_state(
    hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator
) -> None:
    """Test the state of an entity pushed by the IPX800."""
    client = await hass_client_no_auth()
    entity_id = "switch.ipx800_v5_relais_2"

    response = await client.get(f"/api/ipx800_v5/{entity_id}/on", headers=_auth())
    assert response.status == HTTPStatus.OK
    assert hass.states.get(entity_id).state == "on"

    response = await client.get("/api/ipx800_v5/switch.unknown/on", headers=_auth())
    assert response.status == HTTPStatus.BAD_REQUEST


@pytest.mark.usefixtures("push_entry")
async def test_push_data(
    hass: HomeAssistant, hass_client_no_auth: ClientSessionGenerator
) -> None:
    """Test the states of several entities pushed by the IPX800."""
    client = await hass_client_no_auth()

    response = await client.get(
        "/api/ipx800_v5_data/switch.ipx800_v5_relais_2=1&switch.ipx800_v5_relais_3=0"
        "&malformed&switch.unknown=1",
        headers=_auth(),
    )
    assert response.status == HTTPStatus.OK
    assert hass.states.get("switch.ipx800_v5_relais_2").state == "on"
    assert hass.states.get("switch.ipx800_v5_relais_3").state == "off"


async def test_push_refresh(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    push_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test a refresh asked by the IPX800, after a reload of the entry."""
    assert await hass.config_entries.async_reload(push_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()

    response = await client.get("/api/ipx800_v5_refresh", headers=_auth())
    assert response.status == HTTPStatus.OK


@pytest.mark.parametrize(
    "headers",
    [
        {},
        _auth("wrong"),
        {"Authorization": "Bearer token"},
        {"Authorization": "Basic not-base64"},
    ],
)
@pytest.mark.usefixtures("push_entry")
async def test_push_unauthorized(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    headers: dict[str, str],
) -> None:
    """Test the push requests without the right credentials are refused."""
    client = await hass_client_no_auth()

    response = await client.get("/api/ipx800_v5_refresh", headers=headers)
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_push_other_host(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
) -> None:
    """Test the push requests not coming from the IPX800 are refused."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()

    response = await client.get("/api/ipx800_v5_data/a=1", headers=_auth())
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_push_entry_unloaded(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
    push_entry: MockConfigEntry,
) -> None:
    """Test the push requests are refused once the entry is unloaded."""
    await hass.config_entries.async_unload(push_entry.entry_id)
    client = await hass_client_no_auth()

    response = await client.get(
        "/api/ipx800_v5/switch.ipx800_v5_relais_2/on", headers=_auth()
    )
    assert response.status == HTTPStatus.UNAUTHORIZED

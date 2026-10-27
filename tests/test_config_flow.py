"""Tests of the config flow of the GCE IPX800 V5 integration."""

from typing import Any

from pypx800v5 import (
    IPX800CannotConnectError,
    IPX800InvalidAuthError,
    IPX800RequestError,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ipx800v5.const import (
    CONF_COMPONENT,
    CONF_DEVICES,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_PUSH_PASSWORD,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER, ConfigFlowResult
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import API_KEY, HOST, PORT, FakeIpxApi

USER_INPUT = {
    CONF_NAME: "IPX800 V5",
    CONF_HOST: HOST,
    CONF_PORT: PORT,
    CONF_API_KEY: API_KEY,
}
# Relays left to their default type
PARAMS_INPUT = {
    CONF_SCAN_INTERVAL: 10,
    CONF_API_KEY: API_KEY,
    CONF_PUSH_PASSWORD: "push",
    **{f"ipx_0_{relay}": "switch" for relay in range(1, 9)},
    **{f"x8r_0_{relay}": "switch" for relay in range(1, 9)},
    "x8r_0_2": "light",
}


def _suggested_values(result: ConfigFlowResult) -> dict[str, Any]:
    """Return the values suggested by a form."""
    return {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description and "suggested_value" in key.description
    }


async def test_user_flow(hass: HomeAssistant, mock_ipx: FakeIpxApi) -> None:
    """Test the creation of an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "params"
    # The relays of the IPX800 and of its X-8R extension
    fields = [str(key) for key in result["data_schema"].schema]
    assert fields[3:] == list(PARAMS_INPUT)[3:11] + [
        f"x8r_0_{relay}" for relay in range(1, 9)
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], PARAMS_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == HOST
    assert result["result"].unique_id == f"{DOMAIN}, {HOST}"
    data = result["data"]
    assert data[CONF_SCAN_INTERVAL] == 10
    assert data[CONF_PUSH_PASSWORD] == "push"
    assert len(data[CONF_DEVICES]) == 16
    assert data[CONF_DEVICES][9] == {
        CONF_NAME: "X8R N°0 Relais 2",
        CONF_EXT_TYPE: "x8r",
        CONF_EXT_NUMBER: 0,
        CONF_EXT_NAME: "X8R N°0",
        CONF_IO_NUMBER: 2,
        CONF_COMPONENT: "light",
    }


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (IPX800CannotConnectError, "cannot_connect"),
        (IPX800RequestError, "cannot_connect"),
        (IPX800InvalidAuthError, "invalid_auth"),
        (RuntimeError, "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_ipx: FakeIpxApi,
    exception: type[Exception],
    error: str,
) -> None:
    """Test the connection errors, and the recovery."""
    mock_ipx.error = exception()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_ipx.error = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["step_id"] == "params"


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test an IPX800 can only be configured once."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_already_configured_from_ui(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the YAML configuration of an IPX800 configured from the UI is ignored."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert CONF_DEVICES in mock_config_entry.data


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the options update the entry and reload it."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["step_id"] == "init"
    user_input = PARAMS_INPUT | {CONF_SCAN_INTERVAL: 30, "ipx_0_1": "light"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 30
    assert mock_config_entry.options[CONF_DEVICES][0][CONF_COMPONENT] == "light"
    # The submitted values are not modified
    assert user_input[CONF_SCAN_INTERVAL] == 30
    # Reloaded with the new options
    assert mock_config_entry.runtime_data.update_interval.total_seconds() == 30
    assert hass.states.get("light.ipx800_v5_ipx_ndeg0_relais_1") is not None


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (IPX800CannotConnectError, "cannot_connect"),
        (RuntimeError, "unknown"),
    ],
)
async def test_options_flow_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ipx: FakeIpxApi,
    exception: type[Exception],
    error: str,
) -> None:
    """Test the options show an error when the IPX800 can't be read."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_ipx.error = exception()
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # Submitting the form tries again
    mock_ipx.error = None
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert "ipx_0_1" in [str(key) for key in result["data_schema"].schema]


async def test_options_flow_yaml(hass: HomeAssistant, mock_ipx: FakeIpxApi) -> None:
    """Test the options of an entry from configuration.yaml."""
    entry = MockConfigEntry(
        domain=DOMAIN, source=SOURCE_IMPORT, data=USER_INPUT | {CONF_DEVICES: []}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert [str(key) for key in result["data_schema"].schema] == [CONF_SCAN_INTERVAL]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 20}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 20}


async def test_reauth_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the new API key replaces the one of the options."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_API_KEY: "old", CONF_SCAN_INTERVAL: 20}
    )

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    assert _suggested_values(result) == {}

    mock_ipx.error = IPX800InvalidAuthError()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}
    assert _suggested_values(result) == {}

    mock_ipx.error = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "new"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == "new"
    assert mock_config_entry.options == {CONF_SCAN_INTERVAL: 20}


async def test_reauth_flow_yaml(hass: HomeAssistant, mock_ipx: FakeIpxApi) -> None:
    """Test the API key of configuration.yaml can't be changed in the UI."""
    entry = MockConfigEntry(
        domain=DOMAIN, source=SOURCE_IMPORT, data=USER_INPUT | {CONF_DEVICES: []}
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "yaml_entry"


async def test_reconfigure_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the address of the IPX800 can be changed."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    assert _suggested_values(result) == {CONF_HOST: HOST, CONF_PORT: PORT}

    mock_ipx.error = RuntimeError()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.20", CONF_PORT: 8080}
    )
    assert result["errors"] == {"base": "unknown"}

    mock_ipx.error = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.20", CONF_PORT: 8080}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.20"
    assert mock_config_entry.data[CONF_PORT] == 8080
    assert mock_config_entry.unique_id == f"{DOMAIN}, 192.168.1.20"


async def test_reconfigure_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_ipx: FakeIpxApi
) -> None:
    """Test the address of another configured IPX800 is refused."""
    mock_config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, unique_id=f"{DOMAIN}, 192.168.1.20", data={}
    ).add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.20", CONF_PORT: 80}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

"""Fixtures of the GCE IPX800 V5 tests."""

from collections.abc import Generator
from itertools import count
from typing import Any
from unittest.mock import patch

from pypx800v5 import IPX800
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

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
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)

HOST = "192.168.1.240"
PORT = 80
MAC = "00:04:A3:00:00:01"
API_KEY = "apikey"
PUSH_PASSWORD = "push"

# Entry created from the UI, with the relay types chosen in the params step
ENTRY_DATA = {
    CONF_NAME: "IPX800 V5",
    CONF_HOST: HOST,
    CONF_PORT: PORT,
    CONF_API_KEY: API_KEY,
    CONF_SCAN_INTERVAL: 15,
    CONF_PUSH_PASSWORD: PUSH_PASSWORD,
    CONF_DEVICES: [
        {
            CONF_NAME: "IPX N°0 Relais 1",
            CONF_EXT_TYPE: "ipx",
            CONF_EXT_NUMBER: 0,
            CONF_EXT_NAME: "IPX N°0",
            CONF_IO_NUMBER: 1,
            CONF_COMPONENT: "light",
        },
        {
            CONF_NAME: "X8R N°0 Relais 1",
            CONF_EXT_TYPE: "x8r",
            CONF_EXT_NUMBER: 0,
            CONF_EXT_NAME: "X8R N°0",
            CONF_IO_NUMBER: 1,
            CONF_COMPONENT: "light",
        },
        {
            CONF_NAME: "X8R N°0 Relais 2",
            CONF_EXT_TYPE: "x8r",
            CONF_EXT_NUMBER: 0,
            CONF_EXT_NAME: "X8R N°0",
            CONF_IO_NUMBER: 2,
            CONF_COMPONENT: "switch",
        },
    ],
}


def _ipx_config(ids: count) -> dict[str, Any]:
    """Return the configuration of an IPX800 V5 with its IO and analog IDs."""

    def io_ids(number: int) -> list[int]:
        return [next(ids) for _ in range(number)]

    return {
        "ioRelayState_id": io_ids(8),
        "ioRelays_id": io_ids(8),
        "ioCollOutputState_id": io_ids(4),
        "ioCollOutput_id": io_ids(4),
        "ioDInput_id": io_ids(8),
        "ana_IPX_Input": io_ids(4),
        "ioCollInput_id": io_ids(4),
        "ioIPXReset_id": next(ids),
        "ioDetectionAC_id": next(ids),
        "anaHeapFree_id": next(ids),
        "anaIPXClock_id": next(ids),
        # Not known by the integration, named after the analog
        "anaIPXNewCounter_id": next(ids),
    }


class FakeIpxApi:
    """Answer the API requests of pypx800v5 like an IPX800 V5."""

    def __init__(self) -> None:
        """Build the configuration and the values of the IPX800."""
        ids = count(100)

        def io_ids(number: int) -> list[int]:
            return [next(ids) for _ in range(number)]

        self.error: Exception | None = None
        self.mac_address = MAC
        self.requests: list[tuple[str, str, Any]] = []
        self.ipx_config = _ipx_config(ids)
        self.extensions: dict[str, list[dict[str, Any]]] = {
            "x8r": [
                {
                    "_id": 1,
                    "name": "X-8R 1",
                    "ioOutputState_id": io_ids(8),
                    "ioOutput_id": io_ids(8),
                    "ioLongPush_id": io_ids(8),
                }
            ],
            "xthl": [
                {
                    "_id": 2,
                    "name": "Salon",
                    "anaTemp_id": next(ids),
                    "anaHum_id": next(ids),
                    "anaLum_id": next(ids),
                }
            ],
            "x4fp": [
                {
                    "_id": 3,
                    "name": "Radiateurs",
                    **{
                        f"io{mode}_id": io_ids(4)
                        for mode in (
                            "Comfort",
                            "Comfort_1",
                            "Comfort_2",
                            "Eco",
                            "AntiFreeze",
                            "Stop",
                        )
                    },
                }
            ],
            "x4vr": [
                {
                    "_id": 4,
                    "name": "Volets",
                    "mode": 2,
                    "anaPosition_id": io_ids(4),
                    "anaCommand_id": io_ids(4),
                    "ioCommandUp_id": io_ids(4),
                    "ioCommandDown_id": io_ids(4),
                    "ioCommandStop_id": io_ids(4),
                    "ioCommandBsoUp_id": io_ids(4),
                    "ioCommandBsoDown_id": io_ids(4),
                }
            ],
            "xdimmer": [
                {
                    "_id": 5,
                    "name": "Variateur",
                    "ioOn_id": io_ids(4),
                    "anaPosition_id": io_ids(4),
                    "anaCommand_id": io_ids(4),
                }
            ],
            "xpwm": [{"_id": 6, "name": "PWM", "anaCommand_id": io_ids(12)}],
            "x010v": [
                {
                    "_id": 7,
                    "name": "Sorties 0-10V",
                    "ioOn_id": io_ids(4),
                    "anaLevel_id": io_ids(4),
                    "anaCommand_id": io_ids(4),
                }
            ],
            "x8d": [{"_id": 8, "name": "X-8D", "ioInput_id": io_ids(8)}],
            "x400": [
                {
                    "_id": 9,
                    "name": "Pinces",
                    "func": "x400 CT",
                    "anaOutputVal_id": io_ids(4),
                }
            ],
            "xdisplay": [
                {
                    "_id": 10,
                    "name": "Ecran",
                    "ioOnScreen_id": next(ids),
                    "ioLockSet_id": next(ids),
                    "anaSelectScreen_id": next(ids),
                    "autoOff": 30,
                    "sensitive": 2,
                    "bVersion2": True,
                    "screensType": [3, 7, 0],
                    "strScreenName_id": io_ids(3),
                }
            ],
        }
        self.objects: dict[str, list[dict[str, Any]]] = {
            "thermostat": [
                {
                    "_id": 11,
                    "name": "Thermostat",
                    "ioOutput_id": next(ids),
                    "ioFault_id": next(ids),
                    "ioOnOff_id": next(ids),
                    "anaMeasure_id": next(ids),
                    "anaCurrSetPoint_id": next(ids),
                    "ioEco_id": next(ids),
                    "ioComfort_id": next(ids),
                    "ioNoFrost_id": next(ids),
                    "hysteresis": 0.5,
                    "setPointComfort": 20,
                    "setPointEco": 18,
                    "setPointNoFrost": 8,
                    "invMode": False,
                }
            ],
            "counter": [
                {
                    "_id": 12,
                    "name": "Compteur",
                    "anaOut_id": next(ids),
                    "anaSetValue_id": next(ids),
                    "anaPulseValue_id": next(ids),
                    "ioSet_id": next(ids),
                }
            ],
            "timer": [
                {
                    "_id": 13,
                    "name": "Tempo Garage",
                    "func": "tempo",
                    "ioOut_id": next(ids),
                    "ioEnable_id": next(ids),
                    "anaTime1_id": next(ids),
                },
                # Timer of another kind, ignored
                {"_id": 14, "name": "Minuterie", "func": "timer"},
            ],
            "access_control": [
                {
                    "_id": 15,
                    "name": "Digicode",
                    "ioOut_id": next(ids),
                    "ioFault_id": next(ids),
                    "bindCurrentCode_id": next(ids),
                    "strPoolCode_id": io_ids(2),
                }
            ],
        }
        last_id = next(ids)
        # The IDs are shared by the IO and analog values here: IO on for even
        # IDs, analog values from the ID
        self.values = {
            i: {"_id": i, "on": i % 2 == 0, "value": float(i % 100)}
            for i in range(100, last_id)
        }
        self.strings = {i: f"text {i}" for i in range(100, last_id)}
        self.strings |= {
            screen_id: f"Screen {index}"
            for index, screen_id in enumerate(
                self.extensions["xdisplay"][0]["strScreenName_id"]
            )
        }

    async def request_api(
        self,
        path: str,
        data: dict | None = None,
        params: dict | None = None,
        method: str = "GET",
    ) -> Any:
        """Answer a request of the API."""
        if self.error is not None:
            raise self.error
        if method != "GET":
            self.requests.append((method, path, data))
            return {}
        return self._get(path)

    def _get(self, path: str) -> Any:
        """Return the response of a GET request."""
        match path.split("/"):
            case ["system", "info"]:
                return {
                    "firmwareVersion": "5.6.1",
                    "macAdress": self.mac_address,
                    "hostName": "ipx800",
                }
            case ["system", "ipx"]:
                return self.ipx_config
            case ["ebx", ext_type]:
                return self.extensions.get(ext_type, [])
            case ["object", obj_type]:
                return self.objects.get(obj_type, [])
            case ["core", "io" | "ana"]:
                return list(self.values.values())
            case ["core", "io" | "ana", value_id]:
                return self.values[int(value_id)]
            case ["core", "str", str_id]:
                return {"value": self.strings[int(str_id)]}
        raise AssertionError(f"Unexpected request {path}")


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return the snapshot assertion with the Home Assistant serializer."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable the custom integrations in every test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the config entry of an IPX800 V5 created from the UI."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=HOST,
        unique_id=f"{DOMAIN}, {HOST}",
        data=ENTRY_DATA,
    )


@pytest.fixture
def mock_ipx() -> Generator[FakeIpxApi]:
    """Mock the API of the IPX800 V5."""
    api = FakeIpxApi()

    async def request_api(ipx: IPX800, *args: Any, **kwargs: Any) -> Any:
        return await api.request_api(*args, **kwargs)

    with patch.object(IPX800, "request_api", new=request_api):
        yield api

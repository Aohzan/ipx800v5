"""Data update coordinator of the GCE IPX800 V5 integration."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging
from typing import Any

from pypx800v5 import (
    IPX800,
    OBJECT_ACCESS_CONTROL,
    AccessControl,
    IPX800CannotConnectError,
    IPX800InvalidAuthError,
    IPX800RequestError,
)

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICES,
    CONF_DEVICES_AUTO,
    CONF_DIAG_SENSORS,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    REQUEST_REFRESH_DELAY,
)
from .helpers import (
    build_extensions_entities,
    build_ipx_entities,
    build_ipx_system_entities,
    build_objects_entities,
    filter_entities_by_platform,
    get_entry_config,
    remove_duplicate_entities,
)

_LOGGER = logging.getLogger(__name__)

type IpxConfigEntry = ConfigEntry[IpxCoordinator]


class IpxCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Fetch the IO and analog values of an IPX800 V5."""

    config_entry: IpxConfigEntry

    def __init__(self, hass: HomeAssistant, entry: IpxConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config = get_entry_config(entry)
        scan_interval = self.config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if scan_interval < 10:
            _LOGGER.warning(
                "A scan interval too low has been set, you will send too many requests to your IPX800"
            )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=self.config[CONF_NAME],
            update_interval=timedelta(seconds=scan_interval),
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=REQUEST_REFRESH_DELAY, immediate=False
            ),
        )
        self.ipx = IPX800(
            host=self.config[CONF_HOST],
            port=self.config[CONF_PORT],
            api_key=self.config[CONF_API_KEY],
            session=async_get_clientsession(hass, verify_ssl=False),
        )
        # Configuration of the entities of each platform
        self.devices: dict[Platform, list[dict[str, Any]]] = {}
        # Text values are not part of the global io/ana states
        self.str_ids: list[int] = []

    async def _async_setup(self) -> None:
        """Read the configuration of the IPX800 and build its entities."""
        await self._async_call(self.ipx.init_config)

        # Entities according to the configuration and the discovered
        # extensions and objects
        source = self.config_entry.source
        devices_config = self.config[CONF_DEVICES]
        devices_auto = self.config.get(CONF_DEVICES_AUTO, [])
        auto_entities = [
            *build_ipx_entities(source, devices_config, devices_auto),
            *build_ipx_system_entities(
                self.ipx, self.config.get(CONF_DIAG_SENSORS, False)
            ),
            *build_extensions_entities(source, self.ipx, devices_config, devices_auto),
            *build_objects_entities(source, self.ipx, devices_config, devices_auto),
        ]
        entities = [
            *devices_config,
            *remove_duplicate_entities(auto_entities, devices_config),
        ]
        self.devices = {
            platform: filter_entities_by_platform(entities, platform)
            for platform in PLATFORMS
        }

        # Poll the text values used by the entities
        self.str_ids = [
            AccessControl(self.ipx, device[CONF_EXT_NUMBER]).str_last_code_id
            for device in self.devices[Platform.SENSOR]
            if device[CONF_EXT_TYPE] == OBJECT_ACCESS_CONTROL
        ]

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch the values of the IPX800."""
        return await self._async_call(self._async_fetch)

    async def _async_fetch(self) -> dict[int, dict[str, Any]]:
        """Fetch the IO and analog values, and the text values used."""
        data = await self.ipx.global_get()
        for str_id in self.str_ids:
            data[str_id] = {"_id": str_id, "value": await self.ipx.get_str(str_id)}
        return data

    async def _async_call[T](self, method: Callable[[], Awaitable[T]]) -> T:
        """Call the IPX800 API, raising the Home Assistant exceptions."""
        try:
            return await method()
        except IPX800InvalidAuthError as err:
            if self.config_entry.source == SOURCE_IMPORT:
                # The API key of configuration.yaml replaces a new one at startup
                raise ConfigEntryError(
                    translation_domain=DOMAIN, translation_key="invalid_auth_yaml"
                ) from err
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except (IPX800CannotConnectError, IPX800RequestError) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err

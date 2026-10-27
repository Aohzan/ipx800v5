"""IPX800V5 request views to handle push information."""

from base64 import b64decode
from hmac import compare_digest
from http import HTTPStatus
import logging
from typing import TYPE_CHECKING

from aiohttp import web

from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.util import slugify

from .const import CONF_PUSH_PASSWORD, DOMAIN, PUSH_USERNAME

if TYPE_CHECKING:
    from .coordinator import IpxCoordinator

_LOGGER = logging.getLogger(__name__)


def check_api_auth(request, host, push_password) -> bool:
    """Check authentication on API call."""
    _LOGGER.debug(
        "Check API authentication from %s (expected %s)", request.remote, host
    )
    if (error := _api_auth_error(request, host, push_password)) is not None:
        _LOGGER.warning(error)
        return False
    return True


def _api_auth_error(request, host, push_password) -> str | None:
    """Return why the API call isn't authorized, None if it is."""
    if request.remote != host:
        return "API call not coming from IPX800 IP."
    if "Authorization" not in request.headers:
        return "API call no authentication provided."
    split = request.headers["Authorization"].strip().split(" ")
    if len(split) != 2 or split[0].strip().lower() != "basic":
        return "Malformed Authorization header"
    try:
        username, password = b64decode(split[1]).decode().split(":", 1)
    except ValueError:
        return "Malformed Authorization header"
    if username != PUSH_USERNAME or not compare_digest(
        password.encode(), push_password.encode()
    ):
        return "API call authentication invalid."
    return None


class IpxPushView(HomeAssistantView):
    """Base view for the push requests of an IPX800 config entry.

    Views can't be unregistered, so they are registered once and read the
    config entry on each request to follow its reloads.
    """

    requires_auth = False

    def __init__(self, entry_id: str) -> None:
        """Init the IPX push view."""
        self.entry_id = entry_id
        super().__init__()

    def get_coordinator(self, request) -> IpxCoordinator | None:
        """Return the coordinator of the entry if the request is authorized."""
        entry = request.app[KEY_HASS].config_entries.async_get_entry(self.entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
            or (push_password := entry.runtime_data.config.get(CONF_PUSH_PASSWORD))
            is None
        ):
            _LOGGER.warning("Push request for an IPX800 not loaded or without push")
            return None
        if not check_api_auth(
            request, entry.runtime_data.config[CONF_HOST], push_password
        ):
            return None
        return entry.runtime_data


class IpxRequestView(IpxPushView):
    """Provide a page for the device to call."""

    name = "api:ipx800v5"

    def __init__(self, entry_id: str, ipx_name: str) -> None:
        """Init the IPX view."""
        super().__init__(entry_id)
        self.url = f"/api/{slugify(ipx_name)}/{{entity_id}}/{{state}}"
        _LOGGER.info("Dedicated push url for '%s': '%s'", ipx_name, self.url)

    async def get(self, request, entity_id, state):
        """Respond to requests from the device."""
        if self.get_coordinator(request) is None:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        _LOGGER.debug("State update pushed from IPX")
        hass = request.app[KEY_HASS]
        old_state = hass.states.get(entity_id)
        _LOGGER.debug("Update %s to state %s", entity_id, state)
        if old_state:
            hass.states.async_set(entity_id, state, old_state.attributes)
            return web.Response(status=HTTPStatus.OK, text="OK")
        _LOGGER.warning("Entity not found for state updating: %s", entity_id)
        return web.Response(status=HTTPStatus.BAD_REQUEST)


class IpxRequestDataView(IpxPushView):
    """Provide a page for the device to call for send multiple data at once."""

    name = "api:ipx800v5_data"

    def __init__(self, entry_id: str, ipx_name: str) -> None:
        """Init the IPX view."""
        super().__init__(entry_id)
        self.url = f"/api/{slugify(ipx_name)}_data/{{data}}"
        _LOGGER.info("Dedicated push data url for '%s': '%s'", ipx_name, self.url)

    async def get(self, request, data):
        """Respond to requests from the device."""
        if self.get_coordinator(request) is None:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        _LOGGER.debug("State update pushed from IPX")
        hass = request.app[KEY_HASS]
        entities_data = data.split("&")
        for entity_data in entities_data:
            entity_id, separator, value = entity_data.partition("=")
            if not separator:
                _LOGGER.warning("Malformed push data ignored: %s", entity_data)
                continue
            state = "on" if value in ["1", "on", "true"] else "off"

            old_state = hass.states.get(entity_id)
            _LOGGER.debug("Update %s to state %s", entity_id, state)
            if old_state:
                hass.states.async_set(entity_id, state, old_state.attributes)
            else:
                _LOGGER.warning("Entity not found for state updating: %s", entity_id)

        return web.Response(status=HTTPStatus.OK, text="OK")


class IpxRequestRefreshView(IpxPushView):
    """Provide a page for the device to call for send multiple data at once."""

    name = "api:ipx800v5_refresh"

    def __init__(self, entry_id: str, ipx_name: str) -> None:
        """Init the IPX view."""
        super().__init__(entry_id)
        self.url = f"/api/{slugify(ipx_name)}_refresh"
        _LOGGER.info("Dedicated push refresh url for '%s': '%s'", ipx_name, self.url)

    async def get(self, request):
        """Respond to requests from the device."""
        if (coordinator := self.get_coordinator(request)) is None:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        _LOGGER.debug("Update asked from IPX PUSH")
        await coordinator.async_request_refresh()
        return web.Response(status=HTTPStatus.OK, text="OK")

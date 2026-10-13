"""IPX800V5 request views to handle push information."""

import logging
from base64 import b64decode
from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_HOST
from homeassistant.util import slugify

from .const import CONF_PUSH_PASSWORD, COORDINATOR, DOMAIN, PUSH_USERNAME

_LOGGER = logging.getLogger(__name__)


def check_api_auth(request, host, push_password) -> bool:
    """Check authentication on API call."""
    _LOGGER.debug(
        "Check API authentication from %s (expected %s)", request.remote, host
    )
    try:
        if request.remote != host:
            raise ApiCallNotAuthorized("API call not coming from IPX800 IP.")
        if "Authorization" not in request.headers:
            raise ApiCallNotAuthorized("API call no authentication provided.")
        header_auth = request.headers["Authorization"]
        split = header_auth.strip().split(" ")
        if len(split) != 2 or split[0].strip().lower() != "basic":
            raise ApiCallNotAuthorized("Malformed Authorization header")
        username, password = b64decode(split[1]).decode().split(":", 1)
        if username != PUSH_USERNAME or password != push_password:
            raise ApiCallNotAuthorized("API call authentication invalid.")
    except ApiCallNotAuthorized as err:
        _LOGGER.warning(err)
        return False
    return True


class IpxPushView(HomeAssistantView):
    """Base view for the push requests of an IPX800 config entry.

    Views can't be unregistered, so they are registered once and read the
    config entry data on each request to follow its reloads.
    """

    requires_auth = False

    def __init__(self, entry_id: str) -> None:
        """Init the IPX push view."""
        self.entry_id = entry_id
        super().__init__()

    def get_entry_data(self, request) -> dict | None:
        """Return the entry data if the request is authorized, else None."""
        entry_data = request.app["hass"].data.get(DOMAIN, {}).get(self.entry_id)
        if entry_data is None or entry_data[CONF_PUSH_PASSWORD] is None:
            _LOGGER.warning("Push request for an IPX800 not loaded or without push")
            return None
        if not check_api_auth(
            request, entry_data[CONF_HOST], entry_data[CONF_PUSH_PASSWORD]
        ):
            return None
        return entry_data


class IpxRequestView(IpxPushView):
    """Provide a page for the device to call."""

    name = "api:ipx800v5"

    def __init__(self, entry_id: str, ipx_name: str) -> None:
        """Init the IPX view."""
        super().__init__(entry_id)
        self.url = "/api/%s/{entity_id}/{state}" % slugify(ipx_name)
        _LOGGER.info("Dedicated push url for '%s': '%s'", ipx_name, self.url)

    async def get(self, request, entity_id, state):
        """Respond to requests from the device."""
        if self.get_entry_data(request) is None:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        _LOGGER.debug("State update pushed from IPX")
        hass = request.app["hass"]
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
        self.url = "/api/%s_data/{data}" % slugify(ipx_name)
        _LOGGER.info("Dedicated push data url for '%s': '%s'", ipx_name, self.url)

    async def get(self, request, data):
        """Respond to requests from the device."""
        if self.get_entry_data(request) is None:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        _LOGGER.debug("State update pushed from IPX")
        hass = request.app["hass"]
        entities_data = data.split("&")
        for entity_data in entities_data:
            entity_id = entity_data.split("=")[0]
            state = "on" if entity_data.split("=")[1] in ["1", "on", "true"] else "off"

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
        if (entry_data := self.get_entry_data(request)) is None:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        _LOGGER.debug("Update asked from IPX PUSH")
        await entry_data[COORDINATOR].async_request_refresh()
        return web.Response(status=HTTPStatus.OK, text="OK")


class ApiCallNotAuthorized(BaseException):
    """API call for IPX800 view not authorized."""

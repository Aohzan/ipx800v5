"""IPX800V5 request views to handle push information."""

from base64 import b64decode
from http import HTTPStatus
import logging

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify

from .const import PUSH_USERNAME

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


class IpxRequestView(HomeAssistantView):
    """Provide a page for the device to call."""

    requires_auth = False
    name = "api:ipx800v5"

    def __init__(self, host: str, password: str, ipx_name: str) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        self.url = "/api/%s/{entity_id}/{state}" % slugify(ipx_name)
        self.extra_urls = [
            "/api/ipx800v5/{entity_id}/{state}"
        ]  # retrocompat to remove in next major versions
        _LOGGER.info("Dedicated push url for '%s': '%s'", ipx_name, self.url)
        for extra_url in self.extra_urls:
            _LOGGER.info(
                "/!\\ Removed in next major version: legacy push refresh url for '%s': '%s'",
                ipx_name,
                extra_url,
            )
        super().__init__()

    async def get(self, request, entity_id, state):
        """Respond to requests from the device."""
        if not check_api_auth(request, self.host, self.password):
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        # To be removed in next major version
        if "/api/ipx800v5/" in str(request.url) and "/api/ipx800v5/" not in self.url:
            _LOGGER.warning(
                "Legacy URL %s called, please update your IPX800 configuration",
                str(request.url),
            )
        _LOGGER.debug("State update pushed from IPX")
        hass = request.app["hass"]
        old_state = hass.states.get(entity_id)
        _LOGGER.debug("Update %s to state %s", entity_id, state)
        if old_state:
            hass.states.async_set(entity_id, state, old_state.attributes)
            return web.Response(status=HTTPStatus.OK, text="OK")
        _LOGGER.warning("Entity not found for state updating: %s", entity_id)
        return web.Response(status=HTTPStatus.BAD_REQUEST)


class IpxRequestDataView(HomeAssistantView):
    """Provide a page for the device to call for send multiple data at once."""

    requires_auth = False
    name = "api:ipx800v5_data"

    def __init__(self, host: str, password: str, ipx_name: str) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        self.url = "/api/%s_data/{data}" % slugify(ipx_name)
        self.extra_urls = ["/api/ipx800v5_data/{data}"]  # retrocompat
        _LOGGER.info("Dedicated push data url for '%s': '%s'", ipx_name, self.url)
        for extra_url in self.extra_urls:
            _LOGGER.info(
                "/!\\ Removed in next major version: legacy push refresh url for '%s': '%s'",
                ipx_name,
                extra_url,
            )
        super().__init__()

    async def get(self, request, data):
        """Respond to requests from the device."""
        if not check_api_auth(request, self.host, self.password):
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        # To be removed in next major version
        if (
            "/api/ipx800v5_data/" in str(request.url)
            and "/api/ipx800v5_data/" not in self.url
        ):
            _LOGGER.warning(
                "Legacy URL %s called, please update your IPX800 configuration",
                str(request.url),
            )
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


class IpxRequestRefreshView(HomeAssistantView):
    """Provide a page for the device to call for send multiple data at once."""

    requires_auth = False
    name = "api:ipx800v5_refresh"

    def __init__(
        self,
        host: str,
        password: str,
        ipx_name: str,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        self.coordinator = coordinator
        self.url = f"/api/{slugify(ipx_name)}_refresh"
        self.extra_urls = [
            "/api/ipx800v5_refresh",  # retrocompat
            "/api/ipx800v5_refresh/{data}",  # retrocompat
        ]
        _LOGGER.info("Dedicated push refresh url for '%s': '%s'", ipx_name, self.url)
        for extra_url in self.extra_urls:
            _LOGGER.info(
                "/!\\ Removed in next major version: legacy push refresh url for '%s': '%s'",
                ipx_name,
                extra_url,
            )
        super().__init__()

    async def get(self, request):
        """Respond to requests from the device."""
        if not check_api_auth(request, self.host, self.password):
            return web.Response(status=HTTPStatus.UNAUTHORIZED)
        # To be removed in next major version
        if (
            "/api/ipx800v5_refresh" in str(request.url)
            and "/api/ipx800v5_refresh" not in self.url
        ):
            _LOGGER.warning(
                "Legacy URL %s called, please update your IPX800 configuration",
                str(request.url),
            )
        _LOGGER.debug("Update asked from IPX PUSH")
        await self.coordinator.async_request_refresh()
        return web.Response(status=HTTPStatus.OK, text="OK")


class ApiCallNotAuthorized(BaseException):
    """API call for IPX800 view not authorized."""

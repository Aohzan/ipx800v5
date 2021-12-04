"""IPX800V5 request views to handle push information."""
from base64 import b64decode
from http import HTTPStatus
import logging

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .const import PUSH_USERNAME

_LOGGER = logging.getLogger(__name__)


def check_api_auth(request, host, password) -> bool:
    """Check authentication on API call."""
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
        if username != PUSH_USERNAME or password != password:
            raise ApiCallNotAuthorized("API call authentication invalid.")
        return True
    except ApiCallNotAuthorized as err:
        _LOGGER.warning(err)
        return False


class IpxRequestView(HomeAssistantView):
    """Provide a page for the device to call."""

    requires_auth = False
    url = "/api/ipx800v5/{entity_id}/{state}"
    name = "api:ipx800v5"

    def __init__(self, host: str, password: str) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        super().__init__()

    async def get(self, request, entity_id, state):
        """Respond to requests from the device."""
        if check_api_auth(request, self.host, self.password):
            hass = request.app["hass"]
            old_state = hass.states.get(entity_id)
            _LOGGER.debug("Update %s to state %s", entity_id, state)
            if old_state:
                hass.states.async_set(entity_id, state, old_state.attributes)
                return web.Response(status=HTTPStatus.OK, text="OK")
            _LOGGER.warning("Entity not found for state updating: %s", entity_id)


class IpxRequestDataView(HomeAssistantView):
    """Provide a page for the device to call for send multiple data at once."""

    requires_auth = False
    url = "/api/ipx800v5_data/{data}"
    name = "api:ipx800v5_data"

    def __init__(self, host: str, password: str) -> None:
        """Init the IPX view."""
        self.host = host
        self.password = password
        super().__init__()

    async def get(self, request, data):
        """Respond to requests from the device."""
        if check_api_auth(request, self.host, self.password):
            hass = request.app["hass"]
            entities_data = data.split("&")
            for entity_data in entities_data:
                entity_id = entity_data.split("=")[0]
                state = (
                    "on" if entity_data.split("=")[1] in ["1", "on", "true"] else "off"
                )

                old_state = hass.states.get(entity_id)
                _LOGGER.debug("Update %s to state %s", entity_id, state)
                if old_state:
                    hass.states.async_set(entity_id, state, old_state.attributes)
                else:
                    _LOGGER.warning(
                        "Entity not found for state updating: %s", entity_id
                    )

            return web.Response(status=HTTPStatus.OK, text="OK")


class ApiCallNotAuthorized(BaseException):
    """API call for IPX800 view not authorized."""

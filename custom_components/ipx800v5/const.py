"""Constants for the ipx800v5 integration."""
DOMAIN = "ipx800v5"

CONTROLLER = "controller"
COORDINATOR = "coordinator"
UNDO_UPDATE_LISTENER = "undo_update_listener"
PUSH_USERNAME = "ipx800"

DEFAULT_IPX_NAME = "IPX800 V5"
DEFAULT_SCAN_INTERVAL = 15
DEFAULT_TRANSITION = 0.5
REQUEST_REFRESH_DELAY = 0.5

CONF_DEVICES = "devices"

CONF_COMPONENT = "component"
CONF_DEFAULT_BRIGHTNESS = "default_brightness"
CONF_DEVICES_AUTO = "devices_auto"
CONF_PUSH_PASSWORD = "push_password"
CONF_TRANSITION = "transition"
CONF_EXT_TYPE = "ext_type"
CONF_EXT_NAME = "ext_name"
CONF_EXT_NUMBER = "ext_number"
CONF_IO_NUMBER = "io_number"
CONF_IO_NUMBERS = "io_numbers"

TYPE_XPWM_RGB = "xpwm_rgb"
TYPE_XPWM_RGBW = "xpwm_rgbw"

PLATFORMS = [
    "light",
    "switch",
    "sensor",
    "binary_sensor",
    "cover",
    "climate",
    "number",
    "button",
]

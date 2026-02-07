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
CONF_DIAG_SENSORS = "diag_sensors"
CONF_PUSH_PASSWORD = "push_password"
CONF_TRANSITION = "transition"
CONF_EXT_TYPE = "ext_type"
CONF_EXT_NAME = "ext_name"
CONF_EXT_NUMBER = "ext_number"
CONF_IO_NUMBER = "io_number"
CONF_IO_NUMBERS = "io_numbers"
# min_temp is NOT configurable - always read from IPX800 NoFrost value for safety
CONF_MAX_TEMP = "max_temp"
CONF_TARGET_TEMP_STEP = "target_temp_step"

# Default temperature settings
# min_temp is ALWAYS read from IPX800 NoFrost value (safety)
# If NoFrost not available, use 7°C as absolute safety minimum
DEFAULT_MIN_TEMP = 7
# max_temp has no equivalent in IPX800, use reasonable default
DEFAULT_MAX_TEMP = 22
# target_temp_step has no equivalent in IPX800, 0.5°C is more practical than 0.1°C
DEFAULT_TARGET_TEMP_STEP = 0.5

TYPE_IPX_OPENCOLL = "opencoll"
TYPE_IPX_OPTO = "opto"
TYPE_XPWM_RGB = "xpwm_rgb"
TYPE_XPWM_RGBW = "xpwm_rgbw"

PLATFORMS = [
    "binary_sensor",
    "button",
    "climate",
    "cover",
    "light",
    "number",
    "select",
    "sensor",
    "switch",
]

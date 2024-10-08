"""Tools to manage IPX800V5 tools."""

from itertools import groupby
import logging

from pypx800v5 import (
    API_CONFIG_NAME,
    API_CONFIG_TYPE,
    EXT_X010V,
    EXT_X4FP,
    EXT_X4VR,
    EXT_X8D,
    EXT_X8R,
    EXT_X24D,
    EXT_XDIMMER,
    EXT_XDISPLAY,
    EXT_XPWM,
    EXT_XTHL,
    IPX,
    IPX800,
    OBJECT_ACCESS_CONTROL,
    OBJECT_COUNTER,
    OBJECT_TEMPO,
    OBJECT_THERMOSTAT,
    TYPE_ANA,
    TYPE_IO,
)

from homeassistant.const import (
    CONF_ENTITY_CATEGORY,
    CONF_ID,
    CONF_NAME,
    CONF_TYPE,
    EntityCategory,
)

from .const import (
    CONF_COMPONENT,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
    DEFAULT_IPX_NAME,
    TYPE_IPX_OPENCOLL,
    TYPE_IPX_OPTO,
    TYPE_XPWM_RGB,
    TYPE_XPWM_RGBW,
)

_LOGGER = logging.getLogger(__name__)


def filter_entities_by_platform(devices: list, component: str) -> list:
    """Filter device list by platform."""
    return list(filter(lambda d: d[CONF_COMPONENT] == component, devices))


def check_devices_config(devices_config: list) -> list:
    """Check and build device list from config."""
    _LOGGER.debug("Check and build devices configuration")

    devices = []
    for device_config in devices_config:
        _LOGGER.debug("Read device name: %s", device_config.get(CONF_NAME))

        if (
            device_config[CONF_EXT_TYPE]
            in [
                EXT_X4VR,
                EXT_XTHL,
                EXT_X24D,
                EXT_X4FP,
                EXT_X8D,
                EXT_X8R,
                EXT_XDIMMER,
                EXT_XPWM,
                EXT_XDISPLAY,
            ]
            and CONF_EXT_NUMBER not in device_config
        ):
            _LOGGER.error(
                "Device from extension %s skipped: %s must have %s set",
                device_config[CONF_NAME],
                device_config[CONF_EXT_TYPE],
                CONF_EXT_NUMBER,
            )
            continue

        # Check if RGB/RBW or FP/RELAY have ids set
        if (
            device_config[CONF_TYPE] in [TYPE_XPWM_RGB, TYPE_XPWM_RGBW]
            or (
                device_config[CONF_EXT_TYPE] in [IPX, EXT_X8R]
                and device_config[CONF_COMPONENT] == "climate"
            )
        ) and CONF_IO_NUMBERS not in device_config:
            _LOGGER.error(
                "Device %s skipped: RGB/RGBW and climate relais must have %s set",
                device_config[CONF_NAME],
                CONF_IO_NUMBERS,
            )
            continue

        devices.append(device_config)
        _LOGGER.info(
            "Device %s added (component: %s)",
            device_config[CONF_NAME],
            device_config[CONF_COMPONENT],
        )
    return devices


def get_device_in_devices_config(
    devices_config: list, device_auto: dict, use_device_name_as_ext_name: bool = False
) -> dict:
    """Build a device config from config and automatic config."""
    device = None
    # Filter on base keys
    found_devices = [
        device_conf
        for device_conf in devices_config
        if str(device_conf[CONF_EXT_TYPE]) == str(device_auto[CONF_EXT_TYPE])
        and int(device_conf[CONF_EXT_NUMBER]) == int(device_auto[CONF_EXT_NUMBER])
        and (
            str(device_conf[CONF_COMPONENT]) == str(device_auto[CONF_COMPONENT])
            or (
                str(device_auto[CONF_EXT_TYPE]) in [IPX, EXT_X8R]
                and str(device_auto[CONF_COMPONENT]) in ["light", "switch"]
                and str(device_conf[CONF_COMPONENT]) in ["light", "switch"]
            )
        )
        and (device_conf.get(CONF_TYPE) == device_auto.get(CONF_TYPE))
    ]
    # Filter on others keys
    for device_config in found_devices:
        # if filter return only one result and don't need io_number(s)
        if (
            device_config[CONF_EXT_TYPE]
            in [
                OBJECT_ACCESS_CONTROL,
                OBJECT_TEMPO,
                OBJECT_COUNTER,
                OBJECT_THERMOSTAT,
                EXT_XTHL,
            ]
            and len(found_devices) == 1
        ):
            device = device_config
            break
        # elif io_number(s) are equals
        if CONF_IO_NUMBER in device_auto and CONF_IO_NUMBER in device_config:
            if device_config[CONF_IO_NUMBER] == device_auto[CONF_IO_NUMBER]:
                device = device_config
                break
        elif CONF_IO_NUMBERS in device_auto and CONF_IO_NUMBERS in device_config:
            if device_config[CONF_IO_NUMBERS] == device_auto[CONF_IO_NUMBERS]:
                device = device_config
                break
    if device is not None:
        _LOGGER.debug("Found custom config for device %s", device[CONF_NAME])
        if use_device_name_as_ext_name:
            device[CONF_EXT_NAME] = device[CONF_NAME]
        elif CONF_EXT_NAME not in device:
            device[CONF_EXT_NAME] = device_auto.get(CONF_EXT_NAME, device[CONF_NAME])
        return dict(device)
    return device_auto


def build_ipx_system_entities(ipx: IPX800, enable_diag_sensors: bool = False) -> list:
    """Add system, configuration and diagnostic IPX800 entities."""
    entities = [
        {
            CONF_NAME: f"{DEFAULT_IPX_NAME} Reboot",
            CONF_COMPONENT: "button",
            CONF_EXT_TYPE: IPX,
            CONF_EXT_NUMBER: 0,
            CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
        }
    ]
    # Add all diagnostic entities
    if enable_diag_sensors:
        for key, value in ipx.ipx_config.items():
            key = str(key).removesuffix("_id")
            if key.startswith("anaIPX") or key in [
                "anaHeapFree",
                "anaDeltaHeapFree",
                "anaMonitorConnections",
            ]:
                name = key.removeprefix("ana")
                entities.append(
                    {
                        CONF_NAME: f"{DEFAULT_IPX_NAME} {name}",
                        CONF_COMPONENT: "sensor",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_TYPE: TYPE_ANA,
                        CONF_ID: value,
                        CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
                    }
                )
    if ipx.io_acpower_id in ipx.ipx_config:
        entities.append(
            {
                CONF_NAME: f"{DEFAULT_IPX_NAME} AC Power",
                CONF_COMPONENT: "binary_sensor",
                CONF_EXT_TYPE: IPX,
                CONF_EXT_NUMBER: 0,
                CONF_TYPE: TYPE_IO,
                CONF_ID: ipx.ipx_config[ipx.io_acpower_id],
                CONF_ENTITY_CATEGORY: EntityCategory.DIAGNOSTIC,
            }
        )
    return entities


def build_ipx_entities(
    entry_source: str, devices_config: list, auto_ext_list: list
) -> list:
    """Build entities list for the IPX800 from config and discovery."""
    entities = []
    # ipx
    if entry_source == "user" or IPX in auto_ext_list:
        _LOGGER.debug("Build entities for the IPX800 V5")
        for i in range(8):
            # relais
            entities.append(  # noqa: PERF401
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"{DEFAULT_IPX_NAME} Relais {i + 1}",
                        CONF_COMPONENT: "switch",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
        for i in range(4):
            # open collector
            entities.append(  # noqa: PERF401
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"{DEFAULT_IPX_NAME} Open Collector {i + 1}",
                        CONF_COMPONENT: "switch",
                        CONF_EXT_TYPE: IPX,
                        CONF_TYPE: TYPE_IPX_OPENCOLL,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
        for i in range(8):
            # digital inputs
            entities.append(  # noqa: PERF401
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"{DEFAULT_IPX_NAME} Digital Input {i + 1}",
                        CONF_COMPONENT: "binary_sensor",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
        for i in range(4):
            # analog inputs
            entities.append(  # noqa: PERF401
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"{DEFAULT_IPX_NAME} Analog Input {i + 1}",
                        CONF_COMPONENT: "sensor",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
        for i in range(4):
            # opto inputs
            entities.append(  # noqa: PERF401
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"{DEFAULT_IPX_NAME} Opto Input {i + 1}",
                        CONF_COMPONENT: "binary_sensor",
                        CONF_EXT_TYPE: IPX,
                        CONF_TYPE: TYPE_IPX_OPTO,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
    return entities


def build_extensions_entities(
    entry_source: str, ipx: IPX800, devices_config: list, auto_ext_list: list
) -> list:
    """Build entities list for extensions from config and discovery."""
    entities = []
    ext_type = None
    for ext_type, extensions in groupby(
        ipx.extensions_config, lambda x: x[API_CONFIG_TYPE]
    ):
        if entry_source == "user" or ext_type in auto_ext_list:
            _LOGGER.debug("Build entities for %s extension", ext_type)
            ext_number = 0
            for extension in extensions:
                if ext_type == EXT_X8R:
                    for i in range(8):
                        main_entity = get_device_in_devices_config(
                            devices_config,
                            {
                                CONF_NAME: f"{extension[API_CONFIG_NAME]} Relais {i + 1}",
                                CONF_COMPONENT: "switch",
                                CONF_EXT_TYPE: ext_type,
                                CONF_EXT_NUMBER: ext_number,
                                CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                CONF_IO_NUMBER: i + 1,
                            },
                        )
                        entities.append(main_entity)
                        entities.append(
                            {
                                CONF_NAME: main_entity[CONF_NAME],
                                CONF_COMPONENT: "binary_sensor",
                                CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                                CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                                CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                                CONF_IO_NUMBER: i + 1,
                            }
                        )
                elif ext_type == EXT_XDIMMER:
                    for i in range(4):
                        entities.append(  # noqa: PERF401
                            get_device_in_devices_config(
                                devices_config,
                                {
                                    CONF_NAME: f"{extension[API_CONFIG_NAME]} Sortie {i + 1}",
                                    CONF_COMPONENT: "light",
                                    CONF_EXT_TYPE: ext_type,
                                    CONF_EXT_NUMBER: ext_number,
                                    CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                    CONF_IO_NUMBER: i + 1,
                                },
                            )
                        )
                elif ext_type == EXT_XPWM:
                    for i in range(12):
                        entities.append(  # noqa: PERF401
                            get_device_in_devices_config(
                                devices_config,
                                {
                                    CONF_NAME: f"{extension[API_CONFIG_NAME]} Sortie {i + 1}",
                                    CONF_COMPONENT: "light",
                                    CONF_EXT_TYPE: ext_type,
                                    CONF_EXT_NUMBER: ext_number,
                                    CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                    CONF_IO_NUMBER: i + 1,
                                },
                            )
                        )
                elif ext_type in [EXT_X24D, EXT_X8D]:
                    for i in range(24 if ext_type == EXT_X24D else 8):
                        entities.append(  # noqa: PERF401
                            get_device_in_devices_config(
                                devices_config,
                                {
                                    CONF_NAME: f"{extension[API_CONFIG_NAME]} Digital Input {i + 1}",
                                    CONF_COMPONENT: "binary_sensor",
                                    CONF_EXT_TYPE: ext_type,
                                    CONF_EXT_NUMBER: ext_number,
                                    CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                    CONF_IO_NUMBER: i + 1,
                                },
                            )
                        )
                elif ext_type == EXT_X4FP:
                    for i in range(4):
                        entities.append(  # noqa: PERF401
                            get_device_in_devices_config(
                                devices_config,
                                {
                                    CONF_NAME: f"{extension['name']} FP {i + 1}",
                                    CONF_COMPONENT: "climate",
                                    CONF_EXT_TYPE: ext_type,
                                    CONF_EXT_NUMBER: ext_number,
                                    CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                    CONF_IO_NUMBER: i + 1,
                                },
                            )
                        )
                elif ext_type == EXT_X4VR:
                    for i in range(4):
                        entities.append(  # noqa: PERF401
                            get_device_in_devices_config(
                                devices_config,
                                {
                                    CONF_NAME: f"{extension['name']} VR {i + 1}",
                                    CONF_COMPONENT: "cover",
                                    CONF_EXT_TYPE: ext_type,
                                    CONF_EXT_NUMBER: ext_number,
                                    CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                    CONF_IO_NUMBER: i + 1,
                                },
                            )
                        )
                elif ext_type == EXT_XTHL:
                    entities.append(
                        get_device_in_devices_config(
                            devices_config,
                            {
                                CONF_NAME: extension[API_CONFIG_NAME],
                                CONF_COMPONENT: "sensor",
                                CONF_EXT_TYPE: ext_type,
                                CONF_EXT_NUMBER: ext_number,
                                CONF_EXT_NAME: extension[API_CONFIG_NAME],
                            },
                        )
                    )
                elif ext_type == EXT_XDISPLAY:
                    main_entity = get_device_in_devices_config(
                        devices_config,
                        {
                            CONF_NAME: extension[API_CONFIG_NAME],
                            CONF_COMPONENT: "select",
                            CONF_EXT_TYPE: ext_type,
                            CONF_EXT_NUMBER: ext_number,
                            CONF_EXT_NAME: extension[API_CONFIG_NAME],
                        },
                    )
                    entities.append(main_entity)
                    entities.append(
                        {
                            CONF_NAME: main_entity[API_CONFIG_NAME],
                            CONF_COMPONENT: "switch",
                            CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                            CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                            CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                        }
                    )
                    entities.append(
                        {
                            CONF_NAME: main_entity[API_CONFIG_NAME],
                            CONF_COMPONENT: "sensor",
                            CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                            CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                            CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                        }
                    )
                elif ext_type == EXT_X010V:
                    for i in range(4):
                        entities.append(  # noqa: PERF401
                            get_device_in_devices_config(
                                devices_config,
                                {
                                    CONF_NAME: f"{extension[API_CONFIG_NAME]} Sortie {i + 1}",
                                    CONF_COMPONENT: "light",
                                    CONF_EXT_TYPE: ext_type,
                                    CONF_EXT_NUMBER: ext_number,
                                    CONF_EXT_NAME: extension[API_CONFIG_NAME],
                                    CONF_IO_NUMBER: i + 1,
                                },
                            )
                        )
                else:
                    _LOGGER.warning(
                        "%s extension type not currently supported", ext_type
                    )

                ext_number += 1  # noqa: SIM113
    return entities


def build_objects_entities(
    entry_source: str, ipx: IPX800, devices_config: list, auto_ext_list: list
) -> list:
    """Build entities list for objects from config and discory."""
    entities = []
    obj_type = None
    for obj_type, objs in groupby(ipx.objects_config, lambda x: x[API_CONFIG_TYPE]):
        if entry_source == "user" or obj_type in auto_ext_list:
            _LOGGER.debug("Build entities for objects type of %s", obj_type)
            obj_number = 0
            for obj in objs:
                if obj_type == OBJECT_THERMOSTAT:
                    main_entity = get_device_in_devices_config(
                        devices_config,
                        {
                            CONF_NAME: obj[API_CONFIG_NAME],
                            CONF_COMPONENT: "climate",
                            CONF_EXT_TYPE: obj_type,
                            CONF_EXT_NUMBER: obj_number,
                            CONF_EXT_NAME: obj[API_CONFIG_NAME],
                        },
                        True,
                    )
                    entities.append(main_entity)
                    entities.append(
                        {
                            CONF_NAME: main_entity[CONF_NAME],
                            CONF_COMPONENT: "number",
                            CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                            CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                            CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                        }
                    )
                    entities.append(
                        {
                            CONF_NAME: main_entity[CONF_NAME],
                            CONF_COMPONENT: "binary_sensor",
                            CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                            CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                            CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                        }
                    )
                elif obj_type == OBJECT_COUNTER:
                    entities.append(
                        get_device_in_devices_config(
                            devices_config,
                            {
                                CONF_NAME: obj[API_CONFIG_NAME],
                                CONF_COMPONENT: "number",
                                CONF_EXT_TYPE: obj_type,
                                CONF_EXT_NUMBER: obj_number,
                                CONF_EXT_NAME: obj[API_CONFIG_NAME],
                            },
                            True,
                        )
                    )
                elif obj_type == OBJECT_TEMPO:
                    main_entity = get_device_in_devices_config(
                        devices_config,
                        {
                            CONF_NAME: obj[API_CONFIG_NAME],
                            CONF_COMPONENT: "binary_sensor",
                            CONF_EXT_TYPE: obj_type,
                            CONF_EXT_NUMBER: obj_number,
                            CONF_EXT_NAME: obj[API_CONFIG_NAME],
                        },
                        True,
                    )
                    entities.append(main_entity)
                    entities.append(
                        {
                            CONF_NAME: main_entity[CONF_NAME],
                            CONF_COMPONENT: "number",
                            CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                            CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                            CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                        }
                    )
                    entities.append(
                        {
                            CONF_NAME: main_entity[CONF_NAME],
                            CONF_COMPONENT: "switch",
                            CONF_EXT_TYPE: main_entity[CONF_EXT_TYPE],
                            CONF_EXT_NUMBER: main_entity[CONF_EXT_NUMBER],
                            CONF_EXT_NAME: main_entity[CONF_EXT_NAME],
                        }
                    )
                elif obj_type == OBJECT_ACCESS_CONTROL:
                    entities.append(
                        get_device_in_devices_config(
                            devices_config,
                            {
                                CONF_NAME: obj[API_CONFIG_NAME],
                                CONF_COMPONENT: "binary_sensor",
                                CONF_EXT_TYPE: obj_type,
                                CONF_EXT_NUMBER: obj_number,
                                CONF_EXT_NAME: obj[API_CONFIG_NAME],
                            },
                            True,
                        )
                    )
                else:
                    _LOGGER.warning("%s object type not currently supported", obj_type)

                obj_number += 1  # noqa: SIM113

    return entities


def remove_duplicate_entities(auto_entities: list, devices_config: list) -> list:
    """Remove existing entities in auto_entities from device_config."""
    filtered_auto_entities = list(auto_entities)
    for entity in auto_entities:
        entity["original"] = True
        config = get_device_in_devices_config(devices_config, entity)
        if "original" not in config:
            _LOGGER.debug(
                "Remove already auto configured device config %s", config[CONF_NAME]
            )
            filtered_auto_entities.remove(entity)
    return filtered_auto_entities

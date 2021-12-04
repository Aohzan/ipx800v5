"""Tools to manage IPX800V5 tools."""
from itertools import groupby
import logging

from pypx800v5 import IPX800
from pypx800v5.const import (
    API_CONFIG_NAME,
    API_CONFIG_TYPE,
    EXT_X4FP,
    EXT_X4VR,
    EXT_X8D,
    EXT_X8R,
    EXT_X24D,
    EXT_XDIMMER,
    EXT_XPWM,
    EXT_XTHL,
    IPX,
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
    ENTITY_CATEGORY_DIAGNOSTIC,
    ENTITY_CATEGORY_SYSTEM,
)

from .const import (
    CONF_COMPONENT,
    CONF_EXT_NAME,
    CONF_EXT_NUMBER,
    CONF_EXT_TYPE,
    CONF_IO_NUMBER,
    CONF_IO_NUMBERS,
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

        # TODO

        devices.append(device_config)
        _LOGGER.info(
            "Device %s added (component: %s)",
            device_config[CONF_NAME],
            device_config[CONF_COMPONENT],
        )
    return devices


def get_device_in_devices_config(devices_config: list, device_auto: dict) -> dict:
    """Build a device config from config and automatic config."""
    device = None
    # Filter on base keys
    found_devices = [
        d
        for d in devices_config
        if str(d[CONF_EXT_TYPE]) == str(device_auto[CONF_EXT_TYPE])
        and int(d[CONF_EXT_NUMBER]) == int(device_auto[CONF_EXT_NUMBER])
        and (
            str(d[CONF_COMPONENT]) == str(device_auto[CONF_COMPONENT])
            or (
                str(device_auto[CONF_EXT_TYPE]) in [IPX, EXT_X8R]
                and str(device_auto[CONF_COMPONENT]) in ["light", "switch"]
                and str(d[CONF_COMPONENT]) in ["light", "switch"]
            )
        )
    ]
    # Filter on others keys
    for device_config in found_devices:
        # if filter return only one result and don't need io_number(s)
        if (
            device_config[CONF_EXT_TYPE]
            in [OBJECT_TEMPO, OBJECT_COUNTER, OBJECT_THERMOSTAT, EXT_XTHL]
            and len(found_devices) == 1
        ):
            device = device_config
            break
        # elif io_number(s) are equals
        elif CONF_IO_NUMBER in device_auto and CONF_IO_NUMBER in device_config:
            if device_config[CONF_IO_NUMBER] == device_auto[CONF_IO_NUMBER]:
                device = device_config
                break
        elif CONF_IO_NUMBERS in device_auto and CONF_IO_NUMBERS in device_config:
            if device_config[CONF_IO_NUMBERS] == device_auto[CONF_IO_NUMBERS]:
                device = device_config
                break
    if device is not None:
        _LOGGER.debug("Found custom config for device %s", device[CONF_NAME])
        if CONF_EXT_NAME not in device:
            device[CONF_EXT_NAME] = device_auto.get(CONF_EXT_NAME, device[CONF_NAME])
        return dict(device)
    return device_auto


def build_ipx_system_entities(ipx: IPX800) -> list:
    """Add system, configuration and diagnostic IPX800 entities."""
    entities = [
        {
            CONF_NAME: "IPX800 Reboot",
            CONF_COMPONENT: "button",
            CONF_EXT_TYPE: IPX,
            CONF_EXT_NUMBER: 0,
            CONF_ENTITY_CATEGORY: ENTITY_CATEGORY_SYSTEM,
        },
        {
            CONF_NAME: "IPX800 Heap Free",
            CONF_COMPONENT: "sensor",
            CONF_EXT_TYPE: IPX,
            CONF_EXT_NUMBER: 0,
            CONF_TYPE: TYPE_ANA,
            CONF_ID: ipx.ipx_config[ipx.ana_heap_free_id],
            CONF_ENTITY_CATEGORY: ENTITY_CATEGORY_DIAGNOSTIC,
        },
        {
            CONF_NAME: "IPX800 Delta Heap Free",
            CONF_COMPONENT: "sensor",
            CONF_EXT_TYPE: IPX,
            CONF_EXT_NUMBER: 0,
            CONF_TYPE: TYPE_ANA,
            CONF_ID: ipx.ipx_config[ipx.ana_delta_heap_free_id],
            CONF_ENTITY_CATEGORY: ENTITY_CATEGORY_DIAGNOSTIC,
        },
    ]
    if ipx.io_acpower_id in ipx.ipx_config:
        entities.append(
            {
                CONF_NAME: "IPX800 AC Power",
                CONF_COMPONENT: "binary_sensor",
                CONF_EXT_TYPE: IPX,
                CONF_EXT_NUMBER: 0,
                CONF_TYPE: TYPE_IO,
                CONF_ID: ipx.ipx_config[ipx.io_acpower_id],
                CONF_ENTITY_CATEGORY: ENTITY_CATEGORY_DIAGNOSTIC,
            }
        )
    return entities


def build_ipx_entities(
    entry_source: str, devices_config: list, auto_ext_list: list
) -> list:
    """Build entities list for the IPX800 from config and discory."""
    entities = []
    # ipx
    if entry_source == "user" or IPX in auto_ext_list:
        _LOGGER.debug("Build entities for the IPX800 V5")
        for i in range(8):
            # relais
            entities.append(
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"IPX800 Relais {i + 1}",
                        CONF_COMPONENT: "switch",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
            # digital inputs
            entities.append(
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"IPX800 Digital Input {i + 1}",
                        CONF_COMPONENT: "binary_sensor",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
        for i in range(4):
            # analog inputs
            entities.append(
                get_device_in_devices_config(
                    devices_config,
                    {
                        CONF_NAME: f"IPX800 Analog Input {i + 1}",
                        CONF_COMPONENT: "sensor",
                        CONF_EXT_TYPE: IPX,
                        CONF_EXT_NUMBER: 0,
                        CONF_IO_NUMBER: i + 1,
                    },
                )
            )
    return entities


def build_extensions_entities(
    entry_source: str, ipx: IPX800, devices_config: list, auto_ext_list: list
) -> list:
    """Build entities list for extensions from config and discory."""
    entities = []
    ext_type = None
    for ext_type, extensions in groupby(
        ipx.extensions_config, lambda x: x[API_CONFIG_TYPE]
    ):
        if entry_source == "user" or ext_type in auto_ext_list:
            _LOGGER.debug("Build entities for %s extension", ext_type)
            ext_number = 1
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
                        entities.append(
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
                        entities.append(
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
                        entities.append(
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
                        entities.append(
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
                        entities.append(
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
                else:
                    _LOGGER.warning(
                        "%s extension type not currently supported", ext_type
                    )

                ext_number += 1
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
            obj_number = 1
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
                else:
                    _LOGGER.warning("%s object type not currently supported", obj_type)

                obj_number += 1

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

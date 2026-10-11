#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""SMART attributes read through pySMART, for the smart plugin.

Moved out of the v4 plugin module at the v5 cutover; the v5 smart model and
its renderer use it. `import_error_tag` is module state: `get_smart_data()`
sets it when the device list cannot be read, and readers look it up here.
"""

from glances.logger import logger

# Import plugin specific dependency
try:
    from pySMART import DeviceList
    from pySMART.interface.nvme import NvmeAttributes
except ImportError as e:
    import_error_tag = True
    logger.warning(f"Missing Python Lib ({e}), HDD Smart plugin is disabled")
else:
    import_error_tag = False


def convert_attribute_to_dict(attr):
    return {
        'name': attr.name,
        'key': attr.name,
        'num': attr.num,
        'flags': attr.flags,
        'raw': attr.raw,
        'value': attr.value,
        'worst': attr.worst,
        'threshold': attr.thresh,
        'type': attr.type,
        'updated': attr.updated,
        'when_failed': attr.when_failed,
    }


# Keys for attributes that should be formatted with auto_unit (large byte values)
LARGE_VALUE_KEYS = frozenset(
    [
        "bytesWritten",
        "bytesRead",
        "dataUnitsRead",
        "dataUnitsWritten",
        "hostReadCommands",
        "hostWriteCommands",
    ]
)

NVME_ATTRIBUTE_LABELS = {
    "criticalWarning": "Number of critical warnings",
    "_temperature": "Temperature (°C)",
    "availableSpare": "Available spare (%)",
    "availableSpareThreshold": "Available spare threshold (%)",
    "percentageUsed": "Percentage used (%)",
    "dataUnitsRead": "Data units read",
    "bytesRead": "Bytes read",
    "dataUnitsWritten": "Data units written",
    "bytesWritten": "Bytes written",
    "hostReadCommands": "Host read commands",
    "hostWriteCommands": "Host write commands",
    "controllerBusyTime": "Controller busy time (min)",
    "powerCycles": "Power cycles",
    "powerOnHours": "Power-on hours",
    "unsafeShutdowns": "Unsafe shutdowns",
    "integrityErrors": "Integrity errors",
    "errorEntries": "Error log entries",
    "warningTemperatureTime": "Warning temperature time (min)",
    "criticalTemperatureTime": "Critical temperature time (min)",
    "_logical_sector_size": "Logical sector size",
    "_physical_sector_size": "Physical sector size",
    "errors": "Errors",
    "tests": "Self-tests",
}


def convert_nvme_attribute_to_dict(key, value):
    label = NVME_ATTRIBUTE_LABELS.get(key, key)

    return {
        'name': label,
        'key': key,
        'value': value,
        'flags': None,
        'raw': value,
        'worst': None,
        'threshold': None,
        'type': None,
        'updated': None,
        'when_failed': None,
    }


def _process_standard_attributes(device_stats, attributes, hide_attributes):
    """Process standard SMART attributes and add them to device_stats."""
    for attribute in attributes:
        if attribute is None or attribute.name in hide_attributes:
            continue

        attrib_dict = convert_attribute_to_dict(attribute)
        num = attrib_dict.pop('num', None)
        if num is None:
            logger.debug(f'Smart plugin error - Skip attribute with no num: {attribute}')
            continue

        device_stats[num] = attrib_dict


def _process_nvme_attributes(device_stats, if_attributes, hide_attributes):
    """Process NVMe-specific attributes and add them to device_stats."""
    if not isinstance(if_attributes, NvmeAttributes):
        return

    for idx, (attr, value) in enumerate(vars(if_attributes).items(), start=1):
        attrib_dict = convert_nvme_attribute_to_dict(attr, value)
        if attrib_dict['name'] in hide_attributes:
            continue

        # Verify the value is serializable to prevent rendering errors
        if value is not None:
            try:
                str(value)
            except Exception:
                logger.debug(f'Unable to serialize attribute {attr} from NVME')
                attrib_dict['value'] = None
                attrib_dict['raw'] = None

        device_stats[idx] = attrib_dict


def get_smart_data(hide_attributes):
    """Get SMART attribute data.

    Returns a list of dictionaries, each containing:
    - 'DeviceName': Device identification string
    - Numeric keys: SMART attribute dictionaries with flags, raw values, etc.
    """
    stats = []
    try:
        devlist = DeviceList()
    except (TypeError, FileNotFoundError) as e:
        logger.debug(f'Smart plugin error - Can not grab device list ({e})')
        global import_error_tag
        import_error_tag = True
        return stats

    for dev in devlist.devices:
        device_stats = {'DeviceName': f'{dev.name} {dev.model}'}
        _process_standard_attributes(device_stats, dev.attributes, hide_attributes)
        _process_nvme_attributes(device_stats, dev.if_attributes, hide_attributes)
        stats.append(device_stats)

    return stats

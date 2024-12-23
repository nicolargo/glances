#
# This file is part of Glances.
#
# Copyright (C) 2018 Tim Nibert <docz2a@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
Hard disk SMART attributes plugin.
Depends on pySMART and smartmontools
Must execute as root
"usermod -a -G disk USERNAME" is not sufficient unfortunately
SmartCTL (/usr/sbin/smartctl) must be in system path for python2.

Regular PySMART is a python2 library.
We are using the pySMART.smartx updated library to support both python 2 and 3.

If we only have disk group access (no root):
$ smartctl -i /dev/sda
smartctl 6.6 2016-05-31 r4324 [x86_64-linux-4.15.0-30-generic] (local build)
Copyright (C) 2002-16, Bruce Allen, Christian Franke, www.smartmontools.org


Probable ATA device behind a SAT layer
Try an additional '-d ata' or '-d sat' argument.

This is not very hopeful: https://medium.com/opsops/why-smartctl-could-not-be-run-without-root-7ea0583b1323

So, here is what we are going to do:
Check for admin access.  If no admin access, disable SMART plugin.

If smartmontools is not installed, we should catch the error upstream in plugin initialization.
"""

from glances.globals import is_admin
from glances.logger import logger
from glances.main import disable
from glances.plugins.plugin.model import GlancesPluginModel

# Import plugin specific dependency
try:
    from pySMART import DeviceList
except ImportError as e:
    import_error_tag = True
    logger.warning(f"Missing Python Lib ({e}), HDD Smart plugin is disabled")
else:
    import_error_tag = False


def convert_attribute_to_dict(attr):
    return {
        'name': attr.name,
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


def get_smart_data():
    """
    Get SMART attribute data
    :return: list of multi leveled dictionaries
             each dict has a key "DeviceName" with the identification of the device in smartctl
             also has keys of the SMART attribute id, with value of another dict of the attributes
             [
                {
                    "DeviceName": "/dev/sda blahblah",
                    "1":
                    {
                        "flags": "..",
                        "raw": "..",
                        etc,
                    }
                    ...
                }
             ]
    """
    stats = []
    # get all devices
    try:
        devlist = DeviceList()
    except TypeError as e:
        # Catch error  (see #1806)
        logger.debug(f'Smart plugin error - Can not grab device list ({e})')
        global import_error_tag
        import_error_tag = True
        return stats

    for dev in devlist.devices:
        stats.append(
            {
                'DeviceName': f'{dev.name} {dev.model}',
            }
        )
        for attribute in dev.attributes:
            if attribute is None:
                pass
            else:
                attrib_dict = convert_attribute_to_dict(attribute)

                # we will use the attribute number as the key
                num = attrib_dict.pop('num', None)
                try:
                    assert num is not None
                except Exception as e:
                    # we should never get here, but if we do, continue to next iteration and skip this attribute
                    logger.debug(f'Smart plugin error - Skip the attribute {attribute} ({e})')
                    continue

                stats[-1][num] = attrib_dict
    return stats


class PluginModel(GlancesPluginModel):
    """Glances' HDD SMART plugin."""

    def __init__(self, args=None, config=None, stats_init_value=[]):
        """Init the plugin."""
        # check if user is admin
        if not is_admin() and args:
            disable(args, "smart")
            logger.debug("Current user is not admin, HDD SMART plugin disabled.")

        super().__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update SMART stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if import_error_tag:
            return self.stats

        if self.input_method == 'local':
            # Update stats and hide some sensors(#2996)
            stats = [s for s in get_smart_data() if self.is_display(s[self.get_key()])]
        elif self.input_method == 'snmp':
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_key(self):
        """Return the key of the list."""
        return 'DeviceName'

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if import_error_tag or not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        if max_width:
            name_max_width = max_width - 6
        else:
            # No max_width defined, return an empty curse message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Header
        msg = '{:{width}}'.format('SMART disks', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Data
        for device_stat in self.stats:
            # New line
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(device_stat['DeviceName'][:max_width], width=max_width)
            ret.append(self.curse_add_line(msg))
            try:
                device_stat_sorted = sorted([i for i in device_stat.keys() if i != 'DeviceName'], key=int)
            except ValueError:
                # Catch ValueError, see #2904
                device_stat_sorted = [i for i in device_stat.keys() if i != 'DeviceName']
            for smart_stat in device_stat_sorted:
                ret.append(self.curse_new_line())
                msg = ' {:{width}}'.format(
                    device_stat[smart_stat]['name'][: name_max_width - 1].replace('_', ' '), width=name_max_width - 1
                )
                ret.append(self.curse_add_line(msg))
                msg = '{:>8}'.format(device_stat[smart_stat]['raw'])
                ret.append(self.curse_add_line(msg))

        return ret

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2018 Tim Nibert <docz2a@gmail.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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

from glances.plugins.glances_plugin import GlancesPlugin
from glances.logger import logger
from glances.main import disable
from glances.compat import is_admin

# Import plugin specific dependency
try:
    from pySMART import DeviceList
except ImportError as e:
    import_error_tag = True
    logger.warning("Missing Python Lib ({}), HDD Smart plugin is disabled".format(e))
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
    devlist = DeviceList()

    for dev in devlist.devices:
        stats.append({
            'DeviceName': '{} {}'.format(dev.name, dev.model),
        })
        for attribute in dev.attributes:
            if attribute is None:
                pass
            else:
                attribdict = convert_attribute_to_dict(attribute)

                # we will use the attribute number as the key
                num = attribdict.pop('num', None)
                try:
                    assert num is not None
                except Exception as e:
                    # we should never get here, but if we do, continue to next iteration and skip this attribute
                    continue

                stats[-1][num] = attribdict
    return stats


class Plugin(GlancesPlugin):
    """
    Glances' HDD SMART plugin.

    stats is a list of dicts
    """

    def __init__(self,
                 args=None,
                 config=None,
                 stats_init_value=[]):
        """Init the plugin."""
        # check if user is admin
        if not is_admin():
            disable(args, "smart")
            logger.debug("Current user is not admin, HDD SMART plugin disabled.")

        super(Plugin, self).__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update SMART stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if import_error_tag:
            return self.stats

        if self.input_method == 'local':
            stats = get_smart_data()
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
        if not self.stats or self.is_disable():
            return ret

        # Max size for the interface name
        name_max_width = max_width - 6

        # Header
        msg = '{:{width}}'.format('SMART disks',
                                  width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Data
        for device_stat in self.stats:
            # New line
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(device_stat['DeviceName'][:max_width],
                                      width=max_width)
            ret.append(self.curse_add_line(msg))
            for smart_stat in sorted([i for i in device_stat.keys() if i != 'DeviceName'], key=int):
                ret.append(self.curse_new_line())
                msg = ' {:{width}}'.format(device_stat[smart_stat]['name'][:name_max_width-1].replace('_', ' '),
                                          width=name_max_width-1)
                ret.append(self.curse_add_line(msg))
                msg = '{:>8}'.format(device_stat[smart_stat]['raw'])
                ret.append(self.curse_add_line(msg))

        return ret

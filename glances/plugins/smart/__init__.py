#
# This file is part of Glances.
#
# Copyright (C) 2018 Tim Nibert <docz2a@gmail.com>
# Copyright (C) 2026 Github@Drake7707
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
from glances.plugins.smart import data as smart_data
from glances.plugins.smart.data import (  # noqa: F401 -- the v4 plugin below still uses them
    LARGE_VALUE_KEYS,
    convert_attribute_to_dict,
    convert_nvme_attribute_to_dict,
    get_smart_data,
)


class SmartPlugin(GlancesPluginModel):
    """Glances' HDD SMART plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        if not is_admin() and args:
            disable(args, "smart")
            logger.debug("Current user is not admin, HDD SMART plugin disabled.")

        super().__init__(args=args, config=config, stats_init_value=[])

        self.display_curse = True
        self.hide_attributes = self._parse_hide_attributes(config)

    def _parse_hide_attributes(self, config):
        """Parse and return the list of attributes to hide from config."""
        smart_config = config.as_dict().get('smart', {})
        hide_attr_str = smart_config.get('hide_attributes', '')
        if hide_attr_str:
            logger.info(f'Following SMART attributes will not be displayed: {hide_attr_str}')
            # Strip each item: this key is read from config.as_dict(), not through
            # load_limits, so the PR #3700 strip never reached it and an attribute
            # written as `Self-tests, Errors` stayed visible.
            return [attr.strip() for attr in hide_attr_str.split(',')]
        return []

    @property
    def hide_attributes(self):
        """Set hide_attributes list"""
        return self._hide_attributes

    @hide_attributes.setter
    def hide_attributes(self, attr_list):
        """Set hide_attributes list"""
        self._hide_attributes = list(attr_list)

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update SMART stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if smart_data.import_error_tag:
            return self.stats

        if self.input_method == 'local':
            # Update stats and hide some sensors(#2996)
            stats = [
                dict(s, key=self.get_key())
                for s in get_smart_data(self.hide_attributes)
                if self.is_display(s[self.get_key()])
            ]
        elif self.input_method == 'snmp':
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_key(self):
        """Return the key of the list."""
        return 'DeviceName'

    def _format_raw_value(self, stat):
        """Format a raw SMART attribute value for display."""
        raw = stat['raw']
        if raw is None:
            return ""
        if stat['key'] in LARGE_VALUE_KEYS:
            return self.auto_unit(raw)
        return str(raw)

    def _get_sorted_stat_keys(self, device_stat):
        """Get sorted attribute keys from device stats, excluding the non attribute ones."""
        # 'key' is the name of the identifier field, added by update() (see #3704)
        keys = [k for k in device_stat if k not in ('DeviceName', 'key')]
        try:
            return sorted(keys, key=int)
        except ValueError:
            # Some keys may not be numeric (see #2904)
            return keys

    def _add_device_stats(self, ret, device_stat, max_width, name_max_width):
        """Add a device's SMART stats to the curse output."""
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(f'{device_stat["DeviceName"][:max_width]:{max_width}}'))

        for key in self._get_sorted_stat_keys(device_stat):
            stat = device_stat[key]
            ret.append(self.curse_new_line())

            # Attribute name
            name = stat['name'][: name_max_width - 1].replace('_', ' ')
            ret.append(self.curse_add_line(f' {name:{name_max_width - 1}}'))

            # Attribute value
            try:
                value_str = self._format_raw_value(stat)
                ret.append(self.curse_add_line(f'{value_str:>8}'))
            except Exception:
                logger.debug(f"Failed to serialize {key}")
                ret.append(self.curse_add_line(""))

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        ret = []

        if smart_data.import_error_tag or not self.stats or self.is_disabled():
            return ret

        if not max_width:
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        name_max_width = max_width - 6

        # Header
        ret.append(self.curse_add_line(f'{"SMART disks":{name_max_width}}', "TITLE"))

        # Device data
        for device_stat in self.stats:
            self._add_device_stats(ret, device_stat, max_width, name_max_width)

        return ret

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Disk I/O plugin."""
from __future__ import unicode_literals

from glances.globals import nativestr
from glances.timer import getTimeSinceLastUpdate
from glances.plugins.plugin.model import GlancesPluginModel

import psutil

# Fields description
# description: human readable description
# short_name: shortname to use in UI
# unit: unit type
# rate: is it a rate ? If yes generate metadata with _gauge and _rate_per_sec
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
# if field has a key=True then this field will be used as iterator for the stat (dict of dict)
fields_description = {
    'disk_name': {
        'key': True,
        'description': 'Disk name.',
    },
    'read_count': {
        'description': 'Number of read since the last update.',
        'unit': 'number',
        'rate': True,
        'min_symbol': 'K',
    },
    'write_count': {
        'description': 'Number of write since the last update.',
        'unit': 'number',
        'rate': True,
        'min_symbol': 'K',
    },
    'read_bytes': {
        'description': 'Number of bytes read since the last update.',
        'unit': 'bytes',
        'rate': True,
        'min_symbol': 'K',
    },
    'write_bytes': {
        'description': 'Number of bytes write since the last update.',
        'unit': 'bytes',
        'rate': True,
        'min_symbol': 'K',
    },
    'time_since_update': {
        'description': 'Number of seconds since last update.',
        'unit': 'seconds'
    },
}

# Define the history items list
items_history_list = [
    {'name': 'read_bytes_rate_per_sec', 'description': 'Bytes read per second', 'y_unit': 'B/s'},
    {'name': 'write_bytes_rate_per_sec', 'description': 'Bytes write per second', 'y_unit': 'B/s'},
]


class PluginModel(GlancesPluginModel):
    """Glances disks I/O plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(
            args=args, config=config,
            items_history_list=items_history_list,
            fields_description=fields_description
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Hide stats if it has never been != 0
        if config is not None:
            self.hide_zero = config.get_bool_value(self.plugin_name, 'hide_zero', default=False)
        else:
            self.hide_zero = False
        self.hide_zero_fields = ['read_bytes_rate_per_sec', 'write_bytes_rate_per_sec']

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    @GlancesPluginModel._manage_rate
    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update disk I/O stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Grab the stat using the psutil disk_io_counters method
            # read_count: number of reads
            # write_count: number of writes
            # read_bytes: number of bytes read
            # write_bytes: number of bytes written
            # read_time: time spent reading from disk (in milliseconds)
            # write_time: time spent writing to disk (in milliseconds)
            try:
                diskio = psutil.disk_io_counters(perdisk=True)
            except Exception:
                return stats

            for disk in diskio:
                # By default, RamFS is not displayed (issue #714)
                if self.args is not None and \
                   not self.args.diskio_show_ramfs and disk.startswith('ram'):
                    continue

                # Shall we display the stats ?
                if not self.is_display(disk):
                    continue

                # Convert disk stat to plain Python Dict
                diskio_stats = {}
                for key in diskio[disk]._fields:
                    diskio_stats[key] = getattr(diskio[disk], key)
                stats[disk] = diskio_stats

                # Add alias if exist (define in the configuration file)
                if self.has_alias(disk) is not None:
                    stats[disk]['alias'] = self.has_alias(disk)

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # No standard way for the moment...
            pass

        # Update the stats
        self.stats = stats

        return stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Check if the stats should be hidden
        self.update_views_hidden()

        # Add specifics information
        # Alert
        for k, v in self.get_raw().items():
            if 'read_bytes_rate_per_sec' in v and 'write_bytes_rate_per_sec' in v:
                self.views[k]['read_bytes_rate_per_sec']['decoration'] = self.get_alert(
                    int(v['read_bytes_rate_per_sec']), header=k + '_rx'
                )
                self.views[k]['read_bytes_rate_per_sec']['decoration'] = self.get_alert(
                    int(v['write_bytes_rate_per_sec']), header=k + '_tx'
                )

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        name_max_width = max_width - 13

        # Header
        msg = '{:{width}}'.format('DISK I/O', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        if args.diskio_iops:
            msg = '{:>8}'.format('IOR/s')
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format('IOW/s')
            ret.append(self.curse_add_line(msg))
        else:
            msg = '{:>8}'.format('R/s')
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format('W/s')
            ret.append(self.curse_add_line(msg))
        # Disk list (sorted by name)
        # for i in self.sorted_stats():
        for k in sorted(self.stats):
            v = self.stats[k]
            if 'read_bytes_rate_per_sec' not in v or 'write_bytes_rate_per_sec' not in v:
                continue
            # Hide stats if never be different from 0 (issue #1787)
            if all([self.get_views(item=k, key=f, option='hidden') for f in self.hide_zero_fields]):
                continue
            # Is there an alias for the disk name ?
            disk_name = self.has_alias(k) if self.has_alias(k) else k
            # New line
            ret.append(self.curse_new_line())
            if len(disk_name) > name_max_width:
                # Cut disk name if it is too long
                disk_name = '_' + disk_name[-name_max_width + 1:]
            msg = '{:{width}}'.format(nativestr(disk_name), width=name_max_width + 1)
            ret.append(self.curse_add_line(msg))
            if args.diskio_iops:
                # count
                txps = self.auto_unit(v['read_count_rate_per_sec'])
                rxps = self.auto_unit(v['write_count_rate_per_sec'])
                msg = '{:>7}'.format(txps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=k, key='read_count_rate_per_sec', option='decoration')
                    )
                )
                msg = '{:>7}'.format(rxps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=k, key='write_count_rate_per_sec', option='decoration')
                    )
                )
            else:
                # Bitrate
                txps = self.auto_unit(v['read_bytes_rate_per_sec'])
                rxps = self.auto_unit(v['write_bytes_rate_per_sec'])
                msg = '{:>7}'.format(txps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=k, key='read_bytes_rate_per_sec', option='decoration')
                    )
                )
                msg = '{:>7}'.format(rxps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=k, key='write_bytes_rate_per_sec', option='decoration')
                    )
                )

        return ret

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


# Define the history items list
items_history_list = [
    {'name': 'read_bytes', 'description': 'Bytes read per second', 'y_unit': 'B/s'},
    {'name': 'write_bytes', 'description': 'Bytes write per second', 'y_unit': 'B/s'},
]


class PluginModel(GlancesPluginModel):
    """Glances disks I/O plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(
            args=args, config=config, items_history_list=items_history_list, stats_init_value=[]
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Hide stats if it has never been != 0
        if config is not None:
            self.hide_zero = config.get_bool_value(self.plugin_name, 'hide_zero', default=False)
        else:
            self.hide_zero = False
        self.hide_zero_fields = ['read_bytes', 'write_bytes']

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def get_key(self):
        """Return the key of the list."""
        return 'disk_name'

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

            # Previous disk IO stats are stored in the diskio_old variable
            # By storing time data we enable Rx/s and Tx/s calculations in the
            # XML/RPC API, which would otherwise be overly difficult work
            # for users of the API
            time_since_update = getTimeSinceLastUpdate('disk')

            diskio = diskio
            for disk in diskio:
                # By default, RamFS is not displayed (issue #714)
                if self.args is not None and not self.args.diskio_show_ramfs and disk.startswith('ram'):
                    continue

                # Shall we display the stats ?
                if not self.is_display(disk):
                    continue

                # Compute count and bit rate
                try:
                    diskstat = {
                        'time_since_update': time_since_update,
                        'disk_name': disk,
                        'read_count': diskio[disk].read_count - self.diskio_old[disk].read_count,
                        'write_count': diskio[disk].write_count - self.diskio_old[disk].write_count,
                        'read_bytes': diskio[disk].read_bytes - self.diskio_old[disk].read_bytes,
                        'write_bytes': diskio[disk].write_bytes - self.diskio_old[disk].write_bytes,
                    }
                except (KeyError, AttributeError):
                    diskstat = {
                        'time_since_update': time_since_update,
                        'disk_name': disk,
                        'read_count': 0,
                        'write_count': 0,
                        'read_bytes': 0,
                        'write_bytes': 0,
                    }

                # Add alias if exist (define in the configuration file)
                if self.has_alias(disk) is not None:
                    diskstat['alias'] = self.has_alias(disk)

                # Add the dict key
                diskstat['key'] = self.get_key()

                # Add the current disk stat to the list
                stats.append(diskstat)

            # Save stats to compute next bitrate
            try:
                self.diskio_old = diskio
            except (IOError, UnboundLocalError):
                pass
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # No standard way for the moment...
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Check if the stats should be hidden
        self.update_views_hidden()

        # Add specifics information
        # Alert
        for i in self.get_raw():
            disk_real_name = i['disk_name']
            self.views[i[self.get_key()]]['read_bytes']['decoration'] = self.get_alert(
                int(i['read_bytes'] // i['time_since_update']), header=disk_real_name + '_rx'
            )
            self.views[i[self.get_key()]]['write_bytes']['decoration'] = self.get_alert(
                int(i['write_bytes'] // i['time_since_update']), header=disk_real_name + '_tx'
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
        for i in self.sorted_stats():
            # Hide stats if never be different from 0 (issue #1787)
            if all([self.get_views(item=i[self.get_key()], key=f, option='hidden') for f in self.hide_zero_fields]):
                continue
            # Is there an alias for the disk name ?
            disk_name = self.has_alias(i['disk_name']) if self.has_alias(i['disk_name']) else i['disk_name']
            # New line
            ret.append(self.curse_new_line())
            if len(disk_name) > name_max_width:
                # Cut disk name if it is too long
                disk_name = '_' + disk_name[-name_max_width + 1 :]
            msg = '{:{width}}'.format(nativestr(disk_name), width=name_max_width + 1)
            ret.append(self.curse_add_line(msg))
            if args.diskio_iops:
                # count
                txps = self.auto_unit(int(i['read_count'] // i['time_since_update']))
                rxps = self.auto_unit(int(i['write_count'] // i['time_since_update']))
                msg = '{:>7}'.format(txps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='read_count', option='decoration')
                    )
                )
                msg = '{:>7}'.format(rxps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='write_count', option='decoration')
                    )
                )
            else:
                # Bitrate
                txps = self.auto_unit(int(i['read_bytes'] // i['time_since_update']))
                rxps = self.auto_unit(int(i['write_bytes'] // i['time_since_update']))
                msg = '{:>7}'.format(txps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='read_bytes', option='decoration')
                    )
                )
                msg = '{:>7}'.format(rxps)
                ret.append(
                    self.curse_add_line(
                        msg, self.get_views(item=i[self.get_key()], key='write_bytes', option='decoration')
                    )
                )

        return ret

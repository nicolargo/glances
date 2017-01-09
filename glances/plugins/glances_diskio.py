# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

"""Disk I/O plugin."""

import operator

from glances.timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin

import psutil


# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
# 'color' define the graph color in #RGB format
items_history_list = [{'name': 'read_bytes',
                       'description': 'Bytes read per second',
                       'color': '#00FF00',
                       'y_unit': 'B/s'},
                      {'name': 'write_bytes',
                       'description': 'Bytes write per second',
                       'color': '#FF0000',
                       'y_unit': 'B/s'}]


class Plugin(GlancesPlugin):

    """Glances disks I/O plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def get_key(self):
        """Return the key of the list."""
        return 'disk_name'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update disk I/O stats using the input method."""
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Grab the stat using the PsUtil disk_io_counters method
            # read_count: number of reads
            # write_count: number of writes
            # read_bytes: number of bytes read
            # write_bytes: number of bytes written
            # read_time: time spent reading from disk (in milliseconds)
            # write_time: time spent writing to disk (in milliseconds)
            try:
                diskiocounters = psutil.disk_io_counters(perdisk=True)
            except Exception:
                return self.stats

            # Previous disk IO stats are stored in the diskio_old variable
            if not hasattr(self, 'diskio_old'):
                # First call, we init the diskio_old var
                try:
                    self.diskio_old = diskiocounters
                except (IOError, UnboundLocalError):
                    pass
            else:
                # By storing time data we enable Rx/s and Tx/s calculations in the
                # XML/RPC API, which would otherwise be overly difficult work
                # for users of the API
                time_since_update = getTimeSinceLastUpdate('disk')

                diskio_new = diskiocounters
                for disk in diskio_new:
                    # By default, RamFS is not displayed (issue #714)
                    if self.args is not None and not self.args.diskio_show_ramfs and disk.startswith('ram'):
                        continue

                    # Do not take hide disk into account
                    if self.is_hide(disk):
                        continue

                    # Compute count and bit rate
                    try:
                        read_count = (diskio_new[disk].read_count -
                                      self.diskio_old[disk].read_count)
                        write_count = (diskio_new[disk].write_count -
                                       self.diskio_old[disk].write_count)
                        read_bytes = (diskio_new[disk].read_bytes -
                                      self.diskio_old[disk].read_bytes)
                        write_bytes = (diskio_new[disk].write_bytes -
                                       self.diskio_old[disk].write_bytes)
                        diskstat = {
                            'time_since_update': time_since_update,
                            'disk_name': disk,
                            'read_count': read_count,
                            'write_count': write_count,
                            'read_bytes': read_bytes,
                            'write_bytes': write_bytes}
                        # Add alias if exist (define in the configuration file)
                        if self.has_alias(disk) is not None:
                            diskstat['alias'] = self.has_alias(disk)
                    except KeyError:
                        continue
                    else:
                        diskstat['key'] = self.get_key()
                        self.stats.append(diskstat)

                # Save stats to compute next bitrate
                self.diskio_old = diskio_new
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # No standard way for the moment...
            pass

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert
        for i in self.stats:
            disk_real_name = i['disk_name']
            self.views[i[self.get_key()]]['read_bytes']['decoration'] = self.get_alert(int(i['read_bytes'] // i['time_since_update']),
                                                                                       header=disk_real_name + '_rx')
            self.views[i[self.get_key()]]['write_bytes']['decoration'] = self.get_alert(int(i['write_bytes'] // i['time_since_update']),
                                                                                        header=disk_real_name + '_tx')

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disable():
            return ret

        # Build the string message
        # Header
        msg = '{:9}'.format('DISK I/O')
        ret.append(self.curse_add_line(msg, "TITLE"))
        if args.diskio_iops:
            msg = '{:>7}'.format('IOR/s')
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format('IOW/s')
            ret.append(self.curse_add_line(msg))
        else:
            msg = '{:>7}'.format('R/s')
            ret.append(self.curse_add_line(msg))
            msg = '{:>7}'.format('W/s')
            ret.append(self.curse_add_line(msg))
        # Disk list (sorted by name)
        for i in sorted(self.stats, key=operator.itemgetter(self.get_key())):
            # Is there an alias for the disk name ?
            disk_real_name = i['disk_name']
            disk_name = self.has_alias(i['disk_name'])
            if disk_name is None:
                disk_name = disk_real_name
            # New line
            ret.append(self.curse_new_line())
            if len(disk_name) > 9:
                # Cut disk name if it is too long
                disk_name = '_' + disk_name[-8:]
            msg = '{:9}'.format(disk_name)
            ret.append(self.curse_add_line(msg))
            if args.diskio_iops:
                # count
                txps = self.auto_unit(
                    int(i['read_count'] // i['time_since_update']))
                rxps = self.auto_unit(
                    int(i['write_count'] // i['time_since_update']))
                msg = '{:>7}'.format(txps)
                ret.append(self.curse_add_line(msg,
                                               self.get_views(item=i[self.get_key()],
                                                              key='read_count',
                                                              option='decoration')))
                msg = '{:>7}'.format(rxps)
                ret.append(self.curse_add_line(msg,
                                               self.get_views(item=i[self.get_key()],
                                                              key='write_count',
                                                              option='decoration')))
            else:
                # Bitrate
                txps = self.auto_unit(
                    int(i['read_bytes'] // i['time_since_update']))
                rxps = self.auto_unit(
                    int(i['write_bytes'] // i['time_since_update']))
                msg = '{:>7}'.format(txps)
                ret.append(self.curse_add_line(msg,
                                               self.get_views(item=i[self.get_key()],
                                                              key='read_bytes',
                                                              option='decoration')))
                msg = '{:>7}'.format(rxps)
                ret.append(self.curse_add_line(msg,
                                               self.get_views(item=i[self.get_key()],
                                                              key='write_bytes',
                                                              option='decoration')))

        return ret

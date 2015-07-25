# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""Virtual memory plugin."""

from glances.plugins.glances_plugin import GlancesPlugin

import psutil

# SNMP OID
# Total RAM in machine: .1.3.6.1.4.1.2021.4.5.0
# Total RAM used: .1.3.6.1.4.1.2021.4.6.0
# Total RAM Free: .1.3.6.1.4.1.2021.4.11.0
# Total RAM Shared: .1.3.6.1.4.1.2021.4.13.0
# Total RAM Buffered: .1.3.6.1.4.1.2021.4.14.0
# Total Cached Memory: .1.3.6.1.4.1.2021.4.15.0
# Note: For Windows, stats are in the FS table
snmp_oid = {'default': {'total': '1.3.6.1.4.1.2021.4.5.0',
                        'free': '1.3.6.1.4.1.2021.4.11.0',
                        'shared': '1.3.6.1.4.1.2021.4.13.0',
                        'buffers': '1.3.6.1.4.1.2021.4.14.0',
                        'cached': '1.3.6.1.4.1.2021.4.15.0'},
            'windows': {'mnt_point': '1.3.6.1.2.1.25.2.3.1.3',
                        'alloc_unit': '1.3.6.1.2.1.25.2.3.1.4',
                        'size': '1.3.6.1.2.1.25.2.3.1.5',
                        'used': '1.3.6.1.2.1.25.2.3.1.6'},
            'esxi': {'mnt_point': '1.3.6.1.2.1.25.2.3.1.3',
                     'alloc_unit': '1.3.6.1.2.1.25.2.3.1.4',
                     'size': '1.3.6.1.2.1.25.2.3.1.5',
                     'used': '1.3.6.1.2.1.25.2.3.1.6'}}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
# 'color' define the graph color in #RGB format
items_history_list = [{'name': 'percent', 'color': '#00FF00', 'y_unit': '%'}]


class Plugin(GlancesPlugin):

    """Glances' memory plugin.

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args, items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update RAM memory stats using the input method."""
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Grab MEM using the PSUtil virtual_memory method
            vm_stats = psutil.virtual_memory()

            # Get all the memory stats (copy/paste of the PsUtil documentation)
            # total: total physical memory available.
            # available: the actual amount of available memory that can be given instantly to processes that request more memory in bytes; this is calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux) and it is supposed to be used to monitor actual memory usage in a cross platform fashion.
            # percent: the percentage usage calculated as (total - available) / total * 100.
            # used: memory used, calculated differently depending on the platform and designed for informational purposes only.
            # free: memory not being used at all (zeroed) that is readily available; note that this doesn’t reflect the actual memory available (use ‘available’ instead).
            # Platform-specific fields:
            # active: (UNIX): memory currently in use or very recently used, and so it is in RAM.
            # inactive: (UNIX): memory that is marked as not used.
            # buffers: (Linux, BSD): cache for things like file system metadata.
            # cached: (Linux, BSD): cache for various things.
            # wired: (BSD, OSX): memory that is marked to always stay in RAM. It is never moved to disk.
            # shared: (BSD): memory that may be simultaneously accessed by multiple processes.
            self.reset()
            for mem in ['total', 'available', 'percent', 'used', 'free',
                        'active', 'inactive', 'buffers', 'cached',
                        'wired', 'shared']:
                if hasattr(vm_stats, mem):
                    self.stats[mem] = getattr(vm_stats, mem)

            # Use the 'free'/htop calculation
            # free=available+buffer+cached
            self.stats['free'] = self.stats['available']
            if hasattr(self.stats, 'buffers'):
                self.stats['free'] += self.stats['buffers']
            if hasattr(self.stats, 'cached'):
                self.stats['free'] += self.stats['cached']
            # used=total-free
            self.stats['used'] = self.stats['total'] - self.stats['free']
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            if self.short_system_name in ('windows', 'esxi'):
                # Mem stats for Windows|Vmware Esxi are stored in the FS table
                try:
                    fs_stat = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name],
                                                  bulk=True)
                except KeyError:
                    self.reset()
                else:
                    for fs in fs_stat:
                        # The Physical Memory (Windows) or Real Memory (VMware)
                        # gives statistics on RAM usage and availability.
                        if fs in ('Physical Memory', 'Real Memory'):
                            self.stats['total'] = int(fs_stat[fs]['size']) * int(fs_stat[fs]['alloc_unit'])
                            self.stats['used'] = int(fs_stat[fs]['used']) * int(fs_stat[fs]['alloc_unit'])
                            self.stats['percent'] = float(self.stats['used'] * 100 / self.stats['total'])
                            self.stats['free'] = self.stats['total'] - self.stats['used']
                            break
            else:
                # Default behavor for others OS
                self.stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])

                if self.stats['total'] == '':
                    self.reset()
                    return self.stats

                for key in list(self.stats.keys()):
                    if self.stats[key] != '':
                        self.stats[key] = float(self.stats[key]) * 1024

                # Use the 'free'/htop calculation
                self.stats['free'] = self.stats['free'] - self.stats['total'] + (self.stats['buffers'] + self.stats['cached'])

                # used=total-free
                self.stats['used'] = self.stats['total'] - self.stats['free']

                # percent: the percentage usage calculated as (total - available) / total * 100.
                self.stats['percent'] = float((self.stats['total'] - self.stats['free']) / self.stats['total'] * 100)

        # Update the history list
        self.update_stats_history()

        # Update the view
        self.update_views()

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        GlancesPlugin.update_views(self)

        # Add specifics informations
        # Alert and log
        self.views['used']['decoration'] = self.get_alert_log(self.stats['used'], maximum=self.stats['total'])
        # Optional
        for key in ['active', 'inactive', 'buffers', 'cached']:
            if key in self.stats:
                self.views[key]['optional'] = True

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or args.disable_mem:
            return ret

        # Build the string message
        # Header
        msg = '{0:5} '.format('MEM')
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Percent memory usage
        msg = '{0:>7.1%}'.format(self.stats['percent'] / 100)
        ret.append(self.curse_add_line(msg))
        # Active memory usage
        if 'active' in self.stats:
            msg = '  {0:9}'.format('active:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='active', option='optional')))
            msg = '{0:>7}'.format(self.auto_unit(self.stats['active']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='active', option='optional')))
        # New line
        ret.append(self.curse_new_line())
        # Total memory usage
        msg = '{0:6}'.format('total:')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>7}'.format(self.auto_unit(self.stats['total']))
        ret.append(self.curse_add_line(msg))
        # Inactive memory usage
        if 'inactive' in self.stats:
            msg = '  {0:9}'.format('inactive:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='inactive', option='optional')))
            msg = '{0:>7}'.format(self.auto_unit(self.stats['inactive']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='inactive', option='optional')))
        # New line
        ret.append(self.curse_new_line())
        # Used memory usage
        msg = '{0:6}'.format('used:')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>7}'.format(self.auto_unit(self.stats['used']))
        ret.append(self.curse_add_line(
            msg, self.get_views(key='used', option='decoration')))
        # Buffers memory usage
        if 'buffers' in self.stats:
            msg = '  {0:9}'.format('buffers:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='buffers', option='optional')))
            msg = '{0:>7}'.format(self.auto_unit(self.stats['buffers']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='buffers', option='optional')))
        # New line
        ret.append(self.curse_new_line())
        # Free memory usage
        msg = '{0:6}'.format('free:')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>7}'.format(self.auto_unit(self.stats['free']))
        ret.append(self.curse_add_line(msg))
        # Cached memory usage
        if 'cached' in self.stats:
            msg = '  {0:9}'.format('cached:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='cached', option='optional')))
            msg = '{0:>7}'.format(self.auto_unit(self.stats['cached']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='cached', option='optional')))

        return ret

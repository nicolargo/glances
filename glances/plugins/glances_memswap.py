# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Swap memory plugin."""

from glances.compat import iterkeys
from glances.plugins.glances_plugin import GlancesPlugin

import psutil

# SNMP OID
# Total Swap Size: .1.3.6.1.4.1.2021.4.3.0
# Available Swap Space: .1.3.6.1.4.1.2021.4.4.0
snmp_oid = {'default': {'total': '1.3.6.1.4.1.2021.4.3.0',
                        'free': '1.3.6.1.4.1.2021.4.4.0'},
            'windows': {'mnt_point': '1.3.6.1.2.1.25.2.3.1.3',
                        'alloc_unit': '1.3.6.1.2.1.25.2.3.1.4',
                        'size': '1.3.6.1.2.1.25.2.3.1.5',
                        'used': '1.3.6.1.2.1.25.2.3.1.6'}}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [{'name': 'percent',
                       'description': 'Swap memory usage',
                       'y_unit': '%'}]


class Plugin(GlancesPlugin):
    """Glances swap memory plugin.

    stats is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update swap memory stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Grab SWAP using the psutil swap_memory method
            sm_stats = psutil.swap_memory()

            # Get all the swap stats (copy/paste of the psutil documentation)
            # total: total swap memory in bytes
            # used: used swap memory in bytes
            # free: free swap memory in bytes
            # percent: the percentage usage
            # sin: the number of bytes the system has swapped in from disk (cumulative)
            # sout: the number of bytes the system has swapped out from disk
            # (cumulative)
            for swap in ['total', 'used', 'free', 'percent',
                         'sin', 'sout']:
                if hasattr(sm_stats, swap):
                    stats[swap] = getattr(sm_stats, swap)
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            if self.short_system_name == 'windows':
                # Mem stats for Windows OS are stored in the FS table
                try:
                    fs_stat = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name],
                                                  bulk=True)
                except KeyError:
                    self.reset()
                else:
                    for fs in fs_stat:
                        # The virtual memory concept is used by the operating
                        # system to extend (virtually) the physical memory and
                        # thus to run more programs by swapping unused memory
                        # zone (page) to a disk file.
                        if fs == 'Virtual Memory':
                            stats['total'] = int(
                                fs_stat[fs]['size']) * int(fs_stat[fs]['alloc_unit'])
                            stats['used'] = int(
                                fs_stat[fs]['used']) * int(fs_stat[fs]['alloc_unit'])
                            stats['percent'] = float(
                                stats['used'] * 100 / stats['total'])
                            stats['free'] = stats['total'] - stats['used']
                            break
            else:
                stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])

                if stats['total'] == '':
                    self.reset()
                    return stats

                for key in iterkeys(stats):
                    if stats[key] != '':
                        stats[key] = float(stats[key]) * 1024

                # used=total-free
                stats['used'] = stats['total'] - stats['free']

                # percent: the percentage usage calculated as (total -
                # available) / total * 100.
                stats['percent'] = float(
                    (stats['total'] - stats['free']) / stats['total'] * 100)

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert and log
        self.views['used']['decoration'] = self.get_alert_log(self.stats['used'], maximum=self.stats['total'])

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or self.is_disable():
            return ret

        # Build the string message
        # Header
        msg = '{}'.format('SWAP')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {:3}'.format(self.trend_msg(self.get_trend('percent')))
        ret.append(self.curse_add_line(msg))
        # Percent memory usage
        msg = '{:>6.1%}'.format(self.stats['percent'] / 100)
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # Total memory usage
        msg = '{:8}'.format('total:')
        ret.append(self.curse_add_line(msg))
        msg = '{:>6}'.format(self.auto_unit(self.stats['total']))
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # Used memory usage
        msg = '{:8}'.format('used:')
        ret.append(self.curse_add_line(msg))
        msg = '{:>6}'.format(self.auto_unit(self.stats['used']))
        ret.append(self.curse_add_line(
            msg, self.get_views(key='used', option='decoration')))
        # New line
        ret.append(self.curse_new_line())
        # Free memory usage
        msg = '{:8}'.format('free:')
        ret.append(self.curse_add_line(msg))
        msg = '{:>6}'.format(self.auto_unit(self.stats['free']))
        ret.append(self.curse_add_line(msg))

        return ret

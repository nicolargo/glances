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

"""Swap memory plugin."""

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
# 'color' define the graph color in #RGB format
items_history_list = [{'name': 'percent', 'color': '#00FF00', 'y_unit': '%'}]


class Plugin(GlancesPlugin):

    """Glances swap memory plugin.

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(
            self, args=args, items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update swap memory stats using the input method."""
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Grab SWAP using the PSUtil swap_memory method
            sm_stats = psutil.swap_memory()

            # Get all the swap stats (copy/paste of the PsUtil documentation)
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
                    self.stats[swap] = getattr(sm_stats, swap)
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
                            self.stats['total'] = int(
                                fs_stat[fs]['size']) * int(fs_stat[fs]['alloc_unit'])
                            self.stats['used'] = int(
                                fs_stat[fs]['used']) * int(fs_stat[fs]['alloc_unit'])
                            self.stats['percent'] = float(
                                self.stats['used'] * 100 / self.stats['total'])
                            self.stats['free'] = self.stats[
                                'total'] - self.stats['used']
                            break
            else:
                self.stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])

                if self.stats['total'] == '':
                    self.reset()
                    return self.stats

                for key in list(self.stats.keys()):
                    if self.stats[key] != '':
                        self.stats[key] = float(self.stats[key]) * 1024

                # used=total-free
                self.stats['used'] = self.stats['total'] - self.stats['free']

                # percent: the percentage usage calculated as (total -
                # available) / total * 100.
                self.stats['percent'] = float(
                    (self.stats['total'] - self.stats['free']) / self.stats['total'] * 100)

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

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or args.disable_swap:
            return ret

        # Build the string message
        # Header
        msg = '{0:7} '.format('SWAP')
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Percent memory usage
        msg = '{0:>6.1%}'.format(self.stats['percent'] / 100)
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # Total memory usage
        msg = '{0:8}'.format('total:')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6}'.format(self.auto_unit(self.stats['total']))
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # Used memory usage
        msg = '{0:8}'.format('used:')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6}'.format(self.auto_unit(self.stats['used']))
        ret.append(self.curse_add_line(
            msg, self.get_views(key='used', option='decoration')))
        # New line
        ret.append(self.curse_new_line())
        # Free memory usage
        msg = '{0:8}'.format('free:')
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6}'.format(self.auto_unit(self.stats['free']))
        ret.append(self.curse_add_line(msg))

        return ret

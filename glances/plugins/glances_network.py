# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

"""Network plugin."""

import base64
import operator

import psutil

from glances.core.glances_timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin

# SNMP OID
# http://www.net-snmp.org/docs/mibs/interfaces.html
# Dict key = interface_name
snmp_oid = {'default': {'interface_name': '1.3.6.1.2.1.2.2.1.2',
                        'cumulative_rx': '1.3.6.1.2.1.2.2.1.10',
                        'cumulative_tx': '1.3.6.1.2.1.2.2.1.16'}}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
# 'color' define the graph color in #RGB format
items_history_list = [{'name': 'rx', 'color': '#00FF00', 'y_unit': 'bit/s'},
                      {'name': 'tx', 'color': '#FF0000', 'y_unit': 'bit/s'}]


class Plugin(GlancesPlugin):

    """Glances' network Plugin.

    stats is a list
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
        self.stats = []

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update network stats using the input method.

        Stats is a list of dict (one dict per interface)
        """
        # Reset stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the standard system lib

            # Grab network interface stat using the PsUtil net_io_counter method
            try:
                netiocounters = psutil.net_io_counters(pernic=True)
            except UnicodeDecodeError:
                return self.stats

            # Previous network interface stats are stored in the network_old variable
            if not hasattr(self, 'network_old'):
                # First call, we init the network_old var
                try:
                    self.network_old = netiocounters
                except (IOError, UnboundLocalError):
                    pass
            else:
                # By storing time data we enable Rx/s and Tx/s calculations in the
                # XML/RPC API, which would otherwise be overly difficult work
                # for users of the API
                time_since_update = getTimeSinceLastUpdate('net')

                # Loop over interfaces
                network_new = netiocounters
                for net in network_new:
                    try:
                        # Try necessary to manage dynamic network interface
                        netstat = {}
                        netstat['interface_name'] = net
                        netstat['time_since_update'] = time_since_update
                        netstat['cumulative_rx'] = network_new[net].bytes_recv
                        netstat['rx'] = (network_new[net].bytes_recv -
                                         self.network_old[net].bytes_recv)
                        netstat['cumulative_tx'] = network_new[net].bytes_sent
                        netstat['tx'] = (network_new[net].bytes_sent -
                                         self.network_old[net].bytes_sent)
                        netstat['cumulative_cx'] = (netstat['cumulative_rx'] +
                                                    netstat['cumulative_tx'])
                        netstat['cx'] = netstat['rx'] + netstat['tx']
                    except KeyError:
                        continue
                    else:
                        self.stats.append(netstat)

                # Save stats to compute next bitrate
                self.network_old = network_new

        elif self.get_input() == 'snmp':
            # Update stats using SNMP

            # SNMP bulk command to get all network interface in one shot
            try:
                netiocounters = self.set_stats_snmp(snmp_oid=snmp_oid[self.get_short_system_name()],
                                                    bulk=True)
            except KeyError:
                netiocounters = self.set_stats_snmp(snmp_oid=snmp_oid['default'],
                                                    bulk=True)

            # Previous network interface stats are stored in the network_old variable
            if not hasattr(self, 'network_old'):
                # First call, we init the network_old var
                try:
                    self.network_old = netiocounters
                except (IOError, UnboundLocalError):
                    pass
            else:
                # See description in the 'local' block
                time_since_update = getTimeSinceLastUpdate('net')

                # Loop over interfaces
                network_new = netiocounters

                for net in network_new:
                    try:
                        # Try necessary to manage dynamic network interface
                        netstat = {}
                        # Windows: a tips is needed to convert HEX to TXT
                        # http://blogs.technet.com/b/networking/archive/2009/12/18/how-to-query-the-list-of-network-interfaces-using-snmp-via-the-ifdescr-counter.aspx
                        if self.get_short_system_name() == 'windows':
                            try:
                                netstat['interface_name'] = str(base64.b16decode(net[2:-2].upper()))
                            except TypeError:
                                netstat['interface_name'] = net
                        else:
                            netstat['interface_name'] = net
                        netstat['time_since_update'] = time_since_update
                        netstat['cumulative_rx'] = float(network_new[net]['cumulative_rx'])
                        netstat['rx'] = (float(network_new[net]['cumulative_rx']) -
                                         float(self.network_old[net]['cumulative_rx']))
                        netstat['cumulative_tx'] = float(network_new[net]['cumulative_tx'])
                        netstat['tx'] = (float(network_new[net]['cumulative_tx']) -
                                         float(self.network_old[net]['cumulative_tx']))
                        netstat['cumulative_cx'] = (netstat['cumulative_rx'] +
                                                    netstat['cumulative_tx'])
                        netstat['cx'] = netstat['rx'] + netstat['tx']
                    except KeyError:
                        continue
                    else:
                        self.stats.append(netstat)

                # Save stats to compute next bitrate
                self.network_old = network_new

        # Update the history list
        self.update_stats_history('interface_name')

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""

        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_network:
            return ret

        # Max size for the interface name
        if max_width is not None and max_width >= 23:
            # Interface size name = max_width - space for interfaces bitrate
            ifname_max_width = max_width - 14
        else:
            ifname_max_width = 9

        # Build the string message
        # Header
        msg = '{0:{width}}'.format(_("NETWORK"), width=ifname_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        if args.network_cumul:
            # Cumulative stats
            if args.network_sum:
                # Sum stats
                msg = '{0:>14}'.format(_("Rx+Tx"))
                ret.append(self.curse_add_line(msg))
            else:
                # Rx/Tx stats
                msg = '{0:>7}'.format(_("Rx"))
                ret.append(self.curse_add_line(msg))
                msg = '{0:>7}'.format(_("Tx"))
                ret.append(self.curse_add_line(msg))
        else:
            # Bitrate stats
            if args.network_sum:
                # Sum stats
                msg = '{0:>14}'.format(_("Rx+Tx/s"))
                ret.append(self.curse_add_line(msg))
            else:
                msg = '{0:>7}'.format(_("Rx/s"))
                ret.append(self.curse_add_line(msg))
                msg = '{0:>7}'.format(_("Tx/s"))
                ret.append(self.curse_add_line(msg))
        # Interface list (sorted by name)
        for i in sorted(self.stats, key=operator.itemgetter('interface_name')):
            # Do not display hidden interfaces
            if self.is_hide(i['interface_name']):
                continue
            # Format stats
            # Is there an alias for the interface name ?
            ifname = self.has_alias(i['interface_name'])
            if ifname is None:
                ifname = i['interface_name'].split(':')[0]
            if len(ifname) > ifname_max_width:
                # Cut interface name if it is too long
                ifname = '_' + ifname[-ifname_max_width + 1:]
            if args.byte:
                # Bytes per second (for dummy)
                if args.network_cumul:
                    rx = self.auto_unit(int(i['cumulative_rx']))
                    tx = self.auto_unit(int(i['cumulative_tx']))
                    sx = self.auto_unit(int(i['cumulative_tx'])
                                        + int(i['cumulative_tx']))
                else:
                    rx = self.auto_unit(int(i['rx'] // i['time_since_update']))
                    tx = self.auto_unit(int(i['tx'] // i['time_since_update']))
                    sx = self.auto_unit(int(i['rx'] // i['time_since_update'])
                                        + int(i['tx'] // i['time_since_update']))
            else:
                # Bits per second (for real network administrator | Default)
                if args.network_cumul:
                    rx = self.auto_unit(int(i['cumulative_rx'] * 8)) + "b"
                    tx = self.auto_unit(int(i['cumulative_tx'] * 8)) + "b"
                    sx = self.auto_unit(int(i['cumulative_rx'] * 8)
                                        + int(i['cumulative_tx'] * 8)) + "b"
                else:
                    rx = self.auto_unit(int(i['rx'] // i['time_since_update'] * 8)) + "b"
                    tx = self.auto_unit(int(i['tx'] // i['time_since_update'] * 8)) + "b"
                    sx = self.auto_unit(int(i['rx'] // i['time_since_update'] * 8) +
                                        int(i['tx'] // i['time_since_update'] * 8)) + "b"
            # New line
            ret.append(self.curse_new_line())
            msg = '{0:{width}}'.format(ifname, width=ifname_max_width)
            ret.append(self.curse_add_line(msg))
            if args.network_sum:
                msg = '{0:>14}'.format(sx)
                ret.append(self.curse_add_line(msg))
            else:
                msg = '{0:>7}'.format(rx)
                ret.append(self.curse_add_line(
                    msg, self.get_alert(int(i['rx'] // i['time_since_update'] * 8),
                                        header=ifname + '_rx')))
                msg = '{0:>7}'.format(tx)
                ret.append(self.curse_add_line(
                    msg, self.get_alert(int(i['tx'] // i['time_since_update'] * 8),
                                        header=ifname + '_tx')))

        return ret

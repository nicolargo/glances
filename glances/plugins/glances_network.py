#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# Import system libs
try:
    # psutil >= 1.0.0
    from psutil import net_io_counters
except:
    # psutil < 1.0.0
    try:
        from psutil import network_io_counters
    except:
        pass

# Import Glances lib
from glances_plugin import GlancesPlugin
from glances.core.glances_timer import getTimeSinceLastUpdate


class Plugin(GlancesPlugin):
    """
    Glances's network Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 0
        # Enter -1 to diplay bottom
        self.line_curse = 2

    def update(self):
        """
        Update network stats
        """
        network = []

        # psutil >= 1.0.0
        try:
            get_net_io_counters = net_io_counters(pernic=True)
        except IOError:
            # psutil < 1.0.0
            try:
                get_net_io_counters = network_io_counters(pernic=True)
            except IOError:
                pass

        # By storing time data we enable Rx/s and Tx/s calculations in the
        # XML/RPC API, which would otherwise be overly difficult work
        # for users of the API
        time_since_update = getTimeSinceLastUpdate('net')

        # Previous network interface stats are stored in the network_old variable
        if not hasattr(self, 'network_old'):
            # First call, we init the network_old var
            try:
                self.network_old = get_net_io_counters
            except (IOError, UnboundLocalError):
                pass
        else:
            network_new = get_net_io_counters
            for net in network_new:
                try:
                    # Try necessary to manage dynamic network interface
                    netstat = {}
                    netstat['time_since_update'] = time_since_update
                    netstat['interface_name'] = net
                    netstat['cumulative_rx'] = network_new[net].bytes_recv
                    netstat['rx'] = (network_new[net].bytes_recv -
                                     self.network_old[net].bytes_recv)
                    netstat['cumulative_tx'] = network_new[net].bytes_sent
                    netstat['tx'] = (network_new[net].bytes_sent -
                                     self.network_old[net].bytes_sent)
                    netstat['cumulative_cx'] = (netstat['cumulative_rx'] +
                                                netstat['cumulative_tx'])
                    netstat['cx'] = netstat['rx'] + netstat['tx']
                except Exception:
                    continue
                else:
                    network.append(netstat)
            self.network_old = network_new

        self.stats = network

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Build the string message
        # Header
        msg = "{0:8}".format(_("NETWORK"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = " {0:>6}".format(_("Rx/s"))
        ret.append(self.curse_add_line(msg))
        msg = "  {0:>6}".format(_("Tx/s"))
        ret.append(self.curse_add_line(msg))
        # Interface list (sorted by name)
        for i in sorted(self.stats, key=lambda network: network['interface_name']):
            # Format stats
            ifname = i['interface_name'].split(':')[0]
            if (args.byte):
                rxps = self.auto_unit(int(i['rx'] // i['time_since_update']))
                txps = self.auto_unit(int(i['tx'] // i['time_since_update']))
            else:
                rxps = self.auto_unit(int(i['rx'] // i['time_since_update'] * 8)) + "b"
                txps = self.auto_unit(int(i['tx'] // i['time_since_update'] * 8)) + "b"
            # !!! TODO: manage the hide tag
            # New line
            ret.append(self.curse_new_line())
            msg = "{0:8}".format(ifname)
            ret.append(self.curse_add_line(msg))
            msg = " {0:>6}".format(rxps)
            ret.append(self.curse_add_line(msg))
            msg = "  {0:>6}".format(txps)
            ret.append(self.curse_add_line(msg))

        return ret

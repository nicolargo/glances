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
import json

try:
    # psutil >= 1.0.0
    from psutil import net_io_counters
except:
    # psutil < 1.0.0
    try:
        from psutil import network_io_counters
    except:
        pass

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin, getTimeSinceLastUpdate

class Plugin(GlancesPlugin):
    """
    Glances's network Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)


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


    def get_stats(self):
        # Return the stats object for the RPC API
        # !!! Sort it by interface name (why do it here ? Better in client side ?)
        self.stats = sorted(self.stats, key=lambda network: network['interface_name'])
        return GlancesPlugin.get_stats(self)

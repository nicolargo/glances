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

"""Connections plugin."""
from __future__ import unicode_literals

from glances.timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin
from glances.compat import n, u, b, nativestr

import psutil

# Define the history items list
# items_history_list = [{'name': 'rx',
#                        'description': 'Download rate per second',
#                        'y_unit': 'bit/s'},
#                       {'name': 'tx',
#                        'description': 'Upload rate per second',
#                        'y_unit': 'bit/s'}]


class Plugin(GlancesPlugin):
    """Glances connections plugin.

    stats is a dict
    """

    status_list = [psutil.CONN_LISTEN,
                   psutil.CONN_ESTABLISHED]
    initiated_states = [psutil.CONN_SYN_SENT,
                        psutil.CONN_SYN_RECV]
    terminated_states = [psutil.CONN_FIN_WAIT1,
                         psutil.CONN_FIN_WAIT2,
                         psutil.CONN_TIME_WAIT,
                         psutil.CONN_CLOSE,
                         psutil.CONN_CLOSE_WAIT,
                         psutil.CONN_LAST_ACK]
    conntrack = {'nf_conntrack_count': '/proc/sys/net/netfilter/nf_conntrack_count',
                 'nf_conntrack_max': '/proc/sys/net/netfilter/nf_conntrack_max'}

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     # items_history_list=items_history_list,
                                     stats_init_value={})

        # We want to display the stat in the curse interface
        self.display_curse = True

        # @TODO the plugin should be enable only for Linux OS

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update connections stats using the input method.

        Stats is a dict
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the PSUtils lib

            # Grab network interface stat using the psutil net_connections method
            try:
                net_connections = psutil.net_connections(kind="tcp")
            except Exception as e:
                logger.debug('Can not get network connections stats ({})'.format(e))
                return self.stats

            for s in self.status_list:
                stats[s] = len([c for c in net_connections if c.status == s])
            initiated = 0
            for s in self.initiated_states:
                stats[s] = len([c for c in net_connections if c.status == s])
                initiated += stats[s]
            stats['initiated'] = initiated
            terminated = 0
            for s in self.initiated_states:
                stats[s] = len([c for c in net_connections if c.status == s])
                terminated += stats[s]
            stats['terminated'] = terminated

            # Grab connections track directly from the /proc file
            for i in self.conntrack:
                with open(self.conntrack[i], 'r') as f:
                    stats[i] = float(f.readline().rstrip("\n"))

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert
        # for i in self.stats:
        #     ifrealname = i['interface_name'].split(':')[0]
        #     # Convert rate in bps ( to be able to compare to interface speed)
        #     bps_rx = int(i['rx'] // i['time_since_update'] * 8)
        #     bps_tx = int(i['tx'] // i['time_since_update'] * 8)
        #     # Decorate the bitrate with the configuration file thresolds
        #     alert_rx = self.get_alert(bps_rx, header=ifrealname + '_rx')
        #     alert_tx = self.get_alert(bps_tx, header=ifrealname + '_tx')
        #     # If nothing is define in the configuration file...
        #     # ... then use the interface speed (not available on all systems)
        #     if alert_rx == 'DEFAULT' and 'speed' in i and i['speed'] != 0:
        #         alert_rx = self.get_alert(current=bps_rx,
        #                                   maximum=i['speed'],
        #                                   header='rx')
        #     if alert_tx == 'DEFAULT' and 'speed' in i and i['speed'] != 0:
        #         alert_tx = self.get_alert(current=bps_tx,
        #                                   maximum=i['speed'],
        #                                   header='tx')
        #     # then decorates
        #     self.views[i[self.get_key()]]['rx']['decoration'] = alert_rx
        #     self.views[i[self.get_key()]]['tx']['decoration'] = alert_tx

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disable():
            return ret

        # Header
        msg = '{}'.format('TCP CONNECTIONS')
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Connections status
        for s in [psutil.CONN_LISTEN, 'initiated', psutil.CONN_ESTABLISHED, 'terminated']:
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(nativestr(s).capitalize(), width=len(s))
            ret.append(self.curse_add_line(msg))
            msg = '{:>{width}}'.format(self.stats[s], width=max_width - len(s) + 2)
            ret.append(self.curse_add_line(msg))
        # Connections track
        s = 'Tracked'
        ret.append(self.curse_new_line())
        msg = '{:{width}}'.format(nativestr(s).capitalize(), width=len(s))
        ret.append(self.curse_add_line(msg))
        msg = '{:>{width}}'.format('{:0.0f}/{:0.0f}'.format(self.stats['nf_conntrack_count'],
                                                            self.stats['nf_conntrack_max']),
                                   width=max_width - len(s) + 2)
        ret.append(self.curse_add_line(msg))

        return ret

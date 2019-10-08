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

from glances.logger import logger
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

        # This plugin is composed if net_connections and nf_conntrack
        # Enabled by default
        self.net_connections_enabled = True
        self.nf_conntrack_enabled = True

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
            if self.net_connections_enabled:
                try:
                    net_connections = psutil.net_connections(kind="tcp")
                except Exception as e:
                    logger.debug('Can not get network connections stats ({})'.format(e))
                    self.net_connections_enabled = False
                    self.stats = stats
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

            if self.nf_conntrack_enabled:
                # Grab connections track directly from the /proc file
                for i in self.conntrack:
                    try:
                        with open(self.conntrack[i], 'r') as f:
                            stats[i] = float(f.readline().rstrip("\n"))
                    except IOError as e:
                        logger.debug('Can not get network connections track ({})'.format(e))
                        self.nf_conntrack_enabled = False
                        self.stats = stats
                        return self.stats
                stats['nf_conntrack_percent'] = stats['nf_conntrack_count'] * 100 / stats['nf_conntrack_max']

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
        try:
            # Alert and log
            if self.nf_conntrack_enabled:
                self.views['nf_conntrack_percent']['decoration'] = self.get_alert(header='nf_conntrack_percent')
        except KeyError:
            # try/except mandatory for Windows compatibility (no conntrack stats)
            pass

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disable():
            return ret

        # Header
        if self.net_connections_enabled or self.nf_conntrack_enabled:
            msg = '{}'.format('TCP CONNECTIONS')
            ret.append(self.curse_add_line(msg, "TITLE"))
        # Connections status
        if self.net_connections_enabled:
            for s in [psutil.CONN_LISTEN, 'initiated', psutil.CONN_ESTABLISHED, 'terminated']:
                ret.append(self.curse_new_line())
                msg = '{:{width}}'.format(nativestr(s).capitalize(), width=len(s))
                ret.append(self.curse_add_line(msg))
                msg = '{:>{width}}'.format(self.stats[s], width=max_width - len(s) + 2)
                ret.append(self.curse_add_line(msg))
        # Connections track
        if self.nf_conntrack_enabled:
            s = 'Tracked'
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(nativestr(s).capitalize(), width=len(s))
            ret.append(self.curse_add_line(msg))
            msg = '{:>{width}}'.format('{:0.0f}/{:0.0f}'.format(self.stats['nf_conntrack_count'],
                                                                self.stats['nf_conntrack_max']),
                                       width=max_width - len(s) + 2)
            ret.append(self.curse_add_line(msg,
                                           self.get_views(key='nf_conntrack_percent',
                                                          option='decoration')))

        return ret

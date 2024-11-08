#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Connections plugin."""

import psutil

from glances.globals import nativestr
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'LISTEN': {
        'description': 'Number of TCP connections in LISTEN state',
        'unit': 'number',
    },
    'ESTABLISHED': {
        'description': 'Number of TCP connections in ESTABLISHED state',
        'unit': 'number',
    },
    'SYN_SENT': {
        'description': 'Number of TCP connections in SYN_SENT state',
        'unit': 'number',
    },
    'SYN_RECV': {
        'description': 'Number of TCP connections in SYN_RECV state',
        'unit': 'number',
    },
    'initiated': {
        'description': 'Number of TCP connections initiated',
        'unit': 'number',
    },
    'terminated': {
        'description': 'Number of TCP connections terminated',
        'unit': 'number',
    },
    'nf_conntrack_count': {
        'description': 'Number of tracked connections',
        'unit': 'number',
    },
    'nf_conntrack_max': {
        'description': 'Maximum number of tracked connections',
        'unit': 'number',
    },
    'nf_conntrack_percent': {
        'description': 'Percentage of tracked connections',
        'unit': 'percent',
    },
}

# Define the history items list
# items_history_list = [{'name': 'rx',
#                        'description': 'Download rate per second',
#                        'y_unit': 'bit/s'},
#                       {'name': 'tx',
#                        'description': 'Upload rate per second',
#                        'y_unit': 'bit/s'}]


class PluginModel(GlancesPluginModel):
    """Glances connections plugin.

    stats is a dict
    """

    status_list = [psutil.CONN_LISTEN, psutil.CONN_ESTABLISHED]
    initiated_states = [psutil.CONN_SYN_SENT, psutil.CONN_SYN_RECV]
    terminated_states = [
        psutil.CONN_FIN_WAIT1,
        psutil.CONN_FIN_WAIT2,
        psutil.CONN_TIME_WAIT,
        psutil.CONN_CLOSE,
        psutil.CONN_CLOSE_WAIT,
        psutil.CONN_LAST_ACK,
    ]
    conntrack = {
        'nf_conntrack_count': '/proc/sys/net/netfilter/nf_conntrack_count',
        'nf_conntrack_max': '/proc/sys/net/netfilter/nf_conntrack_max',
    }

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args,
            config=config,
            # items_history_list=items_history_list,
            stats_init_value={'net_connections_enabled': True, 'nf_conntrack_enabled': True},
            fields_description=fields_description,
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update connections stats using the input method.

        Stats is a dict
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the PSUtils lib

            # Grab network interface stat using the psutil net_connections method
            if stats['net_connections_enabled']:
                try:
                    net_connections = psutil.net_connections(kind="tcp")
                except Exception as e:
                    logger.warning(f'Can not get network connections stats ({e})')
                    logger.info('Disable connections stats')
                    stats['net_connections_enabled'] = False
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

            if stats['nf_conntrack_enabled']:
                # Grab connections track directly from the /proc file
                for i in self.conntrack:
                    try:
                        with open(self.conntrack[i]) as f:
                            stats[i] = float(f.readline().rstrip("\n"))
                    except (OSError, FileNotFoundError) as e:
                        logger.warning(f'Can not get network connections track ({e})')
                        logger.info('Disable connections track')
                        stats['nf_conntrack_enabled'] = False
                        self.stats = stats
                        return self.stats
                if 'nf_conntrack_max' in stats and 'nf_conntrack_count' in stats:
                    stats['nf_conntrack_percent'] = stats['nf_conntrack_count'] * 100 / stats['nf_conntrack_max']
                else:
                    stats['nf_conntrack_enabled'] = False
                    self.stats = stats
                    return self.stats

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            pass

        # Update the stats
        self.stats = stats
        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        # Add specific information
        try:
            # Alert and log
            if self.stats['nf_conntrack_enabled']:
                self.views['nf_conntrack_percent']['decoration'] = self.get_alert(header='nf_conntrack_percent')
        except KeyError:
            # try/except mandatory for Windows compatibility (no conntrack stats)
            pass

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled() or not max_width:
            return ret

        # Header
        if self.stats['net_connections_enabled'] or self.stats['nf_conntrack_enabled']:
            msg = '{}'.format('TCP CONNECTIONS')
            ret.append(self.curse_add_line(msg, "TITLE"))
        # Connections status
        if self.stats['net_connections_enabled']:
            for s in [psutil.CONN_LISTEN, 'initiated', psutil.CONN_ESTABLISHED, 'terminated']:
                if s not in self.stats:
                    continue
                ret.append(self.curse_new_line())
                msg = '{:{width}}'.format(nativestr(s).capitalize(), width=len(s))
                ret.append(self.curse_add_line(msg))
                msg = '{:>{width}}'.format(self.stats[s], width=max_width - len(s) + 2)
                ret.append(self.curse_add_line(msg))
        # Connections track
        if (
            self.stats['nf_conntrack_enabled']
            and 'nf_conntrack_count' in self.stats
            and 'nf_conntrack_max' in self.stats
        ):
            s = 'Tracked'
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(nativestr(s).capitalize(), width=len(s))
            ret.append(self.curse_add_line(msg))
            msg = '{:>{width}}'.format(
                '{:0.0f}/{:0.0f}'.format(self.stats['nf_conntrack_count'], self.stats['nf_conntrack_max']),
                width=max_width - len(s) + 2,
            )
            ret.append(self.curse_add_line(msg, self.get_views(key='nf_conntrack_percent', option='decoration')))

        return ret

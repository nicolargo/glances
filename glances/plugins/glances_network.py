# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Network plugin."""
from __future__ import unicode_literals

import base64

from glances.timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin
from glances.compat import n
from glances.logger import logger

import psutil

# {'interface_name': 'mpqemubr0-dummy',
# 'alias': None,
# 'time_since_update': 2.081636428833008,
# 'cumulative_rx': 0,
# 'rx': 0, 'cumulative_tx': 0, 'tx': 0, 'cumulative_cx': 0, 'cx': 0,
# 'is_up': False,
# 'speed': 0,
# 'key': 'interface_name'}
# Fields description
fields_description = {
    'interface_name': {
        'description': 'Interface name.',
        'unit': 'string'
    },
    'alias': {
        'description': 'Interface alias name (optional).',
        'unit': 'string'
    },
    'rx': {
        'description': 'The received/input rate (in bit per second).',
        'unit': 'bps'
    },
    'tx': {
        'description': 'The sent/output rate (in bit per second).',
        'unit': 'bps'
    },
    'cx': {
        'description': 'The cumulative received+sent rate (in bit per second).',
        'unit': 'bps'
    },
    'cumulative_rx': {
        'description': 'The number of bytes received through the interface (cumulative).',
        'unit': 'bytes',
    },
    'cumulative_tx': {
        'description': 'The number of bytes sent through the interface (cumulative).',
        'unit': 'bytes'
    },
    'cumulative_cx': {
        'description': 'The cumulative number of bytes reveived and sent through the interface (cumulative).',
        'unit': 'bytes'
    },
    'speed': {
        'description': 'Maximum interface speed (in bit per second). Can return 0 on some operating-system.',
        'unit': 'bps',
    },
    'is_up': {
        'description': 'Is the interface up ?',
        'unit': 'bool'
    },
    'time_since_update': {
        'description': 'Number of seconds since last update.',
        'unit': 'seconds'
    },
}

# SNMP OID
# http://www.net-snmp.org/docs/mibs/interfaces.html
# Dict key = interface_name
snmp_oid = {
    'default': {
        'interface_name': '1.3.6.1.2.1.2.2.1.2',
        'cumulative_rx': '1.3.6.1.2.1.2.2.1.10',
        'cumulative_tx': '1.3.6.1.2.1.2.2.1.16',
    }
}

# Define the history items list
items_history_list = [
    {'name': 'rx', 'description': 'Download rate per second', 'y_unit': 'bit/s'},
    {'name': 'tx', 'description': 'Upload rate per second', 'y_unit': 'bit/s'},
]


class Plugin(GlancesPlugin):
    """Glances network plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            fields_description=fields_description,
            stats_init_value=[],
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Hide stats if it has never been != 0
        if config is not None:
            self.hide_zero = config.get_bool_value(self.plugin_name, 'hide_zero', default=False)
        else:
            self.hide_zero = False
        self.hide_zero_fields = ['rx', 'tx']

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def get_key(self):
        """Return the key of the list."""
        return 'interface_name'

    # @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update network stats using the input method.

        :return: list of stats dict (one dict per interface)
        """
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib

            # Grab network interface stat using the psutil net_io_counter method
            try:
                net_io_counters = psutil.net_io_counters(pernic=True)
            except UnicodeDecodeError as e:
                logger.debug('Can not get network interface counters ({})'.format(e))
                return self.stats

            # Grab interface's status (issue #765)
            # Grab interface's speed (issue #718)
            net_status = {}
            try:
                net_status = psutil.net_if_stats()
            except OSError as e:
                # see psutil #797/glances #1106
                logger.debug('Can not get network interface status ({})'.format(e))

            # Previous network interface stats are stored in the network_old variable
            if not hasattr(self, 'network_old'):
                # First call, we init the network_old var
                try:
                    self.network_old = net_io_counters
                except (IOError, UnboundLocalError):
                    pass
                return self.stats

            # By storing time data we enable Rx/s and Tx/s calculations in the
            # XML/RPC API, which would otherwise be overly difficult work
            # for users of the API
            time_since_update = getTimeSinceLastUpdate('net')

            # Loop over interfaces
            network_new = net_io_counters
            for net in network_new:
                # Do not take hidden interface into account
                # or KeyError: 'eth0' when interface is not connected #1348
                if not self.is_display(net) or net not in net_status:
                    continue
                try:
                    cumulative_rx = network_new[net].bytes_recv
                    cumulative_tx = network_new[net].bytes_sent
                    cumulative_cx = cumulative_rx + cumulative_tx
                    rx = cumulative_rx - self.network_old[net].bytes_recv
                    tx = cumulative_tx - self.network_old[net].bytes_sent
                    cx = rx + tx
                    netstat = {
                        'interface_name': n(net),
                        'alias': self.has_alias(n(net)),
                        'time_since_update': time_since_update,
                        'cumulative_rx': cumulative_rx,
                        'rx': rx,
                        'cumulative_tx': cumulative_tx,
                        'tx': tx,
                        'cumulative_cx': cumulative_cx,
                        'cx': cx,
                        # Interface status
                        'is_up': net_status[net].isup,
                        # Interface speed in Mbps, convert it to bps
                        # Can be always 0 on some OSes
                        'speed': net_status[net].speed * 1048576,
                        # Set the key for the dict
                        'key': self.get_key(),
                    }
                except KeyError:
                    continue
                else:
                    # Append the interface stats to the list
                    stats.append(netstat)

            # Save stats to compute next bitrate
            self.network_old = network_new

        elif self.input_method == 'snmp':
            # Update stats using SNMP

            # SNMP bulk command to get all network interface in one shot
            try:
                net_io_counters = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name], bulk=True)
            except KeyError:
                net_io_counters = self.get_stats_snmp(snmp_oid=snmp_oid['default'], bulk=True)

            # Previous network interface stats are stored in the network_old variable
            if not hasattr(self, 'network_old'):
                # First call, we init the network_old var
                try:
                    self.network_old = net_io_counters
                except (IOError, UnboundLocalError):
                    pass
            else:
                # See description in the 'local' block
                time_since_update = getTimeSinceLastUpdate('net')

                # Loop over interfaces
                network_new = net_io_counters

                for net in network_new:
                    # Do not take hidden interface into account
                    if not self.is_display(net):
                        continue

                    try:
                        # Windows: a tips is needed to convert HEX to TXT
                        # http://blogs.technet.com/b/networking/archive/2009/12/18/how-to-query-the-list-of-network-interfaces-using-snmp-via-the-ifdescr-counter.aspx
                        if self.short_system_name == 'windows':
                            try:
                                interface_name = str(base64.b16decode(net[2:-2].upper()))
                            except TypeError:
                                interface_name = net
                        else:
                            interface_name = net

                        cumulative_rx = float(network_new[net]['cumulative_rx'])
                        cumulative_tx = float(network_new[net]['cumulative_tx'])
                        cumulative_cx = cumulative_rx + cumulative_tx
                        rx = cumulative_rx - float(self.network_old[net]['cumulative_rx'])
                        tx = cumulative_tx - float(self.network_old[net]['cumulative_tx'])
                        cx = rx + tx
                        netstat = {
                            'interface_name': interface_name,
                            'alias': self.has_alias(interface_name),
                            'time_since_update': time_since_update,
                            'cumulative_rx': cumulative_rx,
                            'rx': rx,
                            'cumulative_tx': cumulative_tx,
                            'tx': tx,
                            'cumulative_cx': cumulative_cx,
                            'cx': cx,
                        }
                    except KeyError:
                        continue
                    else:
                        netstat['key'] = self.get_key()
                        stats.append(netstat)

                # Save stats to compute next bitrate
                self.network_old = network_new

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Check if the stats should be hidden
        self.update_views_hidden()

        # Add specifics information
        # Alert
        for i in self.get_raw():
            if_real_name = i['interface_name'].split(':')[0]
            # Convert rate in bps (to be able to compare to interface speed)
            bps_rx = int(i['rx'] // i['time_since_update'] * 8)
            bps_tx = int(i['tx'] // i['time_since_update'] * 8)

            # Decorate the bitrate with the configuration file thresholds
            alert_rx = self.get_alert(bps_rx, header=if_real_name + '_rx')
            alert_tx = self.get_alert(bps_tx, header=if_real_name + '_tx')
            # If nothing is define in the configuration file...
            # ... then use the interface speed (not available on all systems)
            if alert_rx == 'DEFAULT' and 'speed' in i and i['speed'] != 0:
                alert_rx = self.get_alert(current=bps_rx, maximum=i['speed'], header='rx')
            if alert_tx == 'DEFAULT' and 'speed' in i and i['speed'] != 0:
                alert_tx = self.get_alert(current=bps_tx, maximum=i['speed'], header='tx')
            # then decorates
            self.views[i[self.get_key()]]['rx']['decoration'] = alert_rx
            self.views[i[self.get_key()]]['tx']['decoration'] = alert_tx

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or self.is_disabled():
            return ret

        # Max size for the interface name
        name_max_width = max_width - 12

        # Header
        msg = '{:{width}}'.format('NETWORK', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        if args.network_cumul:
            # Cumulative stats
            if args.network_sum:
                # Sum stats
                msg = '{:>14}'.format('Rx+Tx')
                ret.append(self.curse_add_line(msg))
            else:
                # Rx/Tx stats
                msg = '{:>7}'.format('Rx')
                ret.append(self.curse_add_line(msg))
                msg = '{:>7}'.format('Tx')
                ret.append(self.curse_add_line(msg))
        else:
            # Bitrate stats
            if args.network_sum:
                # Sum stats
                msg = '{:>14}'.format('Rx+Tx/s')
                ret.append(self.curse_add_line(msg))
            else:
                msg = '{:>7}'.format('Rx/s')
                ret.append(self.curse_add_line(msg))
                msg = '{:>7}'.format('Tx/s')
                ret.append(self.curse_add_line(msg))
        # Interface list (sorted by name)
        for i in self.sorted_stats():
            # Do not display interface in down state (issue #765)
            if ('is_up' in i) and (i['is_up'] is False):
                continue
            # Hide stats if never be different from 0 (issue #1787)
            if all([self.get_views(item=i[self.get_key()], key=f, option='hidden') for f in self.hide_zero_fields]):
                continue
            # Format stats
            # Is there an alias for the interface name ?
            if i['alias'] is None:
                if_name = i['interface_name'].split(':')[0]
            else:
                if_name = i['alias']
            if len(if_name) > name_max_width:
                # Cut interface name if it is too long
                if_name = '_' + if_name[-name_max_width + 1 :]

            if args.byte:
                # Bytes per second (for dummy)
                to_bit = 1
                unit = ''
            else:
                # Bits per second (for real network administrator | Default)
                to_bit = 8
                unit = 'b'

            if args.network_cumul:
                rx = self.auto_unit(int(i['cumulative_rx'] * to_bit)) + unit
                tx = self.auto_unit(int(i['cumulative_tx'] * to_bit)) + unit
                sx = self.auto_unit(int(i['cumulative_rx'] * to_bit) + int(i['cumulative_tx'] * to_bit)) + unit
            else:
                rx = self.auto_unit(int(i['rx'] // i['time_since_update'] * to_bit)) + unit
                tx = self.auto_unit(int(i['tx'] // i['time_since_update'] * to_bit)) + unit
                sx = (
                    self.auto_unit(
                        int(i['rx'] // i['time_since_update'] * to_bit)
                        + int(i['tx'] // i['time_since_update'] * to_bit)
                    )
                    + unit
                )

            # New line
            ret.append(self.curse_new_line())
            msg = '{:{width}}'.format(if_name, width=name_max_width)
            ret.append(self.curse_add_line(msg))
            if args.network_sum:
                msg = '{:>14}'.format(sx)
                ret.append(self.curse_add_line(msg))
            else:
                msg = '{:>7}'.format(rx)
                ret.append(
                    self.curse_add_line(msg, self.get_views(item=i[self.get_key()], key='rx', option='decoration'))
                )
                msg = '{:>7}'.format(tx)
                ret.append(
                    self.curse_add_line(msg, self.get_views(item=i[self.get_key()], key='tx', option='decoration'))
                )

        return ret

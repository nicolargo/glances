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

"""CPU plugin."""

from glances.timer import getTimeSinceLastUpdate
from glances.compat import iterkeys
from glances.cpu_percent import cpu_percent
from glances.globals import LINUX
from glances.plugins.glances_core import Plugin as CorePlugin
from glances.plugins.glances_plugin import GlancesPlugin

import psutil

# SNMP OID
# percentage of user CPU time: .1.3.6.1.4.1.2021.11.9.0
# percentages of system CPU time: .1.3.6.1.4.1.2021.11.10.0
# percentages of idle CPU time: .1.3.6.1.4.1.2021.11.11.0
snmp_oid = {'default': {'user': '1.3.6.1.4.1.2021.11.9.0',
                        'system': '1.3.6.1.4.1.2021.11.10.0',
                        'idle': '1.3.6.1.4.1.2021.11.11.0'},
            'windows': {'percent': '1.3.6.1.2.1.25.3.3.1.2'},
            'esxi': {'percent': '1.3.6.1.2.1.25.3.3.1.2'},
            'netapp': {'system': '1.3.6.1.4.1.789.1.2.1.3.0',
                       'idle': '1.3.6.1.4.1.789.1.2.1.5.0',
                       'nb_log_core': '1.3.6.1.4.1.789.1.2.1.6.0'}}

# Define the history items list
# - 'name' define the stat identifier
# - 'y_unit' define the Y label
items_history_list = [{'name': 'user',
                       'description': 'User CPU usage',
                       'y_unit': '%'},
                      {'name': 'system',
                       'description': 'System CPU usage',
                       'y_unit': '%'}]


class Plugin(GlancesPlugin):
    """Glances CPU plugin.

    'stats' is a dictionary that contains the system-wide CPU utilization as a
    percentage.
    """

    def __init__(self, args=None, config=None):
        """Init the CPU plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Call CorePlugin in order to display the core number
        try:
            self.nb_log_core = CorePlugin(args=self.args).update()["log"]
        except Exception:
            self.nb_log_core = 1

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update CPU stats using the input method."""

        # Grab stats into self.stats
        if self.input_method == 'local':
            stats = self.update_local()
        elif self.input_method == 'snmp':
            stats = self.update_snmp()
        else:
            stats = self.get_init_value()

        # Update the stats
        self.stats = stats

        return self.stats

    def update_local(self):
        """Update CPU stats using psutil."""
        # Grab CPU stats using psutil's cpu_percent and cpu_times_percent
        # Get all possible values for CPU stats: user, system, idle,
        # nice (UNIX), iowait (Linux), irq (Linux, FreeBSD), steal (Linux 2.6.11+)
        # The following stats are returned by the API but not displayed in the UI:
        # softirq (Linux), guest (Linux 2.6.24+), guest_nice (Linux 3.2.0+)

        # Init new stats
        stats = self.get_init_value()

        stats['total'] = cpu_percent.get()
        cpu_times_percent = psutil.cpu_times_percent(interval=0.0)
        for stat in ['user', 'system', 'idle', 'nice', 'iowait',
                     'irq', 'softirq', 'steal', 'guest', 'guest_nice']:
            if hasattr(cpu_times_percent, stat):
                stats[stat] = getattr(cpu_times_percent, stat)

        # Additional CPU stats (number of events not as a %; psutil>=4.1.0)
        # ctx_switches: number of context switches (voluntary + involuntary) per second
        # interrupts: number of interrupts per second
        # soft_interrupts: number of software interrupts per second. Always set to 0 on Windows and SunOS.
        # syscalls: number of system calls since boot. Always set to 0 on Linux.
        cpu_stats = psutil.cpu_stats()
        # By storing time data we enable Rx/s and Tx/s calculations in the
        # XML/RPC API, which would otherwise be overly difficult work
        # for users of the API
        time_since_update = getTimeSinceLastUpdate('cpu')

        # Previous CPU stats are stored in the cpu_stats_old variable
        if not hasattr(self, 'cpu_stats_old'):
            # First call, we init the cpu_stats_old var
            self.cpu_stats_old = cpu_stats
        else:
            for stat in cpu_stats._fields:
                if getattr(cpu_stats, stat) is not None:
                    stats[stat] = getattr(cpu_stats, stat) - getattr(self.cpu_stats_old, stat)

            stats['time_since_update'] = time_since_update

            # Core number is needed to compute the CTX switch limit
            stats['cpucore'] = self.nb_log_core

            # Save stats to compute next step
            self.cpu_stats_old = cpu_stats

        return stats

    def update_snmp(self):
        """Update CPU stats using SNMP."""

        # Init new stats
        stats = self.get_init_value()

        # Update stats using SNMP
        if self.short_system_name in ('windows', 'esxi'):
            # Windows or VMWare ESXi
            # You can find the CPU utilization of windows system by querying the oid
            # Give also the number of core (number of element in the table)
            try:
                cpu_stats = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name],
                                                bulk=True)
            except KeyError:
                self.reset()

            # Iter through CPU and compute the idle CPU stats
            stats['nb_log_core'] = 0
            stats['idle'] = 0
            for c in cpu_stats:
                if c.startswith('percent'):
                    stats['idle'] += float(cpu_stats['percent.3'])
                    stats['nb_log_core'] += 1
            if stats['nb_log_core'] > 0:
                stats['idle'] = stats['idle'] / stats['nb_log_core']
            stats['idle'] = 100 - stats['idle']
            stats['total'] = 100 - stats['idle']

        else:
            # Default behavor
            try:
                stats = self.get_stats_snmp(
                    snmp_oid=snmp_oid[self.short_system_name])
            except KeyError:
                stats = self.get_stats_snmp(
                    snmp_oid=snmp_oid['default'])

            if stats['idle'] == '':
                self.reset()
                return self.stats

            # Convert SNMP stats to float
            for key in iterkeys(stats):
                stats[key] = float(stats[key])
            stats['total'] = 100 - stats['idle']

        return stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert and log
        for key in ['user', 'system', 'iowait']:
            if key in self.stats:
                self.views[key]['decoration'] = self.get_alert_log(self.stats[key], header=key)
        # Alert only
        for key in ['steal', 'total']:
            if key in self.stats:
                self.views[key]['decoration'] = self.get_alert(self.stats[key], header=key)
        # Alert only but depend on Core number
        for key in ['ctx_switches']:
            if key in self.stats:
                self.views[key]['decoration'] = self.get_alert(self.stats[key], maximum=100 * self.stats['cpucore'], header=key)
        # Optional
        for key in ['nice', 'irq', 'iowait', 'steal', 'ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls']:
            if key in self.stats:
                self.views[key]['optional'] = True

    def msg_curse(self, args=None, max_width=None):
        """Return the list to display in the UI."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disable
        if not self.stats or self.args.percpu or self.is_disable():
            return ret

        # Build the string message
        # If user stat is not here, display only idle / total CPU usage (for
        # exemple on Windows OS)
        idle_tag = 'user' not in self.stats

        # Header
        msg = '{}'.format('CPU')
        ret.append(self.curse_add_line(msg, "TITLE"))
        trend_user = self.get_trend('user')
        trend_system = self.get_trend('system')
        if trend_user is None or trend_user is None:
            trend_cpu = None
        else:
            trend_cpu = trend_user + trend_system
        msg = ' {:4}'.format(self.trend_msg(trend_cpu))
        ret.append(self.curse_add_line(msg))
        # Total CPU usage
        msg = '{:5.1f}%'.format(self.stats['total'])
        if idle_tag:
            ret.append(self.curse_add_line(
                msg, self.get_views(key='total', option='decoration')))
        else:
            ret.append(self.curse_add_line(msg))
        # Nice CPU
        if 'nice' in self.stats:
            msg = '  {:8}'.format('nice:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='nice', option='optional')))
            msg = '{:5.1f}%'.format(self.stats['nice'])
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='nice', option='optional')))
        # ctx_switches
        if 'ctx_switches' in self.stats:
            msg = '  {:8}'.format('ctx_sw:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='ctx_switches', option='optional')))
            msg = '{:>5}'.format(self.auto_unit(int(self.stats['ctx_switches'] // self.stats['time_since_update']),
                                                min_symbol='K'))
            ret.append(self.curse_add_line(
                msg, self.get_views(key='ctx_switches', option='decoration'),
                optional=self.get_views(key='ctx_switches', option='optional')))

        # New line
        ret.append(self.curse_new_line())
        # User CPU
        if 'user' in self.stats:
            msg = '{:8}'.format('user:')
            ret.append(self.curse_add_line(msg))
            msg = '{:5.1f}%'.format(self.stats['user'])
            ret.append(self.curse_add_line(
                msg, self.get_views(key='user', option='decoration')))
        elif 'idle' in self.stats:
            msg = '{:8}'.format('idle:')
            ret.append(self.curse_add_line(msg))
            msg = '{:5.1f}%'.format(self.stats['idle'])
            ret.append(self.curse_add_line(msg))
        # IRQ CPU
        if 'irq' in self.stats:
            msg = '  {:8}'.format('irq:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='irq', option='optional')))
            msg = '{:5.1f}%'.format(self.stats['irq'])
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='irq', option='optional')))
        # interrupts
        if 'interrupts' in self.stats:
            msg = '  {:8}'.format('inter:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='interrupts', option='optional')))
            msg = '{:>5}'.format(int(self.stats['interrupts'] // self.stats['time_since_update']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='interrupts', option='optional')))

        # New line
        ret.append(self.curse_new_line())
        # System CPU
        if 'system' in self.stats and not idle_tag:
            msg = '{:8}'.format('system:')
            ret.append(self.curse_add_line(msg))
            msg = '{:5.1f}%'.format(self.stats['system'])
            ret.append(self.curse_add_line(
                msg, self.get_views(key='system', option='decoration')))
        else:
            msg = '{:8}'.format('core:')
            ret.append(self.curse_add_line(msg))
            msg = '{:>6}'.format(self.stats['nb_log_core'])
            ret.append(self.curse_add_line(msg))
        # IOWait CPU
        if 'iowait' in self.stats:
            msg = '  {:8}'.format('iowait:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='iowait', option='optional')))
            msg = '{:5.1f}%'.format(self.stats['iowait'])
            ret.append(self.curse_add_line(
                msg, self.get_views(key='iowait', option='decoration'),
                optional=self.get_views(key='iowait', option='optional')))
        # soft_interrupts
        if 'soft_interrupts' in self.stats:
            msg = '  {:8}'.format('sw_int:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='soft_interrupts', option='optional')))
            msg = '{:>5}'.format(int(self.stats['soft_interrupts'] // self.stats['time_since_update']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='soft_interrupts', option='optional')))

        # New line
        ret.append(self.curse_new_line())
        # Idle CPU
        if 'idle' in self.stats and not idle_tag:
            msg = '{:8}'.format('idle:')
            ret.append(self.curse_add_line(msg))
            msg = '{:5.1f}%'.format(self.stats['idle'])
            ret.append(self.curse_add_line(msg))
        # Steal CPU usage
        if 'steal' in self.stats:
            msg = '  {:8}'.format('steal:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='steal', option='optional')))
            msg = '{:5.1f}%'.format(self.stats['steal'])
            ret.append(self.curse_add_line(
                msg, self.get_views(key='steal', option='decoration'),
                optional=self.get_views(key='steal', option='optional')))
        # syscalls
        # syscalls: number of system calls since boot. Always set to 0 on Linux. (do not display)
        if 'syscalls' in self.stats and not LINUX:
            msg = '  {:8}'.format('syscal:')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='syscalls', option='optional')))
            msg = '{:>5}'.format(int(self.stats['syscalls'] // self.stats['time_since_update']))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='syscalls', option='optional')))

        # Return the message with decoration
        return ret

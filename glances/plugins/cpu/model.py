# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CPU plugin."""

from glances.globals import LINUX, WINDOWS, SUNOS, iterkeys
from glances.cpu_percent import cpu_percent
from glances.plugins.core.model import PluginModel as CorePluginModel
from glances.plugins.plugin.model import GlancesPluginModel
from glances.data.item import GlancesDataItem
from glances.data.plugin import GlancesDataPlugin

import psutil

# =============================================================================
# Fields description
# =============================================================================
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True, the value is a rate (per second, compute automaticaly)
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
# =============================================================================

fields_description = {
    'total': {
        'description': 'Sum of all CPU percentages (except idle).',
        'unit': 'percent'
    },
    'system': {
        'description': 'percent time spent in kernel space. System CPU time is the \
time spent running code in the Operating System kernel.',
        'unit': 'percent',
    },
    'user': {
        'description': 'CPU percent time spent in user space. \
User CPU time is the time spent on the processor running your program\'s code (or code in libraries).',
        'unit': 'percent',
    },
    'iowait': {
        'description': '*(Linux)*: percent time spent by the CPU waiting for I/O \
operations to complete.',
        'unit': 'percent',
    },
    'dpc': {
        'description': '*(Windows)*: time spent servicing deferred procedure calls (DPCs)',
        'unit': 'percent',
    },
    'idle': {
        'description': 'percent of CPU used by any program. Every program or task \
that runs on a computer system occupies a certain amount of processing \
time on the CPU. If the CPU has completed all tasks it is idle.',
        'unit': 'percent',
    },
    'irq': {
        'description': '*(Linux and BSD)*: percent time spent servicing/handling \
hardware/software interrupts. Time servicing interrupts (hardware + \
software).',
        'unit': 'percent',
    },
    'nice': {
        'description': '*(Unix)*: percent time occupied by user level processes with \
a positive nice value. The time the CPU has spent running users\' \
processes that have been *niced*.',
        'unit': 'percent',
    },
    'steal': {
        'description': '*(Linux)*: percentage of time a virtual CPU waits for a real \
CPU while the hypervisor is servicing another virtual processor.',
        'unit': 'percent',
    },
    'ctx_switches': {
        'description': 'number of context switches (voluntary + involuntary) per \
second. A context switch is a procedure that a computer\'s CPU (central \
processing unit) follows to change from one task (or process) to \
another while ensuring that the tasks do not conflict.',
        'unit': 'number',
        'rate': True,
        'min_symbol': 'K',
        'short_name': 'ctx_sw',
    },
    'interrupts': {
        'description': 'number of interrupts per second.',
        'unit': 'number',
        'rate': True,
        'min_symbol': 'K',
        'short_name': 'inter',
    },
    'soft_interrupts': {
        'description': 'number of software interrupts per second. Always set to \
0 on Windows and SunOS.',
        'unit': 'number',
        'rate': True,
        'min_symbol': 'K',
        'short_name': 'sw_int',
    },
    'syscalls': {
        'description': 'number of system calls per second. Always 0 on Linux OS.',
        'unit': 'number',
        'rate': True,
        'min_symbol': 'K',
        'short_name': 'sys_call',
    },
    'cpucore': {
        'description': 'Total number of CPU core.',
        'unit': 'number'
    },
}

# =============================================================================
# Define the history items list
# =============================================================================
# - 'name' define the stat identifier
# - 'y_unit' define the Y label
# =============================================================================

items_history_list = [
    {'name': 'user', 'description': 'User CPU usage', 'y_unit': '%'},
    {'name': 'system', 'description': 'System CPU usage', 'y_unit': '%'},
]

# =============================================================================
# SNMP OID
# =============================================================================
# percentage of user CPU time: .1.3.6.1.4.1.2021.11.9.0
# percentages of system CPU time: .1.3.6.1.4.1.2021.11.10.0
# percentages of idle CPU time: .1.3.6.1.4.1.2021.11.11.0
# =============================================================================

snmp_oid = {
    'default': {
        'user': '1.3.6.1.4.1.2021.11.9.0',
        'system': '1.3.6.1.4.1.2021.11.10.0',
        'idle': '1.3.6.1.4.1.2021.11.11.0',
    },
    'windows': {'percent': '1.3.6.1.2.1.25.3.3.1.2'},
    'esxi': {'percent': '1.3.6.1.2.1.25.3.3.1.2'},
    'netapp': {
        'system': '1.3.6.1.4.1.789.1.2.1.3.0',
        'idle': '1.3.6.1.4.1.789.1.2.1.5.0',
        'cpucore': '1.3.6.1.4.1.789.1.2.1.6.0',
    },
}


class PluginModel(GlancesPluginModel):
    """Glances CPU plugin.

    'stats' is a dictionary that contains the system-wide CPU utilization as a
    percentage.
    """

    def __init__(self, args=None, config=None):
        """Init the CPU plugin."""
        super(PluginModel, self).__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            fields_description=fields_description
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Call CorePluginModel in order to display the core number
        try:
            self.nb_log_core = CorePluginModel(args=self.args).update()["log"]
        except Exception:
            self.nb_log_core = 1

        # Init the data
        # TODO: to be done in the top level plugin class
        self.stats = GlancesDataPlugin(name=self.plugin_name,
                                       description='Glances {} plugin'.format(self.plugin_name.upper()))
        for key, value in fields_description.items():
            self.stats.add_item(GlancesDataItem(**value, name=key))

    # TODO: To be done in the top level plugin class
    def get_raw(self):
        return self.stats.export()

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update CPU stats using the input method."""
        if self.input_method == 'local':
            self.update_local()
        elif self.input_method == 'snmp':
            self.update_snmp()

    def update_local(self):
        """Update CPU stats using psutil."""
        # Grab total CPU stats using psutil's cpu_percent
        self.stats.update_item('total', cpu_percent.get())

        # Standards stats
        # - user: time spent by normal processes executing in user mode; on Linux this also includes guest time
        # - system: time spent by processes executing in kernel mode
        # - idle: time spent doing nothing
        # - nice (UNIX): time spent by niced (prioritized) processes executing in user mode
        #                on Linux this also includes guest_nice time
        # - iowait (Linux): time spent waiting for I/O to complete.
        #                   This is not accounted in idle time counter.
        # - irq (Linux, BSD): time spent for servicing hardware interrupts
        # - softirq (Linux): time spent for servicing software interrupts
        # - steal (Linux 2.6.11+): time spent by other operating systems running in a virtualized environment
        # - guest (Linux 2.6.24+): time spent running a virtual CPU for guest operating systems under
        #                          the control of the Linux kernel
        # - guest_nice (Linux 3.2.0+): time spent running a niced guest (virtual CPU for guest operating systems
        #                              under the control of the Linux kernel)
        # - interrupt (Windows): time spent for servicing hardware interrupts ( similar to “irq” on UNIX)
        # - dpc (Windows): time spent servicing deferred procedure calls (DPCs)
        cpu_times_percent = psutil.cpu_times_percent(interval=0.0)
        for stat in cpu_times_percent._fields:
            if stat in fields_description:
                self.stats.update_item(stat, getattr(cpu_times_percent, stat))

        # Additional CPU stats (number of events not as a %; psutil>=4.1.0)
        # - ctx_switches: number of context switches (voluntary + involuntary) since boot.
        # - interrupts: number of interrupts since boot.
        # - soft_interrupts: number of software interrupts since boot. Always set to 0 on Windows and SunOS.
        # - syscalls: number of system calls since boot. Always set to 0 on Linux.
        cpu_stats = psutil.cpu_stats()
        for stat in cpu_stats._fields:
            if stat in fields_description:
                self.stats.update_item(stat, getattr(cpu_stats, stat))

        # Core number is needed to compute the CTX switch limit
        self.stats.update_item('cpucore', self.nb_log_core)

    # TODO: to be refactored
    def update_snmp(self):
        """Update CPU stats using SNMP."""

        # Update stats using SNMP
        if self.short_system_name in ('windows', 'esxi'):
            # Windows or VMWare ESXi
            # You can find the CPU utilization of windows system by querying the oid
            # Give also the number of core (number of element in the table)
            try:
                cpu_stats = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name], bulk=True)
            except KeyError:
                return

            # Iter through CPU and compute the idle CPU stats
            self.stats.update_item('nb_log_core', 0)
            self.stats.update_item('idle', 0)
            for c in cpu_stats:
                if c.startswith('percent'):
                    self.stats.update_item('nb_log_core', self.stats.get_item('nb_log_core') + 1)
                    self.stats.update_item('idle', self.stats.get_item('idle') + float(cpu_stats['percent.3']))
            if self.stats.get_item('nb_log_core') > 0:
                self.stats.update_item('idle', self.stats.get_item('idle') / self.stats.get_item('nb_log_core'))
            self.stats.update_item('total', 100 - self.get_item('idle'))
        else:
            # Default behavior
            try:
                stats = self.get_stats_snmp(snmp_oid=snmp_oid[self.short_system_name])
            except KeyError:
                stats = self.get_stats_snmp(snmp_oid=snmp_oid['default'])

            if stats['idle'] == '':
                return

            # Convert SNMP stats to float
            for stat in iterkeys(stats):
                if stat in fields_description:
                    self.stats.update_item(stat, float(stats[stat]))

            self.stats.update_item('total', 100 - self.get_item('idle'))

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Add specifics information
        # Alert and log
        for key in ['user', 'system', 'iowait', 'dpc', 'total']:
            if key in self.stats.items:
                self.views[key]['decoration'] = self.get_alert_log(self.stats.get_item(key), header=key)
        # Alert only
        for key in ['steal']:
            if key in self.stats.items:
                self.views[key]['decoration'] = self.get_alert(self.stats.get_item(key), header=key)
        # Alert only but depend on Core number
        for key in ['ctx_switches']:
            if key in self.stats.items and self.stats.get_item(key) is not None:
                self.views[key]['decoration'] = self.get_alert(
                    self.stats.get_item(key), maximum=100 * self.stats.get_item('cpucore'), header=key)
        # Optional
        for key in ['nice', 'irq', 'idle', 'steal', 'ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls']:
            if key in self.stats.items:
                self.views[key]['optional'] = True

    def msg_curse(self, args=None, max_width=None):
        """Return the list to display in the UI."""
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disable
        if not self.stats.items or self.args.percpu or self.is_disabled():
            return ret

        # Some tag to enable/disable stats (example: idle_tag triggered on Windows OS)
        idle_tag = 'user' not in self.stats.items

        # First line
        # Total + (idle) + ctx_sw
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
        msg = '{:5.1f}%'.format(self.stats.get_item('total'))
        ret.append(self.curse_add_line(msg, self.get_views(key='total', option='decoration')))
        # Idle CPU
        if 'idle' in self.stats.items and not idle_tag:
            msg = '  {:8}'.format('idle')
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='idle', option='optional')))
            msg = '{:4.1f}%'.format(self.stats.get_item('idle'))
            ret.append(self.curse_add_line(msg, optional=self.get_views(key='idle', option='optional')))
        # ctx_switches
        # On WINDOWS/SUNOS the ctx_switches is displayed in the third line
        if not WINDOWS and not SUNOS:
            ret.extend(self.curse_add_stat('ctx_switches', width=15, header='  '))

        # Second line
        # user|idle + irq + interrupts
        ret.append(self.curse_new_line())
        # User CPU
        if not idle_tag:
            ret.extend(self.curse_add_stat('user', width=15))
        elif 'idle' in self.stats.items:
            ret.extend(self.curse_add_stat('idle', width=15))
        # IRQ CPU
        ret.extend(self.curse_add_stat('irq', width=14, header='  '))
        # interrupts
        ret.extend(self.curse_add_stat('interrupts', width=15, header='  '))

        # Third line
        # system|core + nice + sw_int
        ret.append(self.curse_new_line())
        # System CPU
        if not idle_tag:
            ret.extend(self.curse_add_stat('system', width=15))
        else:
            ret.extend(self.curse_add_stat('core', width=15))
        # Nice CPU
        ret.extend(self.curse_add_stat('nice', width=14, header='  '))
        # soft_interrupts
        if not WINDOWS and not SUNOS:
            ret.extend(self.curse_add_stat('soft_interrupts', width=15, header='  '))
        else:
            ret.extend(self.curse_add_stat('ctx_switches', width=15, header='  '))

        # Fourth line
        # iowait + steal + syscalls
        ret.append(self.curse_new_line())
        if 'iowait' in self.stats.items:
            # IOWait CPU
            ret.extend(self.curse_add_stat('iowait', width=15))
        elif 'dpc' in self.stats.items:
            # DPC CPU
            ret.extend(self.curse_add_stat('dpc', width=15))
        # Steal CPU usage
        ret.extend(self.curse_add_stat('steal', width=14, header='  '))
        # syscalls: number of system calls since boot. Always set to 0 on Linux. (do not display)
        if not LINUX:
            ret.extend(self.curse_add_stat('syscalls', width=15, header='  '))

        # Return the message with decoration
        return ret

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Per-CPU plugin."""

from glances.cpu_percent import cpu_percent
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'cpu_number': {
        'description': 'CPU number',
    },
    'total': {
        'description': 'Sum of CPU percentages (except idle) for current CPU number.',
        'unit': 'percent',
    },
    'system': {
        'description': 'Percent time spent in kernel space. System CPU time is the \
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
    'guest': {
        'description': '*(Linux)*: percent of time spent running a virtual CPU for \
guest operating systems under the control of the Linux kernel.',
        'unit': 'percent',
    },
    'guest_nice': {
        'description': '*(Linux)*: percent of time spent running a niced guest (virtual CPU).',
        'unit': 'percent',
    },
    'softirq': {
        'description': '*(Linux)*: percent of time spent handling software interrupts.',
        'unit': 'percent',
    },
}


# Define the history items list
items_history_list = [
    {'name': 'user', 'description': 'User CPU usage', 'y_unit': '%'},
    {'name': 'system', 'description': 'System CPU usage', 'y_unit': '%'},
]


class PluginModel(GlancesPluginModel):
    """Glances per-CPU plugin.

    'stats' is a list of dictionaries that contain the utilization percentages
    for each CPU.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(
            args=args, config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

    def get_key(self):
        """Return the key of the list."""
        return 'cpu_number'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update per-CPU stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        # Grab per-CPU stats using psutil's cpu_percent(percpu=True) and
        # cpu_times_percent(percpu=True) methods
        if self.input_method == 'local':
            stats = cpu_percent.get(percpu=True)
        else:
            # Update stats using SNMP
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or not self.args.percpu or self.is_disabled():
            return ret

        # Build the string message
        if self.is_disabled('quicklook'):
            msg = '{:7}'.format('PER CPU')
            ret.append(self.curse_add_line(msg, "TITLE"))

        # Per CPU stats displayed per line
        for stat in ['user', 'system', 'idle', 'iowait', 'steal']:
            if stat not in self.stats[0]:
                continue
            msg = '{:>7}'.format(stat)
            ret.append(self.curse_add_line(msg))

        # Per CPU stats displayed per column
        for cpu in self.stats:
            ret.append(self.curse_new_line())
            if self.is_disabled('quicklook'):
                try:
                    msg = '{:6.1f}%'.format(cpu['total'])
                except TypeError:
                    # TypeError: string indices must be integers (issue #1027)
                    msg = '{:>6}%'.format('?')
                ret.append(self.curse_add_line(msg))
            for stat in ['user', 'system', 'idle', 'iowait', 'steal']:
                if stat not in self.stats[0]:
                    continue
                try:
                    msg = '{:6.1f}%'.format(cpu[stat])
                except TypeError:
                    msg = '{:>6}%'.format('?')
                ret.append(self.curse_add_line(msg, self.get_alert(cpu[stat], header=stat)))

        return ret

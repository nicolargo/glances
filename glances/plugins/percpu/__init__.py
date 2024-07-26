#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Per-CPU plugin."""

from glances.cpu_percent import cpu_percent
from glances.globals import BSD, LINUX, MACOS, WINDOWS
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
    'dpc': {
        'description': '*(Windows)*: percent of time spent handling deferred procedure calls.',
        'unit': 'percent',
    },
    'interrupt': {
        'description': '*(Windows)*: percent of time spent handling software interrupts.',
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
        super().__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description,
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Manage the maximum number of CPU to display (related to enhancement request #2734)
        if config:
            self.max_cpu_display = config.get_int_value('percpu', 'max_cpu_display', 4)
        else:
            self.max_cpu_display = 4

    def get_key(self):
        """Return the key of the list."""
        return 'cpu_number'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update per-CPU stats using the input method."""
        # Grab per-CPU stats using psutil's
        if self.input_method == 'local':
            stats = cpu_percent.get_percpu()
        else:
            # Update stats using SNMP
            stats = self.get_init_value()

        # Update the stats
        self.stats = stats

        return self.stats

    def define_headers_from_os(self):
        base = ['user', 'system']

        if LINUX:
            extension = ['iowait', 'idle', 'irq', 'nice', 'steal', 'guest']
        elif MACOS:
            extension = ['idle', 'nice']
        elif BSD:
            extension = ['idle', 'irq', 'nice']
        elif WINDOWS:
            extension = ['dpc', 'interrupt']

        return base + extension

    def maybe_build_string_msg(self, header, return_):
        if self.is_disabled('quicklook'):
            msg = '{:5}'.format('CPU')
            return_.append(self.curse_add_line(msg, "TITLE"))
            header.insert(0, 'total')

        return (header, return_)

    def display_cpu_stats_per_line(self, header, return_):
        for stat in header:
            msg = f'{stat:>7}'
            return_.append(self.curse_add_line(msg))

        return return_

    def manage_max_cpu_to_display(self):
        if len(self.stats) > self.max_cpu_display:
            # sort and display top 'n'
            percpu_list = sorted(self.stats, key=lambda x: x['total'], reverse=True)
        else:
            percpu_list = self.stats

        return percpu_list

    def display_cpu_header_in_columns(self, cpu, return_):
        return_.append(self.curse_new_line())
        if self.is_disabled('quicklook'):
            try:
                cpu_id = cpu[cpu['key']]
                if cpu_id < 10:
                    msg = f'CPU{cpu_id:1} '
                else:
                    msg = f'{cpu_id:4} '
            except TypeError:
                # TypeError: string indices must be integers (issue #1027)
                msg = '{:4} '.format('?')
            return_.append(self.curse_add_line(msg))

        return return_

    def display_cpu_stats_in_columns(self, cpu, header, return_):
        for stat in header:
            try:
                msg = f'{cpu[stat]:6.1f}%'
            except TypeError:
                msg = '{:>6}%'.format('?')
            return_.append(self.curse_add_line(msg, self.get_alert(cpu[stat], header=stat)))

        return return_

    def summarize_all_cpus_not_displayed(self, percpu_list, header, return_):
        if len(self.stats) > self.max_cpu_display:
            return_.append(self.curse_new_line())
            if self.is_disabled('quicklook'):
                return_.append(self.curse_add_line('CPU* '))

            for stat in header:
                percpu_stats = [i[stat] for i in percpu_list[0 : self.max_cpu_display]]
                cpu_stat = sum(percpu_stats) / len(percpu_stats)
                try:
                    msg = f'{cpu_stat:6.1f}%'
                except TypeError:
                    msg = '{:>6}%'.format('?')
                return_.append(self.curse_add_line(msg, self.get_alert(cpu_stat, header=stat)))

        return return_

    def msg_curse(self, args=None, max_width=None):
        """Return the list of dict to display in the curse interface."""

        # Init the return message
        return_ = []

        # Only process if stats exist...
        missing = [not self.stats, not self.args.percpu, self.is_disabled()]
        if any(missing):
            return return_

        # Define the headers based on OS
        header = self.define_headers_from_os()

        # Build the string message
        header, return_ = self.maybe_build_string_msg(header, return_)

        # Per CPU stats displayed per line
        return_ = self.display_cpu_stats_per_line(header, return_)

        # Manage the maximum number of CPU to display (related to enhancement request #2734)
        percpu_list = self.manage_max_cpu_to_display()

        # Per CPU stats displayed per column
        for cpu in percpu_list[0 : self.max_cpu_display]:
            header_added = self.display_cpu_header_in_columns(cpu, return_)
            stats_added = self.display_cpu_stats_in_columns(cpu, header, header_added)

        # Add a new line with sum of all others CPU
        return self.summarize_all_cpus_not_displayed(percpu_list, header, stats_added)

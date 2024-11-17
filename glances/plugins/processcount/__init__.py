#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Process count plugin."""

from glances.plugins.plugin.model import GlancesPluginModel
from glances.processes import glances_processes, sort_for_human

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True then compute and add *_gauge and *_rate_per_is fields
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'total': {
        'description': 'Total number of processes',
        'unit': 'number',
    },
    'running': {
        'description': 'Total number of running processes',
        'unit': 'number',
    },
    'sleeping': {
        'description': 'Total number of sleeping processes',
        'unit': 'number',
    },
    'thread': {
        'description': 'Total number of threads',
        'unit': 'number',
    },
    'pid_max': {
        'description': 'Maximum number of processes',
        'unit': 'number',
    },
}

# Define the history items list
items_history_list = [
    {'name': 'total', 'description': 'Total number of processes', 'y_unit': ''},
    {'name': 'running', 'description': 'Total number of running processes', 'y_unit': ''},
    {'name': 'sleeping', 'description': 'Total number of sleeping processes', 'y_unit': ''},
    {'name': 'thread', 'description': 'Total number of threads', 'y_unit': ''},
]


class PluginModel(GlancesPluginModel):
    """Glances process count plugin.

    stats is a list
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args, config=config, items_history_list=items_history_list, fields_description=fields_description
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Note: 'glances_processes' is already init in the glances_processes.py script

    def enable_extended(self):
        """Enable extended stats."""
        glances_processes.enable_extended()

    def disable_extended(self):
        """Disable extended stats."""
        glances_processes.disable_extended()

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update processes stats using the input method."""
        # Update the stats
        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Here, update is call for processcount, processlist and programlist
            glances_processes.update()

            # For the ProcessCount, only return the processes count
            stats = glances_processes.get_count()
        else:
            stats = self.get_init_value()

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if args.disable_process:
            msg = "PROCESSES DISABLED (press 'z' to display)"
            ret.append(self.curse_add_line(msg))
            return ret

        if not self.stats:
            return ret

        # Display the filter (if it exists)
        if glances_processes.process_filter is not None:
            msg = 'Processes filter:'
            ret.append(self.curse_add_line(msg, "TITLE"))
            msg = f' {glances_processes.process_filter} '
            if glances_processes.process_filter_key is not None:
                msg += f'on column {glances_processes.process_filter_key} '
            ret.append(self.curse_add_line(msg, "FILTER"))
            msg = '(\'ENTER\' to edit, \'E\' to reset)'
            ret.append(self.curse_add_line(msg))
            ret.append(self.curse_new_line())

        # Build the string message
        # Header
        msg = 'TASKS'
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Compute processes
        other = self.stats['total']
        msg = '{:>4}'.format(self.stats['total'])
        ret.append(self.curse_add_line(msg))

        if 'thread' in self.stats:
            msg = ' ({} thr),'.format(self.stats['thread'])
            ret.append(self.curse_add_line(msg))

        if 'running' in self.stats:
            other -= self.stats['running']
            msg = ' {} run,'.format(self.stats['running'])
            ret.append(self.curse_add_line(msg))

        if 'sleeping' in self.stats:
            other -= self.stats['sleeping']
            msg = ' {} slp,'.format(self.stats['sleeping'])
            ret.append(self.curse_add_line(msg))

        msg = f' {other} oth '
        ret.append(self.curse_add_line(msg))

        # Display sort information
        msg = 'Programs' if self.args.programs else 'Threads'
        try:
            sort_human = sort_for_human[glances_processes.sort_key]
        except KeyError:
            sort_human = glances_processes.sort_key
        if glances_processes.auto_sort:
            msg += ' sorted automatically'
            ret.append(self.curse_add_line(msg))
            msg = f' by {sort_human}'
        else:
            msg += f' sorted by {sort_human}'
        ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        return ret

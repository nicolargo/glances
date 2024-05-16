#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Monitor plugin."""

from glances.amps_list import AmpsList as glancesAmpsList
from glances.globals import iteritems
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'name': {'description': 'AMP name.'},
    'result': {'description': 'AMP result (a string).'},
    'refresh': {'description': 'AMP refresh interval.', 'unit': 'second'},
    'timer': {'description': 'Time until next refresh.', 'unit': 'second'},
    'count': {'description': 'Number of matching processes.', 'unit': 'number'},
    'countmin': {'description': 'Minimum number of matching processes.', 'unit': 'number'},
    'countmax': {'description': 'Maximum number of matching processes.', 'unit': 'number'},
}


class PluginModel(GlancesPluginModel):
    """Glances AMPs plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, stats_init_value=[], fields_description=fields_description)
        self.args = args
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the list of AMP (classes define in the glances/amps_list.py script)
        self.glances_amps = glancesAmpsList(self.args, self.config)

    def get_key(self):
        """Return the key of the list."""
        return 'name'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the AMP list."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            for k, v in iteritems(self.glances_amps.update()):
                stats.append(
                    {
                        'key': self.get_key(),
                        'name': v.NAME,
                        'result': v.result(),
                        'refresh': v.refresh(),
                        'timer': v.time_until_refresh(),
                        'count': v.count(),
                        'countmin': v.count_min(),
                        'countmax': v.count_max(),
                        'regex': v.regex() is not None,
                    },
                )
        else:
            # Not available in SNMP mode
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def get_alert(self, nbprocess=0, countmin=None, countmax=None, header="", log=False):
        """Return the alert status relative to the process number."""
        if nbprocess is None:
            return 'OK'
        if countmin is None:
            countmin = nbprocess
        if countmax is None:
            countmax = nbprocess
        if nbprocess > 0:
            if int(countmin) <= int(nbprocess) <= int(countmax):
                return 'OK'
            return 'WARNING'

        if int(countmin) == 0:
            return 'OK'
        return 'CRITICAL'

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        # Only process if stats exist and display plugin enable...
        ret = []

        if not self.stats or args.disable_process or self.is_disabled():
            return ret

        # Build the string message
        for m in self.stats:
            # Only display AMP if a result exist
            if m['result'] is None:
                continue
            # Display AMP
            first_column = '{}'.format(m['name'])
            first_column_style = self.get_alert(m['count'], m['countmin'], m['countmax'])
            second_column = '{}'.format(m['count'] if m['regex'] else '')
            for line in m['result'].split('\n'):
                # Display first column with the process name...
                msg = f'{first_column:<16} '
                ret.append(self.curse_add_line(msg, first_column_style))
                # ... and second column with the number of matching processes...
                msg = f'{second_column:<4} '
                ret.append(self.curse_add_line(msg))
                # ... only on the first line
                first_column = second_column = ''
                # Display AMP result in the third column
                ret.append(self.curse_add_line(line, splittable=True))
                ret.append(self.curse_new_line())

        # Delete the last empty line
        try:
            ret.pop()
        except IndexError:
            pass

        return ret

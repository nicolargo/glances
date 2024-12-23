#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
Help plugin.

Just a stupid plugin to display the help screen.
"""

from itertools import chain

from glances import __version__, psutil_version
from glances.globals import iteritems
from glances.plugins.plugin.model import GlancesPluginModel


class PluginModel(GlancesPluginModel):
    """Glances help plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

        # Set the config instance
        self.config = config
        self.args = args

        # We want to display the stat in the curse interface
        self.display_curse = True

        # init data dictionary, to preserve insertion order
        self.view_data = {}
        self.generate_view_data()

    def reset(self):
        """No stats. It is just a plugin to display the help."""

    def update(self):
        """No stats. It is just a plugin to display the help."""

    def generate_view_data(self):
        """Generate the views."""
        self.view_data['version'] = '{} {}'.format('Glances', __version__)
        self.view_data['psutil_version'] = f' with psutil {psutil_version}'

        try:
            self.view_data['configuration_file'] = f'Configuration file: {self.config.loaded_config_file}'
        except AttributeError:
            pass

        msg_col = '  {0:1}  {1:34}'
        msg_header = '{0:39}'

        self.view_data.update(
            [
                # First column
                #
                ('header_sort', msg_header.format('SORT PROCESSES:')),
                ('sort_auto', msg_col.format('a', 'Automatically')),
                ('sort_cpu', msg_col.format('c', 'CPU%')),
                ('sort_io_rate', msg_col.format('i', 'I/O rate')),
                ('sort_mem', msg_col.format('m', 'MEM%')),
                ('sort_process_name', msg_col.format('p', 'Process name')),
                ('sort_cpu_times', msg_col.format('t', 'TIME')),
                ('sort_user', msg_col.format('u', 'USER')),
                ('header_show_hide', msg_header.format('SHOW/HIDE SECTION:')),
                ('show_hide_application_monitoring', msg_col.format('A', 'Application monitoring')),
                ('show_hide_diskio', msg_col.format('d', 'Disk I/O')),
                ('show_hide_docker', msg_col.format('D', 'Docker')),
                ('show_hide_top_extended_stats', msg_col.format('e', 'Top extended stats')),
                ('show_hide_filesystem', msg_col.format('f', 'Filesystem')),
                ('show_hide_gpu', msg_col.format('G', 'GPU')),
                ('show_hide_ip', msg_col.format('I', 'IP')),
                ('show_hide_tcp_connection', msg_col.format('K', 'TCP')),
                ('show_hide_alert', msg_col.format('l', 'Alert logs')),
                ('show_hide_network', msg_col.format('n', 'Network')),
                ('show_hide_current_time', msg_col.format('N', 'Time')),
                ('show_hide_irq', msg_col.format('Q', 'IRQ')),
                ('show_hide_raid_plugin', msg_col.format('R', 'RAID')),
                ('show_hide_sensors', msg_col.format('s', 'Sensors')),
                ('show_hide_wifi_module', msg_col.format('W', 'Wifi')),
                ('show_hide_processes', msg_col.format('z', 'Processes')),
                ('show_hide_left_sidebar', msg_col.format('2', 'Left sidebar')),
                # Second column
                #
                ('show_hide_quick_look', msg_col.format('3', 'Quick Look')),
                ('show_hide_cpu_mem_swap', msg_col.format('4', 'CPU, MEM, and SWAP')),
                ('show_hide_all', msg_col.format('5', 'ALL')),
                ('header_toggle', msg_header.format('TOGGLE DATA TYPE:')),
                ('toggle_bits_bytes', msg_col.format('b', 'Network I/O, bits/bytes')),
                ('toggle_count_rate', msg_col.format('B', 'Disk I/O, count/rate')),
                ('toggle_used_free', msg_col.format('F', 'Filesystem space, used/free')),
                ('toggle_bar_sparkline', msg_col.format('S', 'Quick Look, bar/sparkline')),
                ('toggle_separate_combined', msg_col.format('T', 'Network I/O, separate/combined')),
                ('toggle_live_cumulative', msg_col.format('U', 'Network I/O, live/cumulative')),
                ('toggle_linux_percentage', msg_col.format('0', 'Load, Linux/percentage')),
                ('toggle_cpu_individual_combined', msg_col.format('1', 'CPU, individual/combined')),
                ('toggle_gpu_individual_combined', msg_col.format('6', 'GPU, individual/combined')),
                (
                    'toggle_short_full',
                    (
                        msg_col.format('S', 'Process names, short/full')
                        if self.args and self.args.webserver
                        else msg_col.format('/', 'Process names, short/full')
                    ),
                ),
                ('header_miscellaneous', msg_header.format('MISCELLANEOUS:')),
                (
                    'misc_erase_process_filter',
                    '' if self.args and self.args.webserver else msg_col.format('E', 'Erase process filter'),
                ),
                (
                    'misc_generate_history_graphs',
                    '' if self.args and self.args.webserver else msg_col.format('g', 'Generate history graphs'),
                ),
                ('misc_help', msg_col.format('h', 'HELP')),
                (
                    'misc_accumulate_processes_by_program',
                    '' if self.args and self.args.webserver else msg_col.format('j', 'Display threads or programs'),
                ),
                ('misc_increase_nice_process', msg_col.format('+', 'Increase nice process')),
                ('misc_decrease_nice_process', msg_col.format('-', 'Decrease nice process (need admin rights)')),
                ('misc_kill_process', '' if self.args and self.args.webserver else msg_col.format('k', 'Kill process')),
                (
                    'misc_reset_processes_summary_min_max',
                    '' if self.args and self.args.webserver else msg_col.format('M', 'Reset processes summary min/max'),
                ),
                (
                    'misc_quit',
                    '' if self.args and self.args.webserver else msg_col.format('q', 'QUIT (or Esc or Ctrl-C)'),
                ),
                ('misc_reset_history', msg_col.format('r', 'Reset history')),
                ('misc_delete_warning_alerts', msg_col.format('w', 'Delete warning alerts')),
                ('misc_delete_warning_and_critical_alerts', msg_col.format('x', 'Delete warning & critical alerts')),
                (
                    'misc_edit_process_filter_pattern',
                    '' if self.args and self.args.webserver else '  ENTER: Edit process filter pattern',
                ),
            ]
        )

    def get_view_data(self, args=None):
        """Return the view."""
        return self.view_data

    def msg_curse(self, args=None, max_width=None):
        """Return the list to display in the curse interface."""
        # Init the return message
        ret = []

        # Build the header message
        ret.append(self.curse_add_line(self.view_data['version'], 'TITLE'))
        ret.append(self.curse_add_line(self.view_data['psutil_version']))
        ret.append(self.curse_new_line())

        # Build the configuration file path
        if 'configuration_file' in self.view_data:
            ret.append(self.curse_add_line(self.view_data['configuration_file']))
            ret.append(self.curse_new_line())

        ret.append(self.curse_new_line())

        # key-shortcuts
        #
        # Collect all values after the 1st key-msg
        # in a list of curse-lines.
        #
        shortcuts = []
        collecting = False
        for k, v in iteritems(self.view_data):
            if collecting:
                pass
            elif k == 'header_sort':
                collecting = True
            else:
                continue
            shortcuts.append(self.curse_add_line(v))
        # Divide shortcuts into 2 columns
        # and if number of schortcuts is even,
        # make the 1st column taller (len+1).
        #
        nlines = (len(shortcuts) + 1) // 2
        ret.extend(
            msg
            for triplet in zip(
                iter(shortcuts[:nlines]),
                chain(shortcuts[nlines:], iter(lambda: self.curse_add_line(''), None)),
                iter(self.curse_new_line, None),
            )
            for msg in triplet
        )

        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('For an exhaustive list of key bindings:'))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('https://glances.readthedocs.io/en/latest/cmds.html#interactive-commands'))
        ret.append(self.curse_new_line())

        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('Colors binding:'))
        ret.append(self.curse_new_line())
        for c in [
            'DEFAULT',
            'UNDERLINE',
            'BOLD',
            'SORT',
            'OK',
            'MAX',
            'FILTER',
            'TITLE',
            'PROCESS',
            'PROCESS_SELECTED',
            'STATUS',
            'CPU_TIME',
            'CAREFUL',
            'WARNING',
            'CRITICAL',
            'OK_LOG',
            'CAREFUL_LOG',
            'WARNING_LOG',
            'CRITICAL_LOG',
            'PASSWORD',
            'SELECTED',
            'INFO',
            'ERROR',
            'SEPARATOR',
        ]:
            ret.append(self.curse_add_line(c, decoration=c))
            if c == 'CPU_TIME':
                ret.append(self.curse_new_line())
            else:
                ret.append(self.curse_add_line(' '))

        # Return the message with decoration
        return ret

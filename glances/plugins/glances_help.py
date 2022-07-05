# -*- coding: utf-8 -*-
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

from glances import __version__, psutil_version
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """Glances help plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, config=config)

        # Set the config instance
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # init data dictionary
        self.view_data = {}
        self.generate_view_data()

    def reset(self):
        """No stats. It is just a plugin to display the help."""
        pass

    def update(self):
        """No stats. It is just a plugin to display the help."""
        pass

    def generate_view_data(self):
        """Generate the views."""
        self.view_data['version'] = '{} {}'.format('Glances', __version__)
        self.view_data['psutil_version'] = ' with psutil {}'.format(psutil_version)

        try:
            self.view_data['configuration_file'] = 'Configuration file: {}'.format(self.config.loaded_config_file)
        except AttributeError:
            pass

        msg_col = '  {0:1}  {1:34}'
        msg_header = '{0:39}'

        """First column"""
        self.view_data['header_sort'] = msg_header.format('SORT PROCESSES:')
        self.view_data['sort_auto'] = msg_col.format('a', 'Automatically')
        self.view_data['sort_cpu'] = msg_col.format('c', 'CPU%')
        self.view_data['sort_io_rate'] = msg_col.format('i', 'I/O rate')
        self.view_data['sort_mem'] = msg_col.format('m', 'MEM%')
        self.view_data['sort_process_name'] = msg_col.format('p', 'Process name')
        self.view_data['sort_cpu_times'] = msg_col.format('t', 'TIME')
        self.view_data['sort_user'] = msg_col.format('u', 'USER')

        self.view_data['header_show_hide'] = msg_header.format('SHOW/HIDE SECTION:')
        self.view_data['show_hide_application_monitoring'] = msg_col.format('A', 'Application monitoring')
        self.view_data['show_hide_diskio'] = msg_col.format('d', 'Disk I/O')
        self.view_data['show_hide_docker'] = msg_col.format('D', 'Docker')
        self.view_data['show_hide_top_extended_stats'] = msg_col.format('e', 'Top extended stats')
        self.view_data['show_hide_filesystem'] = msg_col.format('f', 'Filesystem')
        self.view_data['show_hide_gpu'] = msg_col.format('G', 'GPU')
        self.view_data['show_hide_ip'] = msg_col.format('I', 'IP')
        self.view_data['show_hide_tcp_connection'] = msg_col.format('K', 'TCP')
        self.view_data['show_hide_alert'] = msg_col.format('l', 'Alert logs')
        self.view_data['show_hide_network'] = msg_col.format('n', 'Network')
        self.view_data['show_hide_current_time'] = msg_col.format('N', 'Time')
        self.view_data['show_hide_irq'] = msg_col.format('Q', 'IRQ')
        self.view_data['show_hide_raid_plugin'] = msg_col.format('R', 'RAID')
        self.view_data['show_hide_sensors'] = msg_col.format('s', 'Sensors')
        self.view_data['show_hide_wifi_module'] = msg_col.format('W', 'Wifi')
        self.view_data['show_hide_processes'] = msg_col.format('z', 'Processes')
        self.view_data['show_hide_left_sidebar'] = msg_col.format('2', 'Left sidebar')

        """Second column"""
        self.view_data['show_hide_quick_look'] = msg_col.format('3', 'Quick Look')
        self.view_data['show_hide_cpu_mem_swap'] = msg_col.format('4', 'CPU, MEM, and SWAP')
        self.view_data['show_hide_all'] = msg_col.format('5', 'ALL')

        self.view_data['header_toggle'] = msg_header.format('TOGGLE DATA TYPE:')
        self.view_data['toggle_bits_bytes'] = msg_col.format('b', 'Network I/O: bits/bytes')
        self.view_data['toggle_count_rate'] = msg_col.format('B', 'Disk I/O: count/rate')
        self.view_data['toggle_used_free'] = msg_col.format('F', 'Filesystem space: used/free')
        self.view_data['toggle_bar_sparkline'] = msg_col.format('S', 'Quick Look: bar/sparkline')
        self.view_data['toggle_separate_combined'] = msg_col.format('T', 'Network I/O: separate/combined')
        self.view_data['toggle_live_cumulative'] = msg_col.format('U', 'Network I/O: live/cumulative')
        self.view_data['toggle_linux_percentage'] = msg_col.format('0', 'Load: Linux/percentage')
        self.view_data['toggle_cpu_individual_combined'] = msg_col.format('1', 'CPU: individual/combined')
        self.view_data['toggle_gpu_individual_combined'] = msg_col.format('6', 'GPU: individual/combined')
        self.view_data['toggle_short_full'] = msg_col.format('/', 'Process names: short/full')

        self.view_data['header_miscellaneous'] = msg_header.format('MISCELLANEOUS:')
        self.view_data['misc_erase_process_filter'] = msg_col.format('E', 'Erase process filter')
        self.view_data['misc_generate_history_graphs'] = msg_col.format('g', 'Generate history graphs')
        self.view_data['misc_help'] = msg_col.format('h', 'HELP')
        self.view_data['misc_accumulate processes_by_program'] = msg_col.format('j', 'Accumulate processes by program')
        self.view_data['misc_kill_process'] = msg_col.format('k', 'Kill process')
        self.view_data['misc_reset_processes_summary_min_max'] = msg_col.format('M', 'Reset processes summary min/max')
        self.view_data['misc_quit'] = msg_col.format('q', 'QUIT (or Esc or Ctrl-C)')
        self.view_data['misc_reset_history'] = msg_col.format('r', 'Reset history')
        self.view_data['misc_delete_warning_alerts'] = msg_col.format('w', 'Delete warning alerts')
        self.view_data['misc_delete_warning_and_critical_alerts'] = msg_col.format('x', 'Delete warning & critical alerts')
        self.view_data['misc_edit_process_filter_pattern'] = '  ENTER: Edit process filter pattern'        

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

        # Keys
        ret.append(self.curse_add_line(self.view_data['header_sort']))
        ret.append(self.curse_add_line(self.view_data['show_hide_quick_look']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_auto']))
        ret.append(self.curse_add_line(self.view_data['show_hide_cpu_mem_swap']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_cpu']))
        ret.append(self.curse_add_line(self.view_data['show_hide_all']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_io_rate']))
        ret.append(self.curse_add_line(self.view_data['header_toggle']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_mem']))
        ret.append(self.curse_add_line(self.view_data['toggle_bits_bytes']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_process_name']))
        ret.append(self.curse_add_line(self.view_data['toggle_count_rate']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_cpu_times']))
        ret.append(self.curse_add_line(self.view_data['toggle_used_free']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_user']))
        ret.append(self.curse_add_line(self.view_data['toggle_bar_sparkline']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['header_show_hide']))
        ret.append(self.curse_add_line(self.view_data['toggle_separate_combined']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_application_monitoring']))
        ret.append(self.curse_add_line(self.view_data['toggle_live_cumulative']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_diskio']))
        ret.append(self.curse_add_line(self.view_data['toggle_linux_percentage']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_docker']))
        ret.append(self.curse_add_line(self.view_data['toggle_cpu_individual_combined']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_top_extended_stats']))
        ret.append(self.curse_add_line(self.view_data['toggle_gpu_individual_combined']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_filesystem']))
        ret.append(self.curse_add_line(self.view_data['toggle_short_full']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_gpu']))
        ret.append(self.curse_add_line(self.view_data['header_miscellaneous']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_ip']))
        ret.append(self.curse_add_line(self.view_data['misc_erase_process_filter']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_tcp_connection']))
        ret.append(self.curse_add_line(self.view_data['misc_generate_history_graphs']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_alert']))
        ret.append(self.curse_add_line(self.view_data['misc_help']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_network']))
        ret.append(self.curse_add_line(self.view_data['misc_accumulate processes_by_program']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_current_time']))
        ret.append(self.curse_add_line(self.view_data['misc_kill_process']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_irq']))
        ret.append(self.curse_add_line(self.view_data['misc_reset_processes_summary_min_max']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_raid_plugin']))
        ret.append(self.curse_add_line(self.view_data['misc_quit']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_sensors']))
        ret.append(self.curse_add_line(self.view_data['misc_reset_history']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_wifi_module']))
        ret.append(self.curse_add_line(self.view_data['misc_delete_warning_alerts']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_processes']))
        ret.append(self.curse_add_line(self.view_data['misc_delete_warning_and_critical_alerts']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_left_sidebar']))
        ret.append(self.curse_add_line(self.view_data['misc_edit_process_filter_pattern']))

        # Return the message with decoration
        return ret

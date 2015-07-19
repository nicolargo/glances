# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""
Help plugin.

Just a stupid plugin to display the help screen.
"""

# Import Glances libs
from glances.core.glances_globals import appname, psutil_version, version
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances help plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # Set the config instance
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # init data dictionary
        self.view_data = {}
        self.generate_view_data()

    def update(self):
        """No stats. It is just a plugin to display the help."""
        pass

    def generate_view_data(self):
        self.view_data['version'] = '{0} {1}'.format(appname.title(), version)
        self.view_data['psutil_version'] = ' with PSutil {0}'.format(psutil_version)

        try:
            self.view_data['configuration_file'] = 'Configuration file: {0}'.format(self.config.loaded_config_file)
        except AttributeError:
            pass

        msg_col = ' {0:1}  {1:35}'
        msg_col2 = '   {0:1}  {1:35}'
        self.view_data['sort_auto'] = msg_col.format('a', 'Sort processes automatically')
        self.view_data['sort_network'] = msg_col2.format('b', 'Bytes or bits for network I/O')
        self.view_data['sort_cpu'] = msg_col.format('c', 'Sort processes by CPU%')
        self.view_data['show_hide_alert'] = msg_col2.format('l', 'Show/hide alert logs')
        self.view_data['sort_mem'] = msg_col.format('m', 'Sort processes by MEM%')
        self.view_data['sort_user'] = msg_col.format('u', 'Sort processes by USER')
        self.view_data['delete_warning_alerts'] = msg_col2.format('w', 'Delete warning alerts')
        self.view_data['sort_proc'] = msg_col.format('p', 'Sort processes by name')
        self.view_data['delete_warning_critical_alerts'] = msg_col2.format('x', 'Delete warning and critical alerts')
        self.view_data['sort_io'] = msg_col.format('i', 'Sort processes by I/O rate')
        self.view_data['percpu'] = msg_col2.format('1', 'Global CPU or per-CPU stats')
        self.view_data['sort_cpu_times'] = msg_col.format('t', 'Sort processes by TIME')
        self.view_data['show_hide_help'] = msg_col2.format('h', 'Show/hide this help screen')
        self.view_data['show_hide_diskio'] = msg_col.format('d', 'Show/hide disk I/O stats')
        self.view_data['view_network_io_combination'] = msg_col2.format('T', 'View network I/O as combination')
        self.view_data['show_hide_filesystem'] = msg_col.format('f', 'Show/hide filesystem stats')
        self.view_data['view_cumulative_network'] = msg_col2.format('U', 'View cumulative network I/O')
        self.view_data['show_hide_network'] = msg_col.format('n', 'Show/hide network stats')
        self.view_data['show_hide_filesytem_freespace'] = msg_col2.format('F', 'Show filesystem free space')
        self.view_data['show_hide_sensors'] = msg_col.format('s', 'Show/hide sensors stats')
        self.view_data['generate_graphs'] = msg_col2.format('g', 'Generate graphs for current history')
        self.view_data['show_hide_left_sidebar'] = msg_col.format('2', 'Show/hide left sidebar')
        self.view_data['reset_history'] = msg_col2.format('r', 'Reset history')
        self.view_data['enable_disable_process_stats'] = msg_col.format('z', 'Enable/disable processes stats')
        self.view_data['quit'] = msg_col2.format('q', 'Quit (Esc and Ctrl-C also work)')
        self.view_data['enable_disable_top_extends_stats'] = msg_col.format('e', 'Enable/disable top extended stats')
        self.view_data['enable_disable_short_processname'] = msg_col.format('/', 'Enable/disable short processes name')
        self.view_data['enable_disable_irix'] = msg_col.format('0', 'Enable/disable Irix process CPU')
        self.view_data['enable_disable_docker'] = msg_col2.format('D', 'Enable/disable Docker stats')
        self.view_data['enable_disable_quick_look'] = msg_col.format('3', 'Enable/disable quick look plugin')
        self.view_data['show_hide_ip'] = msg_col2.format('I', 'Show/hide IP module')
        self.view_data['edit_pattern_filter'] = 'ENTER: Edit the process filter pattern'

    def get_view_data(self, args=None):
        return self.view_data

    def msg_curse(self, args=None):
        """Return the list to display in the curse interface."""
        # Init the return message
        ret = []

        # Build the string message
        # Header
        ret.append(self.curse_add_line(self.view_data['version'], 'TITLE'))
        ret.append(self.curse_add_line(self.view_data['psutil_version']))
        ret.append(self.curse_new_line())

        # Configuration file path
        if 'configuration_file' in self.view_data:
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line(self.view_data['configuration_file']))
            ret.append(self.curse_new_line())

        # Keys
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_auto']))
        ret.append(self.curse_add_line(self.view_data['sort_network']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_cpu']))
        ret.append(self.curse_add_line(self.view_data['show_hide_alert']))
        ret.append(self.curse_new_line())

        ret.append(self.curse_add_line(self.view_data['sort_mem']))
        ret.append(self.curse_add_line(self.view_data['delete_warning_alerts']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_user']))
        ret.append(self.curse_add_line(self.view_data['delete_warning_critical_alerts']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_proc']))
        ret.append(self.curse_add_line(self.view_data['percpu']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_io']))
        ret.append(self.curse_add_line(self.view_data['show_hide_ip']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['sort_cpu_times']))
        ret.append(self.curse_add_line(self.view_data['enable_disable_docker']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_diskio']))
        ret.append(self.curse_add_line(self.view_data['view_network_io_combination']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_filesystem']))
        ret.append(self.curse_add_line(self.view_data['view_cumulative_network']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_network']))
        ret.append(self.curse_add_line(self.view_data['show_hide_filesytem_freespace']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_sensors']))
        ret.append(self.curse_add_line(self.view_data['generate_graphs']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['show_hide_left_sidebar']))
        ret.append(self.curse_add_line(self.view_data['reset_history']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['enable_disable_process_stats']))
        ret.append(self.curse_add_line(self.view_data['show_hide_help']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['enable_disable_quick_look']))
        ret.append(self.curse_add_line(self.view_data['quit']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['enable_disable_top_extends_stats']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['enable_disable_short_processname']))
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(self.view_data['enable_disable_irix']))
        ret.append(self.curse_new_line())

        ret.append(self.curse_new_line())

        ret.append(self.curse_add_line(self.view_data['edit_pattern_filter']))

        # Return the message with decoration
        return ret

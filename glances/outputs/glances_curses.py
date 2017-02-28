# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

"""Curses interface class."""

import re
import sys

from glances.compat import u, itervalues
from glances.globals import MACOS, WINDOWS
from glances.logger import logger
from glances.logs import glances_logs
from glances.processes import glances_processes
from glances.timer import Timer

# Import curses library for "normal" operating system
if not WINDOWS:
    try:
        import curses
        import curses.panel
        from curses.textpad import Textbox
    except ImportError:
        logger.critical("Curses module not found. Glances cannot start in standalone mode.")
        sys.exit(1)


class _GlancesCurses(object):

    """This class manages the curses display (and key pressed).

    Note: It is a private class, use GlancesCursesClient or GlancesCursesBrowser.
    """

    _hotkeys = {
        '0': {'switch': 'disable_irix'},
        '1': {'switch': 'percpu'},
        '2': {'switch': 'disable_left_sidebar'},
        '3': {'switch': 'disable_quicklook'},
        '6': {'switch': 'meangpu'},
        '/': {'switch': 'process_short_name'},
        'A': {'switch': 'disable_amps'},
        'b': {'switch': 'byte'},
        'B': {'switch': 'diskio_iops'},
        'C': {'switch': 'disable_cloud'},
        'D': {'switch': 'disable_docker'},
        'd': {'switch': 'disable_diskio'},
        'F': {'switch': 'fs_free_space'},
        'G': {'switch': 'disable_gpu'},
        'h': {'switch': 'help_tag'},
        'I': {'switch': 'disable_ip'},
        'l': {'switch': 'disable_alert'},
        'M': {'switch': 'reset_minmax_tag'},
        'n': {'switch': 'disable_network'},
        'N': {'switch': 'disable_now'},
        'P': {'switch': 'disable_ports'},
        'Q': {'switch': 'enable_irq'},
        'R': {'switch': 'disable_raid'},
        's': {'switch': 'disable_sensors'},
        'T': {'switch': 'network_sum'},
        'U': {'switch': 'network_cumul'},
        'W': {'switch': 'disable_wifi'},
        # Processes sort hotkeys
        'a': {'auto_sort': True, 'sort_key': 'cpu_percent'},
        'c': {'auto_sort': False, 'sort_key': 'cpu_percent'},
        'i': {'auto_sort': False, 'sort_key': 'io_counters'},
        'm': {'auto_sort': False, 'sort_key': 'memory_percent'},
        'p': {'auto_sort': False, 'sort_key': 'name'},
        't': {'auto_sort': False, 'sort_key': 'cpu_times'},
        'u': {'auto_sort': False, 'sort_key': 'username'}
    }

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Init windows positions
        self.term_w = 80
        self.term_h = 24

        # Space between stats
        self.space_between_column = 3
        self.space_between_line = 2

        # Init the curses screen
        self.screen = curses.initscr()
        if not self.screen:
            logger.critical("Cannot init the curses library.\n")
            sys.exit(1)

        # Load the 'outputs' section of the configuration file
        # - Init the theme (default is black)
        self.theme = {'name': 'black'}

        # Load configuration file
        self.load_config(config)

        # Init cursor
        self._init_cursor()

        # Init the colors
        self._init_colors()

        # Init main window
        self.term_window = self.screen.subwin(0, 0)

        # Init refresh time
        self.__refresh_time = args.time

        # Init edit filter tag
        self.edit_filter = False

        # Init the process min/max reset
        self.args.reset_minmax_tag = False

        # Catch key pressed with non blocking mode
        self.no_flash_cursor()
        self.term_window.nodelay(1)
        self.pressedkey = -1

        # History tag
        self._init_history()

    def load_config(self, config):
        """Load the outputs section of the configuration file."""
        # Load the theme
        if config is not None and config.has_section('outputs'):
            logger.debug('Read the outputs section in the configuration file')
            self.theme['name'] = config.get_value('outputs', 'curse_theme', default='black')
            logger.debug('Theme for the curse interface: {}'.format(self.theme['name']))

    def is_theme(self, name):
        """Return True if the theme *name* should be used."""
        return getattr(self.args, 'theme_' + name) or self.theme['name'] == name

    def _init_history(self):
        """Init the history option."""

        self.reset_history_tag = False
        self.graph_tag = False
        if self.args.export_graph:
            logger.info('Export graphs function enabled with output path %s' %
                        self.args.path_graph)
            from glances.exports.graph import GlancesGraph
            self.glances_graph = GlancesGraph(self.args.path_graph)
            if not self.glances_graph.graph_enabled():
                self.args.export_graph = False
                logger.error('Export graphs disabled')

    def _init_cursor(self):
        """Init cursors."""

        if hasattr(curses, 'noecho'):
            curses.noecho()
        if hasattr(curses, 'cbreak'):
            curses.cbreak()
        self.set_cursor(0)

    def _init_colors(self):
        """Init the Curses color layout."""

        # Set curses options
        if hasattr(curses, 'start_color'):
            curses.start_color()
        if hasattr(curses, 'use_default_colors'):
            curses.use_default_colors()

        # Init colors
        if self.args.disable_bold:
            A_BOLD = 0
            self.args.disable_bg = True
        else:
            A_BOLD = curses.A_BOLD

        self.title_color = A_BOLD
        self.title_underline_color = A_BOLD | curses.A_UNDERLINE
        self.help_color = A_BOLD

        if curses.has_colors():
            # The screen is compatible with a colored design
            if self.is_theme('white'):
                # White theme: black ==> white
                curses.init_pair(1, curses.COLOR_BLACK, -1)
            else:
                curses.init_pair(1, curses.COLOR_WHITE, -1)
            if self.args.disable_bg:
                curses.init_pair(2, curses.COLOR_RED, -1)
                curses.init_pair(3, curses.COLOR_GREEN, -1)
                curses.init_pair(4, curses.COLOR_BLUE, -1)
                curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            else:
                curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
                curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN)
                curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
                curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
            curses.init_pair(6, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_GREEN, -1)
            curses.init_pair(8, curses.COLOR_BLUE, -1)

            # Colors text styles
            if curses.COLOR_PAIRS > 8:
                try:
                    curses.init_pair(9, curses.COLOR_MAGENTA, -1)
                except Exception:
                    if self.is_theme('white'):
                        curses.init_pair(9, curses.COLOR_BLACK, -1)
                    else:
                        curses.init_pair(9, curses.COLOR_WHITE, -1)
                try:
                    curses.init_pair(10, curses.COLOR_CYAN, -1)
                except Exception:
                    if self.is_theme('white'):
                        curses.init_pair(10, curses.COLOR_BLACK, -1)
                    else:
                        curses.init_pair(10, curses.COLOR_WHITE, -1)

                self.ifWARNING_color2 = curses.color_pair(9) | A_BOLD
                self.ifCRITICAL_color2 = curses.color_pair(6) | A_BOLD
                self.filter_color = curses.color_pair(10) | A_BOLD

            self.no_color = curses.color_pair(1)
            self.default_color = curses.color_pair(3) | A_BOLD
            self.nice_color = curses.color_pair(9)
            self.cpu_time_color = curses.color_pair(9)
            self.ifCAREFUL_color = curses.color_pair(4) | A_BOLD
            self.ifWARNING_color = curses.color_pair(5) | A_BOLD
            self.ifCRITICAL_color = curses.color_pair(2) | A_BOLD
            self.default_color2 = curses.color_pair(7)
            self.ifCAREFUL_color2 = curses.color_pair(8) | A_BOLD

        else:
            # The screen is NOT compatible with a colored design
            # switch to B&W text styles
            self.no_color = curses.A_NORMAL
            self.default_color = curses.A_NORMAL
            self.nice_color = A_BOLD
            self.cpu_time_color = A_BOLD
            self.ifCAREFUL_color = curses.A_UNDERLINE
            self.ifWARNING_color = A_BOLD
            self.ifCRITICAL_color = curses.A_REVERSE
            self.default_color2 = curses.A_NORMAL
            self.ifCAREFUL_color2 = curses.A_UNDERLINE
            self.ifWARNING_color2 = A_BOLD
            self.ifCRITICAL_color2 = curses.A_REVERSE
            self.filter_color = A_BOLD

        # Define the colors list (hash table) for stats
        self.colors_list = {
            'DEFAULT': self.no_color,
            'UNDERLINE': curses.A_UNDERLINE,
            'BOLD': A_BOLD,
            'SORT': A_BOLD,
            'OK': self.default_color2,
            'MAX': self.default_color2 | curses.A_BOLD,
            'FILTER': self.filter_color,
            'TITLE': self.title_color,
            'PROCESS': self.default_color2,
            'STATUS': self.default_color2,
            'NICE': self.nice_color,
            'CPU_TIME': self.cpu_time_color,
            'CAREFUL': self.ifCAREFUL_color2,
            'WARNING': self.ifWARNING_color2,
            'CRITICAL': self.ifCRITICAL_color2,
            'OK_LOG': self.default_color,
            'CAREFUL_LOG': self.ifCAREFUL_color,
            'WARNING_LOG': self.ifWARNING_color,
            'CRITICAL_LOG': self.ifCRITICAL_color,
            'PASSWORD': curses.A_PROTECT
        }

    def flash_cursor(self):
        self.term_window.keypad(1)

    def no_flash_cursor(self):
        self.term_window.keypad(0)

    def set_cursor(self, value):
        """Configure the curse cursor apparence.

        0: invisible
        1: visible
        2: very visible
        """
        if hasattr(curses, 'curs_set'):
            try:
                curses.curs_set(value)
            except Exception:
                pass

    def get_key(self, window):
        # Catch ESC key AND numlock key (issue #163)
        keycode = [0, 0]
        keycode[0] = window.getch()
        keycode[1] = window.getch()

        if keycode != [-1, -1]:
            logger.debug("Keypressed (code: %s)" % keycode)

        if keycode[0] == 27 and keycode[1] != -1:
            # Do not escape on specials keys
            return -1
        else:
            return keycode[0]

    def __catch_key(self, return_to_browser=False):
        # Catch the pressed key
        self.pressedkey = self.get_key(self.term_window)

        # Actions (available in the global hotkey dict)...
        for hotkey in self._hotkeys:
            if self.pressedkey == ord(hotkey) and 'switch' in self._hotkeys[hotkey]:
                setattr(self.args,
                        self._hotkeys[hotkey]['switch'],
                        not getattr(self.args,
                                    self._hotkeys[hotkey]['switch']))
            if self.pressedkey == ord(hotkey) and 'auto_sort' in self._hotkeys[hotkey]:
                setattr(glances_processes,
                        'auto_sort',
                        self._hotkeys[hotkey]['auto_sort'])
            if self.pressedkey == ord(hotkey) and 'sort_key' in self._hotkeys[hotkey]:
                setattr(glances_processes,
                        'sort_key',
                        self._hotkeys[hotkey]['sort_key'])

        # Other actions...
        if self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            if return_to_browser:
                logger.info("Stop Glances client and return to the browser")
            else:
                self.end()
                logger.info("Stop Glances")
                sys.exit(0)
        elif self.pressedkey == ord('\n'):
            # 'ENTER' > Edit the process filter
            self.edit_filter = not self.edit_filter
        elif self.pressedkey == ord('4'):
            self.args.full_quicklook = not self.args.full_quicklook
            if self.args.full_quicklook:
                self.enable_fullquicklook()
            else:
                self.disable_fullquicklook()
        elif self.pressedkey == ord('5'):
            self.args.disable_top = not self.args.disable_top
            if self.args.disable_top:
                self.disable_top()
            else:
                self.enable_top()
        elif self.pressedkey == ord('e'):
            # 'e' > Enable/Disable process extended
            self.args.enable_process_extended = not self.args.enable_process_extended
            if not self.args.enable_process_extended:
                glances_processes.disable_extended()
            else:
                glances_processes.enable_extended()
        elif self.pressedkey == ord('E'):
            # 'E' > Erase the process filter
            glances_processes.process_filter = None
        elif self.pressedkey == ord('f'):
            # 'f' > Show/hide fs / folder stats
            self.args.disable_fs = not self.args.disable_fs
            self.args.disable_folders = not self.args.disable_folders
        elif self.pressedkey == ord('g'):
            # 'g' > Generate graph from history
            self.graph_tag = not self.graph_tag
        elif self.pressedkey == ord('r'):
            # 'r' > Reset graph history
            self.reset_history_tag = not self.reset_history_tag
        elif self.pressedkey == ord('w'):
            # 'w' > Delete finished warning logs
            glances_logs.clean()
        elif self.pressedkey == ord('x'):
            # 'x' > Delete finished warning and critical logs
            glances_logs.clean(critical=True)
        elif self.pressedkey == ord('z'):
            # 'z' > Enable or disable processes
            self.args.disable_process = not self.args.disable_process
            if self.args.disable_process:
                glances_processes.disable()
            else:
                glances_processes.enable()

        # Return the key code
        return self.pressedkey

    def disable_top(self):
        """Disable the top panel"""
        for p in ['quicklook', 'cpu', 'gpu', 'mem', 'memswap', 'load']:
            setattr(self.args, 'disable_' + p, True)

    def enable_top(self):
        """Enable the top panel"""
        for p in ['quicklook', 'cpu', 'gpu', 'mem', 'memswap', 'load']:
            setattr(self.args, 'disable_' + p, False)

    def disable_fullquicklook(self):
        """Disable the full quicklook mode"""
        for p in ['quicklook', 'cpu', 'gpu', 'mem', 'memswap']:
            setattr(self.args, 'disable_' + p, False)

    def enable_fullquicklook(self):
        """Disable the full quicklook mode"""
        self.args.disable_quicklook = False
        for p in ['cpu', 'gpu', 'mem', 'memswap']:
            setattr(self.args, 'disable_' + p, True)

    def end(self):
        """Shutdown the curses window."""
        if hasattr(curses, 'echo'):
            curses.echo()
        if hasattr(curses, 'nocbreak'):
            curses.nocbreak()
        if hasattr(curses, 'curs_set'):
            try:
                curses.curs_set(1)
            except Exception:
                pass
        curses.endwin()

    def init_line_column(self):
        """Init the line and column position for the curses interface."""
        self.init_line()
        self.init_column()

    def init_line(self):
        """Init the line position for the curses interface."""
        self.line = 0
        self.next_line = 0

    def init_column(self):
        """Init the column position for the curses interface."""
        self.column = 0
        self.next_column = 0

    def new_line(self):
        """New line in the curses interface."""
        self.line = self.next_line

    def new_column(self):
        """New column in the curses interface."""
        self.column = self.next_column

    def __get_stat_display(self, stats, plugin_max_width):
        """Return a dict of dict with all the stats display
        * key: plugin name
        * value: dict returned by the get_stats_display Plugin method

        :returns: dict of dict
        """
        ret = {}
        for p in stats.getAllPlugins(enable=False):
            if p in ['network', 'wifi', 'irq', 'fs', 'folders']:
                ret[p] = stats.get_plugin(p).get_stats_display(
                    args=self.args, max_width=plugin_max_width)
            elif p in ['quicklook']:
                # Grab later because we need plugin size
                continue
            else:
                # system, uptime, cpu, percpu, gpu, load, mem, memswap, ip,
                # ... diskio, raid, sensors, ports, now, docker, processcount,
                # ... amps, alert
                try:
                    ret[p] = stats.get_plugin(p).get_stats_display(args=self.args)
                except AttributeError:
                    ret[p] = None
        if self.args.percpu:
            ret['cpu'] = ret['percpu']
        return ret

    def display(self, stats, cs_status=None):
        """Display stats on the screen.

        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to a Glances server
            "SNMP": Client is connected to a SNMP server
            "Disconnected": Client is disconnected from the server

        Return:
            True if the stats have been displayed
            False if the help have been displayed
        """
        # Init the internal line/column for Glances Curses
        self.init_line_column()

        # No processes list in SNMP mode
        if cs_status == 'SNMP':
            # so... more space for others plugins
            plugin_max_width = 43
        else:
            plugin_max_width = None

        # Update the stats messages
        ###########################

        # Update the client server status
        self.args.cs_status = cs_status
        __stat_display = self.__get_stat_display(stats, plugin_max_width)

        # Adapt number of processes to the available space
        max_processes_displayed = (
            self.screen.getmaxyx()[0] - 11 -
            self.get_stats_display_height(__stat_display["alert"]) -
            self.get_stats_display_height(__stat_display["docker"])
        )
        try:
            if self.args.enable_process_extended and not self.args.process_tree:
                max_processes_displayed -= 4
        except AttributeError:
            pass
        if max_processes_displayed < 0:
            max_processes_displayed = 0
        if (glances_processes.max_processes is None or
                glances_processes.max_processes != max_processes_displayed):
            logger.debug("Set number of displayed processes to {}".format(max_processes_displayed))
            glances_processes.max_processes = max_processes_displayed

        __stat_display["processlist"] = stats.get_plugin(
            'processlist').get_stats_display(args=self.args)

        # Display the stats on the curses interface
        ###########################################

        # Help screen (on top of the other stats)
        if self.args.help_tag:
            # Display the stats...
            self.display_plugin(
                stats.get_plugin('help').get_stats_display(args=self.args))
            # ... and exit
            return False

        # =====================================
        # Display first line (system+ip+uptime)
        # Optionnaly: Cloud on second line
        # =====================================
        self.__display_firstline(__stat_display)

        # ==============================================================
        # Display second line (<SUMMARY>+CPU|PERCPU+<GPU>+LOAD+MEM+SWAP)
        # ==============================================================
        self.__display_secondline(__stat_display, stats)

        # ==================================================================
        # Display left sidebar (NETWORK+PORTS+DISKIO+FS+SENSORS+Current time)
        # ==================================================================
        self.__display_left(__stat_display)

        # ====================================
        # Display right stats (process and co)
        # ====================================
        self.__display_right(__stat_display)

        # History option
        # Generate history graph
        if self.graph_tag and self.args.export_graph:
            self.display_popup(
                'Generate graphs history in {}\nPlease wait...'.format(
                    self.glances_graph.get_output_folder()))
            self.display_popup(
                'Generate graphs history in {}\nDone: {} graphs generated'.format(
                    self.glances_graph.get_output_folder(),
                    self.glances_graph.generate_graph(stats)))
        elif self.reset_history_tag and self.args.export_graph:
            self.display_popup('Reset graph history')
            self.glances_graph.reset(stats)
        elif (self.graph_tag or self.reset_history_tag) and not self.args.export_graph:
            try:
                self.glances_graph.graph_enabled()
            except Exception:
                self.display_popup('Graph disabled\nEnable it using --export-graph')
            else:
                self.display_popup('Graph disabled')
        self.graph_tag = False
        self.reset_history_tag = False

        # Display edit filter popup
        # Only in standalone mode (cs_status is None)
        if self.edit_filter and cs_status is None:
            new_filter = self.display_popup(
                'Process filter pattern: \n\n' +
                'Examples:\n' +
                '- python\n' +
                '- .*python.*\n' +
                '- \/usr\/lib.*\n' +
                '- name:.*nautilus.*\n' +
                '- cmdline:.*glances.*\n' +
                '- username:nicolargo\n' +
                '- username:^root        ',
                is_input=True,
                input_value=glances_processes.process_filter_input)
            glances_processes.process_filter = new_filter
        elif self.edit_filter and cs_status is not None:
            self.display_popup('Process filter only available in standalone mode')
        self.edit_filter = False

        return True

    def __display_firstline(self, stat_display):
        """Display the first line in the Curses interface.

        system + ip + uptime
        """
        # Space between column
        self.space_between_column = 0
        self.new_line()
        l_uptime = (self.get_stats_display_width(stat_display["system"]) +
                    self.space_between_column +
                    self.get_stats_display_width(stat_display["ip"]) + 3 +
                    self.get_stats_display_width(stat_display["uptime"]))
        self.display_plugin(
            stat_display["system"],
            display_optional=(self.screen.getmaxyx()[1] >= l_uptime))
        self.new_column()
        self.display_plugin(stat_display["ip"])
        # Space between column
        self.space_between_column = 3
        self.new_column()
        self.display_plugin(stat_display["uptime"],
                            add_space=self.get_stats_display_width(stat_display["cloud"]) == 0)
        self.init_column()
        self.new_line()
        self.display_plugin(stat_display["cloud"])

    def __display_secondline(self, stat_display, stats):
        """Display the second line in the Curses interface.

        <QUICKLOOK> + CPU|PERCPU + <GPU> + MEM + SWAP + LOAD
        """
        self.init_column()
        self.new_line()

        # Init quicklook
        stat_display['quicklook'] = {'msgdict': []}

        # Dict for plugins width
        plugin_widths = {'quicklook': 0}
        for p in ['cpu', 'gpu', 'mem', 'memswap', 'load']:
            plugin_widths[p] = self.get_stats_display_width(stat_display[p]) if hasattr(self.args, 'disable_' + p) and p in stat_display else 0

        # Width of all plugins
        stats_width = sum(itervalues(plugin_widths))

        # Number of plugin but quicklook
        stats_number = (
            int(not self.args.disable_cpu and stat_display["cpu"]['msgdict'] != []) +
            int(not self.args.disable_gpu and stat_display["gpu"]['msgdict'] != []) +
            int(not self.args.disable_mem and stat_display["mem"]['msgdict'] != []) +
            int(not self.args.disable_memswap and stat_display["memswap"]['msgdict'] != []) +
            int(not self.args.disable_load and stat_display["load"]['msgdict'] != []))

        if not self.args.disable_quicklook:
            # Quick look is in the place !
            if self.args.full_quicklook:
                quicklook_width = self.screen.getmaxyx()[1] - (stats_width + 8 + stats_number * self.space_between_column)
            else:
                quicklook_width = min(self.screen.getmaxyx()[1] - (stats_width + 8 + stats_number * self.space_between_column), 79)
            try:
                stat_display["quicklook"] = stats.get_plugin(
                    'quicklook').get_stats_display(max_width=quicklook_width, args=self.args)
            except AttributeError as e:
                logger.debug("Quicklook plugin not available (%s)" % e)
            else:
                plugin_widths['quicklook'] = self.get_stats_display_width(stat_display["quicklook"])
                stats_width = sum(itervalues(plugin_widths)) + 1
            self.space_between_column = 1
            self.display_plugin(stat_display["quicklook"])
            self.new_column()

        # Compute spaces between plugins
        # Note: Only one space between Quicklook and others
        plugin_display_optional = {}
        for p in ['cpu', 'gpu', 'mem', 'memswap', 'load']:
            plugin_display_optional[p] = True
        if stats_number > 1:
            self.space_between_column = max(1, int((self.screen.getmaxyx()[1] - stats_width) / (stats_number - 1)))
            for p in ['mem', 'cpu']:
                # No space ? Remove optional stats
                if self.space_between_column < 3:
                    plugin_display_optional[p] = False
                    plugin_widths[p] = self.get_stats_display_width(stat_display[p], without_option=True) if hasattr(self.args, 'disable_' + p) else 0
                    stats_width = sum(itervalues(plugin_widths)) + 1
                    self.space_between_column = max(1, int((self.screen.getmaxyx()[1] - stats_width) / (stats_number - 1)))
        else:
            self.space_between_column = 0

        # Display CPU, MEM, SWAP and LOAD
        for p in ['cpu', 'gpu', 'mem', 'memswap', 'load']:
            if p in stat_display:
                self.display_plugin(stat_display[p],
                                    display_optional=plugin_display_optional[p])
            if p is not 'load':
                # Skip last column
                self.new_column()

        # Space between column
        self.space_between_column = 3

        # Backup line position
        self.saved_line = self.next_line

    def __display_left(self, stat_display):
        """Display the left sidebar in the Curses interface.

        network+wifi+ports+diskio+fs+irq+folders+raid+sensors+now
        """
        self.init_column()
        if not self.args.disable_left_sidebar:
            for s in ['network', 'wifi', 'ports', 'diskio', 'fs', 'irq',
                      'folders', 'raid', 'sensors', 'now']:
                if ((hasattr(self.args, 'enable_' + s) or
                     hasattr(self.args, 'disable_' + s)) and s in stat_display):
                    self.new_line()
                    self.display_plugin(stat_display[s])

    def __display_right(self, stat_display):
        """Display the right sidebar in the Curses interface.

        docker + processcount + amps + processlist + alert
        """
        # If space available...
        if self.screen.getmaxyx()[1] > 52:
            # Restore line position
            self.next_line = self.saved_line

            # Display right sidebar
            # DOCKER+PROCESS_COUNT+AMPS+PROCESS_LIST+ALERT
            self.new_column()
            self.new_line()
            self.display_plugin(stat_display["docker"])
            self.new_line()
            self.display_plugin(stat_display["processcount"])
            self.new_line()
            self.display_plugin(stat_display["amps"])
            self.new_line()
            self.display_plugin(stat_display["processlist"],
                                display_optional=(self.screen.getmaxyx()[1] > 102),
                                display_additional=(not MACOS),
                                max_y=(self.screen.getmaxyx()[0] - self.get_stats_display_height(stat_display["alert"]) - 2))
            self.new_line()
            self.display_plugin(stat_display["alert"])

    def display_popup(self, message,
                      size_x=None, size_y=None,
                      duration=3,
                      is_input=False,
                      input_size=30,
                      input_value=None):
        """
        Display a centered popup.

        If is_input is False:
         Display a centered popup with the given message during duration seconds
         If size_x and size_y: set the popup size
         else set it automatically
         Return True if the popup could be displayed

        If is_input is True:
         Display a centered popup with the given message and a input field
         If size_x and size_y: set the popup size
         else set it automatically
         Return the input string or None if the field is empty
        """
        # Center the popup
        sentence_list = message.split('\n')
        if size_x is None:
            size_x = len(max(sentence_list, key=len)) + 4
            # Add space for the input field
            if is_input:
                size_x += input_size
        if size_y is None:
            size_y = len(sentence_list) + 4
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if size_x > screen_x or size_y > screen_y:
            # No size to display the popup => abord
            return False
        pos_x = int((screen_x - size_x) / 2)
        pos_y = int((screen_y - size_y) / 2)

        # Create the popup
        popup = curses.newwin(size_y, size_x, pos_y, pos_x)

        # Fill the popup
        popup.border()

        # Add the message
        for y, m in enumerate(message.split('\n')):
            popup.addnstr(2 + y, 2, m, len(m))

        if is_input and not WINDOWS:
            # Create a subwindow for the text field
            subpop = popup.derwin(1, input_size, 2, 2 + len(m))
            subpop.attron(self.colors_list['FILTER'])
            # Init the field with the current value
            if input_value is not None:
                subpop.addnstr(0, 0, input_value, len(input_value))
            # Display the popup
            popup.refresh()
            subpop.refresh()
            # Create the textbox inside the subwindows
            self.set_cursor(2)
            self.flash_cursor()
            textbox = GlancesTextbox(subpop, insert_mode=False)
            textbox.edit()
            self.set_cursor(0)
            self.no_flash_cursor()
            if textbox.gather() != '':
                logger.debug(
                    "User enters the following string: %s" % textbox.gather())
                return textbox.gather()[:-1]
            else:
                logger.debug("User centers an empty string")
                return None
        else:
            # Display the popup
            popup.refresh()
            self.wait(duration * 1000)
            return True

    def display_plugin(self, plugin_stats,
                       display_optional=True,
                       display_additional=True,
                       max_y=65535,
                       add_space=True):
        """Display the plugin_stats on the screen.

        If display_optional=True display the optional stats
        If display_additional=True display additionnal stats
        max_y do not display line > max_y
        """
        # Exit if:
        # - the plugin_stats message is empty
        # - the display tag = False
        if plugin_stats is None or not plugin_stats['msgdict'] or not plugin_stats['display']:
            # Exit
            return 0

        # Get the screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        # Set the upper/left position of the message
        if plugin_stats['align'] == 'right':
            # Right align (last column)
            display_x = screen_x - self.get_stats_display_width(plugin_stats)
        else:
            display_x = self.column
        if plugin_stats['align'] == 'bottom':
            # Bottom (last line)
            display_y = screen_y - self.get_stats_display_height(plugin_stats)
        else:
            display_y = self.line

        # Display
        x = display_x
        x_max = x
        y = display_y
        for m in plugin_stats['msgdict']:
            # New line
            if m['msg'].startswith('\n'):
                # Go to the next line
                y += 1
                # Return to the first column
                x = display_x
                continue
            # Do not display outside the screen
            if x < 0:
                continue
            if not m['splittable'] and (x + len(m['msg']) > screen_x):
                continue
            if y < 0 or (y + 1 > screen_y) or (y > max_y):
                break
            # If display_optional = False do not display optional stats
            if not display_optional and m['optional']:
                continue
            # If display_additional = False do not display additional stats
            if not display_additional and m['additional']:
                continue
            # Is it possible to display the stat with the current screen size
            # !!! Crach if not try/except... Why ???
            try:
                self.term_window.addnstr(y, x,
                                         m['msg'],
                                         # Do not disply outside the screen
                                         screen_x - x,
                                         self.colors_list[m['decoration']])
            except Exception:
                pass
            else:
                # New column
                # Python 2: we need to decode to get real screen size because
                # UTF-8 special tree chars occupy several bytes.
                # Python 3: strings are strings and bytes are bytes, all is
                # good.
                try:
                    x += len(u(m['msg']))
                except UnicodeDecodeError:
                    # Quick and dirty hack for issue #745
                    pass
                if x > x_max:
                    x_max = x

        # Compute the next Glances column/line position
        self.next_column = max(
            self.next_column, x_max + self.space_between_column)
        self.next_line = max(self.next_line, y + self.space_between_line)

        if not add_space and self.next_line > 0:
            # Do not have empty line after
            self.next_line -= 1

    def erase(self):
        """Erase the content of the screen."""
        self.term_window.erase()

    def flush(self, stats, cs_status=None):
        """Clear and update the screen.

        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        self.erase()
        self.display(stats, cs_status=cs_status)

    def update(self, stats, cs_status=None, return_to_browser=False):
        """Update the screen.

        Wait for __refresh_time sec / catch key every 100 ms.

        INPUT
        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        return_to_browser:
            True: Do not exist, return to the browser list
            False: Exit and return to the shell

        OUPUT
        True: Exit key has been pressed
        False: Others cases...
        """
        # Flush display
        self.flush(stats, cs_status=cs_status)

        # Wait
        exitkey = False
        countdown = Timer(self.__refresh_time)
        while not countdown.finished() and not exitkey:
            # Getkey
            pressedkey = self.__catch_key(return_to_browser=return_to_browser)
            # Is it an exit key ?
            exitkey = (pressedkey == ord('\x1b') or pressedkey == ord('q'))
            if not exitkey and pressedkey > -1:
                # Redraw display
                self.flush(stats, cs_status=cs_status)
            # Wait 100ms...
            self.wait()

        return exitkey

    def wait(self, delay=100):
        """Wait delay in ms"""
        curses.napms(100)

    def get_stats_display_width(self, curse_msg, without_option=False):
        """Return the width of the formatted curses message.

        The height is defined by the maximum line.
        """
        try:
            if without_option:
                # Size without options
                c = len(max(''.join([(re.sub(r'[^\x00-\x7F]+', ' ', i['msg']) if not i['optional'] else "")
                                     for i in curse_msg['msgdict']]).split('\n'), key=len))
            else:
                # Size with all options
                c = len(max(''.join([re.sub(r'[^\x00-\x7F]+', ' ', i['msg'])
                                     for i in curse_msg['msgdict']]).split('\n'), key=len))
        except Exception:
            return 0
        else:
            return c

    def get_stats_display_height(self, curse_msg):
        r"""Return the height of the formatted curses message.

        The height is defined by the number of '\n' (new line).
        """
        try:
            c = [i['msg'] for i in curse_msg['msgdict']].count('\n')
        except Exception:
            return 0
        else:
            return c + 1


class GlancesCursesStandalone(_GlancesCurses):

    """Class for the Glances curse standalone."""

    pass


class GlancesCursesClient(_GlancesCurses):

    """Class for the Glances curse client."""

    pass


if not WINDOWS:
    class GlancesTextbox(Textbox, object):

        def __init__(self, *args, **kwargs):
            super(GlancesTextbox, self).__init__(*args, **kwargs)

        def do_command(self, ch):
            if ch == 10:  # Enter
                return 0
            if ch == 127:  # Back
                return 8
            return super(GlancesTextbox, self).do_command(ch)

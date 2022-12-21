# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Curses interface class."""
from __future__ import unicode_literals

import sys

from glances.compat import nativestr, u, itervalues, enable, disable
from glances.globals import MACOS, WINDOWS
from glances.logger import logger
from glances.events import glances_events
from glances.processes import glances_processes, sort_processes_key_list
from glances.outputs.glances_unicode import unicode_message
from glances.timer import Timer

# Import curses library for "normal" operating system
try:
    import curses
    import curses.panel
    from curses.textpad import Textbox
except ImportError:
    logger.critical("Curses module not found. Glances cannot start in standalone mode.")
    if WINDOWS:
        logger.critical("For Windows you can try installing windows-curses with pip install.")
    sys.exit(1)


class _GlancesCurses(object):

    """This class manages the curses display (and key pressed).

    Note: It is a private class, use GlancesCursesClient or GlancesCursesBrowser.
    """

    _hotkeys = {
        # 'ENTER' > Edit the process filter
        '0': {'switch': 'disable_irix'},
        '1': {'switch': 'percpu'},
        '2': {'switch': 'disable_left_sidebar'},
        '3': {'switch': 'disable_quicklook'},
        # '4' > Enable or disable quicklook
        # '5' > Enable or disable top menu
        '6': {'switch': 'meangpu'},
        '9': {'switch': 'theme_white'},
        '/': {'switch': 'process_short_name'},
        'a': {'sort_key': 'auto'},
        'A': {'switch': 'disable_amps'},
        'b': {'switch': 'byte'},
        'B': {'switch': 'diskio_iops'},
        'c': {'sort_key': 'cpu_percent'},
        'C': {'switch': 'disable_cloud'},
        'd': {'switch': 'disable_diskio'},
        'D': {'switch': 'disable_docker'},
        # 'e' > Enable/Disable process extended
        # 'E' > Erase the process filter
        # 'f' > Show/hide fs / folder stats
        'F': {'switch': 'fs_free_space'},
        'g': {'switch': 'generate_graph'},
        'G': {'switch': 'disable_gpu'},
        'h': {'switch': 'help_tag'},
        'i': {'sort_key': 'io_counters'},
        'I': {'switch': 'disable_ip'},
        'j': {'switch': 'programs'},
        # 'k' > Kill selected process
        'K': {'switch': 'disable_connections'},
        'l': {'switch': 'disable_alert'},
        'm': {'sort_key': 'memory_percent'},
        'M': {'switch': 'reset_minmax_tag'},
        'n': {'switch': 'disable_network'},
        'N': {'switch': 'disable_now'},
        'p': {'sort_key': 'name'},
        'P': {'switch': 'disable_ports'},
        # 'q' or ESCAPE > Quit
        'Q': {'switch': 'enable_irq'},
        'r': {'switch': 'disable_smart'},
        'R': {'switch': 'disable_raid'},
        's': {'switch': 'disable_sensors'},
        'S': {'switch': 'sparkline'},
        't': {'sort_key': 'cpu_times'},
        'T': {'switch': 'network_sum'},
        'u': {'sort_key': 'username'},
        'U': {'switch': 'network_cumul'},
        # 'w' > Delete finished warning logs
        'W': {'switch': 'disable_wifi'},
        # 'x' > Delete finished warning and critical logs
        # 'z' > Enable or disable processes
        # '+' > Increase the process nice level
        # '-' > Decrease the process nice level
        # "<" (left arrow) navigation through process sort
        # ">" (right arrow) navigation through process sort
        # 'UP' > Up in the server list
        # 'DOWN' > Down in the server list
    }

    _sort_loop = sort_processes_key_list

    # Define top menu
    _top = ['quicklook', 'cpu', 'percpu', 'gpu', 'mem', 'memswap', 'load']
    _quicklook_max_width = 68

    # Define left sidebar
    _left_sidebar = [
        'network',
        'connections',
        'wifi',
        'ports',
        'diskio',
        'fs',
        'irq',
        'folders',
        'raid',
        'smart',
        'sensors',
        'now',
    ]
    _left_sidebar_min_width = 23
    _left_sidebar_max_width = 34

    # Define right sidebar
    _right_sidebar = ['docker', 'processcount', 'amps', 'processlist', 'alert']

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

        # Init edit filter tag
        self.edit_filter = False

        # Init nice increase/decrease tag
        self.increase_nice_process = False
        self.decrease_nice_process = False

        # Init kill process tag
        self.kill_process = False

        # Init the process min/max reset
        self.args.reset_minmax_tag = False

        # Init cursor
        self.args.cursor_position = 0

        # Catch key pressed with non blocking mode
        self.term_window.keypad(1)
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
        try:
            if hasattr(curses, 'start_color'):
                curses.start_color()
                logger.debug('Curses interface compatible with {} colors'.format(curses.COLORS))
            if hasattr(curses, 'use_default_colors'):
                curses.use_default_colors()
        except Exception as e:
            logger.warning('Error initializing terminal color ({})'.format(e))

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
            self.no_color = curses.color_pair(1)
            self.default_color = curses.color_pair(3) | A_BOLD
            self.nice_color = curses.color_pair(5)
            self.cpu_time_color = curses.color_pair(5)
            self.ifCAREFUL_color = curses.color_pair(4) | A_BOLD
            self.ifWARNING_color = curses.color_pair(5) | A_BOLD
            self.ifCRITICAL_color = curses.color_pair(2) | A_BOLD
            self.default_color2 = curses.color_pair(7)
            self.ifCAREFUL_color2 = curses.color_pair(8) | A_BOLD
            self.ifWARNING_color2 = curses.color_pair(5) | A_BOLD
            self.ifCRITICAL_color2 = curses.color_pair(6) | A_BOLD
            self.filter_color = A_BOLD
            self.selected_color = A_BOLD

            if curses.COLOR_PAIRS > 8:
                colors_list = [curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_YELLOW]
                for i in range(0, 3):
                    try:
                        curses.init_pair(i + 9, colors_list[i], -1)
                    except Exception:
                        if self.is_theme('white'):
                            curses.init_pair(i + 9, curses.COLOR_BLACK, -1)
                        else:
                            curses.init_pair(i + 9, curses.COLOR_WHITE, -1)
                self.nice_color = curses.color_pair(9)
                self.cpu_time_color = curses.color_pair(9)
                self.ifWARNING_color2 = curses.color_pair(9) | A_BOLD
                self.filter_color = curses.color_pair(10) | A_BOLD
                self.selected_color = curses.color_pair(11) | A_BOLD

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
            self.selected_color = A_BOLD

        # Define the colors list (hash table) for stats
        self.colors_list = {
            'DEFAULT': self.no_color,
            'UNDERLINE': curses.A_UNDERLINE,
            'BOLD': A_BOLD,
            'SORT': curses.A_UNDERLINE | A_BOLD,
            'OK': self.default_color2,
            'MAX': self.default_color2 | A_BOLD,
            'FILTER': self.filter_color,
            'TITLE': self.title_color,
            'PROCESS': self.default_color2,
            'PROCESS_SELECTED': self.default_color2 | curses.A_UNDERLINE,
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
            'PASSWORD': curses.A_PROTECT,
            'SELECTED': self.selected_color,
        }

    def set_cursor(self, value):
        """Configure the curse cursor appearance.

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
        # @TODO: Check issue #163
        ret = window.getch()
        return ret

    def __catch_key(self, return_to_browser=False):
        # Catch the pressed key
        self.pressedkey = self.get_key(self.term_window)
        if self.pressedkey == -1:
            return -1

        # Actions (available in the global hotkey dict)...
        logger.debug("Keypressed (code: {})".format(self.pressedkey))
        for hotkey in self._hotkeys:
            if self.pressedkey == ord(hotkey) and 'switch' in self._hotkeys[hotkey]:
                # Get the option name
                # Ex: disable_foo return foo
                #     enable_foo_bar return foo_bar
                option = '_'.join(self._hotkeys[hotkey]['switch'].split('_')[1:])
                if self._hotkeys[hotkey]['switch'].startswith('disable_'):
                    # disable_ switch
                    if getattr(self.args, self._hotkeys[hotkey]['switch']):
                        enable(self.args, option)
                    else:
                        disable(self.args, option)
                elif self._hotkeys[hotkey]['switch'].startswith('enable_'):
                    # enable_ switch
                    if getattr(self.args, self._hotkeys[hotkey]['switch']):
                        disable(self.args, option)
                    else:
                        enable(self.args, option)
                else:
                    # Others switchs options (with no enable_ or disable_)
                    setattr(
                        self.args,
                        self._hotkeys[hotkey]['switch'],
                        not getattr(self.args, self._hotkeys[hotkey]['switch']),
                    )
            if self.pressedkey == ord(hotkey) and 'sort_key' in self._hotkeys[hotkey]:
                glances_processes.set_sort_key(
                    self._hotkeys[hotkey]['sort_key'], self._hotkeys[hotkey]['sort_key'] == 'auto'
                )

        # Other actions...
        if self.pressedkey == ord('\n'):
            # 'ENTER' > Edit the process filter
            self.edit_filter = not self.edit_filter
        elif self.pressedkey == ord('4'):
            # '4' > Enable or disable quicklook
            self.args.full_quicklook = not self.args.full_quicklook
            if self.args.full_quicklook:
                self.enable_fullquicklook()
            else:
                self.disable_fullquicklook()
        elif self.pressedkey == ord('5'):
            # '5' > Enable or disable top menu
            self.args.disable_top = not self.args.disable_top
            if self.args.disable_top:
                self.disable_top()
            else:
                self.enable_top()
        elif self.pressedkey == ord('9'):
            # '9' > Theme from black to white and reverse
            self._init_colors()
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
        elif self.pressedkey == ord('+'):
            # '+' > Increase process nice level
            self.increase_nice_process = not self.increase_nice_process
        elif self.pressedkey == ord('-'):
            # '+' > Decrease process nice level
            self.decrease_nice_process = not self.decrease_nice_process
        elif self.pressedkey == ord('k'):
            # 'k' > Kill selected process (after confirmation)
            self.kill_process = not self.kill_process
        elif self.pressedkey == ord('w'):
            # 'w' > Delete finished warning logs
            glances_events.clean()
        elif self.pressedkey == ord('x'):
            # 'x' > Delete finished warning and critical logs
            glances_events.clean(critical=True)
        elif self.pressedkey == ord('z'):
            # 'z' > Enable or disable processes
            self.args.disable_process = not self.args.disable_process
            if self.args.disable_process:
                glances_processes.disable()
            else:
                glances_processes.enable()
        elif self.pressedkey == curses.KEY_LEFT:
            # "<" (left arrow) navigation through process sort
            next_sort = (self.loop_position() - 1) % len(self._sort_loop)
            glances_processes.set_sort_key(self._sort_loop[next_sort], False)
        elif self.pressedkey == curses.KEY_RIGHT:
            # ">" (right arrow) navigation through process sort
            next_sort = (self.loop_position() + 1) % len(self._sort_loop)
            glances_processes.set_sort_key(self._sort_loop[next_sort], False)
        elif self.pressedkey == curses.KEY_UP or self.pressedkey == 65:
            # 'UP' > Up in the server list
            if self.args.cursor_position > 0:
                self.args.cursor_position -= 1
        elif self.pressedkey == curses.KEY_DOWN or self.pressedkey == 66:
            # 'DOWN' > Down in the server list
            # if self.args.cursor_position < glances_processes.max_processes - 2:
            if self.args.cursor_position < glances_processes.processes_count:
                self.args.cursor_position += 1
        elif self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            if return_to_browser:
                logger.info("Stop Glances client and return to the browser")
            else:
                logger.info("Stop Glances (keypressed: {})".format(self.pressedkey))
        elif self.pressedkey == curses.KEY_F5:
            # "F5" manual refresh requested
            pass

        # Return the key code
        return self.pressedkey

    def loop_position(self):
        """Return the current sort in the loop"""
        for i, v in enumerate(self._sort_loop):
            if v == glances_processes.sort_key:
                return i
        return 0

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

    def new_line(self, separator=False):
        """New line in the curses interface."""
        self.line = self.next_line

    def new_column(self):
        """New column in the curses interface."""
        self.column = self.next_column

    def separator_line(self, color='TITLE'):
        """New separator line in the curses interface."""
        if not self.args.enable_separator:
            return
        self.new_line()
        self.line -= 1
        line_width = self.term_window.getmaxyx()[1] - self.column
        self.term_window.addnstr(
            self.line,
            self.column,
            unicode_message('MEDIUM_LINE', self.args) * line_width,
            line_width,
            self.colors_list[color],
        )

    def __get_stat_display(self, stats, layer):
        """Return a dict of dict with all the stats display.
        # TODO: Drop extra parameter

        :param stats: Global stats dict
        :param layer: ~ cs_status
            "None": standalone or server mode
            "Connected": Client is connected to a Glances server
            "SNMP": Client is connected to a SNMP server
            "Disconnected": Client is disconnected from the server

        :returns: dict of dict
            * key: plugin name
            * value: dict returned by the get_stats_display Plugin method
        """
        ret = {}

        for p in stats.getPluginsList(enable=False):
            if p == 'quicklook' or p == 'processlist':
                # processlist is done later
                # because we need to know how many processes could be displayed
                continue

            # Compute the plugin max size
            plugin_max_width = None
            if p in self._left_sidebar:
                plugin_max_width = max(self._left_sidebar_min_width, self.term_window.getmaxyx()[1] - 105)
                plugin_max_width = min(self._left_sidebar_max_width, plugin_max_width)

            # Get the view
            ret[p] = stats.get_plugin(p).get_stats_display(args=self.args, max_width=plugin_max_width)

        return ret

    def display(self, stats, cs_status=None):
        """Display stats on the screen.

        :param stats: Stats database to display
        :param cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to a Glances server
            "SNMP": Client is connected to a SNMP server
            "Disconnected": Client is disconnected from the server

        :return: True if the stats have been displayed else False if the help have been displayed
        """
        # Init the internal line/column for Glances Curses
        self.init_line_column()

        # Update the stats messages
        ###########################

        # Get all the plugins but quicklook and process list
        self.args.cs_status = cs_status
        __stat_display = self.__get_stat_display(stats, layer=cs_status)

        # Adapt number of processes to the available space
        max_processes_displayed = (
            self.term_window.getmaxyx()[0]
            - 11
            - (0 if 'docker' not in __stat_display else self.get_stats_display_height(__stat_display["docker"]))
            - (
                0
                if 'processcount' not in __stat_display
                else self.get_stats_display_height(__stat_display["processcount"])
            )
            - (0 if 'amps' not in __stat_display else self.get_stats_display_height(__stat_display["amps"]))
            - (0 if 'alert' not in __stat_display else self.get_stats_display_height(__stat_display["alert"]))
        )

        try:
            if self.args.enable_process_extended:
                max_processes_displayed -= 4
        except AttributeError:
            pass
        if max_processes_displayed < 0:
            max_processes_displayed = 0
        if glances_processes.max_processes is None or glances_processes.max_processes != max_processes_displayed:
            logger.debug("Set number of displayed processes to {}".format(max_processes_displayed))
            glances_processes.max_processes = max_processes_displayed

        # Get the processlist
        __stat_display["processlist"] = stats.get_plugin('processlist').get_stats_display(args=self.args)

        # Display the stats on the curses interface
        ###########################################

        # Help screen (on top of the other stats)
        if self.args.help_tag:
            # Display the stats...
            self.display_plugin(stats.get_plugin('help').get_stats_display(args=self.args))
            # ... and exit
            return False

        # =====================================
        # Display first line (system+ip+uptime)
        # Optionally: Cloud on second line
        # =====================================
        self.__display_header(__stat_display)
        self.separator_line()

        # ==============================================================
        # Display second line (<SUMMARY>+CPU|PERCPU+<GPU>+LOAD+MEM+SWAP)
        # ==============================================================
        self.__display_top(__stat_display, stats)
        self.init_column()
        self.separator_line()

        # ==================================================================
        # Display left sidebar (NETWORK+PORTS+DISKIO+FS+SENSORS+Current time)
        # ==================================================================
        self.__display_left(__stat_display)

        # ====================================
        # Display right stats (process and co)
        # ====================================
        self.__display_right(__stat_display)

        # =====================
        # Others popup messages
        # =====================

        # Display edit filter popup
        # Only in standalone mode (cs_status is None)
        if self.edit_filter and cs_status is None:
            new_filter = self.display_popup(
                'Process filter pattern: \n\n'
                + 'Examples:\n'
                + '- .*python.*\n'
                + '- /usr/lib.*\n'
                + '- name:.*nautilus.*\n'
                + '- cmdline:.*glances.*\n'
                + '- username:nicolargo\n'
                + '- username:^root        ',
                popup_type='input',
                input_value=glances_processes.process_filter_input,
            )
            glances_processes.process_filter = new_filter
        elif self.edit_filter and cs_status is not None:
            self.display_popup('Process filter only available in standalone mode')
        self.edit_filter = False

        # Manage increase/decrease nice level of the selected process
        # Only in standalone mode (cs_status is None)
        if self.increase_nice_process and cs_status is None:
            self.nice_increase(stats.get_plugin('processlist').get_raw()[self.args.cursor_position])
        self.increase_nice_process = False
        if self.decrease_nice_process and cs_status is None:
            self.nice_decrease(stats.get_plugin('processlist').get_raw()[self.args.cursor_position])
        self.decrease_nice_process = False

        # Display kill process confirmation popup
        # Only in standalone mode (cs_status is None)
        if self.kill_process and cs_status is None:
            self.kill(stats.get_plugin('processlist').get_raw()[self.args.cursor_position])
        elif self.kill_process and cs_status is not None:
            self.display_popup('Kill process only available for local processes')
        self.kill_process = False

        # Display graph generation popup
        if self.args.generate_graph:
            self.display_popup('Generate graph in {}'.format(self.args.export_graph_path))

        return True

    def nice_increase(self, process):
        glances_processes.nice_increase(process['pid'])

    def nice_decrease(self, process):
        glances_processes.nice_decrease(process['pid'])

    def kill(self, process):
        """Kill a process, or a list of process if the process has a childrens field.

        :param process
        :return: None
        """
        logger.debug("Selected process to kill: {}".format(process))

        if 'childrens' in process:
            pid_to_kill = process['childrens']
        else:
            pid_to_kill = [process['pid']]

        confirm = self.display_popup(
            'Kill process: {} (pid: {}) ?\n\nConfirm ([y]es/[n]o): '.format(
                process['name'],
                ', '.join(map(str, pid_to_kill)),
            ),
            popup_type='yesno',
        )

        if confirm.lower().startswith('y'):
            for pid in pid_to_kill:
                try:
                    ret_kill = glances_processes.kill(pid)
                except Exception as e:
                    logger.error('Can not kill process {} ({})'.format(pid, e))
                else:
                    logger.info('Kill signal has been sent to process {} (return code: {})'.format(pid, ret_kill))

    def __display_header(self, stat_display):
        """Display the firsts lines (header) in the Curses interface.

        system + ip + uptime
        (cloud)
        """
        # First line
        self.new_line()
        self.space_between_column = 0
        l_uptime = 1
        for i in ['system', 'ip', 'uptime']:
            if i in stat_display:
                l_uptime += self.get_stats_display_width(stat_display[i])
        self.display_plugin(stat_display["system"], display_optional=(self.term_window.getmaxyx()[1] >= l_uptime))
        self.space_between_column = 3
        if 'ip' in stat_display:
            self.new_column()
            self.display_plugin(stat_display["ip"], display_optional=(self.term_window.getmaxyx()[1] >= 100))
        self.new_column()
        self.display_plugin(
            stat_display["uptime"], add_space=-(self.get_stats_display_width(stat_display["cloud"]) != 0)
        )
        self.init_column()
        if self.get_stats_display_width(stat_display["cloud"]) != 0:
            # Second line (optional)
            self.new_line()
            self.display_plugin(stat_display["cloud"])

    def __display_top(self, stat_display, stats):
        """Display the second line in the Curses interface.

        <QUICKLOOK> + CPU|PERCPU + <GPU> + MEM + SWAP + LOAD
        """
        self.init_column()
        self.new_line()

        # Init quicklook
        stat_display['quicklook'] = {'msgdict': []}

        # Dict for plugins width
        plugin_widths = {}
        for p in self._top:
            plugin_widths[p] = (
                self.get_stats_display_width(stat_display.get(p, 0)) if hasattr(self.args, 'disable_' + p) else 0
            )

        # Width of all plugins
        stats_width = sum(itervalues(plugin_widths))

        # Number of plugin but quicklook
        stats_number = sum(
            [int(stat_display[p]['msgdict'] != []) for p in self._top if not getattr(self.args, 'disable_' + p)]
        )

        if not self.args.disable_quicklook:
            # Quick look is in the place !
            if self.args.full_quicklook:
                quicklook_width = self.term_window.getmaxyx()[1] - (
                    stats_width + 8 + stats_number * self.space_between_column
                )
            else:
                quicklook_width = min(
                    self.term_window.getmaxyx()[1] - (stats_width + 8 + stats_number * self.space_between_column),
                    self._quicklook_max_width - 5,
                )
            try:
                stat_display["quicklook"] = stats.get_plugin('quicklook').get_stats_display(
                    max_width=quicklook_width, args=self.args
                )
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
        for p in self._top:
            plugin_display_optional[p] = True
        if stats_number > 1:
            self.space_between_column = max(1, int((self.term_window.getmaxyx()[1] - stats_width) / (stats_number - 1)))
            for p in ['mem', 'cpu']:
                # No space ? Remove optional stats
                if self.space_between_column < 3:
                    plugin_display_optional[p] = False
                    plugin_widths[p] = (
                        self.get_stats_display_width(stat_display[p], without_option=True)
                        if hasattr(self.args, 'disable_' + p)
                        else 0
                    )
                    stats_width = sum(itervalues(plugin_widths)) + 1
                    self.space_between_column = max(
                        1, int((self.term_window.getmaxyx()[1] - stats_width) / (stats_number - 1))
                    )
        else:
            self.space_between_column = 0

        # Display CPU, MEM, SWAP and LOAD
        for p in self._top:
            if p == 'quicklook':
                continue
            if p in stat_display:
                self.display_plugin(stat_display[p], display_optional=plugin_display_optional[p])
            if p != 'load':
                # Skip last column
                self.new_column()

        # Space between column
        self.space_between_column = 3

        # Backup line position
        self.saved_line = self.next_line

    def __display_left(self, stat_display):
        """Display the left sidebar in the Curses interface."""
        self.init_column()

        if self.args.disable_left_sidebar:
            return

        for p in self._left_sidebar:
            if (hasattr(self.args, 'enable_' + p) or hasattr(self.args, 'disable_' + p)) and p in stat_display:
                self.new_line()
                self.display_plugin(stat_display[p])

    def __display_right(self, stat_display):
        """Display the right sidebar in the Curses interface.

        docker + processcount + amps + processlist + alert
        """
        # Do not display anything if space is not available...
        if self.term_window.getmaxyx()[1] < self._left_sidebar_min_width:
            return

        # Restore line position
        self.next_line = self.saved_line

        # Display right sidebar
        self.new_column()
        for p in self._right_sidebar:
            if (hasattr(self.args, 'enable_' + p) or hasattr(self.args, 'disable_' + p)) and p in stat_display:
                if p not in p:
                    # Catch for issue #1470
                    continue
                self.new_line()
                if p == 'processlist':
                    self.display_plugin(
                        stat_display['processlist'],
                        display_optional=(self.term_window.getmaxyx()[1] > 102),
                        display_additional=(not MACOS),
                        max_y=(
                            self.term_window.getmaxyx()[0] - self.get_stats_display_height(stat_display['alert']) - 2
                        ),
                    )
                else:
                    self.display_plugin(stat_display[p])

    def display_popup(
        self, message, size_x=None, size_y=None, duration=3, popup_type='info', input_size=30, input_value=None
    ):
        """
        Display a centered popup.

         popup_type: ='info'
         Just an information popup, no user interaction
         Display a centered popup with the given message during duration seconds
         If size_x and size_y: set the popup size
         else set it automatically
         Return True if the popup could be displayed

        popup_type='input'
         Display a centered popup with the given message and a input field
         If size_x and size_y: set the popup size
         else set it automatically
         Return the input string or None if the field is empty

        popup_type='yesno'
         Display a centered popup with the given message
         If size_x and size_y: set the popup size
         else set it automatically
         Return True (yes) or False (no)
        """
        # Center the popup
        sentence_list = message.split('\n')
        if size_x is None:
            size_x = len(max(sentence_list, key=len)) + 4
            # Add space for the input field
            if popup_type == 'input':
                size_x += input_size
        if size_y is None:
            size_y = len(sentence_list) + 4
        screen_x = self.term_window.getmaxyx()[1]
        screen_y = self.term_window.getmaxyx()[0]
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
        for y, m in enumerate(sentence_list):
            popup.addnstr(2 + y, 2, m, len(m))

        if popup_type == 'info':
            # Display the popup
            popup.refresh()
            self.wait(duration * 1000)
            return True
        elif popup_type == 'input':
            # Create a sub-window for the text field
            sub_pop = popup.derwin(1, input_size, 2, 2 + len(m))
            sub_pop.attron(self.colors_list['FILTER'])
            # Init the field with the current value
            if input_value is not None:
                sub_pop.addnstr(0, 0, input_value, len(input_value))
            # Display the popup
            popup.refresh()
            sub_pop.refresh()
            # Create the textbox inside the sub-windows
            self.set_cursor(2)
            self.term_window.keypad(1)
            textbox = GlancesTextbox(sub_pop, insert_mode=True)
            textbox.edit()
            self.set_cursor(0)
            # self.term_window.keypad(0)
            if textbox.gather() != '':
                logger.debug("User enters the following string: %s" % textbox.gather())
                return textbox.gather()[:-1]
            else:
                logger.debug("User centers an empty string")
                return None
        elif popup_type == 'yesno':
            # # Create a sub-window for the text field
            sub_pop = popup.derwin(1, 2, len(sentence_list) + 1, len(m) + 2)
            sub_pop.attron(self.colors_list['FILTER'])
            # Init the field with the current value
            sub_pop.addnstr(0, 0, '', 0)
            # Display the popup
            popup.refresh()
            sub_pop.refresh()
            # Create the textbox inside the sub-windows
            self.set_cursor(2)
            self.term_window.keypad(1)
            textbox = GlancesTextboxYesNo(sub_pop, insert_mode=False)
            textbox.edit()
            self.set_cursor(0)
            # self.term_window.keypad(0)
            return textbox.gather()

    def display_plugin(self, plugin_stats, display_optional=True, display_additional=True, max_y=65535, add_space=0):
        """Display the plugin_stats on the screen.

        :param plugin_stats:
        :param display_optional: display the optional stats if True
        :param display_additional: display additional stats if True
        :param max_y: do not display line > max_y
        :param add_space: add x space (line) after the plugin
        """
        # Exit if:
        # - the plugin_stats message is empty
        # - the display tag = False
        if plugin_stats is None or not plugin_stats['msgdict'] or not plugin_stats['display']:
            # Exit
            return 0

        # Get the screen size
        screen_x = self.term_window.getmaxyx()[1]
        screen_y = self.term_window.getmaxyx()[0]

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
            try:
                if m['msg'].startswith('\n'):
                    # Go to the next line
                    y += 1
                    # Return to the first column
                    x = display_x
                    continue
            except:
                # Avoid exception (see issue #1692)
                pass
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
            # !!! Crash if not try/except... Why ???
            try:
                self.term_window.addnstr(
                    y,
                    x,
                    m['msg'],
                    # Do not display outside the screen
                    screen_x - x,
                    self.colors_list[m['decoration']],
                )
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
        self.next_column = max(self.next_column, x_max + self.space_between_column)
        self.next_line = max(self.next_line, y + self.space_between_line)

        # Have empty lines after the plugins
        self.next_line += add_space

    def erase(self):
        """Erase the content of the screen."""
        self.term_window.clear()

    def flush(self, stats, cs_status=None):
        """Clear and update the screen.

        :param stats: Stats database to display
        :param cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        self.erase()
        self.display(stats, cs_status=cs_status)

    def update(self, stats, duration=3, cs_status=None, return_to_browser=False):
        """Update the screen.

        :param stats: Stats database to display
        :param duration: duration of the loop
        :param cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        :param return_to_browser:
            True: Do not exist, return to the browser list
            False: Exit and return to the shell

        :return: True if exit key has been pressed else False
        """
        # Flush display
        self.flush(stats, cs_status=cs_status)

        # If the duration is < 0 (update + export time > refresh_time)
        # Then display the interface and log a message
        if duration <= 0:
            logger.warning('Update and export time higher than refresh_time.')
            duration = 0.1

        # Wait duration (in s) time
        isexitkey = False
        countdown = Timer(duration)
        # Set the default timeout (in ms) between two getch
        self.term_window.timeout(100)
        while not countdown.finished() and not isexitkey:
            # Getkey
            pressedkey = self.__catch_key(return_to_browser=return_to_browser)
            isexitkey = pressedkey == ord('\x1b') or pressedkey == ord('q')

            if pressedkey == curses.KEY_F5:
                # Were asked to refresh
                return isexitkey

            if pressedkey in (curses.KEY_UP, 65, curses.KEY_DOWN, 66):
                # Up of won key pressed, reset the countdown
                # Better for user experience
                countdown.reset()

            if isexitkey and self.args.help_tag:
                # Quit from help should return to main screen, not exit #1874
                self.args.help_tag = not self.args.help_tag
                isexitkey = False
                return isexitkey

            if not isexitkey and pressedkey > -1:
                # Redraw display
                self.flush(stats, cs_status=cs_status)
                # Overwrite the timeout with the countdown
                self.wait(delay=int(countdown.get() * 1000))

        return isexitkey

    def wait(self, delay=100):
        """Wait delay in ms"""
        curses.napms(100)

    def get_stats_display_width(self, curse_msg, without_option=False):
        """Return the width of the formatted curses message."""
        try:
            if without_option:
                # Size without options
                c = len(
                    max(
                        ''.join(
                            [
                                (u(u(nativestr(i['msg'])).encode('ascii', 'replace')) if not i['optional'] else "")
                                for i in curse_msg['msgdict']
                            ]
                        ).split('\n'),
                        key=len,
                    )
                )
            else:
                # Size with all options
                c = len(
                    max(
                        ''.join(
                            [u(u(nativestr(i['msg'])).encode('ascii', 'replace')) for i in curse_msg['msgdict']]
                        ).split('\n'),
                        key=len,
                    )
                )
        except Exception as e:
            logger.debug('ERROR: Can not compute plugin width ({})'.format(e))
            return 0
        else:
            return c

    def get_stats_display_height(self, curse_msg):
        """Return the height of the formatted curses message.

        The height is defined by the number of '\n' (new line).
        """
        try:
            c = [i['msg'] for i in curse_msg['msgdict']].count('\n')
        except Exception as e:
            logger.debug('ERROR: Can not compute plugin height ({})'.format(e))
            return 0
        else:
            return c + 1


class GlancesCursesStandalone(_GlancesCurses):

    """Class for the Glances curse standalone."""


class GlancesCursesClient(_GlancesCurses):

    """Class for the Glances curse client."""


class GlancesTextbox(Textbox, object):
    def __init__(self, *args, **kwargs):
        super(GlancesTextbox, self).__init__(*args, **kwargs)

    def do_command(self, ch):
        if ch == 10:  # Enter
            return 0
        if ch == 127:  # Back
            return 8
        return super(GlancesTextbox, self).do_command(ch)


class GlancesTextboxYesNo(Textbox, object):
    def __init__(self, *args, **kwargs):
        super(GlancesTextboxYesNo, self).__init__(*args, **kwargs)

    def do_command(self, ch):
        return super(GlancesTextboxYesNo, self).do_command(ch)

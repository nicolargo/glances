#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Curses interface class."""

import getpass
import sys

from glances.events_list import glances_events
from glances.globals import MACOS, WINDOWS, disable, enable, itervalues, nativestr, u
from glances.logger import logger
from glances.outputs.glances_colors import GlancesColors
from glances.outputs.glances_unicode import unicode_message
from glances.processes import glances_processes, sort_processes_stats_list
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


class _GlancesCurses:
    """This class manages the curses display (and key pressed).

    Note: It is a private class, use GlancesCursesClient or GlancesCursesBrowser.
    """

    _hotkeys = {
        '\n': {'handler': '_handle_enter'},
        '0': {'switch': 'disable_irix'},
        '1': {'switch': 'percpu'},
        '2': {'switch': 'disable_left_sidebar'},
        '3': {'switch': 'disable_quicklook'},
        '4': {'handler': '_handle_quicklook'},
        '5': {'handler': '_handle_top_menu'},
        '6': {'switch': 'meangpu'},
        '/': {'switch': 'process_short_name'},
        'a': {'sort_key': 'auto'},
        'A': {'switch': 'disable_amps'},
        'b': {'switch': 'byte'},
        'B': {'switch': 'diskio_iops'},
        'c': {'sort_key': 'cpu_percent'},
        'C': {'switch': 'disable_cloud'},
        'd': {'switch': 'disable_diskio'},
        'D': {'switch': 'disable_containers'},
        # 'e' > Enable/Disable process extended
        'E': {'handler': '_handle_erase_filter'},
        'f': {'handler': '_handle_fs_stats'},
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
        'V': {'switch': 'disable_vms'},
        'w': {'handler': '_handle_clean_logs'},
        'W': {'switch': 'disable_wifi'},
        'x': {'handler': '_handle_clean_critical_logs'},
        'z': {'handler': '_handle_disable_process'},
        '+': {'handler': '_handle_increase_nice'},
        '-': {'handler': '_handle_decrease_nice'},
        # "<" (left arrow) navigation through process sort
        # ">" (right arrow) navigation through process sort
        # 'UP' > Up in the server list
        # 'DOWN' > Down in the server list
    }

    _sort_loop = sort_processes_stats_list

    # Define top menu
    _top = ['quicklook', 'cpu', 'percpu', 'gpu', 'mem', 'memswap', 'load']
    _quicklook_max_width = 58

    # Define left sidebar
    # This variable is used in the make webui task in order to generate the
    # glances/outputs/static/js/uiconfig.json file for the web interface
    # This lidt can also be overwritten by the configuration file ([outputs] left_menu option)
    _left_sidebar = [
        'network',
        'ports',
        'wifi',
        'connections',
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

    # Define right sidebar in a method because it depends of self.args.programs
    # See def _right_sidebar method

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
        try:
            self.screen = curses.initscr()
            if not self.screen:
                logger.critical("Cannot init the curses library.\n")
                sys.exit(1)
            else:
                logger.debug(f"Curses library initialized with term: {curses.longname()}")
        except Exception as e:
            if args.export:
                logger.info("Cannot init the curses library, quiet mode on and export.")
                args.quiet = True
                return

            logger.critical(f"Cannot init the curses library ({e})")
            sys.exit(1)

        # Load configuration file
        self.load_config(config)

        # Init cursor
        self._init_cursor()

        # Init the colors
        self.colors_list = GlancesColors(args).get()

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
        if config is not None and config.has_section('outputs'):
            logger.debug('Read the outputs section in the configuration file')
            # Separator
            self.args.enable_separator = config.get_bool_value(
                'outputs', 'separator', default=self.args.enable_separator
            )
            # Set the left sidebar list
            self._left_sidebar = config.get_list_value('outputs', 'left_menu', default=self._left_sidebar)

    def _right_sidebar(self):
        return [
            'vms',
            'containers',
            'processcount',
            'amps',
            'programlist' if self.args.programs else 'processlist',
            'alert',
        ]

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
        # TODO: Check issue #163
        return window.getch()

    def catch_actions_from_hotkey(self, hotkey):
        if self.pressedkey == ord(hotkey) and 'switch' in self._hotkeys[hotkey]:
            self._handle_switch(hotkey)
        elif self.pressedkey == ord(hotkey) and 'sort_key' in self._hotkeys[hotkey]:
            self._handle_sort_key(hotkey)
        if self.pressedkey == ord(hotkey) and 'handler' in self._hotkeys[hotkey]:
            action = getattr(self, self._hotkeys[hotkey]['handler'])
            action()

    def catch_other_actions_maybe_return_to_browser(self, return_to_browser):
        if self.pressedkey == ord('e') and not self.args.programs:
            self._handle_process_extended()
        elif self.pressedkey == ord('k') and not self.args.disable_cursor:
            self._handle_kill_process()
        elif self.pressedkey == curses.KEY_LEFT:
            self._handle_sort_left()
        elif self.pressedkey == curses.KEY_RIGHT:
            self._handle_sort_right()
        elif self.pressedkey == curses.KEY_UP or self.pressedkey == 65 and not self.args.disable_cursor:
            self._handle_cursor_up()
        elif self.pressedkey == curses.KEY_DOWN or self.pressedkey == 66 and not self.args.disable_cursor:
            self._handle_cursor_down()
        elif self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            self._handle_quit(return_to_browser)
        elif self.pressedkey == curses.KEY_F5 or self.pressedkey == 18:
            self._handle_refresh()

    def __catch_key(self, return_to_browser=False):
        # Catch the pressed key
        self.pressedkey = self.get_key(self.term_window)
        if self.pressedkey == -1:
            return self.pressedkey

        # Actions (available in the global hotkey dict)...
        logger.debug(f"Keypressed (code: {self.pressedkey})")
        [self.catch_actions_from_hotkey(hotkey) for hotkey in self._hotkeys]

        # Other actions with key > 255 (ord will not work) and/or additional test...
        self.catch_other_actions_maybe_return_to_browser(return_to_browser)

        # Return the key code
        return self.pressedkey

    def _handle_switch(self, hotkey):
        option = '_'.join(self._hotkeys[hotkey]['switch'].split('_')[1:])
        if self._hotkeys[hotkey]['switch'].startswith('disable_'):
            if getattr(self.args, self._hotkeys[hotkey]['switch']):
                enable(self.args, option)
            else:
                disable(self.args, option)
        elif self._hotkeys[hotkey]['switch'].startswith('enable_'):
            if getattr(self.args, self._hotkeys[hotkey]['switch']):
                disable(self.args, option)
            else:
                enable(self.args, option)
        else:
            setattr(
                self.args,
                self._hotkeys[hotkey]['switch'],
                not getattr(self.args, self._hotkeys[hotkey]['switch']),
            )

    def _handle_sort_key(self, hotkey):
        glances_processes.set_sort_key(self._hotkeys[hotkey]['sort_key'], self._hotkeys[hotkey]['sort_key'] == 'auto')

    def _handle_enter(self):
        self.edit_filter = not self.edit_filter

    def _handle_quicklook(self):
        self.args.full_quicklook = not self.args.full_quicklook
        if self.args.full_quicklook:
            self.enable_fullquicklook()
        else:
            self.disable_fullquicklook()

    def _handle_top_menu(self):
        self.args.disable_top = not self.args.disable_top
        if self.args.disable_top:
            self.disable_top()
        else:
            self.enable_top()

    def _handle_process_extended(self):
        self.args.enable_process_extended = not self.args.enable_process_extended
        if not self.args.enable_process_extended:
            glances_processes.disable_extended()
        else:
            glances_processes.enable_extended()
        self.args.disable_cursor = self.args.enable_process_extended and self.args.is_standalone

    def _handle_erase_filter(self):
        glances_processes.process_filter = None

    def _handle_fs_stats(self):
        self.args.disable_fs = not self.args.disable_fs
        self.args.disable_folders = not self.args.disable_folders

    def _handle_increase_nice(self):
        self.increase_nice_process = not self.increase_nice_process

    def _handle_decrease_nice(self):
        self.decrease_nice_process = not self.decrease_nice_process

    def _handle_kill_process(self):
        self.kill_process = not self.kill_process

    def _handle_clean_logs(self):
        glances_events.clean()

    def _handle_clean_critical_logs(self):
        glances_events.clean(critical=True)

    def _handle_disable_process(self):
        self.args.disable_process = not self.args.disable_process
        if self.args.disable_process:
            glances_processes.disable()
        else:
            glances_processes.enable()

    def _handle_sort_left(self):
        next_sort = (self.loop_position() - 1) % len(self._sort_loop)
        glances_processes.set_sort_key(self._sort_loop[next_sort], False)

    def _handle_sort_right(self):
        next_sort = (self.loop_position() + 1) % len(self._sort_loop)
        glances_processes.set_sort_key(self._sort_loop[next_sort], False)

    def _handle_cursor_up(self):
        if self.args.cursor_position > 0:
            self.args.cursor_position -= 1

    def _handle_cursor_down(self):
        if self.args.cursor_position < glances_processes.processes_count:
            self.args.cursor_position += 1

    def _handle_quit(self, return_to_browser):
        if return_to_browser:
            logger.info("Stop Glances client and return to the browser")
        else:
            logger.info(f"Stop Glances (keypressed: {self.pressedkey})")

    def _handle_refresh(self):
        glances_processes.reset_internal_cache()

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
        try:
            curses.curs_set(1)
        except Exception:
            pass
        try:
            curses.endwin()
        except Exception:
            pass

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

    def separator_line(self, color='SEPARATOR'):
        """Add a separator line in the curses interface."""
        if not self.args.enable_separator:
            return
        self.new_line()
        self.line -= 1
        line_width = self.term_window.getmaxyx()[1] - self.column
        if self.line >= 0 and self.line < self.term_window.getmaxyx()[0]:
            position = [self.line, self.column]
            line_color = self.colors_list[color]
            line_type = curses.ACS_HLINE if not self.args.disable_unicode else unicode_message('MEDIUM_LINE', self.args)
            self.term_window.hline(
                *position,
                line_type,
                line_width,
                line_color,
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
            # Ignore Quicklook because it is compute later in __display_top
            if p == 'quicklook':
                continue

            # Compute the plugin max size for the left sidebar
            plugin_max_width = None
            if p in self._left_sidebar:
                plugin_max_width = min(
                    self._left_sidebar_max_width,
                    max(self._left_sidebar_min_width, self.term_window.getmaxyx()[1] - 105),
                )

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

        # Get all the plugins view
        self.args.cs_status = cs_status
        __stat_display = self.__get_stat_display(stats, layer=cs_status)

        # Display the stats on the curses interface
        ###########################################

        # Help screen (on top of the other stats)
        if self.args.help_tag:
            # Display the stats...
            self.display_plugin(stats.get_plugin('help').get_stats_display(args=self.args))
            # ... and exit
            return False

        # =======================================
        # Display first line (system+ip+uptime)
        # Optionally: Cloud is on the second line
        # =======================================
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
            if 'graph' in stats.getExportsList():
                self.display_popup(f'Generate graph in {self.args.export_graph_path}')
            else:
                logger.warning('Graph export module is disable. Run Glances with --export graph to enable it.')
                self.args.generate_graph = False

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
        logger.debug(f"Selected process to kill: {process}")

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
                    logger.error(f'Can not kill process {pid} ({e})')
                else:
                    logger.info(f'Kill signal has been sent to process {pid} (return code: {ret_kill})')

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
                logger.debug(f"Quicklook plugin not available ({e})")
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
                if p == 'sensors':
                    self.display_plugin(
                        stat_display['sensors'],
                        max_y=(self.term_window.getmaxyx()[0] - self.get_stats_display_height(stat_display['now']) - 2),
                    )
                else:
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
        for p in self._right_sidebar():
            if (hasattr(self.args, 'enable_' + p) or hasattr(self.args, 'disable_' + p)) and p in stat_display:
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
        self,
        message,
        size_x=None,
        size_y=None,
        duration=3,
        popup_type='info',
        input_size=30,
        input_value=None,
        is_password=False,
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
            if m:
                popup.addnstr(2 + y, 2, m, len(m))

        if popup_type == 'info':
            # Display the popup
            popup.refresh()
            self.wait(duration * 1000)
            return True

        if popup_type == 'input':
            logger.info(popup_type)
            logger.info(is_password)
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
            if is_password:
                textbox = getpass.getpass('')
                self.set_cursor(0)
                if textbox != '':
                    return textbox
                return None

            # No password
            textbox = GlancesTextbox(sub_pop, insert_mode=True)
            textbox.edit()
            self.set_cursor(0)
            if textbox.gather() != '':
                return textbox.gather()[:-1]
            return None

        if popup_type == 'yesno':
            # Create a sub-window for the text field
            sub_pop = popup.derwin(1, 2, len(sentence_list) + 1, len(m) + 2)
            sub_pop.attron(self.colors_list['FILTER'])
            # Init the field with the current value
            try:
                sub_pop.addnstr(0, 0, '', 0)
            except curses.error:
                pass
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

        return None

    def setup_upper_left_pos(self, plugin_stats):
        screen_y, screen_x = self.term_window.getmaxyx()

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

        return display_y, display_x

    def get_next_x_and_x_max(self, m, x, x_max):
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

        return x, x_max

    def display_stats_with_current_size(self, m, y, x):
        screen_x = self.term_window.getmaxyx()[1]
        self.term_window.addnstr(
            y,
            x,
            m['msg'],
            # Do not display outside the screen
            screen_x - x,
            self.colors_list[m['decoration']],
        )

    def display_stats(self, plugin_stats, init, helper):
        y, x, x_max = init
        for m in plugin_stats['msgdict']:
            # New line
            try:
                if m['msg'].startswith('\n'):
                    y, x = helper['goto next, add first col'](y, x)
                    continue
            except Exception:
                # Avoid exception (see issue #1692)
                pass
            # Do not display outside the screen
            if x < 0:
                continue
            if helper['x overbound?'](m, x):
                continue
            if helper['y overbound?'](y):
                break
            # If display_optional = False do not display optional stats
            if helper['display optional?'](m):
                continue
            # If display_additional = False do not display additional stats
            if helper['display additional?'](m):
                continue
            # Is it possible to display the stat with the current screen size
            # !!! Crash if not try/except... Why ???
            try:
                self.display_stats_with_current_size(m, y, x)
            except Exception:
                pass
            else:
                x, x_max = self.get_next_x_and_x_max(m, x, x_max)

        return y, x, x_max

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
        screen_y, screen_x = self.term_window.getmaxyx()

        # Set the upper/left position of the message
        display_y, display_x = self.setup_upper_left_pos(plugin_stats)

        helper = {
            'goto next, add first col': lambda y, x: (y + 1, display_x),
            'x overbound?': lambda m, x: not m['splittable'] and (x + len(m['msg']) > screen_x),
            'y overbound?': lambda y: y < 0 or (y + 1 > screen_y) or (y > max_y),
            'display optional?': lambda m: not display_optional and m['optional'],
            'display additional?': lambda m: not display_additional and m['additional'],
        }

        # Display
        init = display_y, display_x, display_x
        y, x, x_max = self.display_stats(plugin_stats, init, helper)

        # Compute the next Glances column/line position
        self.next_column = max(self.next_column, x_max + self.space_between_column)
        self.next_line = max(self.next_line, y + self.space_between_line)

        # Have empty lines after the plugins
        self.next_line += add_space
        return None

    def clear(self):
        """Erase the content of the screen.
        The difference is that clear() also calls clearok(). clearok()
        basically tells ncurses to forget whatever it knows about the current
        terminal contents, so that when refresh() is called, it will actually
        begin by clearing the entire terminal screen before redrawing any of it."""
        self.term_window.clear()

    def erase(self):
        """Erase the content of the screen.
        erase() on the other hand, just clears the screen (the internal
        object, not the terminal screen). When refresh() is later called,
        ncurses will still compute the minimum number of characters to send to
        update the terminal."""
        self.term_window.erase()

    def refresh(self):
        """Refresh the windows"""
        self.term_window.refresh()

    def flush(self, stats, cs_status=None):
        """Erase and update the screen.

        :param stats: Stats database to display
        :param cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        # See https://stackoverflow.com/a/43486979/1919431
        self.erase()
        self.display(stats, cs_status=cs_status)
        self.refresh()

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

            if pressedkey == curses.KEY_F5 or self.pressedkey == 18:
                # Were asked to refresh (F5 or Ctrl-R)
                self.clear()
                return isexitkey

            if pressedkey in (curses.KEY_UP, 65, curses.KEY_DOWN, 66):
                # Up of won key pressed, reset the countdown
                # Better for user experience
                countdown.reset()

            if isexitkey and self.args.help_tag:
                # Quit from help should return to main screen, not exit #1874
                self.args.help_tag = not self.args.help_tag
                return False

            if not isexitkey and pressedkey > -1:
                # Redraw display
                self.flush(stats, cs_status=cs_status)
                # Overwrite the timeout with the countdown
                self.wait(delay=int(countdown.get() * 1000))

        return isexitkey

    def wait(self, delay=100):
        """Wait delay in ms"""
        curses.napms(delay)

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
            logger.debug(f'ERROR: Can not compute plugin width ({e})')
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
            logger.debug(f'ERROR: Can not compute plugin height ({e})')
            return 0
        else:
            return c + 1


class GlancesCursesStandalone(_GlancesCurses):
    """Class for the Glances curse standalone."""


class GlancesCursesClient(_GlancesCurses):
    """Class for the Glances curse client."""


class GlancesTextbox(Textbox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_command(self, ch):
        if ch == 10:  # Enter
            return 0
        if ch == 127:  # Back
            return 8
        return super().do_command(ch)


class GlancesTextboxYesNo(Textbox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_command(self, ch):
        return super().do_command(ch)

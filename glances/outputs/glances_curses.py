# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

from glances.compat import u
from glances.globals import OSX, WINDOWS
from glances.logger import logger
from glances.logs import glances_logs
from glances.processes import glances_processes
from glances.timer import Timer

# Import curses lib for "normal" operating system and consolelog for Windows
if not WINDOWS:
    try:
        import curses
        import curses.panel
        from curses.textpad import Textbox
    except ImportError:
        logger.critical(
            "Curses module not found. Glances cannot start in standalone mode.")
        sys.exit(1)
else:
    from glances.outputs.glances_colorconsole import WCurseLight
    curses = WCurseLight()


class _GlancesCurses(object):

    """This class manages the curses display (and key pressed).

    Note: It is a private class, use GlancesCursesClient or GlancesCursesBrowser.
    """

    def __init__(self, args=None):
        # Init args
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

    def _init_history(self):
        '''Init the history option'''

        self.reset_history_tag = False
        self.history_tag = False
        if self.args.enable_history:
            logger.info('Stats history enabled with output path %s' %
                        self.args.path_history)
            from glances.exports.glances_history import GlancesHistory
            self.glances_history = GlancesHistory(self.args.path_history)
            if not self.glances_history.graph_enabled():
                self.args.enable_history = False
                logger.error(
                    'Stats history disabled because MatPlotLib is not installed')

    def _init_cursor(self):
        '''Init cursors'''

        if hasattr(curses, 'noecho'):
            curses.noecho()
        if hasattr(curses, 'cbreak'):
            curses.cbreak()
        self.set_cursor(0)

    def _init_colors(self):
        '''Init the Curses color layout'''

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
            if self.args.theme_white:
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
                    if self.args.theme_white:
                        curses.init_pair(9, curses.COLOR_BLACK, -1)
                    else:
                        curses.init_pair(9, curses.COLOR_WHITE, -1)
                try:
                    curses.init_pair(10, curses.COLOR_CYAN, -1)
                except Exception:
                    if self.args.theme_white:
                        curses.init_pair(10, curses.COLOR_BLACK, -1)
                    else:
                        curses.init_pair(10, curses.COLOR_WHITE, -1)

                self.ifWARNING_color2 = curses.color_pair(9) | A_BOLD
                self.ifCRITICAL_color2 = curses.color_pair(6) | A_BOLD
                self.filter_color = curses.color_pair(10) | A_BOLD

            self.no_color = curses.color_pair(1)
            self.default_color = curses.color_pair(3) | A_BOLD
            self.nice_color = curses.color_pair(9) | A_BOLD
            self.cpu_time_color = curses.color_pair(9) | A_BOLD
            self.ifCAREFUL_color = curses.color_pair(4) | A_BOLD
            self.ifWARNING_color = curses.color_pair(5) | A_BOLD
            self.ifCRITICAL_color = curses.color_pair(2) | A_BOLD
            self.default_color2 = curses.color_pair(7) | A_BOLD
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

        # Actions...
        if self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            if return_to_browser:
                logger.info("Stop Glances client and return to the browser")
            else:
                self.end()
                logger.info("Stop Glances")
                sys.exit(0)
        elif self.pressedkey == 10:
            # 'ENTER' > Edit the process filter
            self.edit_filter = not self.edit_filter
        elif self.pressedkey == ord('0'):
            # '0' > Switch between IRIX and Solaris mode
            self.args.disable_irix = not self.args.disable_irix
        elif self.pressedkey == ord('1'):
            # '1' > Switch between CPU and PerCPU information
            self.args.percpu = not self.args.percpu
        elif self.pressedkey == ord('2'):
            # '2' > Enable/disable left sidebar
            self.args.disable_left_sidebar = not self.args.disable_left_sidebar
        elif self.pressedkey == ord('3'):
            # '3' > Enable/disable quicklook
            self.args.disable_quicklook = not self.args.disable_quicklook
        elif self.pressedkey == ord('4'):
            # '4' > Enable/disable all but quick look and load
            self.args.full_quicklook = not self.args.full_quicklook
            if self.args.full_quicklook:
                self.args.disable_quicklook = False
                self.args.disable_cpu = True
                self.args.disable_mem = True
                self.args.disable_swap = True
            else:
                self.args.disable_quicklook = False
                self.args.disable_cpu = False
                self.args.disable_mem = False
                self.args.disable_swap = False
        elif self.pressedkey == ord('5'):
            # '5' > Enable/disable top menu
            logger.info(self.args.disable_top)
            self.args.disable_top = not self.args.disable_top
            if self.args.disable_top:
                self.args.disable_quicklook = True
                self.args.disable_cpu = True
                self.args.disable_mem = True
                self.args.disable_swap = True
                self.args.disable_load = True
            else:
                self.args.disable_quicklook = False
                self.args.disable_cpu = False
                self.args.disable_mem = False
                self.args.disable_swap = False
                self.args.disable_load = False
        elif self.pressedkey == ord('/'):
            # '/' > Switch between short/long name for processes
            self.args.process_short_name = not self.args.process_short_name
        elif self.pressedkey == ord('a'):
            # 'a' > Sort processes automatically and reset to 'cpu_percent'
            glances_processes.auto_sort = True
            glances_processes.sort_key = 'cpu_percent'
        elif self.pressedkey == ord('b'):
            # 'b' > Switch between bit/s and Byte/s for network IO
            self.args.byte = not self.args.byte
        elif self.pressedkey == ord('B'):
            # 'B' > Switch between bit/s and IO/s for Disk IO
            self.args.diskio_iops = not self.args.diskio_iops
        elif self.pressedkey == ord('c'):
            # 'c' > Sort processes by CPU usage
            glances_processes.auto_sort = False
            glances_processes.sort_key = 'cpu_percent'
        elif self.pressedkey == ord('d'):
            # 'd' > Show/hide disk I/O stats
            self.args.disable_diskio = not self.args.disable_diskio
        elif self.pressedkey == ord('D'):
            # 'D' > Show/hide Docker stats
            self.args.disable_docker = not self.args.disable_docker
        elif self.pressedkey == ord('e'):
            # 'e' > Enable/Disable extended stats for top process
            self.args.enable_process_extended = not self.args.enable_process_extended
            if not self.args.enable_process_extended:
                glances_processes.disable_extended()
            else:
                glances_processes.enable_extended()
        elif self.pressedkey == ord('E'):
            # 'E' > Erase the process filter
            logger.info("Erase process filter")
            glances_processes.process_filter = None
        elif self.pressedkey == ord('F'):
            # 'F' > Switch between FS available and free space
            self.args.fs_free_space = not self.args.fs_free_space
        elif self.pressedkey == ord('f'):
            # 'f' > Show/hide fs / folder stats
            self.args.disable_fs = not self.args.disable_fs
            self.args.disable_folder = not self.args.disable_folder
        elif self.pressedkey == ord('g'):
            # 'g' > History
            self.history_tag = not self.history_tag
        elif self.pressedkey == ord('h'):
            # 'h' > Show/hide help
            self.args.help_tag = not self.args.help_tag
        elif self.pressedkey == ord('i'):
            # 'i' > Sort processes by IO rate (not available on OS X)
            glances_processes.auto_sort = False
            glances_processes.sort_key = 'io_counters'
        elif self.pressedkey == ord('I'):
            # 'I' > Show/hide IP module
            self.args.disable_ip = not self.args.disable_ip
        elif self.pressedkey == ord('l'):
            # 'l' > Show/hide log messages
            self.args.disable_log = not self.args.disable_log
        elif self.pressedkey == ord('m'):
            # 'm' > Sort processes by MEM usage
            glances_processes.auto_sort = False
            glances_processes.sort_key = 'memory_percent'
        elif self.pressedkey == ord('M'):
            # 'M' > Reset processes summary min/max
            self.args.reset_minmax_tag = not self.args.reset_minmax_tag
        elif self.pressedkey == ord('n'):
            # 'n' > Show/hide network stats
            self.args.disable_network = not self.args.disable_network
        elif self.pressedkey == ord('p'):
            # 'p' > Sort processes by name
            glances_processes.auto_sort = False
            glances_processes.sort_key = 'name'
        elif self.pressedkey == ord('r'):
            # 'r' > Reset history
            self.reset_history_tag = not self.reset_history_tag
        elif self.pressedkey == ord('R'):
            # 'R' > Hide RAID plugins
            self.args.disable_raid = not self.args.disable_raid
        elif self.pressedkey == ord('s'):
            # 's' > Show/hide sensors stats (Linux-only)
            self.args.disable_sensors = not self.args.disable_sensors
        elif self.pressedkey == ord('t'):
            # 't' > Sort processes by TIME usage
            glances_processes.auto_sort = False
            glances_processes.sort_key = 'cpu_times'
        elif self.pressedkey == ord('T'):
            # 'T' > View network traffic as sum Rx+Tx
            self.args.network_sum = not self.args.network_sum
        elif self.pressedkey == ord('u'):
            # 'u' > Sort processes by USER
            glances_processes.auto_sort = False
            glances_processes.sort_key = 'username'
        elif self.pressedkey == ord('U'):
            # 'U' > View cumulative network I/O (instead of bitrate)
            self.args.network_cumul = not self.args.network_cumul
        elif self.pressedkey == ord('w'):
            # 'w' > Delete finished warning logs
            glances_logs.clean()
        elif self.pressedkey == ord('x'):
            # 'x' > Delete finished warning and critical logs
            glances_logs.clean(critical=True)
        elif self.pressedkey == ord('z'):
            # 'z' > Enable/Disable processes stats (count + list + monitor)
            # Enable/Disable display
            self.args.disable_process = not self.args.disable_process
            # Enable/Disable update
            if self.args.disable_process:
                glances_processes.disable()
            else:
                glances_processes.enable()
        # Return the key code
        return self.pressedkey

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
        """Init the line and column position for the curses inteface."""
        self.init_line()
        self.init_column()

    def init_line(self):
        """Init the line position for the curses inteface."""
        self.line = 0
        self.next_line = 0

    def init_column(self):
        """Init the column position for the curses inteface."""
        self.column = 0
        self.next_column = 0

    def new_line(self):
        """New line in the curses interface."""
        self.line = self.next_line

    def new_column(self):
        """New column in the curses interface."""
        self.column = self.next_column

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

        # Get the screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

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
        stats_system = stats.get_plugin(
            'system').get_stats_display(args=self.args)
        stats_uptime = stats.get_plugin('uptime').get_stats_display()
        if self.args.percpu:
            stats_cpu = stats.get_plugin('percpu').get_stats_display(args=self.args)
        else:
            stats_cpu = stats.get_plugin('cpu').get_stats_display(args=self.args)
        stats_load = stats.get_plugin('load').get_stats_display(args=self.args)
        stats_mem = stats.get_plugin('mem').get_stats_display(args=self.args)
        stats_memswap = stats.get_plugin('memswap').get_stats_display(args=self.args)
        stats_network = stats.get_plugin('network').get_stats_display(
            args=self.args, max_width=plugin_max_width)
        try:
            stats_ip = stats.get_plugin('ip').get_stats_display(args=self.args)
        except AttributeError:
            stats_ip = None
        stats_diskio = stats.get_plugin(
            'diskio').get_stats_display(args=self.args)
        stats_fs = stats.get_plugin('fs').get_stats_display(
            args=self.args, max_width=plugin_max_width)
        stats_folders = stats.get_plugin('folders').get_stats_display(
            args=self.args, max_width=plugin_max_width)
        stats_raid = stats.get_plugin('raid').get_stats_display(
            args=self.args)
        stats_sensors = stats.get_plugin(
            'sensors').get_stats_display(args=self.args)
        stats_now = stats.get_plugin('now').get_stats_display()
        stats_docker = stats.get_plugin('docker').get_stats_display(
            args=self.args)
        stats_processcount = stats.get_plugin(
            'processcount').get_stats_display(args=self.args)
        stats_monitor = stats.get_plugin(
            'monitor').get_stats_display(args=self.args)
        stats_alert = stats.get_plugin(
            'alert').get_stats_display(args=self.args)

        # Adapt number of processes to the available space
        max_processes_displayed = screen_y - 11 - \
            self.get_stats_display_height(stats_alert) - \
            self.get_stats_display_height(stats_docker)
        try:
            if self.args.enable_process_extended and not self.args.process_tree:
                max_processes_displayed -= 4
        except AttributeError:
            pass
        if max_processes_displayed < 0:
            max_processes_displayed = 0
        if (glances_processes.max_processes is None or
                glances_processes.max_processes != max_processes_displayed):
            logger.debug("Set number of displayed processes to {0}".format(max_processes_displayed))
            glances_processes.max_processes = max_processes_displayed

        stats_processlist = stats.get_plugin(
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

        # ==================================
        # Display first line (system+uptime)
        # ==================================
        # Space between column
        self.space_between_column = 0
        self.new_line()
        l_uptime = self.get_stats_display_width(
            stats_system) + self.space_between_column + self.get_stats_display_width(stats_ip) + 3 + self.get_stats_display_width(stats_uptime)
        self.display_plugin(
            stats_system, display_optional=(screen_x >= l_uptime))
        self.new_column()
        self.display_plugin(stats_ip)
        # Space between column
        self.space_between_column = 3
        self.new_column()
        self.display_plugin(stats_uptime)

        # ========================================================
        # Display second line (<SUMMARY>+CPU|PERCPU+LOAD+MEM+SWAP)
        # ========================================================
        self.init_column()
        self.new_line()

        # Init quicklook
        stats_quicklook = {'msgdict': []}
        quicklook_width = 0

        # Get stats for CPU, MEM, SWAP and LOAD (if needed)
        if self.args.disable_cpu:
            cpu_width = 0
        else:
            cpu_width = self.get_stats_display_width(stats_cpu)
        if self.args.disable_mem:
            mem_width = 0
        else:
            mem_width = self.get_stats_display_width(stats_mem)
        if self.args.disable_swap:
            swap_width = 0
        else:
            swap_width = self.get_stats_display_width(stats_memswap)
        if self.args.disable_load:
            load_width = 0
        else:
            load_width = self.get_stats_display_width(stats_load)

        # Size of plugins but quicklook
        stats_width = cpu_width + mem_width + swap_width + load_width

        # Number of plugin but quicklook
        stats_number = (
            int(not self.args.disable_cpu and stats_cpu['msgdict'] != []) +
            int(not self.args.disable_mem and stats_mem['msgdict'] != []) +
            int(not self.args.disable_swap and stats_memswap['msgdict'] != []) +
            int(not self.args.disable_load and stats_load['msgdict'] != []))

        if not self.args.disable_quicklook:
            # Quick look is in the place !
            if self.args.full_quicklook:
                quicklook_width = screen_x - (stats_width + 8 + stats_number * self.space_between_column)
            else:
                quicklook_width = min(screen_x - (stats_width + 8 + stats_number * self.space_between_column), 79)
            try:
                stats_quicklook = stats.get_plugin(
                    'quicklook').get_stats_display(max_width=quicklook_width, args=self.args)
            except AttributeError as e:
                logger.debug("Quicklook plugin not available (%s)" % e)
            else:
                quicklook_width = self.get_stats_display_width(stats_quicklook)
                stats_width += quicklook_width + 1
            self.space_between_column = 1
            self.display_plugin(stats_quicklook)
            self.new_column()

        # Compute spaces between plugins
        # Note: Only one space between Quicklook and others
        display_optional_cpu = True
        display_optional_mem = True
        if stats_number > 1:
            self.space_between_column = max(1, int((screen_x - stats_width) / (stats_number - 1)))
            # No space ? Remove optionnal MEM stats
            if self.space_between_column < 3:
                display_optional_mem = False
                if self.args.disable_mem:
                    mem_width = 0
                else:
                    mem_width = self.get_stats_display_width(stats_mem, without_option=True)
                stats_width = quicklook_width + 1 + cpu_width + mem_width + swap_width + load_width
                self.space_between_column = max(1, int((screen_x - stats_width) / (stats_number - 1)))
            # No space again ? Remove optionnal CPU stats
            if self.space_between_column < 3:
                display_optional_cpu = False
                if self.args.disable_cpu:
                    cpu_width = 0
                else:
                    cpu_width = self.get_stats_display_width(stats_cpu, without_option=True)
                stats_width = quicklook_width + 1 + cpu_width + mem_width + swap_width + load_width
                self.space_between_column = max(1, int((screen_x - stats_width) / (stats_number - 1)))
        else:
            self.space_between_column = 0

        # Display CPU, MEM, SWAP and LOAD
        self.display_plugin(stats_cpu, display_optional=display_optional_cpu)
        self.new_column()
        self.display_plugin(stats_mem, display_optional=display_optional_mem)
        self.new_column()
        self.display_plugin(stats_memswap)
        self.new_column()
        self.display_plugin(stats_load)

        # Space between column
        self.space_between_column = 3

        # Backup line position
        self.saved_line = self.next_line

        # ==================================================================
        # Display left sidebar (NETWORK+DISKIO+FS+SENSORS+Current time)
        # ==================================================================
        self.init_column()
        if not (self.args.disable_network and
                self.args.disable_diskio and
                self.args.disable_fs and
                self.args.disable_folder and
                self.args.disable_raid and
                self.args.disable_sensors) and not self.args.disable_left_sidebar:
            self.new_line()
            self.display_plugin(stats_network)
            self.new_line()
            self.display_plugin(stats_diskio)
            self.new_line()
            self.display_plugin(stats_fs)
            self.new_line()
            self.display_plugin(stats_folders)
            self.new_line()
            self.display_plugin(stats_raid)
            self.new_line()
            self.display_plugin(stats_sensors)
            self.new_line()
            self.display_plugin(stats_now)

        # ====================================
        # Display right stats (process and co)
        # ====================================
        # If space available...
        if screen_x > 52:
            # Restore line position
            self.next_line = self.saved_line

            # Display right sidebar
            # ((DOCKER)+PROCESS_COUNT+(MONITORED)+PROCESS_LIST+ALERT)
            self.new_column()
            self.new_line()
            self.display_plugin(stats_docker)
            self.new_line()
            self.display_plugin(stats_processcount)
            if glances_processes.process_filter is None and cs_status is None:
                # Do not display stats monitor list if a filter exist
                self.new_line()
                self.display_plugin(stats_monitor)
            self.new_line()
            self.display_plugin(stats_processlist,
                                display_optional=(screen_x > 102),
                                display_additional=(not OSX),
                                max_y=(screen_y - self.get_stats_display_height(stats_alert) - 2))
            self.new_line()
            self.display_plugin(stats_alert)

        # History option
        # Generate history graph
        if self.history_tag and self.args.enable_history:
            self.display_popup(
                'Generate graphs history in {0}\nPlease wait...'.format(
                    self.glances_history.get_output_folder()))
            self.display_popup(
                'Generate graphs history in {0}\nDone: {1} graphs generated'.format(
                    self.glances_history.get_output_folder(),
                    self.glances_history.generate_graph(stats)))
        elif self.reset_history_tag and self.args.enable_history:
            self.display_popup('Reset history')
            self.glances_history.reset(stats)
        elif (self.history_tag or self.reset_history_tag) and not self.args.enable_history:
            try:
                self.glances_history.graph_enabled()
            except Exception:
                self.display_popup('History disabled\nEnable it using --enable-history')
            else:
                self.display_popup('History disabled\nPlease install matplotlib')
        self.history_tag = False
        self.reset_history_tag = False

        # Display edit filter popup
        # Only in standalone mode (cs_status is None)
        if self.edit_filter and cs_status is None:
            new_filter = self.display_popup(
                'Process filter pattern: ', is_input=True,
                input_value=glances_processes.process_filter)
            glances_processes.process_filter = new_filter
        elif self.edit_filter and cs_status != 'None':
            self.display_popup('Process filter only available in standalone mode')
        self.edit_filter = False

        return True

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
                       max_y=65535):
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

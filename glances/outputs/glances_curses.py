#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

# Import system lib
import sys
try:
    import curses
    import curses.panel
except ImportError:
    print('Curses module not found. Glances cannot start in standalone mode.')
    sys.exit(1)

# Import Glances lib
from ..core.glances_timer import Timer
from ..core.glances_globals import glances_logs


class glancesCurses:
    """
    This class manage the curses display (and key pressed)
    """

    def __init__(self, args=None):

        # Init args
        self.args = args
        # By default, display bitrate instead of cumulative in the network plugin
        self.args.network_stats_cumulative = False

        # Init windows positions
        self.term_w = 80
        self.term_h = 24

        # Space between stats
        self.space_between_column = 3
        self.space_between_line = 2

        # Init the curses screen
        self.screen = curses.initscr()
        if not self.screen:
            print(_("Error: Cannot init the curses library.\n"))

        # Set curses options
        if hasattr(curses, 'start_color'):
            curses.start_color()
        if hasattr(curses, 'use_default_colors'):
            curses.use_default_colors()
        if hasattr(curses, 'noecho'):
            curses.noecho()
        if hasattr(curses, 'cbreak'):
            curses.cbreak()
        if hasattr(curses, 'curs_set'):
            try:
                curses.curs_set(0)
            except Exception:
                pass

        # Init colors
        self.hascolors = False
        if curses.has_colors() and curses.COLOR_PAIRS > 8:
            self.hascolors = True
            # FG color, BG color
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN)
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
            curses.init_pair(6, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_GREEN, -1)
            curses.init_pair(8, curses.COLOR_BLUE, -1)
            curses.init_pair(9, curses.COLOR_MAGENTA, -1)
        else:
            self.hascolors = False

        if (args.no_bold):
            A_BOLD = curses.A_BOLD
        else:
            A_BOLD = 0

        self.title_color = A_BOLD
        self.title_underline_color = A_BOLD | curses.A_UNDERLINE
        self.help_color = A_BOLD
        if self.hascolors:
            # Colors text styles
            self.no_color = curses.color_pair(1)
            self.default_color = curses.color_pair(3) | A_BOLD
            self.ifCAREFUL_color = curses.color_pair(4) | A_BOLD
            self.ifWARNING_color = curses.color_pair(5) | A_BOLD
            self.ifCRITICAL_color = curses.color_pair(2) | A_BOLD
            self.default_color2 = curses.color_pair(7) | A_BOLD
            self.ifCAREFUL_color2 = curses.color_pair(8) | A_BOLD
            self.ifWARNING_color2 = curses.color_pair(9) | A_BOLD
            self.ifCRITICAL_color2 = curses.color_pair(6) | A_BOLD
        else:
            # B&W text styles
            self.no_color = curses.A_NORMAL
            self.default_color = curses.A_NORMAL
            self.ifCAREFUL_color = curses.A_UNDERLINE
            self.ifWARNING_color = A_BOLD
            self.ifCRITICAL_color = curses.A_REVERSE
            self.default_color2 = curses.A_NORMAL
            self.ifCAREFUL_color2 = curses.A_UNDERLINE
            self.ifWARNING_color2 = A_BOLD
            self.ifCRITICAL_color2 = curses.A_REVERSE

        # Define the colors list (hash table) for stats
        self.__colors_list = {
            'DEFAULT': self.no_color,
            'UNDERLINE': curses.A_UNDERLINE,
            'BOLD': A_BOLD,
            'OK': self.default_color2,
            'TITLE': self.title_color,
            'CAREFUL': self.ifCAREFUL_color2,
            'WARNING': self.ifWARNING_color2,
            'CRITICAL': self.ifCRITICAL_color2,
            'OK_LOG': self.default_color,
            'CAREFUL_LOG': self.ifCAREFUL_color,
            'WARNING_LOG': self.ifWARNING_color,
            'CRITICAL_LOG': self.ifCRITICAL_color
        }

        # Init main window
        self.term_window = self.screen.subwin(0, 0)

        # Init refresh time
        self.__refresh_time = args.time

        # Init process sort method
        self.args.process_sorted_by = 'auto'

        # Catch key pressed with non blocking mode
        self.term_window.keypad(1)
        self.term_window.nodelay(1)
        self.pressedkey = -1

    def __getkey(self, window):
        """
        A getKey function to catch ESC key AND Numlock key (issue #163)
        """
        keycode = [0, 0]
        keycode[0] = window.getch()
        keycode[1] = window.getch()

        if keycode[0] == 27 and keycode[1] != -1:
            # Do not escape on specials keys
            return -1
        else:
            return keycode[0]

    def __catchKey(self):
        # Get key
        #~ self.pressedkey = self.term_window.getch()
        self.pressedkey = self.__getkey(self.term_window)

        # Actions...
        if self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            self.end()
            sys.exit(0)
        elif self.pressedkey == ord('1'):
            # '1' > Switch between CPU and PerCPU information
            self.args.percpu = not self.args.percpu
        elif self.pressedkey == ord('a'):
            # 'a' > Sort processes automatically
            self.args.process_sorted_by = 'auto'
        elif self.pressedkey == ord('b'):
            # 'b' > Switch between bit/s and Byte/s for network IO
            # self.net_byteps_tag = not self.net_byteps_tag
            self.args.byte = not self.args.byte
        elif self.pressedkey == ord('c'):
            # 'c' > Sort processes by CPU usage
            self.args.process_sorted_by = 'cpu_percent'
        elif self.pressedkey == ord('d') and diskio_tag:
            # 'd' > Show/hide disk I/O stats
            self.diskio_tag = not self.diskio_tag
        elif self.pressedkey == ord('f') and fs_tag:
            # 'f' > Show/hide fs stats
            self.fs_tag = not self.fs_tag
        elif self.pressedkey == ord('h'):
            # 'h' > Show/hide help
            self.args.help_tag = not self.args.help_tag
        elif self.pressedkey == ord('i'):
        # elif self.pressedkey == ord('i') and psutil_get_io_counter_tag:
            # !!! Manage IORate (non existing) on Mac OS
            # 'i' > Sort processes by IO rate (not available on OS X)
            self.args.process_sorted_by = 'io_counters'
        elif self.pressedkey == ord('l'):
            # 'l' > Show/hide log messages
            self.log_tag = not self.log_tag
        elif self.pressedkey == ord('m'):
            # 'm' > Sort processes by MEM usage
            self.args.process_sorted_by = 'memory_percent'
        elif self.pressedkey == ord('n') and network_tag:
            # 'n' > Show/hide network stats
            self.network_tag = not self.network_tag
        elif self.pressedkey == ord('p'):
            # 'p' > Sort processes by name
            self.args.process_sorted_by = 'name'
        elif self.pressedkey == ord('s'):
            # 's' > Show/hide sensors stats (Linux-only)
            self.sensors_tag = not self.sensors_tag
        elif self.pressedkey == ord('t'):
            # 't' > View network traffic as combination
            self.network_stats_combined = not self.network_stats_combined
        elif self.pressedkey == ord('u'):
            # 'u' > View cumulative network IO
            self.args.network_stats_cumulative = not self.args.network_stats_cumulative
        elif self.pressedkey == ord('w'):
            # 'w' > Delete finished warning logs
            glances_logs.clean()
        elif self.pressedkey == ord('x'):
            # 'x' > Delete finished warning and critical logs
            glances_logs.clean(critical=True)
        elif self.pressedkey == ord('y'):
            # 'y' > Show/hide hddtemp stats
            self.hddtemp_tag = not self.hddtemp_tag

        # Return the key code
        return self.pressedkey

    def end(self):
        # Shutdown the curses window
        curses.echo()
        curses.nocbreak()
        curses.curs_set(1)
        curses.endwin()

    def display(self, stats, cs_status="None"):
        """
        Display stats on the screen

        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server

        Return:
            True if the stats have been displayed
            False if the help have been displayed
        """

        # Init the internal line/column dict for Glances Curses
        self.line_to_y = {}
        self.column_to_x = {}

        # Get the screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        if (self.args.help_tag):
            # Display the stats...
            self.display_plugin(stats.get_plugin('help').get_curse(args=self.args))
            # ... and exit
            return False

        # Update the client server status
        self.args.cs_status = cs_status

        # Display first line (system+uptime)
        stats_system = stats.get_plugin('system').get_curse(args=self.args)
        stats_uptime = stats.get_plugin('uptime').get_curse()
        l = self.get_curse_width(stats_system) + self.get_curse_width(stats_uptime) + self.space_between_column
        self.display_plugin(stats_system, display_optional=(screen_x >= l))
        self.display_plugin(stats_uptime)

        # Display second line (CPU|PERCPU+LOAD+MEM+SWAP+<SUMMARY>)
        # CPU|PERCPU
        if (self.args.percpu):
            stats_percpu = stats.get_plugin('percpu').get_curse()
            l = self.get_curse_width(stats_percpu)
        else:
            stats_cpu = stats.get_plugin('cpu').get_curse()
            l = self.get_curse_width(stats_cpu)
        stats_load = stats.get_plugin('load').get_curse()
        stats_mem = stats.get_plugin('mem').get_curse()
        stats_memswap = stats.get_plugin('memswap').get_curse()
        l += self.get_curse_width(stats_load) + self.get_curse_width(stats_mem) + self.get_curse_width(stats_memswap)
        # Space between column
        if (screen_x > (3 * self.space_between_column + l)):
            self.space_between_column = int((screen_x - l) / 3)
        # Display
        if (self.args.percpu):
            self.display_plugin(stats_percpu)
        else:
            self.display_plugin(stats_cpu, display_optional=(screen_x >= 76))
        self.display_plugin(stats_load)
        self.display_plugin(stats_mem, display_optional=(screen_x >= (3 * self.space_between_column + l)))
        self.display_plugin(stats_memswap)
        # Space between column
        self.space_between_column = 3

        # Display left sidebar (NETWORK+DISKIO+FS+SENSORS)
        self.display_plugin(stats.get_plugin('network').get_curse(args=self.args))
        self.display_plugin(stats.get_plugin('diskio').get_curse(args=self.args))
        self.display_plugin(stats.get_plugin('fs').get_curse(args=self.args))
        self.display_plugin(stats.get_plugin('sensors').get_curse(args=self.args))

        # Display last line (currenttime)
        self.display_plugin(stats.get_plugin('now').get_curse())

        # Display right sidebar (PROCESS_COUNT)
        if (screen_x > 52):
            stats_processcount = stats.get_plugin('processcount').get_curse(args=self.args)
            stats_processlist = stats.get_plugin('processlist').get_curse(args=self.args)
            stats_alert = stats.get_plugin('alert').get_curse(args=self.args)
            stats_monitor = stats.get_plugin('monitor').get_curse(args=self.args)
            self.display_plugin(stats_processcount)
            self.display_plugin(stats_monitor)
            self.display_plugin(stats_processlist, max_y=(screen_y - self.get_curse_height(stats_alert) - 3))
            self.display_plugin(stats_alert)

        return True

    def display_plugin(self, plugin_stats, display_optional=True, max_y=65535):
        """
        Display the plugin_stats on the screen
        If display_optional=True display the optional stats
        max_y do not display line > max_y
        """
        # Exit if the display tag = False
        if (not plugin_stats['display']):
            return 0

        # Get the screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        # Set the upper/left position of the message
        if (plugin_stats['column'] < 0):
            # Right align (last column)
            display_x = screen_x - self.get_curse_width(plugin_stats)
        else:
            if (plugin_stats['column'] not in self.column_to_x):
                self.column_to_x[plugin_stats['column']] = plugin_stats['column']
            display_x = self.column_to_x[plugin_stats['column']]
        if (plugin_stats['line'] < 0):
            # Bottom (last line)
            display_y = screen_y - self.get_curse_height(plugin_stats)
        else:
            if (plugin_stats['line'] not in self.line_to_y):
                self.line_to_y[plugin_stats['line']] = plugin_stats['line']
            display_y = self.line_to_y[plugin_stats['line']]

        # Display
        x = display_x
        y = display_y
        for m in plugin_stats['msgdict']:
            # New line
            if (m['msg'].startswith('\n')):
                # Go to the next line
                y = y + 1
                # Return to the first column
                x = display_x
                continue
            # Do not display outside the screen
            if ((x < 0) or (x + len(m['msg']) > screen_x)):
                continue
            if ((y < 0) or (y + 1 > screen_y) or (y > max_y)):
                break
            # If display_optional = False do not display optional stats
            if ((not display_optional) and m['optional']):
                continue
            # Is it possible to display the stat with the current screen size
            # !!! Crach if not try/except... Why ???
            try:
                self.term_window.addnstr(y, x,
                                         m['msg'],
                                         screen_x - x,  # Do not disply outside the screen
                                         self.__colors_list[m['decoration']])
            except:
                pass
            else:
                # New column
                x = x + len(m['msg'])

        # Compute the next Glances column/line position
        if (plugin_stats['column'] > -1):
            self.column_to_x[plugin_stats['column'] + 1] = x + self.space_between_column
        if (plugin_stats['line'] > -1):
            self.line_to_y[plugin_stats['line'] + 1] = y + self.space_between_line

    def erase(self):
        # Erase the content of the screen
        self.term_window.erase()

    def flush(self, stats, cs_status="None"):
        """
        Clear and update screen
        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        self.erase()
        self.display(stats, cs_status=cs_status)

    def update(self, stats, cs_status="None"):
        """
        Update the screen and wait __refresh_time sec / catch key every 100 ms
        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        # Flush display
        self.flush(stats, cs_status=cs_status)

        # Wait
        countdown = Timer(self.__refresh_time)
        while (not countdown.finished()):
            # Getkey
            if self.__catchKey() > -1:
                # flush display
                self.flush(stats, cs_status=cs_status)
            # Wait 100ms...
            curses.napms(100)

    def get_curse_width(self, curse_msg, without_option=False):
        # Return the width of the formated curses message
        # The height is defined by the maximum line

        try:
            if (without_option):
                # Size without options
                c = len(max(''.join([(i['msg'] if not i['optional'] else "")
                        for i in curse_msg['msgdict']]).split('\n'), key=len))
            else:
                # Size with all options
                c = len(max(''.join([i['msg']
                        for i in curse_msg['msgdict']]).split('\n'), key=len))
        except:
            return 0
        else:
            return c

    def get_curse_height(self, curse_msg):
        # Return the height of the formated curses message
        # The height is defined by the number of '\n'

        try:
            c = [i['msg'] for i in curse_msg['msgdict']].count('\n')
        except:
            return 0
        else:
            return c + 1

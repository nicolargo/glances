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

"""Curses browser interface class ."""

import sys

from glances.outputs.glances_curses import _GlancesCurses

from glances.logger import logger
from glances.timer import Timer


class GlancesCursesBrowser(_GlancesCurses):

    """Class for the Glances curse client browser."""

    def __init__(self, args=None):
        # Init the father class
        super(GlancesCursesBrowser, self).__init__(args=args)

        _colors_list = {
            'UNKNOWN': self.no_color,
            'SNMP': self.default_color2,
            'ONLINE': self.default_color2,
            'OFFLINE': self.ifCRITICAL_color2,
            'PROTECTED': self.ifWARNING_color2,
        }
        self.colors_list.update(_colors_list)

        # First time scan tag
        # Used to display a specific message when the browser is started
        self.first_scan = True

        # Init refresh time
        self.__refresh_time = args.time

        # Init the cursor position for the client browser
        self.cursor_position = 0

        # Active Glances server number
        self._active_server = None

    @property
    def active_server(self):
        """Return the active server or None if it's the browser list."""
        return self._active_server

    @active_server.setter
    def active_server(self, index):
        """Set the active server or None if no server selected."""
        self._active_server = index

    @property
    def cursor(self):
        """Get the cursor position."""
        return self.cursor_position

    @cursor.setter
    def cursor(self, position):
        """Set the cursor position."""
        self.cursor_position = position

    def cursor_up(self, servers_list):
        """Set the cursor to position N-1 in the list."""
        if self.cursor_position > 0:
            self.cursor_position -= 1
        else:
            self.cursor_position = len(servers_list) - 1

    def cursor_down(self, servers_list):
        """Set the cursor to position N-1 in the list."""
        if self.cursor_position < len(servers_list) - 1:
            self.cursor_position += 1
        else:
            self.cursor_position = 0

    def __catch_key(self, servers_list):
        # Catch the browser pressed key
        self.pressedkey = self.get_key(self.term_window)

        if self.pressedkey != -1:
            logger.debug("Key pressed. Code=%s" % self.pressedkey)

        # Actions...
        if self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            self.end()
            logger.info("Stop Glances client browser")
            sys.exit(0)
        elif self.pressedkey == 10:
            # 'ENTER' > Run Glances on the selected server
            logger.debug("Server number {} selected".format(self.cursor + 1))
            self.active_server = self.cursor
        elif self.pressedkey == 65:
            # 'UP' > Up in the server list
            self.cursor_up(servers_list)
        elif self.pressedkey == 66:
            # 'DOWN' > Down in the server list
            self.cursor_down(servers_list)

        # Return the key code
        return self.pressedkey

    def update(self, servers_list):
        """Update the servers' list screen.

        Wait for __refresh_time sec / catch key every 100 ms.

        servers_list: Dict of dict with servers stats
        """
        # Flush display
        logger.debug('Servers list: {}'.format(servers_list))
        self.flush(servers_list)

        # Wait
        exitkey = False
        countdown = Timer(self.__refresh_time)
        while not countdown.finished() and not exitkey:
            # Getkey
            pressedkey = self.__catch_key(servers_list)
            # Is it an exit or select server key ?
            exitkey = (
                pressedkey == ord('\x1b') or pressedkey == ord('q') or pressedkey == 10)
            if not exitkey and pressedkey > -1:
                # Redraw display
                self.flush(servers_list)
            # Wait 100ms...
            self.wait()

        return self.active_server

    def flush(self, servers_list):
        """Update the servers' list screen.

        servers_list: List of dict with servers stats
        """
        self.erase()
        self.display(servers_list)

    def display(self, servers_list):
        """Display the servers list.

        Return:
            True if the stats have been displayed
            False if the stats have not been displayed (no server available)
        """
        # Init the internal line/column for Glances Curses
        self.init_line_column()

        # Get the current screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        # Init position
        x = 0
        y = 0

        # Display top header
        if len(servers_list) == 0:
            if self.first_scan and not self.args.disable_autodiscover:
                msg = 'Glances is scanning your network. Please wait...'
                self.first_scan = False
            else:
                msg = 'No Glances server available'
        elif len(servers_list) == 1:
            msg = 'One Glances server available'
        else:
            msg = '{} Glances servers available'.format(len(servers_list))
        if self.args.disable_autodiscover:
            msg += ' ' + '(auto discover is disabled)'
        self.term_window.addnstr(y, x,
                                 msg,
                                 screen_x - x,
                                 self.colors_list['TITLE'])

        if len(servers_list) == 0:
            return False

        # Display the Glances server list
        # ================================

        # Table of table
        # Item description: [stats_id, column name, column size]
        column_def = [
            ['name', 'Name', 16],
            ['alias', None, None],
            ['load_min5', 'LOAD', 6],
            ['cpu_percent', 'CPU%', 5],
            ['mem_percent', 'MEM%', 5],
            ['status', 'STATUS', 9],
            ['ip', 'IP', 15],
            # ['port', 'PORT', 5],
            ['hr_name', 'OS', 16],
        ]
        y = 2

        # Display table header
        xc = x + 2
        for cpt, c in enumerate(column_def):
            if xc < screen_x and y < screen_y and c[1] is not None:
                self.term_window.addnstr(y, xc,
                                         c[1],
                                         screen_x - x,
                                         self.colors_list['BOLD'])
                xc += c[2] + self.space_between_column
        y += 1

        # If a servers has been deleted from the list...
        # ... and if the cursor is in the latest position
        if self.cursor > len(servers_list) - 1:
            # Set the cursor position to the latest item
            self.cursor = len(servers_list) - 1

        # Display table
        line = 0
        for v in servers_list:
            # Get server stats
            server_stat = {}
            for c in column_def:
                try:
                    server_stat[c[0]] = v[c[0]]
                except KeyError as e:
                    logger.debug(
                        "Cannot grab stats {} from server (KeyError: {})".format(c[0], e))
                    server_stat[c[0]] = '?'
                # Display alias instead of name
                try:
                    if c[0] == 'alias' and v[c[0]] is not None:
                        server_stat['name'] = v[c[0]]
                except KeyError:
                    pass

            # Display line for server stats
            cpt = 0
            xc = x

            # Is the line selected ?
            if line == self.cursor:
                # Display cursor
                self.term_window.addnstr(
                    y, xc, ">", screen_x - xc, self.colors_list['BOLD'])

            # Display the line
            xc += 2
            for c in column_def:
                if xc < screen_x and y < screen_y and c[1] is not None:
                    # Display server stats
                    self.term_window.addnstr(
                        y, xc, format(server_stat[c[0]]), c[2], self.colors_list[v['status']])
                    xc += c[2] + self.space_between_column
                cpt += 1
            # Next line, next server...
            y += 1
            line += 1

        return True

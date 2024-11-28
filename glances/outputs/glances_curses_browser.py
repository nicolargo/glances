#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Curses browser interface class ."""

import curses
import math

from glances.logger import logger
from glances.outputs.glances_curses import _GlancesCurses
from glances.timer import Timer


class GlancesCursesBrowser(_GlancesCurses):
    """Class for the Glances curse client browser."""

    def __init__(self, args=None):
        """Init the father class."""
        super().__init__(args=args)

        _colors_list = {
            'UNKNOWN': self.colors_list['DEFAULT'],
            'SNMP': self.colors_list['OK'],
            'ONLINE': self.colors_list['OK'],
            'OFFLINE': self.colors_list['CRITICAL'],
            'PROTECTED': self.colors_list['WARNING'],
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

        self._current_page = 0
        self._page_max = 0
        self._page_max_lines = 0

        self.is_end = False
        self._revesed_sorting = False
        self._stats_list = None

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

    def get_pagelines(self, stats):
        if self._current_page == self._page_max - 1:
            page_lines = len(stats) % self._page_max_lines
        else:
            page_lines = self._page_max_lines
        return page_lines

    def _get_status_count(self, stats):
        counts = {}
        for item in stats:
            color = item['status']
            counts[color] = counts.get(color, 0) + 1

        result = ''
        for key in counts.keys():
            result += key + ': ' + str(counts[key]) + ' '

        return result

    def _get_stats(self, stats):
        stats_list = None
        if self._stats_list is not None:
            stats_list = self._stats_list
            stats_list.sort(
                reverse=self._revesed_sorting,
                key=lambda x: {'UNKNOWN': 0, 'OFFLINE': 1, 'PROTECTED': 2, 'SNMP': 3, 'ONLINE': 4}.get(x['status'], 99),
            )
        else:
            stats_list = stats

        return stats_list

    def cursor_up(self, stats):
        """Set the cursor to position N-1 in the list."""
        if 0 <= self.cursor_position - 1:
            self.cursor_position -= 1
        else:
            if self._current_page - 1 < 0:
                self._current_page = self._page_max - 1
                self.cursor_position = (len(stats) - 1) % self._page_max_lines
            else:
                self._current_page -= 1
                self.cursor_position = self._page_max_lines - 1

    def cursor_down(self, stats):
        """Set the cursor to position N-1 in the list."""

        if self.cursor_position + 1 < self.get_pagelines(stats):
            self.cursor_position += 1
        else:
            if self._current_page + 1 < self._page_max:
                self._current_page += 1
            else:
                self._current_page = 0
            self.cursor_position = 0

    def cursor_pageup(self, stats):
        """Set prev page."""
        if self._current_page - 1 < 0:
            self._current_page = self._page_max - 1
        else:
            self._current_page -= 1
        self.cursor_position = 0

    def cursor_pagedown(self, stats):
        """Set next page."""
        if self._current_page + 1 < self._page_max:
            self._current_page += 1
        else:
            self._current_page = 0
        self.cursor_position = 0

    def __catch_key(self, stats):
        # Catch the browser pressed key
        self.pressedkey = self.get_key(self.term_window)
        refresh = False
        if self.pressedkey != -1:
            logger.debug(f"Key pressed. Code={self.pressedkey}")

        # Actions...
        if self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            self.end()
            logger.info("Stop Glances client browser")
            # sys.exit(0)
            self.is_end = True
        elif self.pressedkey == 10:
            # 'ENTER' > Run Glances on the selected server
            self.active_server = self._current_page * self._page_max_lines + self.cursor_position
            logger.debug(f"Server {self.active_server}/{len(stats)} selected")
        elif self.pressedkey == curses.KEY_UP or self.pressedkey == 65:
            # 'UP' > Up in the server list
            self.cursor_up(stats)
            logger.debug(f"Server {self.cursor + 1}/{len(stats)} selected")
        elif self.pressedkey == curses.KEY_DOWN or self.pressedkey == 66:
            # 'DOWN' > Down in the server list
            self.cursor_down(stats)
            logger.debug(f"Server {self.cursor + 1}/{len(stats)} selected")
        elif self.pressedkey == curses.KEY_PPAGE:
            # 'Page UP' > Prev page in the server list
            self.cursor_pageup(stats)
            logger.debug(f"PageUP: Server ({self._current_page + 1}/{self._page_max}) pages.")
        elif self.pressedkey == curses.KEY_NPAGE:
            # 'Page Down' > Next page in the server list
            self.cursor_pagedown(stats)
            logger.debug(f"PageDown: Server {self._current_page + 1}/{self._page_max} pages")
        elif self.pressedkey == ord('1'):
            self._stats_list = None
            refresh = True
        elif self.pressedkey == ord('2'):
            self._revesed_sorting = False
            self._stats_list = stats.copy()
            refresh = True
        elif self.pressedkey == ord('3'):
            self._revesed_sorting = True
            self._stats_list = stats.copy()
            refresh = True

        if refresh:
            self._current_page = 0
            self.cursor_position = 0
            self.flush(stats)

        # Return the key code
        return self.pressedkey

    def update(self, stats, duration=3, cs_status=None, return_to_browser=False):
        """Update the servers' list screen.

        Wait for __refresh_time sec / catch key every 100 ms.

        :param stats: Dict of dict with servers stats
        :param cs_status:
        :param duration:
        :param return_to_browser:
        """
        # Flush display
        logger.debug(f'Servers list: {stats}')
        self.flush(stats)

        # Wait
        exitkey = False
        countdown = Timer(self.__refresh_time)
        while not countdown.finished() and not exitkey:
            # Getkey
            pressedkey = self.__catch_key(stats)
            # Is it an exit or select server key ?
            exitkey = pressedkey == ord('\x1b') or pressedkey == ord('q') or pressedkey == 10
            if not exitkey and pressedkey > -1:
                # Redraw display
                self.flush(stats)
            # Wait 100ms...
            self.wait()

        return self.active_server

    def flush(self, stats):
        """Update the servers' list screen.

        :param stats: List of dict with servers stats
        """
        self.erase()
        self.display(stats)

    def display(self, stats, cs_status=None):
        """Display the servers list.

        :return: True if the stats have been displayed else False (no server available)
        """
        # Init the internal line/column for Glances Curses
        self.init_line_column()

        # Get the current screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        stats_max = screen_y - 3
        self._page_max_lines = stats_max
        self._page_max = int(math.ceil(len(stats) / stats_max))

        # Display header
        x, y = self.__display_header(stats, 0, 0, screen_x, screen_y)

        # Display Glances server list
        # ================================
        return self.__display_server_list(stats, x, y, screen_x, screen_y)

    def __display_header(self, stats, x, y, screen_x, screen_y):
        stats_len = len(stats)
        stats_max = screen_y - 3
        if stats_len == 0:
            if self.first_scan and not self.args.disable_autodiscover:
                msg = 'Glances is scanning your network. Please wait...'
                self.first_scan = False
            else:
                msg = 'No Glances server available'
        elif len(stats) == 1:
            msg = 'One Glances server available'
        else:
            msg = f'{stats_len} Glances servers available'
        # if self.args.disable_autodiscover:
        #     msg += ' (auto discover is disabled)'
        if screen_y > 1:
            self.term_window.addnstr(y, x, msg, screen_x - x, self.colors_list['TITLE'])

            msg = f'{self._get_status_count(stats)}'
            self.term_window.addnstr(y + 1, x, msg, screen_x - x)

        if stats_len > stats_max and screen_y > 2:
            page_lines = self.get_pagelines(stats)
            status_count = self._get_status_count(stats)
            msg = f'{page_lines} servers displayed.({self._current_page + 1}/{self._page_max}) {status_count}'
            self.term_window.addnstr(y + 1, x, msg, screen_x - x)

        return x, y

    def __build_column_def(self, current_page):
        """Define the column and it size to display in the browser"""
        column_def = {'name': 16, 'ip': 15, 'status': 9, 'protocol': 8}

        # Add dynamic columns
        for server_stat in current_page:
            for k, v in server_stat.items():
                if k.endswith('_decoration'):
                    column_def[k.split('_decoration')[0]] = 6
        return column_def

    def __display_server_list(self, stats, x, y, screen_x, screen_y):
        if not stats:
            # No server to display
            return False

        stats_list = self._get_stats(stats)
        start_line = self._page_max_lines * self._current_page
        end_line = start_line + self.get_pagelines(stats_list)
        current_page = stats_list[start_line:end_line]
        column_def = self.__build_column_def(current_page)

        # Display table header
        stats_max = screen_y - 3
        y = 2
        xc = x + 2
        # First line (plugin name)
        for k, v in column_def.items():
            k_split = k.split('_')
            if len(k_split) == 1:
                xc += v + self.space_between_column
                continue
            if xc < screen_x and y < screen_y and v is not None:
                self.term_window.addnstr(y, xc, k_split[0].upper(), screen_x - x, self.colors_list['BOLD'])
                xc += v + self.space_between_column
        xc = x + 2
        y += 1
        # Second line (for item/key)
        for k, v in column_def.items():
            k_split = k.split('_')
            if xc < screen_x and y < screen_y and v is not None:
                self.term_window.addnstr(y, xc, ' '.join(k_split[1:]).upper(), screen_x - x, self.colors_list['BOLD'])
                xc += v + self.space_between_column
        y += 1

        # If a servers has been deleted from the list...
        # ... and if the cursor is in the latest position
        if self.cursor > len(stats) - 1:
            # Set the cursor position to the latest item
            self.cursor = len(stats) - 1

        # Display table
        line = 0
        for server_stat in current_page:
            # Limit the number of displayed server (see issue #1256)
            if line >= stats_max:
                continue

            # Display line for server stats
            cpt = 0
            xc = x

            # Is the line selected ?
            if line == self.cursor:
                # Display cursor
                self.term_window.addnstr(y, xc, ">", screen_x - xc, self.colors_list['BOLD'])

            # Display the line
            xc += 2
            for k, v in column_def.items():
                if xc < screen_x and y < screen_y:
                    # Display server stats
                    value = server_stat.get(k, '?')
                    if isinstance(value, float):
                        value = round(value, 1)
                    if k == 'name' and 'alias' in server_stat and server_stat['alias'] is not None:
                        value = server_stat['alias']
                    decoration = self.colors_list.get(
                        server_stat[k + '_decoration'].replace('_LOG', '')
                        if k + '_decoration' in server_stat
                        else self.colors_list[server_stat['status']],
                        self.colors_list['DEFAULT'],
                    )
                    if k == 'status':
                        decoration = self.colors_list[server_stat['status']]
                    self.term_window.addnstr(y, xc, format(value), v, decoration)
                    xc += v + self.space_between_column
                cpt += 1
            # Next line, next server...
            y += 1
            line += 1

        return True

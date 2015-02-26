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

import sys
import threading
import time

import msvcrt

from glances.core.glances_logging import logger

try:
    import colorconsole
    import colorconsole.terminal
except ImportError:
    logger.critical("Colorconsole module not found. Glances cannot start in standalone mode.")
    sys.exit(1)

try:
    import queue
except ImportError:  # Python 2
    import Queue as queue


class ListenGetch(threading.Thread):

    def __init__(self, nom=''):
        threading.Thread.__init__(self)
        self.Terminated = False
        self.q = queue.Queue()

    def run(self):
        while not self.Terminated:
            char = msvcrt.getch()
            self.q.put(char)

    def stop(self):
        self.Terminated = True
        while not self.q.empty():
            self.q.get()

    def get(self, default=None):
        try:
            return ord(self.q.get_nowait())
        except Exception:
            return default


class Screen(object):

    COLOR_DEFAULT_WIN = '0F'  # 07'#'0F'
    COLOR_BK_DEFAULT = colorconsole.terminal.colors["BLACK"]
    COLOR_FG_DEFAULT = colorconsole.terminal.colors["WHITE"]

    def __init__(self, nc):
        self.nc = nc
        self.term = colorconsole.terminal.get_terminal()
        # os.system('color %s' % self.COLOR_DEFAULT_WIN)
        self.listen = ListenGetch()
        self.listen.start()

        self.term.clear()

    def subwin(self, x, y):
        return self

    def keypad(self, screen_id):
        return None

    def nodelay(self, screen_id):
        return None

    def getch(self):
        return self.listen.get(27)

    def erase(self):
        self.reset()
        return None

    def addnstr(self, y, x, msg, ln, typo=0):
        try:
            fgs, bks = self.nc.colors[typo]
        except Exception:
            fgs, bks = self.COLOR_FG_DEFAULT, self.COLOR_BK_DEFAULT
        self.term.set_color(fg=fgs, bk=bks)
        self.term.print_at(x, y, msg.ljust(ln))
        self.term.set_color(fg=self.COLOR_FG_DEFAULT, bk=self.COLOR_BK_DEFAULT)

    def getmaxyx(self):
        x = (self.term._Terminal__get_console_info().srWindow.Right -
             self.term._Terminal__get_console_info().srWindow.Left + 1)
        y = (self.term._Terminal__get_console_info().srWindow.Bottom -
             self.term._Terminal__get_console_info().srWindow.Top + 1)
        return [y, x]

    def reset(self):
        self.term.clear()
        self.term.reset()
        return None

    def restore_buffered_mode(self):
        self.term.restore_buffered_mode()
        return None


class WCurseLight(object):

    COLOR_WHITE = colorconsole.terminal.colors["WHITE"]
    COLOR_RED = colorconsole.terminal.colors["RED"]
    COLOR_GREEN = colorconsole.terminal.colors["GREEN"]
    COLOR_BLUE = colorconsole.terminal.colors["LBLUE"]
    COLOR_MAGENTA = colorconsole.terminal.colors["LPURPLE"]
    COLOR_BLACK = colorconsole.terminal.colors["BLACK"]
    A_UNDERLINE = 0
    A_BOLD = 0
    COLOR_PAIRS = 9
    colors = {}

    def __init__(self):
        self.term = Screen(self)

    def initscr(self):
        return self.term

    def start_color(self):
        return None

    def use_default_colors(self):
        return None

    def noecho(self):
        return None

    def cbreak(self):
        return None

    def curs_set(self, y):
        return None

    def has_colors(self):
        return True

    def echo(self):
        return None

    def nocbreak(self):
        return None

    def endwin(self):
        self.term.reset()
        self.term.restore_buffered_mode()
        self.term.listen.stop()

    def napms(self, t):
        time.sleep(t / 1000 if t > 1000 else 1)

    def init_pair(self, color_id, fg, bk):
        self.colors[color_id] = [max(fg, 0), max(bk, 0)]

    def color_pair(self, color_id):
        return color_id

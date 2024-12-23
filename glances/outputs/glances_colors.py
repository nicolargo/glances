#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances colors."""

import sys

from glances.logger import logger

try:
    import curses
except ImportError:
    logger.critical("Curses module not found. Glances cannot start in standalone mode.")
    sys.exit(1)


class GlancesColors:
    """Class to manage colors in Glances UI
    For the moment limited to Curses interface.
    But will be used in the WebUI through the issue #2048"""

    def __init__(self, args) -> None:
        self.args = args

        # Define "home made" bold
        self.A_BOLD = 0 if args.disable_bold else curses.A_BOLD

        # Set defaults curses colors
        try:
            if hasattr(curses, 'start_color'):
                curses.start_color()
                logger.debug(f'Curses interface compatible with {curses.COLORS} colors')
            if hasattr(curses, 'use_default_colors'):
                # Use -1 to use the default foregound/background color
                curses.use_default_colors()
            if hasattr(curses, 'assume_default_colors'):
                # Define the color index 0 with -1 and -1 for foregound/background
                # = curses.init_pair(0, -1, -1)
                curses.assume_default_colors(-1, -1)
        except Exception as e:
            logger.warning(f'Error initializing terminal color ({e})')

        if curses.has_colors():
            # The screen is compatible with a colored design
            # ex: export TERM=xterm-256color
            #     export TERM=xterm-color
            self.__define_colors()
        else:
            # The screen is NOT compatible with a colored design
            # switch to B&W text styles
            # ex: export TERM=xterm-mono
            self.__define_bw()

    def __repr__(self) -> dict:
        return self.get()

    def __define_colors(self) -> None:
        curses.init_pair(1, -1, -1)
        if self.args.disable_bg:
            curses.init_pair(2, curses.COLOR_RED, -1)
            curses.init_pair(3, curses.COLOR_GREEN, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        else:
            curses.init_pair(2, -1, curses.COLOR_RED)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(5, -1, curses.COLOR_MAGENTA)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)
        curses.init_pair(7, curses.COLOR_GREEN, -1)
        curses.init_pair(8, curses.COLOR_MAGENTA, -1)

        # Colors text styles
        self.DEFAULT = curses.color_pair(1)
        self.OK_LOG = curses.color_pair(3) | self.A_BOLD
        self.CPU_TIME = curses.color_pair(8)
        self.CAREFUL_LOG = curses.color_pair(4) | self.A_BOLD
        self.WARNING_LOG = curses.color_pair(5) | self.A_BOLD
        self.CRITICAL_LOG = curses.color_pair(2) | self.A_BOLD
        self.OK = curses.color_pair(7)
        self.CAREFUL = curses.color_pair(4)
        self.WARNING = curses.color_pair(8) | self.A_BOLD
        self.CRITICAL = curses.color_pair(6) | self.A_BOLD
        self.INFO = curses.color_pair(4)
        self.FILTER = self.A_BOLD
        self.SELECTED = self.A_BOLD
        self.SEPARATOR = curses.color_pair(1)

        if curses.COLORS > 8:
            # ex: export TERM=xterm-256color
            try:
                curses.init_pair(9, curses.COLOR_CYAN, -1)
                curses.init_pair(10, curses.COLOR_YELLOW, -1)
            except Exception:
                curses.init_pair(9, -1, -1)
                curses.init_pair(10, -1, -1)
            self.FILTER = curses.color_pair(9) | self.A_BOLD
            self.SELECTED = curses.color_pair(10) | self.A_BOLD

            # Define separator line style
            try:
                curses.init_color(11, 500, 500, 500)
                curses.init_pair(11, curses.COLOR_BLACK, -1)
                self.SEPARATOR = curses.color_pair(11)
            except Exception:
                # Catch exception in TMUX
                pass

            # Overwrite CAREFUL color
            try:
                if self.args.disable_bg:
                    curses.init_pair(12, curses.COLOR_BLUE, -1)
                else:
                    curses.init_pair(12, -1, curses.COLOR_BLUE)
            except Exception:
                pass
            else:
                self.CAREFUL_LOG = curses.color_pair(12) | self.A_BOLD

    def __define_bw(self) -> None:
        # The screen is NOT compatible with a colored design
        # switch to B&W text styles
        # ex: export TERM=xterm-mono
        self.DEFAULT = -1
        self.OK_LOG = -1
        self.CPU_TIME = self.A_BOLD
        self.CAREFUL_LOG = self.A_BOLD
        self.WARNING_LOG = curses.A_UNDERLINE
        self.CRITICAL_LOG = curses.A_REVERSE
        self.OK = -1
        self.CAREFUL = self.A_BOLD
        self.WARNING = curses.A_UNDERLINE
        self.CRITICAL = curses.A_REVERSE
        self.INFO = self.A_BOLD
        self.FILTER = self.A_BOLD
        self.SELECTED = self.A_BOLD
        self.SEPARATOR = -1

    def get(self) -> dict:
        return {
            'DEFAULT': self.DEFAULT,
            'UNDERLINE': curses.A_UNDERLINE,
            'BOLD': self.A_BOLD,
            'SORT': curses.A_UNDERLINE | self.A_BOLD,
            'OK': self.OK,
            'MAX': self.OK | self.A_BOLD,
            'FILTER': self.FILTER,
            'TITLE': self.A_BOLD,
            'PROCESS': self.OK,
            'PROCESS_SELECTED': self.OK | curses.A_UNDERLINE,
            'STATUS': self.OK,
            'CPU_TIME': self.CPU_TIME,
            'CAREFUL': self.CAREFUL,
            'WARNING': self.WARNING,
            'CRITICAL': self.CRITICAL,
            'OK_LOG': self.OK_LOG,
            'CAREFUL_LOG': self.CAREFUL_LOG,
            'WARNING_LOG': self.WARNING_LOG,
            'CRITICAL_LOG': self.CRITICAL_LOG,
            'PASSWORD': curses.A_PROTECT,
            'SELECTED': self.SELECTED,
            'INFO': self.INFO,
            'ERROR': self.SELECTED,
            'SEPARATOR': self.SEPARATOR,
        }

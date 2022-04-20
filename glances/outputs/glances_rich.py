# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2022 Nicolargo <nicolas@nicolargo.com>
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

"""Stdout interface class."""

import time
import sys

from glances.logger import logger
from glances.keyboard import KBHit
from glances.timer import Timer

# Import curses library for "normal" operating system
try:
    from rich import print
    from rich.columns import Columns
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.console import Console
    from rich.live import Live
except ImportError:
    logger.critical("Rich module not found. Glances cannot start in standalone mode.")
    sys.exit(1)


class GlancesRich(object):

    """This class manages the Rich display (it replaces Curses in Glances version 4 and higher)."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Init keyboard
        self.kb = KBHit()

        # Init the screen
        self.console = Console()
        self.layout = Layout()
        self.live = Live(console=self.console, screen=True, auto_refresh=False)

    def end(self):
        # Reset the keyboard
        self.kb.set_normal_term()

    def update(self, stats, duration=3):
        """Display stats to the Rich interface.

        Refresh every duration second.
        """
        # If the duration is < 0 (update + export time > refresh_time)
        # Then display the interface and log a message
        if duration <= 0:
            logger.warning('Update and export time higher than refresh_time.')
            duration = 0.1

        # Wait duration (in s) time
        isexitkey = False
        countdown = Timer(duration)

        self.update_layout(stats)
        with Live(console=self.console, screen=True, auto_refresh=False) as live:
            while not countdown.finished() and not isexitkey:
                # Manage if a key was pressed
                if self.kb.kbhit():
                    pressedkey = ord(self.kb.getch())
                    isexitkey = pressedkey == ord('\x1b') or pressedkey == ord('q')
                else:
                    pressedkey = -1
                    isexitkey = False

                # if pressedkey == curses.KEY_F5:
                #     # Were asked to refresh
                #     return isexitkey

                # if isexitkey and self.args.help_tag:
                #     # Quit from help should return to main screen, not exit #1874
                #     self.args.help_tag = not self.args.help_tag
                #     isexitkey = False
                #     return isexitkey

                # Redraw display
                live.update(self.layout, refresh=True)
                # Overwrite the timeout with the countdown
                time.sleep(countdown.get())

        return isexitkey

    def update_layout(self, stats):
        self.layout.split_column(
            Layout(name="top")
        )
        self.layout["top"].split_row(
            Layout(
                Panel("Quickview", title="Quickview", subtitle=""),
                name="quickview"
            ),
            Layout(
                Panel("Cpu", title="Cpu", subtitle=""),
                name="cpu"
            ),
            Layout(
                Panel("Mem", title="Mem", subtitle=""),
                name="mem"
            ),
            Layout(
                Panel("Swap", title="Swap", subtitle=""),
                name="swap"
            ),
            Layout(
                Panel("Load", title="Load", subtitle=""),
                name="Load"
            ),
        )


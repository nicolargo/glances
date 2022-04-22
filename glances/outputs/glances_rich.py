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
from glances.compat import nativestr, u
from glances.processes import glances_processes, sort_processes_key_list

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

# Define plugins order in TUI menu
_top_left = [
    'quicklook',

]

_top_right = [
    'cpu',
    'percpu',
    'gpu',
    'mem',
    'memswap',
    'load'
]

_bottom_left = [
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
_bottom_left_width = 34

_bottom_right = [
    'docker',
    'processcount',
    'amps',
    'processlist',
    'alert'
]


class GlancesRich(object):

    """This class manages the Rich display (it replaces Curses in Glances version 4 and higher)."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Init keyboard
        self.kb = KBHit()

        # Init cursor
        self.args.cursor_position = 0

        # Init the screen
        self.console = Console(soft_wrap=True)
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
            self.live.update(self.layout, refresh=True)
            # Overwrite the timeout with the countdown
            time.sleep(countdown.get())

        return isexitkey

    def update_layout(self, stats):
        """Update the layout with the stats"""
        # Get the stats and apply the Rich transformation
        stats_display = self.plugins_to_rich(stats)

        # Update the layout
        self.layout.split_column(
            Layout(name='top',
                   size=stats_display['cpu']['height'],
                   renderable=False),
            Layout(name='bottom',
                   renderable=False),
        )
        self.layout['top'].split_row(
            Layout(name='top_left',
                   #size=TODO,
                   renderable=False),
            Layout(name='top_right',
                   renderable=False)
        )
        self.layout['top_left'].split_row(
            *[Layout(
                Panel(stats_display[p]['data'],
                      title=stats_display[p]['title'],
                      subtitle=stats_display[p]['subtitle'],
                      height=stats_display[p]['height']),
                name=p) for p in _top_left
              if stats_display[p]['display'] and len(stats_display[p]['data']) > 0]
        )
        self.layout['top_right'].split_row(
            *[Layout(
                Panel(stats_display[p]['data'],
                      title=stats_display[p]['title'],
                      subtitle=stats_display[p]['subtitle'],
                      height=stats_display[p]['height']),
                name=p,
                size=stats_display[p]['width']) for p in _top_right
              if stats_display[p]['display'] and len(stats_display[p]['data']) > 0]
        )
        self.layout['bottom'].split_row(
            Layout(name='bottom_left',
                   renderable=False,
                   size=_bottom_left_width + 8),
            Layout(name='bottom_right',
                   renderable=False)
        )
        # _bottom_left
        self.layout['bottom_left'].split_column(
            *[Layout(
                Panel(stats_display[p]['data'],
                      title=stats_display[p]['title'],
                      subtitle=stats_display[p]['subtitle']),
                size=stats_display[p]['height'],
                name=p) for p in _bottom_left
              if stats_display[p]['display'] and len(stats_display[p]['data']) > 0]
        )
        self.layout['bottom_right'].split_column(
            *[Layout(
                Panel(stats_display[p]['data'],
                      title=stats_display[p]['title'],
                      subtitle=stats_display[p]['subtitle']),
                size=stats_display[p]['height'],
                name=p) for p in _bottom_right
              if stats_display[p]['display'] and len(stats_display[p]['data']) > 0]
        )

    def plugins_to_rich(self, stats):
        ret = {}
        for p in stats.getPluginsList(enable=False):
            ret[p] = self._plugin_to_rich(stats, p)
        return ret

    def _plugin_to_rich(self, stats, plugin):
        """Return a Rich representation of the plugin"""
        ret = {'title': '', 'subtitle': '', 'data': '', 'width': 0, 'height': 0, 'display': False}
        if stats.get_plugin(plugin):
            _max_width = None
            if plugin == 'processlist':
                # @TODO: do not work..
                glances_processes.max_processes = 10
            elif plugin in _bottom_left:
                _max_width = _bottom_left_width
            stat_display = stats.get_plugin(plugin).get_stats_display(args=self.args,
                                                                      max_width=_max_width)
            stat_repr = [i['msg'] for i in stat_display['msgdict']]
            ret['title'] =  plugin.capitalize()
            ret['data'] = ''.join(stat_repr)
            ret['width'] = self._get_width(stat_display) + 4 # +4 for borders
            ret['height'] = self._get_height(stat_display) + 2 # +2 for borders
            ret['display'] = stat_display['display']
            if plugin == 'diskio':
                logger.info(ret)
        return ret

    def _get_width(self, stats_display, without_option=False):
        """Return the width of the formatted curses message."""
        try:
            if without_option:
                # Size without options
                c = len(
                    max(
                        ''.join(
                            [
                                (u(u(nativestr(i['msg'])).encode('ascii', 'replace')) if not i['optional'] else "")
                                for i in stats_display['msgdict']
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
                            [u(u(nativestr(i['msg'])).encode('ascii', 'replace')) for i in stats_display['msgdict']]
                        ).split('\n'),
                        key=len,
                    )
                )
        except Exception as e:
            logger.debug('ERROR: Can not compute plugin width ({})'.format(e))
            return 0
        else:
            return c

    def _get_height(self, stats_display):
        """Return the height of the formatted curses message.

        The height is defined by the number of '\n' (new line).
        """
        try:
            c = [i['msg'] for i in stats_display['msgdict']].count('\n')
        except Exception as e:
            logger.debug('ERROR: Can not compute plugin height ({})'.format(e))
            return 0
        else:
            return c + 1

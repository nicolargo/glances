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

from pprint import pformat
import time
import sys

from glances.logger import logger
from glances.keyboard import KBHit
from glances.timer import Timer
from glances.globals import nativestr, u
from glances.processes import glances_processes, sort_processes_key_list

# Import curses library for "normal" operating system
try:
    from rich.panel import Panel
    from rich.panel import Padding
    from rich.measure import Measurement
    from rich.table import Table
    from rich.layout import Layout
    from rich.style import Style
    from rich.console import Console
    from rich.live import Live
except ImportError:
    logger.critical("Rich module not found. Glances cannot start in standalone mode.")
    sys.exit(1)

# Define plugins order in TUI menu
_top = [
    'quicklook',
    'cpu',
    'percpu',
    'gpu',
    'mem',
    'memswap',
    'load'
]

_middle_left = [
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
    'sensors'
]
_middle_left_width = 34

_middle_right = [
    'docker',
    'processcount',
    'amps',
    'processlist',
    'alert'
]

_bottom = [
    'now'
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
        self._create_main_layout(stats_display)
        self._update_top_layout(stats, stats_display)
        self._update_middle_left_layout(stats, stats_display)
        self._update_middle_right_layout(stats, stats_display)
        self._update_bottom_layout(stats, stats_display)

    def _create_main_layout(self, stats_display):
        # Create the layout
        self.layout.split_column(
            Layout(name='top',
                   size=max([stats_display[p]['height'] if stats_display[p]['display'] else 0 for p in _top]),
                   renderable=False),
            Layout(name='middle',
                   renderable=False),
            Layout(name='bottom',
                   size=max([stats_display[p]['height'] if stats_display[p]['display'] else 0 for p in _bottom]),
                   renderable=False),
        )
        self.layout['middle'].split_row(
            Layout(name='middle_left',
                   size=_middle_left_width + 8,
                   renderable=False),
            Layout(name='middle_right',
                   renderable=False)
        )

    def _update_top_layout(self, stats, stats_display):
        """Update the top layout"""
        renderable = []
        for p in _top:
            # The quicklook plugin will be ignore...
            if stats_display[p]['display'] and len(stats_display[p]['content']) > 0:
                r = Layout(stats_display[p]['content_repr'],
                           size=stats_display[p]['width'],
                           name=p)
                renderable.append(r)
        self.layout['top'].split_row(*renderable)

    def _update_middle_left_layout(self, stats, stats_display):
        """Update the middle left layout"""
        self.layout['middle_left'].split_column(
            *[Layout(stats_display[p]['content_repr'],
                     size=stats_display[p]['height'],
                     name=p) for p in _middle_left
              if stats_display[p]['display'] and len(stats_display[p]['content']) > 0],
            Layout(Padding(''),
                   name='middle_left_padding')
        )

    def _update_middle_right_layout(self, stats, stats_display):
        """Update the middle right layout"""
        renderable = []
        for p in _middle_right:
            # The quicklook plugin will be ignore...
            if stats_display[p]['display'] and len(stats_display[p]['content']) > 0:
                r = Layout(Panel(stats_display[p]['content_repr'],
                                 title=stats_display[p]['title'],
                                 subtitle=stats_display[p]['subtitle']),
                           size=stats_display[p]['height'],
                           name=p)
                renderable.append(r)
        self.layout['middle_right'].split_column(*renderable)

    def _update_bottom_layout(self, stats, stats_display):
        """Update the bottom layout"""
        self.layout['bottom'].split_row(
            *[Layout(
                Panel(stats_display[p]['content_repr'],
                      title=stats_display[p]['title'],
                      subtitle=stats_display[p]['subtitle']),
                name=p) for p in _bottom
              if stats_display[p]['display'] and len(stats_display[p]['content']) > 0]
        )

    def plugins_to_rich(self, stats):
        """Get the 'Rich' stats from the plugins
        Return: a dict of dicts with:
            - key: plugin name
            - value: dict returned by _plugin_to_rich
        Ex: {'cpu': {'title': '', 'subtitle': '', 'content': '', 'width': 0, 'height': 0, 'display': False}, ... }
        """
        ret = {}
        # Some plugin should be processed after others
        after = ['quicklook', 'processlist']
        for p in [p for p in stats.getPluginsList(enable=False) if p not in after]:
            ret[p] = self._plugin_to_rich(stats, p)
        # It is time to process its
        for p in after:
            if p == 'processlist':
                height_but_processlist = max([ret[p]['height'] for p in _top if p in ret]) + \
                    sum([ret[p]['height'] for p in _middle_right if p in ret]) + \
                    max([ret[p]['height'] for p in _bottom if p in ret])
                glances_processes.max_processes = self.console.height - height_but_processlist
                ret[p] = self._plugin_to_rich(stats, p, max_width=None)
            else:
                width_but_after = sum([ret[p]['width']
                                      for p in _top if p in ret and len(ret[p]['content']) > 0 and ret[p]['display']])
                max_width = self.console.width - width_but_after - 13
                ret[p] = self._plugin_to_rich(stats, p, max_width=max_width)
        return ret

    def _plugin_to_rich(self, stats, plugin, max_width=None):
        """Return a dict: Rich representation of the plugin"""

        # Init the returned structure
        ret = {
            'title': '',
            'subtitle': '',
            'content': '',
            'width': 0,
            'height': 0,
            'display': False
        }

        if not stats.get_plugin(plugin):
            return ret

        if plugin in _middle_left:
            max_width = _middle_left_width

        if hasattr(stats.get_plugin(plugin), 'msg_for_human') and stats.get_plugin(plugin).get_template():
            # Grab the stats to display
            ret = stats.get_plugin(plugin).msg_for_human(args=self.args,
                                                         max_width=max_width)

            # TODO: Style should be moved in a dedicated class
            # decoration:
            #     DEFAULT: no decoration
            #     UNDERLINE: underline
            #     BOLD: bold
            #     TITLE: for stat title
            #     PROCESS: for process name
            #     STATUS: for process status
            #     NICE: for process niceness
            #     CPU_TIME: for process cpu time
            #     OK: Value is OK and non logged
            #     OK_LOG: Value is OK and logged
            #     CAREFUL: Value is CAREFUL and non logged
            #     CAREFUL_LOG: Value is CAREFUL and logged
            #     WARNING: Value is WARNING and non logged
            #     WARNING_LOG: Value is WARNING and logged
            #     CRITICAL: Value is CRITICAL and non logged
            #     CRITICAL_LOG: Value is CRITICAL and logged
            rich_style = {
                'title_style': Style(bold=True),
            }
            # https://en.wikipedia.org/wiki/BBCode
            bbcode_style = {
                'DEFAULT': '{}',
                'HEADER': '[bold]{}[/]',
                'OK': '[green bold]{}[/]',
                'OK_LOG': '[green bold reverse]{}[/]',
                'CAREFUL': '[magenta bold]{}[/]',
                'CAREFUL_LOG': '[magenta bold reverse]{}[/]',
                'WARNING': '[yellow bold]{}[/]',
                'WARNING_LOG': '[yellow bold reverse]{}[/]',
                'CRITICAL': '[red bold]{}[/]',
                'CRITICAL_LOG': '[red bold reverse]{}[/]',
            }
            # Create the table
            ret['content_repr'] = Table(title=ret['title'],
                                        title_style=rich_style['title_style'],
                                        title_justify='left',
                                        caption=ret['subtitle'],
                                        box=None,
                                        show_header=False,
                                        show_footer=False,
                                        expand=True,
                                        padding=(0,0,0,0),
                                        )
            # Fill the table
            # Add the columns
            # for row in ret['content']:
            #     for col in row:
            #         ret['content_repr'].add_column()
            # Add the rows
            for row in ret['content']:
                row_with_style = []
                for col in row:
                    data = col['data']
                    data_format = bbcode_style[col['style']] if col['style'] in bbcode_style else '{}'
                    row_with_style.append(data_format.format(data))
                ret['content_repr'].add_row(*row_with_style)
        else:
            # TODO: to be removed when all plugins will have a msg_rich method
            # Grab the stats to display
            stat_display = stats.get_plugin(plugin).get_stats_display(args=self.args,
                                                                        max_width=max_width)
            # Buil the object (a dict) to display
            stat_repr = [i['msg'] for i in stat_display['msgdict']]
            ret['title'] = plugin.capitalize()
            ret['content'] = ''.join(stat_repr)
            ret['content_repr'] = ret['content']
            ret['width'] = self._get_width(stat_display) + 4  # +4 for borders
            ret['height'] = self._get_height(stat_display) + 2  # +2 for borders
            ret['display'] = stat_display['display']

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

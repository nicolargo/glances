#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Issue interface class."""

import os
import platform
import pprint
import sys
import time

import psutil

import glances
from glances import __version__, psutil_version
from glances.timer import Counter

TERMINAL_WIDTH = 79


class colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    BLUE = '\033[94m'
    NO = '\033[0m'

    def disable(self):
        self.RED = ''
        self.GREEN = ''
        self.BLUE = ''
        self.ORANGE = ''
        self.NO = ''


class GlancesStdoutIssue:
    """This class manages the Issue display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def print_version(self):
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')
        sys.stdout.write(f'Glances {colors.BLUE + __version__ + colors.NO} ({os.path.realpath(glances.__file__)})\n')
        sys.stdout.write(f'Python {colors.BLUE + platform.python_version() + colors.NO} ({sys.executable})\n')
        sys.stdout.write(f'PsUtil {colors.BLUE + psutil_version + colors.NO} ({os.path.realpath(psutil.__file__)})\n')
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')
        sys.stdout.flush()

    def print_issue(self, plugin, result, message):
        sys.stdout.write(f'{colors.BLUE + plugin}{result}{message}')
        sys.stdout.write(colors.NO + '\n')
        sys.stdout.flush()

    def update(self, stats, duration=3):
        """Display issue"""
        self.print_version()

        for plugin in sorted(stats._plugins):
            if stats._plugins[plugin].is_disabled():
                continue
            try:
                # Update the stats
                stats._plugins[plugin].update()
            except Exception:
                pass

        time.sleep(2)

        counter_total = Counter()
        for plugin in sorted(stats._plugins):
            if stats._plugins[plugin].is_disabled():
                # If current plugin is disable
                # then continue to next plugin
                result = colors.NO + '[NA]'.rjust(18 - len(plugin))
                message = colors.NO
                self.print_issue(plugin, result, message)
                continue
            # Start the counter
            counter = Counter()
            counter.reset()
            stat = None
            stat_error = None
            try:
                # Update the stats
                stats._plugins[plugin].update()
                # Get the stats
                stat = stats.get_plugin(plugin).get_export()
                # Hide private information
                if plugin == 'ip':
                    for key in stat.keys():
                        stat[key] = '***'
            except Exception as e:
                stat_error = e
            if stat_error is None:
                result = (colors.GREEN + '[OK]   ' + colors.BLUE + f' {counter.get():.5f}s ').rjust(41 - len(plugin))
                if isinstance(stat, list) and len(stat) > 0 and 'key' in stat[0]:
                    key = 'key={} '.format(stat[0]['key'])
                    stat_output = pprint.pformat([stat[0]], compact=True, width=120, depth=3)
                    message = colors.ORANGE + key + colors.NO + '\n' + stat_output[0:-1] + ', ...' + stat_output[-1]
                else:
                    message = '\n' + colors.NO + pprint.pformat(stat, compact=True, width=120, depth=2)
            else:
                result = (colors.RED + '[ERROR]' + colors.BLUE + f' {counter.get():.5f}s ').rjust(41 - len(plugin))
                message = colors.NO + str(stat_error)[0 : TERMINAL_WIDTH - 41]

            # Display the result
            self.print_issue(plugin, result, message)

        # Display total time need to update all plugins
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')
        print(f"Total time to update all stats: {colors.BLUE}{counter_total.get():.5f}s{colors.NO}")
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')

        # Return True to exit directly (no refresh)
        return True

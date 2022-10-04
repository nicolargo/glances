# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Issue interface class."""

import os
import sys
import platform
import shutil
import time

from glances.timer import Counter
from glances import __version__, psutil_version

import psutil
import glances

try:
    TERMINAL_WIDTH = shutil.get_terminal_size(fallback=(79, 24)).columns
except:
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


class GlancesStdoutIssue(object):

    """This class manages the Issue display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def print_version(self):
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')
        sys.stdout.write(
            'Glances {} ({})\n'.format(colors.BLUE + __version__ + colors.NO, os.path.realpath(glances.__file__))
        )
        sys.stdout.write('Python {} ({})\n'.format(colors.BLUE + platform.python_version() + colors.NO, sys.executable))
        sys.stdout.write(
            'PsUtil {} ({})\n'.format(colors.BLUE + psutil_version + colors.NO, os.path.realpath(psutil.__file__))
        )
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')
        sys.stdout.flush()

    def print_issue(self, plugin, result, message):
        sys.stdout.write('{}{}{}'.format(colors.BLUE + plugin, result, message))
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
            except Exception as e:
                stat_error = e
            if stat_error is None:
                result = (colors.GREEN + '[OK]   ' + colors.BLUE + ' {:.5f}s '.format(counter.get())).rjust(
                    41 - len(plugin)
                )
                if isinstance(stat, list) and len(stat) > 0 and 'key' in stat[0]:
                    key = 'key={} '.format(stat[0]['key'])
                    message = colors.ORANGE + key + colors.NO + str(stat)[0 : TERMINAL_WIDTH - 41 - len(key)]
                else:
                    message = colors.NO + str(stat)[0 : TERMINAL_WIDTH - 41]
            else:
                result = (colors.RED + '[ERROR]' + colors.BLUE + ' {:.5f}s '.format(counter.get())).rjust(
                    41 - len(plugin)
                )
                message = colors.NO + str(stat_error)[0 : TERMINAL_WIDTH - 41]
            self.print_issue(plugin, result, message)

        # Display total time need to update all plugins
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')
        print("Total time to update all stats: {}{:.5f}s{}".format(colors.BLUE, counter_total.get(), colors.NO))
        sys.stdout.write('=' * TERMINAL_WIDTH + '\n')

        # Return True to exit directly (no refresh)
        return True

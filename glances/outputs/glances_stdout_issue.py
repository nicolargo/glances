# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

"""Issue interface class."""

import time
import sys
import shutil

from glances.logger import logger
from glances.compat import printandflush
from glances.timer import Counter
from glances import __version__, psutil_version

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

    """
    This class manages the Issue display.
    """

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def print_version(self):
        msg = 'Glances version {} with PsUtil {}'.format(
            colors.BLUE + __version__ + colors.NO,
            colors.BLUE + psutil_version + colors.NO)
        sys.stdout.write('='*len(msg) + '\n')
        sys.stdout.write(msg)
        sys.stdout.write(colors.NO + '\n')
        sys.stdout.write('='*len(msg) + '\n')
        sys.stdout.flush()

    def print_issue(self, plugin, result, message):
        sys.stdout.write('{}{}{}'.format(
            colors.BLUE + plugin, result, message))
        sys.stdout.write(colors.NO + '\n')
        sys.stdout.flush()

    def update(self,
               stats,
               duration=3):
        """Display issue
        """
        self.print_version()
        for plugin in sorted(stats._plugins):
            if stats._plugins[plugin].is_disable():
                # If current plugin is disable
                # then continue to next plugin
                result = colors.NO + '[N/A]'.rjust(19 - len(plugin))
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
                result = (colors.GREEN +
                          '[OK]   ' +
                          colors.BLUE +
                          ' {:.5f}s '.format(counter.get())).rjust(41 - len(plugin))
                if isinstance(stat, list) and len(stat) > 0 and 'key' in stat[0]:
                    key = 'key={} '.format(stat[0]['key'])
                    message = colors.ORANGE + key + colors.NO + str(stat)[0:TERMINAL_WIDTH-41-len(key)]
                else:
                    message = colors.NO + str(stat)[0:TERMINAL_WIDTH-41]
            else:
                result = (colors.RED +
                          '[ERROR]' +
                          colors.BLUE +
                          ' {:.5f}s '.format(counter.get())).rjust(41 - len(plugin))
                message = colors.NO + str(stat_error)[0:TERMINAL_WIDTH-41]
            self.print_issue(plugin, result, message)

        # Return True to exit directly (no refresh)
        return True

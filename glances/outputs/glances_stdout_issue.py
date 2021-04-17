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

    def print_issue(self, plugin, result, message):
        sys.stdout.write('{}{}{}'.format(colors.BLUE + plugin, result, message))
        sys.stdout.write(colors.NO + '\n')
        sys.stdout.flush()

    def update(self,
               stats,
               duration=3):
        """Display issue
        """
        # printandflush(sorted(stats.getPluginsList()))
        for plugin in sorted(stats.getPluginsList()):
            stat = None
            stat_error = None
            try:
                stat = stats.get_plugin(plugin).get_export()
            except Exception as e:
                stat_error = e
            if stat_error is None:
                result = colors.GREEN + '[OK] '.rjust(25 - len(plugin))
                message = colors.NO + str(stat)[0:TERMINAL_WIDTH-25]
            else:
                result = colors.RED + '[ERROR] '.rjust(25 - len(plugin))
                message = colors.NO + str(stat_error)[0:TERMINAL_WIDTH-25]
            self.print_issue(plugin, result, message)

        # Return True to exit directly (no refresh)
        return True

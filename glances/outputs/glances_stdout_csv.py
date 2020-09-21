# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""StdoutCsv interface class."""

import time

from glances.logger import logger
from glances.compat import printandflush, get_stat_from_path, iteritems


class GlancesStdoutCsv(object):

    """
    This class manages the StdoutCsv display.
    """

    separator = ','
    na = 'N/A'

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Display the header only on the first line
        self.header = True

    def end(self):
        pass

    def update(self,
               stats,
               duration=3):
        """Display stats to stdout.
        Refresh every duration second.
        """
        # Build the stats list
        stat_flatten = dict()
        for stat_name in self.args.stdout_csv.split(','):
            stat_path = stat_name.split('.')
            stat_flatten.update(get_stat_from_path(stats, stat_path))

        if self.header:
            # Display header one time
            printandflush(self.separator.join(stat_flatten.keys()))
            self.header = False

        printandflush(self.separator.join([str(i) for i in stat_flatten.values()]))

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)

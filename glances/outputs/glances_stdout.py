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

"""Stdout interface class."""

import time

from glances.logger import logger
from glances.compat import printandflush, get_stat_from_path, iteritems


class GlancesStdout(object):

    """
    This class manages the Stdout display.
    """

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def update(self, stats, duration=3):
        for stat_name in self.args.stdout.split(','):
            stat_path = stat_name.split('.')
            stat_flatten = get_stat_from_path(stats, stat_path)
            for k, v in iteritems(stat_flatten):
                printandflush("{}: {}".format(k, v))
        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)

    def update_old(self, stats, duration=3):
        for stat_name in self.args.stdout.split(','):
            stat_path = stat_name.split('.')
            plugin = stat_path[0]
            stat_path = stat_path[1:]
            if plugin in stats.getPluginsList() and \
               stats.get_plugin(plugin).is_enable():
                printandflush("{}: {}".format(stat_name,
                                              get_stat_from_path(stats.get_plugin(plugin).get_export(),
                                                                 stat_path)))
            else:
                logger.error('Plugin {} does not exist or is disabled'.format(plugin))
                continue

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)

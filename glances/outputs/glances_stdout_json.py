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

from glances.logger import logger
from glances.compat import printandflush


class GlancesStdoutJson(object):

    """This class manages the Stdout JSON display."""

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

        # Build the list of plugin to display
        self.plugins_list = self.build_list()

    def build_list(self):
        """Return a list of tuples taken from self.args.stdout_json

        :return: A list of tuples. Example -[(plugin, attribute), ... ]
        """
        return self.args.stdout_json.split(',')

    def end(self):
        pass

    def update(self, stats, duration=3):
        """Display stats in JSON format to stdout.

        Refresh every duration second.
        """
        for plugin in self.plugins_list:
            # Check if the plugin exist and is enable
            if plugin in stats.getPluginsList() and stats.get_plugin(plugin).is_enabled():
                stat = stats.get_plugin(plugin).get_json()
            else:
                continue
            # Display stats
            printandflush('{}: {}'.format(plugin, stat))

        # Wait until next refresh
        if duration > 0:
            time.sleep(duration)

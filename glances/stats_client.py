# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""The stats server manager."""

import sys

from glances.stats import GlancesStats
from glances.globals import sys_path
from glances.logger import logger


class GlancesStatsClient(GlancesStats):

    """This class stores, updates and gives stats for the client."""

    def __init__(self, config=None, args=None):
        """Init the GlancesStatsClient class."""
        super(GlancesStatsClient, self).__init__()

        # Init the configuration
        self.config = config

        # Init the arguments
        self.args = args

        # Load plugins and exports
        self.load_plugins_and_exports(self.args)

    def set_plugins(self, input_plugins):
        """Set the plugin list according to the Glances server."""
        header = "glances_"
        for item in input_plugins:
            # Import the plugin
            plugin = __import__(header + item)
            # Add the plugin to the dictionary
            # The key is the plugin name
            # for example, the file glances_xxx.py
            # generate self._plugins_list["xxx"] = ...
            logger.debug("Server uses {0} plugin".format(item))
            self._plugins[item] = plugin.Plugin()
        # Restoring system path
        sys.path = sys_path

    def update(self, input_stats):
        """Update all the stats."""
        # For Glances client mode
        for p in input_stats:
            # Update plugin stats with items sent by the server
            self._plugins[p].set_stats(input_stats[p])
            # Update the views for the updated stats
            self._plugins[p].update_views()

#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The stats server manager."""

import importlib
import sys

from glances.globals import sys_path
from glances.logger import logger
from glances.stats import GlancesStats


class GlancesStatsClient(GlancesStats):
    """This class stores, updates and gives stats for the client."""

    def __init__(self, config=None, args=None):
        """Init the GlancesStatsClient class."""
        super().__init__(config=config, args=args)

        # Init the configuration
        self.config = config

        # Init the arguments
        self.args = args

    def set_plugins(self, input_plugins):
        """Set the plugin list according to the Glances server."""
        header = "glances.plugins."
        for item in input_plugins:
            # Import the plugin
            try:
                plugin = importlib.import_module(header + item)
            except ImportError as e:
                # Server plugin can not be imported from the client side
                logger.error(f"Can not import {item} plugin ({e}). Please upgrade your Glances client/server version.")
            else:
                # Add the plugin to the dictionary
                # The key is the plugin name
                # for example, the file glances_xxx.py
                # generate self._plugins_list["xxx"] = ...
                logger.debug(f"Server uses {item} plugin")
                if hasattr(plugin, 'PluginModel'):
                    # Old fashion way to load the plugin (before Glances 5.0)
                    # Should be removed in Glances 5.0 - see #3170
                    self._plugins[item] = getattr(plugin, 'PluginModel')(args=self.args)
                elif hasattr(plugin, item.capitalize() + 'Plugin'):
                    # New fashion way to load the plugin (after Glances 5.0)
                    self._plugins[item] = getattr(plugin, item.capitalize() + 'Plugin')(args=self.args)

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

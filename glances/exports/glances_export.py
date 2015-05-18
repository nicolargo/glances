# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""
I am your father...

...for all Glances exports IF.
"""

# Import system libs
# None...

# Import Glances lib
from glances.core.glances_logging import logger


class GlancesExport(object):

    """Main class for Glances export IF."""

    def __init__(self, config=None, args=None):
        """Init the export class."""
        # Export name (= module name without glances_)
        self.export_name = self.__class__.__module__[len('glances_'):]
        logger.debug("Init export interface %s" % self.export_name)

        # Init the config & args
        self.config = config
        self.args = args

        # By default export is disable
        # Had to be set to True in the __init__ class of child
        self.export_enable = False

    def exit(self):
        """Close the export module."""
        logger.debug("Finalise export interface %s" % self.export_name)

    def plugins_to_export(self):
        """Return the list of plugins to export."""
        return ['cpu',
                'percpu',
                'load',
                'mem',
                'memswap',
                'network',
                'diskio',
                'fs',
                'processcount',
                'ip',
                'system',
                'uptime']

    def update(self, stats):
        """Update stats to a server.

        The method builds two lists: names and values
        and calls the export method to export the stats.
        """
        if not self.export_enable:
            return False

        # Get the stats
        all_stats = stats.getAll()
        all_limits = stats.getAllLimits()
        plugins = stats.getAllPlugins()

        # Loop over available plugins
        for i, plugin in enumerate(plugins):
            if plugin in self.plugins_to_export():
                if isinstance(all_stats[i], list):
                    for item in all_stats[i]:
                        item.update(all_limits[i])
                        export_names = list('{0}.{1}'.format(item[item['key']], key)
                                            for key in item.keys())
                        export_values = list(item.values())
                        self.export(plugin, export_names, export_values)
                elif isinstance(all_stats[i], dict):
                    export_names = list(all_stats[i].keys()) + list(all_limits[i].keys())
                    export_values = list(all_stats[i].values()) + list(all_limits[i].values())
                    self.export(plugin, export_names, export_values)

        return True

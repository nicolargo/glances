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

    """Main class for Glances' export IF."""

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
        """Return the list of plugins to export"""
        return ['cpu', 'load', 'mem', 'memswap', 'network', 'diskio', 'fs', 'processcount']

    def update(self, stats):
        """Update stats to a server.
        The method buil two list: names and values
        and call the export method to export the stats"""
        if not self.export_enable:
            return False

        # Get the stats
        all_stats = stats.getAll()
        plugins = stats.getAllPlugins()

        # Loop over available plugin
        i = 0
        for plugin in plugins:
            if plugin in self.plugins_to_export():
                if type(all_stats[i]) is list:
                    for item in all_stats[i]:
                        export_names = map(
                            lambda x: item[item['key']] + '.' + x, item.keys())
                        export_values = item.values()
                        self.export(plugin, export_names, export_values)
                elif type(all_stats[i]) is dict:
                    export_names = all_stats[i].keys()
                    export_values = all_stats[i].values()
                    self.export(plugin, export_names, export_values)
            i += 1

        return True

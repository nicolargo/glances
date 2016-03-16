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

from glances.compat import iteritems, iterkeys
from glances.logger import logger


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
                'uptime',
                'sensors',
                'docker']

    def get_item_key(self, item):
        """Return the value of the item 'key'."""
        try:
            ret = item[item['key']]
        except KeyError:
            logger.error("No 'key' available in {0}".format(item))
        if isinstance(ret, list):
            return ret[0]
        else:
            return ret

    def parse_tags(self, tags):
        """Parse tags into a dict.

        tags: a comma separated list of 'key:value' pairs.
            Example: foo:bar,spam:eggs
        dtags: a dict of tags.
            Example: {'foo': 'bar', 'spam': 'eggs'}
        """
        dtags = {}
        if tags:
            try:
                dtags = dict([x.split(':') for x in tags.split(',')])
            except ValueError:
                # one of the 'key:value' pairs was missing
                logger.info('Invalid tags passed: %s', tags)
                dtags = {}

        return dtags

    def update(self, stats):
        """Update stats to a server.

        The method builds two lists: names and values
        and calls the export method to export the stats.

        Be aware that CSV export overwrite this class and use a specific one.
        """
        if not self.export_enable:
            return False

        # Get all the stats & limits
        all_stats = stats.getAllExports()
        all_limits = stats.getAllLimits()
        # Get the plugins list
        plugins = stats.getAllPlugins()

        # Loop over available plugins
        for i, plugin in enumerate(plugins):
            if plugin in self.plugins_to_export():
                if isinstance(all_stats[i], dict):
                    all_stats[i].update(all_limits[i])
                elif isinstance(all_stats[i], list):
                    all_stats[i] += all_limits[i]
                else:
                    continue
                export_names, export_values = self.__build_export(all_stats[i])
                self.export(plugin, export_names, export_values)

        return True

    def __build_export(self, stats):
        """Build the export lists."""
        export_names = []
        export_values = []

        if isinstance(stats, dict):
            # Stats is a dict
            # Is there a key ?
            if 'key' in iterkeys(stats):
                pre_key = '{0}.'.format(stats[stats['key']])
            else:
                pre_key = ''
            # Walk through the dict
            for key, value in iteritems(stats):
                if isinstance(value, list):
                    try:
                        value = value[0]
                    except IndexError:
                        value = ''
                if isinstance(value, dict):
                    item_names, item_values = self.__build_export(value)
                    item_names = [pre_key + key.lower() + str(i) for i in item_names]
                    export_names += item_names
                    export_values += item_values
                else:
                    export_names.append(pre_key + key.lower())
                    export_values.append(value)
        elif isinstance(stats, list):
            # Stats is a list (of dict)
            # Recursive loop through the list
            for item in stats:
                item_names, item_values = self.__build_export(item)
                export_names += item_names
                export_values += item_values
        return export_names, export_values

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

"""Statsd interface class."""

# Import sys libs
from statsd import StatsClient
from numbers import Number
import sys

# Import Glances lib
from glances.core.glances_logging import logger
from ConfigParser import NoSectionError, NoOptionError
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the Statsd export module."""

    def __init__(self, config=None, args=None):
        """Init the Statsd export IF."""
        GlancesExport.__init__(self, config=config, args=args)

        # Load the InfluxDB configuration file
        self.host = None
        self.port = None
        self.prefix = None
        self.export_enable = self.load_conf()
        if not self.export_enable:
            sys.exit(2)

        # Default prefix for stats is 'glances'
        if self.prefix is None:
            self.prefix = 'glances'

        # Init the Statsd client
        self.client = StatsClient(self.host,
                                  int(self.port),
                                  prefix=self.prefix)

    def load_conf(self, section="statsd"):
        """Load the Statsd configuration in the Glances configuration file"""
        if self.config is None:
            return False
        try:
            self.host = self.config.get_raw_option(section, "host")
            self.port = self.config.get_raw_option(section, "port")
        except NoSectionError:
            logger.critical("No Statsd configuration found")
            return False
        except NoOptionError as e:
            logger.critical("Error in the Statsd configuration (%s)" % e)
            return False
        else:
            logger.debug("Load Statsd from the Glances configuration file")
        # Prefix is optional
        try:
            self.prefix = self.config.get_raw_option(section, "prefix")
        except NoOptionError as e:
            pass
        return True

    def init(self, prefix='glances'):
        """Init the connection to the Statsd server"""
        if not self.export_enable:
            return None
        return StatsClient(self.host,
                           self.port,
                           prefix=prefix)

    def update(self, stats):
        """Update stats to the InfluxDB server."""
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
                        self.__export(plugin, export_names, export_values)
                elif type(all_stats[i]) is dict:
                    export_names = all_stats[i].keys()
                    export_values = all_stats[i].values()
                    self.__export(plugin, export_names, export_values)
            i += 1

        return True

    def __export(self, name, columns, points):
        """Export the stats to the Statsd server"""
        for i in range(0, len(columns)):
            if not isinstance(points[i], Number):
                continue
            stat_name = '{0}.{1}'.format(name, columns[i])
            stat_value = points[i]
            try:
                self.client.gauge(stat_name, stat_value)
            except Exception as e:
                logger.critical("Can not export stats to Statsd (%s)" % e)

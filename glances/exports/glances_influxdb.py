# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

"""InfluxDB interface class."""

# Import sys libs
from influxdb import InfluxDBClient
import sys

# Import Glances lib
from glances.core.glances_globals import is_py3
from glances.core.glances_logging import logger
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the InfluxDB export module."""

    def __init__(self, args=None):
        """Init the CSV export IF."""
        GlancesExport.__init__(self, args=args)

        # InfluxDB server configuration
        # self.influxdb_host = args.influxdb_host
        self.influxdb_host = 'localhost'
        self.influxdb_port = '8086'
        self.influxdb_user = 'root'
        self.influxdb_password = 'root'
        self.influxdb_db = 'glances'

        # Init the InfluxDB client
        self.client = InfluxDBClient(self.influxdb_host,
                                     self.influxdb_port,
                                     self.influxdb_user,
                                     self.influxdb_password,
                                     self.influxdb_db)

        logger.info(
            "Stats exported to InfluxDB server: {0}".format(self.client._baseurl))

    def update(self, stats):
        """Update stats to the InfluxDB server."""

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
                            lambda x: item[item['key']] + '_' + x, item.keys())
                        export_values = item.values()
                        self.write_to_influxdb(plugin, export_names, export_values)
                elif type(all_stats[i]) is dict:
                    export_names = all_stats[i].keys()
                    export_values = all_stats[i].values()
                    self.write_to_influxdb(plugin, export_names, export_values)
            i += 1

    def write_to_influxdb(self, name, columns, points):
        """Write the points to the InfluxDB server"""
        data = [
            {
                "name": name,
                "columns": columns,
                "points": [points]
            }]
        self.client.write_points(data)

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

import sys

from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError
from influxdb.influxdb08 import InfluxDBClient as InfluxDBClient08
from influxdb.influxdb08.client import InfluxDBClientError as InfluxDBClientError08

# Constants for tracking specific behavior
INFLUXDB_08 = '0.8'
INFLUXDB_09PLUS = '0.9+'


class Export(GlancesExport):

    """This class manages the InfluxDB export module."""

    def __init__(self, config=None, args=None):
        """Init the InfluxDB export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.db = None

        # Optionals configuration keys
        self.prefix = None
        self.tags = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf('influxdb',
                                            mandatories=['host', 'port',
                                                         'user', 'password',
                                                         'db'],
                                            options=['prefix', 'tags'])
        if not self.export_enable:
            sys.exit(2)

        # Init the InfluxDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the InfluxDB server."""
        if not self.export_enable:
            return None

        try:
            db = InfluxDBClient(host=self.host,
                                port=self.port,
                                username=self.user,
                                password=self.password,
                                database=self.db)
            get_all_db = [i['name'] for i in db.get_list_database()]
            self.version = INFLUXDB_09PLUS
        except InfluxDBClientError:
            # https://github.com/influxdb/influxdb-python/issues/138
            logger.info("Trying fallback to InfluxDB v0.8")
            db = InfluxDBClient08(host=self.host,
                                  port=self.port,
                                  username=self.user,
                                  password=self.password,
                                  database=self.db)
            get_all_db = [i['name'] for i in db.get_list_database()]
            self.version = INFLUXDB_08
        except InfluxDBClientError08 as e:
            logger.critical("Cannot connect to InfluxDB database '%s' (%s)" % (self.db, e))
            sys.exit(2)

        if self.db in get_all_db:
            logger.info(
                "Stats will be exported to InfluxDB server: {}".format(db._baseurl))
        else:
            logger.critical("InfluxDB database '%s' did not exist. Please create it" % self.db)
            sys.exit(2)

        return db

    def export(self, name, columns, points):
        """Write the points to the InfluxDB server."""
        logger.debug("Export {} stats to InfluxDB".format(name))
        # Manage prefix
        if self.prefix is not None:
            name = self.prefix + '.' + name
        # Create DB input
        if self.version == INFLUXDB_08:
            data = [{'name': name, 'columns': columns, 'points': [points]}]
        else:
            # Convert all int to float (mandatory for InfluxDB>0.9.2)
            # Correct issue#750 and issue#749
            for i, _ in enumerate(points):
                try:
                    points[i] = float(points[i])
                except (TypeError, ValueError) as e:
                    logger.debug("InfluxDB error during stat convertion %s=%s (%s)" % (columns[i], points[i], e))

            data = [{'measurement': name,
                     'tags': self.parse_tags(self.tags),
                     'fields': dict(zip(columns, points))}]
        # Write input to the InfluxDB database
        try:
            self.client.write_points(data)
        except Exception as e:
            logger.error("Cannot export {} stats to InfluxDB ({})".format(name, e))

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

"""InfluxDB interface class."""

import sys

from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError


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
        self.protocol = 'http'
        self.prefix = None
        self.tags = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf('influxdb',
                                            mandatories=['host', 'port',
                                                         'user', 'password',
                                                         'db'],
                                            options=['protocol',
                                                     'prefix',
                                                     'tags'])
        if not self.export_enable:
            sys.exit(2)

        # Init the InfluxDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the InfluxDB server."""
        if not self.export_enable:
            return None

        # Correct issue #1530
        if self.protocol is not None and (self.protocol.lower() == 'https'):
            ssl = True
        else:
            ssl = False

        try:
            db = InfluxDBClient(host=self.host,
                                port=self.port,
                                ssl=ssl,
                                verify_ssl=False,
                                username=self.user,
                                password=self.password,
                                database=self.db)
            get_all_db = [i['name'] for i in db.get_list_database()]
        except InfluxDBClientError as e:
            logger.critical("Cannot connect to InfluxDB database '%s' (%s)" % (self.db, e))
            sys.exit(2)

        if self.db in get_all_db:
            logger.info(
                "Stats will be exported to InfluxDB server: {}".format(db._baseurl))
        else:
            logger.critical("InfluxDB database '%s' did not exist. Please create it" % self.db)
            sys.exit(2)

        return db

    def _normalize(self, name, columns, points):
        """Normalize data for the InfluxDB's data model."""

        for i, _ in enumerate(points):
            # Supported type:
            # https://docs.influxdata.com/influxdb/v1.5/write_protocols/line_protocol_reference/
            if points[i] is None:
                # Ignore points with None value
                del(points[i])
                del(columns[i])
                continue
            try:
                points[i] = float(points[i])
            except (TypeError, ValueError):
                pass
            else:
                continue
            try:
                points[i] = str(points[i])
            except (TypeError, ValueError):
                pass
            else:
                continue

        return [{'measurement': name,
                 'tags': self.parse_tags(self.tags),
                 'fields': dict(zip(columns, points))}]

    def export(self, name, columns, points):
        """Write the points to the InfluxDB server."""
        # Manage prefix
        if self.prefix is not None:
            name = self.prefix + '.' + name
        # Write input to the InfluxDB database
        if len(points) == 0:
            logger.debug("Cannot export empty {} stats to InfluxDB".format(name))
        else:
            try:
                self.client.write_points(self._normalize(name, columns, points), time_precision="s")
            except Exception as e:
                # Log level set to debug instead of error (see: issue #1561)
                logger.debug("Cannot export {} stats to InfluxDB ({})".format(name, e))
            else:
                logger.debug("Export {} stats to InfluxDB".format(name))

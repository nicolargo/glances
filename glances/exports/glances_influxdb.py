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

"""InfluxDB interface class."""

# Import sys libs
from influxdb import InfluxDBClient, client
import sys

# Import Glances lib
from glances.core.glances_logging import logger
from ConfigParser import NoSectionError, NoOptionError
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the InfluxDB export module."""

    def __init__(self, config=None, args=None):
        """Init the InfluxDB export IF."""
        GlancesExport.__init__(self, config=config, args=args)

        # Load the InfluxDB configuration file
        self.influxdb_host = None
        self.influxdb_port = None
        self.influxdb_user = None
        self.influxdb_password = None
        self.influxdb_db = None
        self.export_enable = self.load_conf()
        if not self.export_enable:
            sys.exit(2)

        # Init the InfluxDB client
        self.client = self.init()

    def load_conf(self, section="influxdb"):
        """Load the InfluxDb configuration in the Glances configuration file"""
        if self.config is None:
            return False
        try:
            self.influxdb_host = self.config.get_raw_option(section, "host")
            self.influxdb_port = self.config.get_raw_option(section, "port")
            self.influxdb_user = self.config.get_raw_option(section, "user")
            self.influxdb_password = self.config.get_raw_option(section, "password")
            self.influxdb_db = self.config.get_raw_option(section, "db")
        except NoSectionError:
            logger.critical("No InfluxDB configuration found")
            return False
        except NoOptionError as e:
            logger.critical("Error in the InfluxDB configuration (%s)" % e)
            return False
        else:
            logger.debug("Load InfluxDB from the Glances configuration file")
        return True

    def init(self):
        """Init the connection to the InfluxDB server"""
        if not self.export_enable:
            return None
        db = InfluxDBClient(self.influxdb_host,
                            self.influxdb_port,
                            self.influxdb_user,
                            self.influxdb_password,
                            self.influxdb_db)
        try:
            get_all_db = db.get_database_list()[0].values()
        except client.InfluxDBClientError as e:
            logger.critical("Can not connect to InfluxDB database '%s' (%s)" % (self.influxdb_db, e))
            sys.exit(2)

        if self.influxdb_db in get_all_db:
            logger.info(
                "Stats will be exported to InfluxDB server: {0}".format(db._baseurl))
        else:
            logger.critical("InfluxDB database '%s' did not exist. Please create it" % self.influxdb_db)
            sys.exit(2)
        return db

    def export(self, name, columns, points):
        """Write the points to the InfluxDB server"""
        data = [
            {
                "name": name,
                "columns": columns,
                "points": [points]
            }]
        try:
            self.client.write_points(data)
        except Exception as e:
            logger.error("Can not export stats to InfluxDB (%s)" % e)

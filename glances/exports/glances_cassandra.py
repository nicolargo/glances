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

"""Cassandra/Scylla interface class."""

import sys
from numbers import Number

from glances.compat import NoOptionError, NoSectionError
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from cassandra.cluster import Cluster
from cassandra.util import uuid_from_time
from cassandra import InvalidRequest
from datetime import datetime


class Export(GlancesExport):

    """This class manages the Cassandra/Scylla export module."""

    def __init__(self, config=None, args=None):
        """Init the Cassandra export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Load the Cassandra configuration file section
        self.host = None
        self.port = None
        self.protocol_version = 3
        self.keyspace = None
        self.replication_factor = 2
        self.table = None
        self.export_enable = self.load_conf()
        if not self.export_enable:
            sys.exit(2)

        # Init the Cassandra client
        self.cluster, self.session = self.init()

    def load_conf(self, section="cassandra"):
        """Load the Cassandra configuration in the Glances configuration file."""
        if self.config is None:
            return False
        try:
            self.host = self.config.get_value(section, 'host')
            self.port = self.config.get_value(section, 'port')
            self.keyspace = self.config.get_value(section, 'keyspace')
        except NoSectionError:
            logger.critical("No Cassandra configuration found")
            return False
        except NoOptionError as e:
            logger.critical("Error in the Cassandra configuration (%s)" % e)
            return False
        else:
            logger.debug("Load Cassandra from the Glances configuration file")

        # Optionals keys
        try:
            self.protocol_version = self.config.get_value(section, 'protocol_version')
        except NoOptionError:
            pass
        try:
            self.replication_factor = self.config.get_value(section, 'replication_factor')
        except NoOptionError:
            pass
        try:
            self.table = self.config.get_value(section, 'table')
        except NoOptionError:
            self.table = self.host

        return True

    def init(self):
        """Init the connection to the InfluxDB server."""
        if not self.export_enable:
            return None

        # Cluster
        try:
            cluster = Cluster([self.host],
                              port=int(self.port),
                              protocol_version=int(self.protocol_version))
            session = cluster.connect()
        except Exception as e:
            logger.critical("Cannot connect to Cassandra cluster '%s:%s' (%s)" % (self.host, self.port, e))
            sys.exit(2)

        # Keyspace
        try:
            session.set_keyspace(self.keyspace)
        except InvalidRequest as e:
            logger.info("Create keyspace {} on the Cassandra cluster".format(self.keyspace))
            c = "CREATE KEYSPACE %s WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '%s' }" % (self.keyspace, self.replication_factor)
            session.execute(c)
            session.set_keyspace(self.keyspace)

        logger.info(
            "Stats will be exported to Cassandra cluster {0} ({1}) in keyspace {2}".format(cluster.metadata.cluster_name,
                                                                                           cluster.metadata.all_hosts(),
                                                                                           self.keyspace))

        # Table
        try:
            session.execute("CREATE TABLE %s (plugin text, time timeuuid, stat map<text,float>, PRIMARY KEY (plugin, time)) WITH CLUSTERING ORDER BY (time DESC)" % self.table)
        except:
            logger.debug("Cassandra table %s already exist" % self.table)

        return cluster, session

    def export(self, name, columns, points):
        """Write the points to the Cassandra cluster."""
        logger.debug("Export {} stats to Cassandra".format(name))

        # Remove non number stats and convert all to float (for Boolean)
        data = {k: float(v) for (k, v) in dict(zip(columns, points)).iteritems() if isinstance(v, Number)}

        # Write input to the Cassandra table
        try:
            self.session.execute(
                """
                INSERT INTO localhost (plugin, time, stat)
                VALUES (%s, %s, %s)
                """,
                (name, uuid_from_time(datetime.now()), data)
            )
        except Exception as e:
            logger.error("Cannot export {} stats to Cassandra ({})".format(name, e))

    def exit(self):
        """Close the Cassandra export module."""
        # To ensure all connections are properly closed
        self.session.shutdown()
        self.cluster.shutdown()
        # Call the father method
        super(Export, self).exit()

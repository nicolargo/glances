# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Cassandra/Scylla interface class."""

import sys
from datetime import datetime
from numbers import Number

from glances.logger import logger
from glances.exports.export import GlancesExport

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.util import uuid_from_time
from cassandra import InvalidRequest


class Export(GlancesExport):

    """This class manages the Cassandra/Scylla export module."""

    def __init__(self, config=None, args=None):
        """Init the Cassandra export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.keyspace = None

        # Optional configuration keys
        self.protocol_version = 3
        self.replication_factor = 2
        self.table = None
        self.username = None
        self.password = None

        # Load the Cassandra configuration file section
        self.export_enable = self.load_conf(
            'cassandra',
            mandatories=['host', 'port', 'keyspace'],
            options=['protocol_version', 'replication_factor', 'table', 'username', 'password'],
        )
        if not self.export_enable:
            sys.exit(2)

        # Init the Cassandra client
        self.cluster, self.session = self.init()

    def init(self):
        """Init the connection to the Cassandra server."""
        if not self.export_enable:
            return None

        # if username and/or password are not set the connection will try to connect with no auth
        auth_provider = PlainTextAuthProvider(username=self.username, password=self.password)

        # Cluster
        try:
            cluster = Cluster(
                [self.host],
                port=int(self.port),
                protocol_version=int(self.protocol_version),
                auth_provider=auth_provider,
            )
            session = cluster.connect()
        except Exception as e:
            logger.critical("Cannot connect to Cassandra cluster '%s:%s' (%s)" % (self.host, self.port, e))
            sys.exit(2)

        # Keyspace
        try:
            session.set_keyspace(self.keyspace)
        except InvalidRequest:
            logger.info("Create keyspace {} on the Cassandra cluster".format(self.keyspace))
            c = "CREATE KEYSPACE %s WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '%s' }" % (
                self.keyspace,
                self.replication_factor,
            )
            session.execute(c)
            session.set_keyspace(self.keyspace)

        logger.info(
            "Stats will be exported to Cassandra cluster {} ({}) in keyspace {}".format(
                cluster.metadata.cluster_name, cluster.metadata.all_hosts(), self.keyspace
            )
        )

        # Table
        try:
            session.execute(
                "CREATE TABLE %s (plugin text, time timeuuid, stat map<text,float>, PRIMARY KEY (plugin, time)) \
                    WITH CLUSTERING ORDER BY (time DESC)"
                % self.table
            )
        except Exception:
            logger.debug("Cassandra table %s already exist" % self.table)

        return cluster, session

    def export(self, name, columns, points):
        """Write the points to the Cassandra cluster."""
        logger.debug("Export {} stats to Cassandra".format(name))

        # Remove non number stats and convert all to float (for Boolean)
        data = {k: float(v) for (k, v) in dict(zip(columns, points)).iteritems() if isinstance(v, Number)}

        # Write input to the Cassandra table
        try:
            stmt = "INSERT INTO {} (plugin, time, stat) VALUES (?, ?, ?)".format(self.table)
            query = self.session.prepare(stmt)
            self.session.execute(query, (name, uuid_from_time(datetime.now()), data))
        except Exception as e:
            logger.error("Cannot export {} stats to Cassandra ({})".format(name, e))

    def exit(self):
        """Close the Cassandra export module."""
        # To ensure all connections are properly closed
        self.session.shutdown()
        self.cluster.shutdown()
        # Call the father method
        super(Export, self).exit()

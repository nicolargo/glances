#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""MongoDB interface class."""

import sys
from urllib.parse import quote_plus

import pymongo

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the MongoDB export module."""

    def __init__(self, config=None, args=None):
        """Init the MongoDB export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.db = None

        # Optional configuration keys
        self.user = None
        self.password = None

        # Load the Cassandra configuration file section
        self.export_enable = self.load_conf('mongodb', mandatories=['host', 'port', 'db'], options=['user', 'password'])
        if not self.export_enable:
            sys.exit(2)

        # Init the CouchDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the CouchDB server."""
        if not self.export_enable:
            return None

        server_uri = f'mongodb://{quote_plus(self.user)}:{quote_plus(self.password)}@{self.host}:{self.port}'

        try:
            client = pymongo.MongoClient(server_uri)
            client.admin.command('ping')
        except Exception as e:
            logger.critical(f"Cannot connect to MongoDB server {self.host}:{self.port} ({e})")
            sys.exit(2)
        else:
            logger.info("Connected to the MongoDB server")

        return client

    def database(self):
        """Return the CouchDB database object"""
        return self.client[self.db]

    def export(self, name, columns, points):
        """Write the points to the MongoDB server."""
        logger.debug(f"Export {name} stats to MongoDB")

        # Create DB input
        data = dict(zip(columns, points))

        # Write data to the MongoDB database
        try:
            self.database()[name].insert_one(data)
        except Exception as e:
            logger.error(f"Cannot export {name} stats to MongoDB ({e})")

#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CouchDB interface class."""

#
# How to test ?
#
# 1) docker run -d -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=admin -p 5984:5984 --name my-couchdb couchdb
# 2) ./venv/bin/python -m glances -C ./conf/glances.conf --export couchdb --quiet
# 3) Result can be seen at: http://127.0.0.1:5984/_utils
#

import sys
from datetime import datetime

import pycouchdb

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the CouchDB export module."""

    def __init__(self, config=None, args=None):
        """Init the CouchDB export IF."""
        super().__init__(config=config, args=args)

        # Load the CouchDB configuration file section
        # User and Password are mandatory with CouchDB 3.0 and higher
        self.export_enable = self.load_conf('couchdb', mandatories=['host', 'port', 'db', 'user', 'password'])
        if not self.export_enable:
            sys.exit(2)

        # Init the CouchDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the CouchDB server."""
        if not self.export_enable:
            return None

        # @TODO: https
        server_uri = f'http://{self.user}:{self.password}@{self.host}:{self.port}/'

        try:
            s = pycouchdb.Server(server_uri)
        except Exception as e:
            logger.critical(f"Cannot connect to CouchDB server ({e})")
            sys.exit(2)
        else:
            logger.info("Connected to the CouchDB server version {}".format(s.info()['version']))

        try:
            s.database(self.db)
        except Exception:
            # Database did not exist
            # Create it...
            s.create(self.db)
            logger.info(f"Create CouchDB database {self.db}")
        else:
            logger.info(f"CouchDB database {self.db} already exist")

        return s.database(self.db)

    def export(self, name, columns, points):
        """Write the points to the CouchDB server."""
        logger.debug(f"Export {name} stats to CouchDB")

        # Create DB input
        data = dict(zip(columns, points))

        # Add the type and the timestamp in ISO format
        data['type'] = name
        data['time'] = datetime.now().isoformat()[:-3] + 'Z'

        # Write data to the CouchDB database
        try:
            self.client.save(data)
        except Exception as e:
            logger.error(f"Cannot export {name} stats to CouchDB ({e})")

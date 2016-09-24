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

"""CouchDB interface class."""

import sys
from datetime import datetime

from glances.compat import NoOptionError, NoSectionError
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

import couchdb
import couchdb.mapping


class Export(GlancesExport):

    """This class manages the CouchDB export module."""

    def __init__(self, config=None, args=None):
        """Init the CouchDB export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Load the Couchdb configuration file section ([export_couchdb])
        self.host = None
        self.port = None
        self.user = None
        self.password = None
        self.db = None
        self.export_enable = self.load_conf()
        if not self.export_enable:
            sys.exit(2)

        # Init the CouchDB client
        self.client = self.init()

    def load_conf(self, section="couchdb"):
        """Load the CouchDB configuration in the Glances configuration file."""
        if self.config is None:
            return False
        try:
            self.host = self.config.get_value(section, 'host')
            self.port = self.config.get_value(section, 'port')
            self.db = self.config.get_value(section, 'db')
        except NoSectionError:
            logger.critical("No CouchDB configuration found")
            return False
        except NoOptionError as e:
            logger.critical("Error in the CouchDB configuration (%s)" % e)
            return False
        else:
            logger.debug("Load CouchDB from the Glances configuration file")

        # user and password are optional
        try:
            self.user = self.config.get_value(section, 'user')
            self.password = self.config.get_value(section, 'password')
        except NoOptionError:
            pass

        return True

    def init(self):
        """Init the connection to the CouchDB server."""
        if not self.export_enable:
            return None

        if self.user is None:
            server_uri = 'http://{}:{}/'.format(self.host,
                                                self.port)
        else:
            server_uri = 'http://{}:{}@{}:{}/'.format(self.user,
                                                      self.password,
                                                      self.host,
                                                      self.port)

        try:
            s = couchdb.Server(server_uri)
        except Exception as e:
            logger.critical("Cannot connect to CouchDB server %s (%s)" % (server_uri, e))
            sys.exit(2)
        else:
            logger.info("Connected to the CouchDB server %s" % server_uri)

        try:
            s[self.db]
        except Exception as e:
            # Database did not exist
            # Create it...
            s.create(self.db)
        else:
            logger.info("There is already a %s database" % self.db)

        return s

    def database(self):
        """Return the CouchDB database object"""
        return self.client[self.db]

    def export(self, name, columns, points):
        """Write the points to the CouchDB server."""
        logger.debug("Export {} stats to CouchDB".format(name))

        # Create DB input
        data = dict(zip(columns, points))

        # Set the type to the current stat name
        data['type'] = name
        data['time'] = couchdb.mapping.DateTimeField()._to_json(datetime.now())

        # Write input to the CouchDB database
        # Result can be view: http://127.0.0.1:5984/_utils
        try:
            self.client[self.db].save(data)
        except Exception as e:
            logger.error("Cannot export {} stats to CouchDB ({})".format(name, e))

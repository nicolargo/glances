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

"""ZeroMQ interface class."""

import sys
import json
import zmq
from zmq.utils.strtypes import asbytes

from glances.compat import NoOptionError, NoSectionError, b
from glances.logger import logger
from glances.exports.glances_export import GlancesExport


class Export(GlancesExport):

    """This class manages the ZeroMQ export module."""

    def __init__(self, config=None, args=None):
        """Init the ZeroMQ export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Load the ZeroMQ configuration file section ([export_zeromq])
        self.host = None
        self.port = None
        self.export_enable = self.load_conf()
        if not self.export_enable:
            sys.exit(2)

        # Init the ZeroMQ context
        self.context = None
        self.client = self.init()

    def load_conf(self, section="zeromq"):
        """Load the ZeroMQ configuration in the Glances configuration file."""
        if self.config is None:
            return False
        try:
            self.host = self.config.get_value(section, 'host')
            self.port = self.config.get_value(section, 'port')
            self.prefix = str(self.config.get_value(section, 'prefix'))
        except NoSectionError:
            logger.critical("No ZeroMQ configuration found")
            return False
        except NoOptionError as e:
            logger.critical("Error in the ZeroMQ configuration (%s)" % e)
            return False
        else:
            logger.debug("Load ZeroMQ from the Glances configuration file")

        return True

    def init(self):
        """Init the connection to the CouchDB server."""
        if not self.export_enable:
            return None

        server_uri = 'tcp://{}:{}'.format(self.host, self.port)

        try:
            self.context = zmq.Context()
            publisher = self.context.socket(zmq.PUB)
            publisher.bind(server_uri)
        except Exception as e:
            logger.critical("Cannot connect to ZeroMQ server %s (%s)" % (server_uri, e))
            sys.exit(2)
        else:
            logger.info("Connected to the ZeroMQ server %s" % server_uri)

        return publisher

    def exit(self):
        """Close the socket and context"""
        if self.client is not None:
            self.client.close()
        if self.context is not None:
            self.context.destroy()

    def export(self, name, columns, points):
        """Write the points to the ZeroMQ server."""
        logger.debug("Export {} stats to ZeroMQ".format(name))

        # Create DB input
        data = dict(zip(columns, points))

        # Do not publish empty stats
        if data == {}:
            return False

        # Glances envelopes the stats in a publish message with two frames:
        # - First frame containing the following prefix (STRING)
        # - Second frame with the Glances plugin name (STRING)
        # - Third frame with the Glances plugin stats (JSON)
        message = [b(self.prefix),
                   b(name),
                   asbytes(json.dumps(data))]

        # Write data to the ZeroMQ bus
        # Result can be view: tcp://host:port
        try:
            self.client.send_multipart(message)
        except Exception as e:
            logger.error("Cannot export {} stats to ZeroMQ ({})".format(name, e))

        return True

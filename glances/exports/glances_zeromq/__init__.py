#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""ZeroMQ interface class."""

import sys

import zmq

from glances.exports.export import GlancesExport
from glances.globals import b, json_dumps
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the ZeroMQ export module."""

    def __init__(self, config=None, args=None):
        """Init the ZeroMQ export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.prefix = None

        # Optionals configuration keys
        # N/A

        # Load the ZeroMQ configuration file section ([export_zeromq])
        self.export_enable = self.load_conf('zeromq', mandatories=['host', 'port', 'prefix'], options=[])
        if not self.export_enable:
            exit('Missing ZEROMQ config')

        # Init the ZeroMQ context
        self.context = None
        self.client = self.init()

    def init(self):
        """Init the connection to the CouchDB server."""
        if not self.export_enable:
            return None

        server_uri = f'tcp://{self.host}:{self.port}'

        try:
            self.context = zmq.Context()
            publisher = self.context.socket(zmq.PUB)
            publisher.bind(server_uri)
        except Exception as e:
            logger.critical(f"Cannot connect to ZeroMQ server {server_uri} ({e})")
            sys.exit(2)
        else:
            logger.info(f"Connected to the ZeroMQ server {server_uri}")

        return publisher

    def exit(self):
        """Close the socket and context"""
        if self.client is not None:
            self.client.close()
        if self.context is not None:
            self.context.destroy()

    def export(self, name, columns, points):
        """Write the points to the ZeroMQ server."""
        logger.debug(f"Export {name} stats to ZeroMQ")

        # Create DB input
        data = dict(zip(columns, points))

        # Do not publish empty stats
        if data == {}:
            return False

        # Glances envelopes the stats in a publish message with two frames:
        # - First frame containing the following prefix (STRING)
        # - Second frame with the Glances plugin name (STRING)
        # - Third frame with the Glances plugin stats (JSON)
        message = [b(self.prefix), b(name), json_dumps(data)]

        # Write data to the ZeroMQ bus
        # Result can be view: tcp://host:port
        try:
            self.client.send_multipart(message)
        except Exception as e:
            logger.error(f"Cannot export {name} stats to ZeroMQ ({e})")

        return True

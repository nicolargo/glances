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

"""Kafka interface class."""

import sys

from glances.logger import logger
from glances.compat import iteritems
from glances.exports.glances_export import GlancesExport

from kafka import KafkaProducer
import json
import codecs


class Export(GlancesExport):

    """This class manages the Kafka export module."""

    def __init__(self, config=None, args=None):
        """Init the Kafka export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.topic = None

        # Optionals configuration keys
        self.compression = None
        self.tags = None

        # Load the Kafka configuration file section
        self.export_enable = self.load_conf('kafka',
                                            mandatories=['host', 'port',
                                                         'topic'],
                                            options=['compression',
                                                     'tags'])
        if not self.export_enable:
            sys.exit(2)

        # Init the kafka client
        self.client = self.init()

    def init(self):
        """Init the connection to the Kafka server."""
        if not self.export_enable:
            return None

        # Build the server URI with host and port
        server_uri = '{}:{}'.format(self.host, self.port)

        try:
            s = KafkaProducer(bootstrap_servers=server_uri,
                              value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                              compression_type=self.compression)
        except Exception as e:
            logger.critical("Cannot connect to Kafka server %s (%s)" % (server_uri, e))
            sys.exit(2)
        else:
            logger.info("Connected to the Kafka server %s" % server_uri)

        return s

    def export(self, name, columns, points):
        """Write the points to the kafka server."""
        logger.debug("Export {} stats to Kafka".format(name))

        # Create DB input
        data = dict(zip(columns, points))
        if self.tags is not None:
            data.update(self.parse_tags(self.tags))

        # Send stats to the kafka topic
        # key=<plugin name>
        # value=JSON dict
        try:
            self.client.send(self.topic,
                             # Kafka key name needs to be bytes #1593
                             key=name.encode('utf-8'),
                             value=data)
        except Exception as e:
            logger.error("Cannot export {} stats to Kafka ({})".format(name, e))

    def exit(self):
        """Close the Kafka export module."""
        # To ensure all connections are properly closed
        self.client.flush()
        self.client.close()
        # Call the father method
        super(Export, self).exit()

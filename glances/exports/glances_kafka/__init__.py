# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Kafka interface class."""

import sys

from glances.logger import logger
from glances.globals import json_dumps
from glances.exports.export import GlancesExport

from kafka import KafkaProducer


class Export(GlancesExport):

    """This class manages the Kafka export module."""

    def __init__(self, config=None, args=None):
        """Init the Kafka export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.topic = None

        # Optional configuration keys
        self.compression = None
        self.tags = None

        # Load the Kafka configuration file section
        self.export_enable = self.load_conf(
            'kafka', mandatories=['host', 'port', 'topic'], options=['compression', 'tags']
        )
        if not self.export_enable:
            exit('Missing KAFKA config')

        # Init the kafka client
        self.client = self.init()

    def init(self):
        """Init the connection to the Kafka server."""
        if not self.export_enable:
            return None

        # Build the server URI with host and port
        server_uri = '{}:{}'.format(self.host, self.port)

        try:
            s = KafkaProducer(
                bootstrap_servers=server_uri,
                value_serializer=lambda v: json_dumps(v).encode('utf-8'),
                compression_type=self.compression,
            )
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
            self.client.send(
                self.topic,
                # Kafka key name needs to be bytes #1593
                key=name.encode('utf-8'),
                value=data,
            )
        except Exception as e:
            logger.error("Cannot export {} stats to Kafka ({})".format(name, e))

    def exit(self):
        """Close the Kafka export module."""
        # To ensure all connections are properly closed
        self.client.flush()
        self.client.close()
        # Call the father method
        super(Export, self).exit()

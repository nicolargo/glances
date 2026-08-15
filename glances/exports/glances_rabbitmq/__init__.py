#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""JMS interface class."""

import datetime
import socket
import sys
from numbers import Number

# Import pika for RabbitMQ
import pika

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the rabbitMQ export module."""

    def __init__(self, config=None, args=None):
        """Init the RabbitMQ export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.queue = None
        self.protocol = None

        # Optionals configuration keys
        # N/A

        # Load the rabbitMQ configuration file
        self.export_enable = self.load_conf(
            'rabbitmq', mandatories=['host', 'port', 'user', 'password', 'queue'], options=['protocol']
        )
        if not self.export_enable:
            exit('Missing RABBITMQ config')

        # Get the current hostname
        self.hostname = socket.gethostname()

        # Init the rabbitmq client
        self.client = self.init()

    def init(self):
        """Init the connection to the rabbitmq server."""
        if not self.export_enable:
            return None

        # Needed for when protocol is not specified and when protocol is upper case
        # only amqp and amqps supported
        if self.protocol is not None and (self.protocol.lower() == 'amqps'):
            self.protocol = 'amqps'
        else:
            self.protocol = 'amqp'

        try:
            parameters = pika.URLParameters(
                self.protocol + '://' + self.user + ':' + self.password + '@' + self.host + ':' + self.port + '/'
            )
            connection = pika.BlockingConnection(parameters)
            return connection.channel()
        except Exception as e:
            logger.critical(f"Connection to rabbitMQ server {self.host}:{self.port} failed. {e}")
            sys.exit(2)

    def export(self, name, columns, points):
        """Write the points in RabbitMQ."""
        data = 'hostname=' + self.hostname + ', name=' + name + ', dateinfo=' + datetime.datetime.utcnow().isoformat()
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            data += ", " + columns[i] + "=" + str(points[i])

        logger.debug(data)
        try:
            self.client.basic_publish(exchange='', routing_key=self.queue, body=data)
        except Exception as e:
            logger.error(f"Can not export stats to RabbitMQ ({e})")

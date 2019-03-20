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

"""JMS interface class."""

import datetime
import socket
import sys
from numbers import Number

from glances.compat import range
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

# Import pika for RabbitMQ
import pika


class Export(GlancesExport):

    """This class manages the rabbitMQ export module."""

    def __init__(self, config=None, args=None):
        """Init the RabbitMQ export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.queue = None

        # Optionals configuration keys
        # N/A

        # Load the rabbitMQ configuration file
        self.export_enable = self.load_conf('rabbitmq',
                                            mandatories=['host', 'port',
                                                         'user', 'password',
                                                         'queue'],
                                            options=[])
        if not self.export_enable:
            sys.exit(2)

        # Get the current hostname
        self.hostname = socket.gethostname()

        # Init the rabbitmq client
        self.client = self.init()

    def init(self):
        """Init the connection to the rabbitmq server."""
        if not self.export_enable:
            return None
        try:
            parameters = pika.URLParameters(
                'amqp://' + self.user +
                ':' + self.password +
                '@' + self.host +
                ':' + self.port + '/')
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            return channel
        except Exception as e:
            logger.critical("Connection to rabbitMQ failed : %s " % e)
            return None

    def export(self, name, columns, points):
        """Write the points in RabbitMQ."""
        data = ('hostname=' + self.hostname + ', name=' + name +
                ', dateinfo=' + datetime.datetime.utcnow().isoformat())
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            else:
                data += ", " + columns[i] + "=" + str(points[i])
        logger.debug(data)
        try:
            self.client.basic_publish(exchange='', routing_key=self.queue, body=data)
        except Exception as e:
            logger.error("Can not export stats to RabbitMQ (%s)" % e)

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

"""MQTT interface class."""

import socket
import string

from glances.logger import logger
from glances.exports.glances_export import GlancesExport

# Import paho for MQTT
from requests import certs
import paho.mqtt.client as paho


class Export(GlancesExport):

    """This class manages the MQTT export module."""

    def __init__(self, config=None, args=None):
        """Init the MQTT export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.topic = None
        self.tls = 'true'

        # Load the MQTT configuration file
        self.export_enable = self.load_conf('mqtt',
                                            mandatories=['host', 'password'],
                                            options=['port', 'user', 'topic', 'tls'])
        if not self.export_enable:
            exit('Missing MQTT config')

        # Get the current hostname
        self.hostname = socket.gethostname()

        self.port = int(self.port) or 8883
        self.topic = self.topic or 'glances'
        self.user = self.user or 'glances'
        self.tls = (self.tls and self.tls.lower() == 'true')

        # Init the MQTT client
        self.client = self.init()

    def init(self):
        """Init the connection to the MQTT server."""
        if not self.export_enable:
            return None
        try:
            client = paho.Client(client_id='glances_' + self.hostname,
                                 clean_session=False)
            client.username_pw_set(username=self.user,
                                   password=self.password)
            if self.tls:
                client.tls_set(certs.where())
            client.connect(host=self.host,
                           port=self.port)
            client.loop_start()
            return client
        except Exception as e:
            logger.critical("Connection to MQTT server failed : %s " % e)
            return None

    def export(self, name, columns, points):
        """Write the points in MQTT."""

        WHITELIST = '_-' + string.ascii_letters + string.digits
        SUBSTITUTE = '_'

        def whitelisted(s,
                        whitelist=WHITELIST,
                        substitute=SUBSTITUTE):
            return ''.join(c if c in whitelist else substitute for c in s)

        for sensor, value in zip(columns, points):
            try:
                sensor = [whitelisted(name) for name in sensor.split('.')]
                tobeexport = [self.topic, self.hostname, name]
                tobeexport.extend(sensor)
                topic = '/'.join(tobeexport)

                self.client.publish(topic, value)
            except Exception as e:
                logger.error("Can not export stats to MQTT server (%s)" % e)

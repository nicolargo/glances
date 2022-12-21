# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""MQTT interface class."""

import socket
import string
import sys

from glances.logger import logger
from glances.exports.glances_export import GlancesExport
from glances.globals import json_dumps

# Import paho for MQTT
from requests import certs
import paho.mqtt.client as paho


class Export(GlancesExport):

    """This class manages the MQTT export module."""

    def __init__(self, config=None, args=None):
        """Init the MQTT export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.topic = None
        self.tls = 'true'

        # Load the MQTT configuration file
        self.export_enable = self.load_conf(
            'mqtt', mandatories=['host', 'password'], options=['port', 'user', 'topic', 'tls', 'topic_structure']
        )
        if not self.export_enable:
            exit('Missing MQTT config')

        # Get the current hostname
        self.hostname = socket.gethostname()
        self.port = int(self.port) or 8883
        self.topic = self.topic or 'glances'
        self.user = self.user or 'glances'
        self.tls = self.tls and self.tls.lower() == 'true'

        self.topic_structure = (self.topic_structure or 'per-metric').lower()
        if self.topic_structure not in ['per-metric', 'per-plugin']:
            logger.critical("topic_structure must be either 'per-metric' or 'per-plugin'.")
            sys.exit(2)

        # Init the MQTT client
        self.client = self.init()
        if not self.client:
            exit("MQTT client initialization failed")

    def init(self):
        """Init the connection to the MQTT server."""
        if not self.export_enable:
            return None
        try:
            client = paho.Client(client_id='glances_' + self.hostname, clean_session=False)
            client.username_pw_set(username=self.user, password=self.password)
            if self.tls:
                client.tls_set(certs.where())
            client.connect(host=self.host, port=self.port)
            client.loop_start()
            return client
        except Exception as e:
            logger.critical("Connection to MQTT server %s:%s failed with error: %s " % (self.host, self.port, e))
            return None

    def export(self, name, columns, points):
        """Write the points in MQTT."""

        WHITELIST = '_-' + string.ascii_letters + string.digits
        SUBSTITUTE = '_'

        def whitelisted(s, whitelist=WHITELIST, substitute=SUBSTITUTE):
            return ''.join(c if c in whitelist else substitute for c in s)

        if self.topic_structure == 'per-metric':
            for sensor, value in zip(columns, points):
                try:
                    sensor = [whitelisted(name) for name in sensor.split('.')]
                    to_export = [self.topic, self.hostname, name]
                    to_export.extend(sensor)
                    topic = '/'.join(to_export)

                    self.client.publish(topic, value)
                except Exception as e:
                    logger.error("Can not export stats to MQTT server (%s)" % e)
        elif self.topic_structure == 'per-plugin':
            try:
                topic = '/'.join([self.topic, self.hostname, name])
                sensor_values = dict(zip(columns, points))

                # Build the value to output
                output_value = dict()
                for key in sensor_values:
                    split_key = key.split('.')

                    # Add the parent keys if they don't exist
                    current_level = output_value
                    for depth in range(len(split_key) - 1):
                        if split_key[depth] not in current_level:
                            current_level[split_key[depth]] = dict()
                        current_level = current_level[split_key[depth]]

                    # Add the value
                    current_level[split_key[len(split_key) - 1]] = sensor_values[key]

                json_value = json_dumps(output_value)
                self.client.publish(topic, json_value)
            except Exception as e:
                logger.error("Can not export stats to MQTT server (%s)" % e)

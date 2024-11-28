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

# Import paho for MQTT
import certifi
import paho.mqtt.client as paho

from glances.exports.export import GlancesExport
from glances.globals import json_dumps
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the MQTT export module."""

    def __init__(self, config=None, args=None):
        """Init the MQTT export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.user = None
        self.password = None
        self.topic = None
        self.tls = 'true'

        # Load the MQTT configuration file
        self.export_enable = self.load_conf(
            'mqtt',
            mandatories=['host', 'password'],
            options=['port', 'devicename', 'user', 'topic', 'tls', 'topic_structure', 'callback_api_version'],
        )
        if not self.export_enable:
            exit('Missing MQTT config')

        # Get the current hostname
        self.devicename = self.devicename or socket.gethostname()
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
        # Get the current callback api version
        self.callback_api_version = int(self.callback_api_version) or 2

        # Set enum for connection
        if self.callback_api_version == 1:
            self.callback_api_version = paho.CallbackAPIVersion.VERSION1
        else:
            self.callback_api_version = paho.CallbackAPIVersion.VERSION2

        """Init the connection to the MQTT server."""
        if not self.export_enable:
            return None
        try:
            client = paho.Client(
                callback_api_version=self.callback_api_version,
                client_id='glances_' + self.devicename,
                clean_session=False,
            )

            def on_connect(client, userdata, flags, reason_code, properties):
                """Action to perform when connecting."""
                self.client.publish(
                    topic='/'.join([self.topic, self.devicename, "availability"]), payload="online", retain=True
                )

            def on_disconnect(client, userdata, flags, reason_code, properties):
                """Action to perform when the connection is over."""
                self.client.publish(
                    topic='/'.join([self.topic, self.devicename, "availability"]), payload="offline", retain=True
                )

            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.will_set(
                topic='/'.join([self.topic, self.devicename, "availability"]), payload="offline", retain=True
            )

            client.username_pw_set(username=self.user, password=self.password)
            if self.tls:
                client.tls_set(certifi.where())
            client.connect(host=self.host, port=self.port)
            client.loop_start()
            return client
        except Exception as e:
            logger.critical(f"Connection to MQTT server {self.host}:{self.port} failed with error: {e} ")
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
                    to_export = [self.topic, self.devicename, name]
                    to_export.extend(sensor)
                    topic = '/'.join(to_export)

                    self.client.publish(topic, value)
                except Exception as e:
                    logger.error(f"Can not export stats to MQTT server ({e})")
        elif self.topic_structure == 'per-plugin':
            try:
                topic = '/'.join([self.topic, self.devicename, name])
                sensor_values = dict(zip(columns, points))

                # Build the value to output
                output_value = {}
                for key in sensor_values:
                    split_key = key.split('.')

                    # Add the parent keys if they don't exist
                    current_level = output_value
                    for depth in range(len(split_key) - 1):
                        if split_key[depth] not in current_level:
                            current_level[split_key[depth]] = {}
                        current_level = current_level[split_key[depth]]

                    # Add the value
                    current_level[split_key[len(split_key) - 1]] = sensor_values[key]

                json_value = json_dumps(output_value)
                self.client.publish(topic, json_value)
            except Exception as e:
                logger.error(f"Can not export stats to MQTT server ({e})")

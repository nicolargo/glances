# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""InfluxDB (from to InfluxDB 1.8+) interface class."""

import sys
from platform import node

from glances.logger import logger
from glances.exports.export import GlancesExport

from influxdb_client import InfluxDBClient, WriteOptions


class Export(GlancesExport):
    """This class manages the InfluxDB export module."""

    def __init__(self, config=None, args=None):
        """Init the InfluxDB export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.org = None
        self.bucket = None
        self.token = None

        # Optional configuration keys
        self.protocol = 'http'
        self.prefix = None
        self.tags = None
        self.hostname = None
        self.interval = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf(
            'influxdb2',
            mandatories=['host', 'port', 'user', 'password', 'org', 'bucket', 'token'],
            options=['protocol', 'prefix', 'tags', 'interval'],
        )
        if not self.export_enable:
            exit('Missing influxdb2 config')

        # Interval between two exports (in seconds)
        if self.interval is None:
            self.interval = 0
        try:
            self.interval = int(self.interval)
        except ValueError:
            logger.warning("InfluxDB export interval is not an integer, use default value")
            self.interval = 0
        # and should be set to the Glances refresh time if the value is 0
        self.interval = self.interval if self.interval > 0 else self.args.time
        logger.debug("InfluxDB export interval is set to {} seconds".format(self.interval))

        # The hostname is always add as a tag
        self.hostname = node().split('.')[0]

        # Init the InfluxDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the InfluxDB server."""
        if not self.export_enable:
            return None

        url = '{}://{}:{}'.format(self.protocol, self.host, self.port)
        try:
            # See docs: https://influxdb-client.readthedocs.io/en/stable/api.html#influxdbclient
            client = InfluxDBClient(url=url, enable_gzip=False, verify_ssl=False, org=self.org, token=self.token)
        except Exception as e:
            logger.critical("Cannot connect to InfluxDB server '%s' (%s)" % (url, e))
            sys.exit(2)
        else:
            logger.info(
                "Connected to InfluxDB server version {} ({})".format(client.health().version, client.health().message)
            )

        # Create the write client
        write_client = client.write_api(
            write_options=WriteOptions(
                batch_size=500,
                flush_interval=self.interval * 1000,
                jitter_interval=2000,
                retry_interval=5000,
                max_retries=5,
                max_retry_delay=30000,
                exponential_base=2,
            )
        )
        return write_client

    def _normalize(self, name, columns, points):
        """Normalize data for the InfluxDB's data model.

        :return: a list of measurements.
        """
        ret = []

        # Build initial dict by crossing columns and point
        data_dict = dict(zip(columns, points))

        # issue1871 - Check if a key exist. If a key exist, the value of
        # the key should be used as a tag to identify the measurement.
        keys_list = [k.split('.')[0] for k in columns if k.endswith('.key')]
        if len(keys_list) == 0:
            keys_list = [None]

        for measurement in keys_list:
            # Manage field
            if measurement is not None:
                fields = {
                    k.replace('{}.'.format(measurement), ''): data_dict[k]
                    for k in data_dict
                    if k.startswith('{}.'.format(measurement))
                }
            else:
                fields = data_dict
            # Transform to InfluxDB datamodel
            # https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/
            for k in fields:
                #  Do not export empty (None) value
                if fields[k] is None:
                    continue
                # Convert numerical to float
                try:
                    fields[k] = float(fields[k])
                except (TypeError, ValueError):
                    # Convert others to string
                    try:
                        fields[k] = str(fields[k])
                    except (TypeError, ValueError):
                        pass
            # Manage tags
            tags = self.parse_tags(self.tags)
            if 'key' in fields and fields['key'] in fields:
                # Create a tag from the key
                # Tag should be an string (see InfluxDB data model)
                tags[fields['key']] = str(fields[fields['key']])
                # Remove it from the field list (can not be a field and a tag)
                fields.pop(fields['key'])
            # Add the hostname as a tag
            tags['hostname'] = self.hostname
            # Add the measurement to the list
            ret.append({'measurement': name, 'tags': tags, 'fields': fields})
        return ret

    def export(self, name, columns, points):
        """Write the points to the InfluxDB server."""
        # Manage prefix
        if self.prefix is not None:
            name = self.prefix + '.' + name
        # Write input to the InfluxDB database
        if len(points) == 0:
            logger.debug("Cannot export empty {} stats to InfluxDB".format(name))
        else:
            try:
                self.client.write(self.bucket, self.org, self._normalize(name, columns, points), time_precision="s")
            except Exception as e:
                # Log level set to debug instead of error (see: issue #1561)
                logger.debug("Cannot export {} stats to InfluxDB ({})".format(name, e))
            else:
                logger.debug("Export {} stats to InfluxDB".format(name))

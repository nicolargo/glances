# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

"""InfluxDB (from to InfluxDB 1.8+) interface class."""

import sys
from platform import node

from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from influxdb_client import InfluxDBClient, WriteOptions


class Export(GlancesExport):
    """This class manages the InfluxDB export module."""

    def __init__(self, config=None, args=None):
        """Init the InfluxDB export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.org = None
        self.bucket = None
        self.token = None

        # Optionals configuration keys
        self.protocol = 'http'
        self.prefix = None
        self.tags = None
        self.hostname = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf('influxdb2',
                                            mandatories=['host', 'port',
                                                         'user', 'password',
                                                         'org', 'bucket', 'token'],
                                            options=['protocol',
                                                     'prefix',
                                                     'tags'])
        if not self.export_enable:
            sys.exit(2)

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
            client = InfluxDBClient(url=url,
                                    enable_gzip=False,
                                    org=self.org,
                                    token=self.token)
        except Exception as e:
            logger.critical("Cannot connect to InfluxDB server '%s' (%s)" % (url, e))
            sys.exit(2)
        else:
            logger.info("Connected to InfluxDB server version {} ({})".format(client.health().version,
                                                                              client.health().message))

        # Create the write client
        write_client = client.write_api(write_options=WriteOptions(batch_size=500,
                                                                   flush_interval=10000,
                                                                   jitter_interval=2000,
                                                                   retry_interval=5000,
                                                                   max_retries=5,
                                                                   max_retry_delay=30000,
                                                                   exponential_base=2))
        return write_client

    def _normalize(self, name, columns, points):
        """Normalize data for the InfluxDB's data model."""
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
                fields = {k.replace('{}.'.format(measurement), ''): data_dict[k]
                          for k in data_dict
                          if k.startswith('{}.'.format(measurement))}
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
            ret.append({'measurement': name,
                        'tags': tags,
                        'fields': fields})
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
                self.client.write(self.bucket,
                                  self.org,
                                  self._normalize(name, columns, points),
                                  time_precision="s")
            except Exception as e:
                # Log level set to debug instead of error (see: issue #1561)
                logger.debug("Cannot export {} stats to InfluxDB ({})".format(name, e))
            else:
                logger.debug("Export {} stats to InfluxDB".format(name))

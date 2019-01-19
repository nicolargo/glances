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

"""OpenTSDB interface class."""

import sys
from numbers import Number

from glances.compat import range
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

import potsdb


class Export(GlancesExport):

    """This class manages the OpenTSDB export module."""

    def __init__(self, config=None, args=None):
        """Init the OpenTSDB export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        # N/A

        # Optionals configuration keys
        self.prefix = None
        self.tags = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf('opentsdb',
                                            mandatories=['host', 'port'],
                                            options=['prefix', 'tags'])
        if not self.export_enable:
            sys.exit(2)

        # Default prefix for stats is 'glances'
        if self.prefix is None:
            self.prefix = 'glances'

        # Init the OpenTSDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the OpenTSDB server."""
        if not self.export_enable:
            return None

        try:
            db = potsdb.Client(self.host,
                               port=int(self.port),
                               check_host=True)
        except Exception as e:
            logger.critical("Cannot connect to OpenTSDB server %s:%s (%s)" % (self.host, self.port, e))
            sys.exit(2)

        return db

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            stat_name = '{}.{}.{}'.format(self.prefix, name, columns[i])
            stat_value = points[i]
            tags = self.parse_tags(self.tags)
            try:
                self.client.send(stat_name, stat_value, **tags)
            except Exception as e:
                logger.error("Can not export stats %s to OpenTSDB (%s)" % (name, e))
        logger.debug("Export {} stats to OpenTSDB".format(name))

    def exit(self):
        """Close the OpenTSDB export module."""
        # Waits for all outstanding metrics to be sent and background thread closes
        self.client.wait()
        # Call the father method
        super(Export, self).exit()

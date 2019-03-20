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

"""Statsd interface class."""

import sys
from numbers import Number

from glances.compat import range
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from statsd import StatsClient


class Export(GlancesExport):

    """This class manages the Statsd export module."""

    def __init__(self, config=None, args=None):
        """Init the Statsd export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        # N/A

        # Optionals configuration keys
        self.prefix = None

        # Load the InfluxDB configuration file
        self.export_enable = self.load_conf('statsd',
                                            mandatories=['host', 'port'],
                                            options=['prefix'])
        if not self.export_enable:
            sys.exit(2)

        # Default prefix for stats is 'glances'
        if self.prefix is None:
            self.prefix = 'glances'

        # Init the Statsd client
        self.client = self.init()

    def init(self):
        """Init the connection to the Statsd server."""
        if not self.export_enable:
            return None
        logger.info(
            "Stats will be exported to StatsD server: {}:{}".format(self.host,
                                                                    self.port))
        return StatsClient(self.host,
                           int(self.port),
                           prefix=self.prefix)

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            stat_name = '{}.{}'.format(name, columns[i])
            stat_value = points[i]
            try:
                self.client.gauge(normalize(stat_name),
                                  stat_value)
            except Exception as e:
                logger.error("Can not export stats to Statsd (%s)" % e)
        logger.debug("Export {} stats to Statsd".format(name))


def normalize(name):
    """Normalize name for the Statsd convention"""

    # Name should not contain some specials chars (issue #1068)
    ret = name.replace(':', '')
    ret = ret.replace('%', '')
    ret = ret.replace(' ', '_')

    return ret

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

"""Graphite interface class."""

import sys
from numbers import Number

from glances.compat import range
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

import graphyte


class Export(GlancesExport):

    """This class manages the Graphite export module."""

    def __init__(self, config=None, args=None):
        """Init the Graphite export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        # N/A

        # Optionals configuration keys
        self.prefix = None
        self.protocol = None
        self.batch_size = None

        # Load the configuration file
        self.export_enable = self.load_conf('graphite',
                                            mandatories=['host', 
                                                         'port'],
                                            options=['prefix',
                                                     'protocol',
                                                     'batch_size'])
        if not self.export_enable:
            sys.exit(2)

        # Default prefix for stats is 'glances'
        if self.prefix is None:
            self.prefix = 'glances'

        if self.protocol is None:
            self.protocol = 'tcp'

        if self.batch_size is None:
            self.batch_size = 1000

        # Convert config option type
        self.port = int(self.port)
        self.batch_size = int(self.batch_size)

        # Init the Graphite client
        self.client = self.init()

    def init(self):
        """Init the connection to the Graphite server."""
        if not self.export_enable:
            return None

        client = graphyte.Sender(self.host,
                                 port=self.port,
                                 prefix=self.prefix,
                                 protocol=self.protocol,
                                 batch_size=self.batch_size)

        # !!! Except is never reached...
        # !!! Have to find  away to test the connection with the Graphite server
        # !!! Waiting that, have to set the logger to debug in the export function
        # try:
        #     client.send("check", 1)
        # except Exception as e:
        #     logger.error("Can not write data to Graphite server: {}:{}/{} ({})".format(self.host,
        #                                                                                self.port,
        #                                                                                self.protocol,
        #                                                                                e))
        #     return None
        # else:
        #     logger.info(
        #         "Stats will be exported to Graphite server: {}:{}/{}".format(self.host,
        #                                                                     self.port,
        #                                                                     self.protocol))

        #     return client

        logger.info(
            "Stats will be exported to Graphite server: {}:{}/{}".format(self.host,
                                                                         self.port,
                                                                         self.protocol))

        return client

    def export(self, name, columns, points):
        """Export the stats to the Graphite server."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                # Only Int and Float are supported in the Graphite datamodel
                continue
            stat_name = '{}.{}'.format(name, columns[i])
            stat_value = points[i]
            try:
                self.client.send(normalize(stat_name),
                                 stat_value)
            except Exception as e:
                # !! Set to error when the connection test is ok
                # logger.error("Can not export stats to Graphite (%s)" % e)
                logger.debug("Can not export stats to Graphite (%s)" % e)
        logger.debug("Export {} stats to Graphite".format(name))


def normalize(name):
    """Normalize name for the Graphite convention"""

    # Name should not contain space
    ret = name.replace(' ', '_')

    return ret

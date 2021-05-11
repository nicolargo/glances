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

from graphitesend import GraphiteClient


class Export(GlancesExport):

    """This class manages the Graphite export module."""

    def __init__(self, config=None, args=None):
        """Init the Graphite export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        # N/A

        # Optionals configuration keys
        self.debug = False
        self.prefix = None
        self.system_name = None

        # Load the configuration file
        self.export_enable = self.load_conf('graphite',
                                            mandatories=['host',
                                                         'port'],
                                            options=['prefix',
                                                     'system_name'])
        if not self.export_enable:
            sys.exit(2)

        # Default prefix for stats is 'glances'
        if self.prefix is None:
            self.prefix = 'glances'

        # Convert config option type
        self.port = int(self.port)

        # Init the Graphite client
        self.client = self.init()

    def init(self):
        """Init the connection to the Graphite server."""
        client = None

        if not self.export_enable:
            return client

        try:
            if self.system_name is None:
                client = GraphiteClient(graphite_server=self.host,
                                        graphite_port=self.port,
                                        prefix=self.prefix,
                                        lowercase_metric_names=True,
                                        debug=self.debug)
            else:
                client = GraphiteClient(graphite_server=self.host,
                                        graphite_port=self.port,
                                        prefix=self.prefix,
                                        system_name=self.system_name,
                                        lowercase_metric_names=True,
                                        debug=self.debug)
        except Exception as e:
            logger.error("Can not write data to Graphite server: {}:{} ({})".format(self.host,
                                                                                    self.port,
                                                                                    e))
            client = None
        else:
            logger.info(
                "Stats will be exported to Graphite server: {}:{}".format(self.host,
                                                                          self.port))

        return client

    def export(self, name, columns, points):
        """Export the stats to the Graphite server."""
        if self.client is None:
            return False
        before_filtering_dict = dict(zip(
            [normalize('{}.{}'.format(name, i)) for i in columns],
            points))
        after_filtering_dict = dict(
            filter(lambda i: isinstance(i[1], Number),
                   before_filtering_dict.items()))
        try:
            self.client.send_dict(after_filtering_dict)
        except Exception as e:
            logger.error("Can not export stats to Graphite (%s)" % e)
            return False
        else:
            logger.debug("Export {} stats to Graphite".format(name))
        return True


def normalize(name):
    """Normalize name for the Graphite convention"""

    # Name should not contain space
    ret = name.replace(' ', '_')

    return ret

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""Riemann interface class."""

import socket
import sys
from numbers import Number

from glances.compat import NoOptionError, NoSectionError, range
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

# Import pika for Riemann
import bernhard


class Export(GlancesExport):

    """This class manages the Riemann export module."""

    def __init__(self, config=None, args=None):
        """Init the Riemann export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Load the rabbitMQ configuration file
        self.riemann_host = None
        self.riemann_port = None
        self.hostname = socket.gethostname()
        self.export_enable = self.load_conf()
        if not self.export_enable:
            sys.exit(2)

        # Init the rabbitmq client
        self.client = self.init()

    def load_conf(self, section="riemann"):
        """Load the Riemann configuration in the Glances configuration file."""
        if self.config is None:
            return False
        try:
            self.riemann_host = self.config.get_value(section, 'host')
            self.riemann_port = int(self.config.get_value(section, 'port'))
        except NoSectionError:
            logger.critical("No riemann configuration found")
            return False
        except NoOptionError as e:
            logger.critical("Error in the Riemann configuration (%s)" % e)
            return False
        else:
            logger.debug("Load Riemann from the Glances configuration file")
        return True

    def init(self):
        """Init the connection to the Riemann server."""
        if not self.export_enable:
            return None
        try:
            client = bernhard.Client(host=self.riemann_host, port=self.riemann_port)
            return client
        except Exception as e:
            logger.critical("Connection to Riemann failed : %s " % e)
            return None

    def export(self, name, columns, points):
        """Write the points in Riemann."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            else:
                data = {'host': self.hostname, 'service': name + " " + columns[i], 'metric': points[i]}
                logger.debug(data)
                try:
                    self.client.send(data)
                except Exception as e:
                    logger.error("Can not export stats to Riemann (%s)" % e)

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

"""RESTful interface class."""

import sys

from glances.compat import listkeys
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from requests import post


class Export(GlancesExport):

    """This class manages the RESTful export module.
    Be aware that stats will be exported in one big POST request"""

    def __init__(self, config=None, args=None):
        """Init the RESTful export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.protocol = None
        self.path = None

        # Load the RESTful section in the configuration file
        self.export_enable = self.load_conf('restful',
                                            mandatories=['host', 'port', 'protocol', 'path'])
        if not self.export_enable:
            sys.exit(2)

        # Init the stats buffer
        # It's a dict of stats
        self.buffer = {}

        # Init the Statsd client
        self.client = self.init()

    def init(self):
        """Init the connection to the RESTful server."""
        if not self.export_enable:
            return None
        # Build the RESTful URL where the stats will be posted
        url = '{}://{}:{}{}'.format(self.protocol,
                                    self.host,
                                    self.port,
                                    self.path)
        logger.info(
            "Stats will be exported to the RESTful endpoint {}".format(url))
        return url

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        if name == self.plugins_to_export()[0] and self.buffer != {}:
            # One complete loop have been done
            logger.debug("Export stats ({}) to RESTful endpoint ({})".format(listkeys(self.buffer),
                                                                             self.client))
            # Export stats
            post(self.client, json=self.buffer, allow_redirects=True)
            # Reset buffer
            self.buffer = {}

        # Add current stat to the buffer
        self.buffer[name] = dict(zip(columns, points))

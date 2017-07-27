# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

"""Restful interface class."""

import sys
from numbers import Number

from glances.compat import range
from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from requests import post


class Export(GlancesExport):

    """This class manages the Restful export module."""

    def __init__(self, config=None, args=None):
        """Init the Restful export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatories configuration keys (additional to host and port)
        self.protocol = None
        self.path = None

        # Load the Restful section in the configuration file
        self.export_enable = self.load_conf('restful',
                                            mandatories=['host', 'port', 'protocol', 'path'])
        if not self.export_enable:
            sys.exit(2)

        # Init the Statsd client
        self.client = self.init()

    def init(self):
        """Init the connection to the restful server."""
        if not self.export_enable:
            return None
        # Build the Restful URL where the stats will be posted
        url = '{}://{}:{}{}'.format(self.protocol,
                                    self.host,
                                    self.port,
                                    self.path)
        logger.info(
            "Stats will be exported to the restful URL: {}".format(url))
        return url

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        post(self.client, json=dict(zip(columns, points)), allow_redirects=True)
        logger.debug("Export {} stats to Restful endpoint".format(name))


def normalize(name):
    """Normalize name for the Statsd convention"""

    # Name should not contain some specials chars (issue #1068)
    ret = name.replace(':', '')
    ret = ret.replace('%', '')
    ret = ret.replace(' ', '_')

    return ret

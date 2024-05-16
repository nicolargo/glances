#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Riemann interface class."""

import socket
from numbers import Number

# Import bernhard for Riemann
import bernhard

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the Riemann export module."""

    def __init__(self, config=None, args=None):
        """Init the Riemann export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        # N/A

        # Optional configuration keys
        # N/A

        # Load the Riemann configuration
        self.export_enable = self.load_conf('riemann', mandatories=['host', 'port'], options=[])
        if not self.export_enable:
            exit('Missing RIEMANN config')

        # Get the current hostname
        self.hostname = socket.gethostname()

        # Init the Riemann client
        self.client = self.init()

    def init(self):
        """Init the connection to the Riemann server."""
        if not self.export_enable:
            return None
        try:
            return bernhard.Client(host=self.host, port=self.port)
        except Exception as e:
            logger.critical(f"Connection to Riemann failed : {e} ")
            return None

    def export(self, name, columns, points):
        """Write the points in Riemann."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue

            data = {'host': self.hostname, 'service': name + " " + columns[i], 'metric': points[i]}
            logger.debug(data)
            try:
                self.client.send(data)
            except Exception as e:
                logger.error(f"Cannot export stats to Riemann ({e})")

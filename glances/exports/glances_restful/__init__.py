#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""RESTful interface class."""

from requests import post

from glances.exports.export import GlancesExport
from glances.globals import listkeys
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the RESTful export module.
    Be aware that stats will be exported in one big POST request"""

    def __init__(self, config=None, args=None):
        """Init the RESTful export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.protocol = None
        self.path = None

        # Load the RESTful section in the configuration file
        self.export_enable = self.load_conf('restful', mandatories=['host', 'port', 'protocol', 'path'])
        if not self.export_enable:
            exit('Missing RESTFUL config')

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
        url = f'{self.protocol}://{self.host}:{self.port}{self.path}'
        logger.info(f"Stats will be exported to the RESTful endpoint {url}")
        return url

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        if name == self.last_exported_list()[0] and self.buffer != {}:
            # One complete loop have been done
            logger.debug(f"Export stats ({listkeys(self.buffer)}) to RESTful endpoint ({self.client})")
            # Export stats
            post(self.client, json=self.buffer, allow_redirects=True)
            # Reset buffer
            self.buffer = {}

        # Add current stat to the buffer
        self.buffer[name] = dict(zip(columns, points))

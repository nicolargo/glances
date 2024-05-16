#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""OpenTSDB interface class."""

import sys
from numbers import Number

import potsdb

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the OpenTSDB export module."""

    def __init__(self, config=None, args=None):
        """Init the OpenTSDB export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        # N/A

        # Optionals configuration keys
        self.prefix = None
        self.tags = None

        # Load the configuration file
        self.export_enable = self.load_conf('opentsdb', mandatories=['host', 'port'], options=['prefix', 'tags'])
        if not self.export_enable:
            exit('Missing OPENTSDB config')

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
            db = potsdb.Client(self.host, port=int(self.port), check_host=True)
        except Exception as e:
            logger.critical(f"Cannot connect to OpenTSDB server {self.host}:{self.port} ({e})")
            sys.exit(2)

        return db

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            stat_name = f'{self.prefix}.{name}.{columns[i]}'
            stat_value = points[i]
            tags = self.parse_tags(self.tags)
            try:
                self.client.send(stat_name, stat_value, **tags)
            except Exception as e:
                logger.error(f"Can not export stats {name} to OpenTSDB ({e})")
        logger.debug(f"Export {name} stats to OpenTSDB")

    def exit(self):
        """Close the OpenTSDB export module."""
        # Waits for all outstanding metrics to be sent and background thread closes
        self.client.wait()
        # Call the father method
        super().exit()

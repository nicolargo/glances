#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Graphite interface class."""

import sys
from numbers import Number

from graphitesend import GraphiteClient

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the Graphite export module."""

    def __init__(self, config=None, args=None):
        """Init the Graphite export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        # N/A

        # Optional configuration keys
        self.debug = False
        self.prefix = None
        self.system_name = None

        # Load the configuration file
        self.export_enable = self.load_conf('graphite', mandatories=['host', 'port'], options=['prefix', 'system_name'])
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
                client = GraphiteClient(
                    graphite_server=self.host,
                    graphite_port=self.port,
                    prefix=self.prefix,
                    lowercase_metric_names=True,
                    debug=self.debug,
                )
            else:
                client = GraphiteClient(
                    graphite_server=self.host,
                    graphite_port=self.port,
                    prefix=self.prefix,
                    system_name=self.system_name,
                    lowercase_metric_names=True,
                    debug=self.debug,
                )
        except Exception as e:
            logger.error(f"Can not write data to Graphite server: {self.host}:{self.port} ({e})")
            client = None
        else:
            logger.info(f"Stats will be exported to Graphite server: {self.host}:{self.port}")
        return client

    def export(self, name, columns, points):
        """Export the stats to the Graphite server."""
        if self.client is None:
            return False
        before_filtering_dict = dict(zip([normalize(f'{name}.{i}') for i in columns], points))
        after_filtering_dict = dict(filter(lambda i: isinstance(i[1], Number), before_filtering_dict.items()))
        try:
            self.client.send_dict(after_filtering_dict)
        except Exception as e:
            logger.error(f"Can not export stats to Graphite ({e})")
            return False
        else:
            logger.debug(f"Export {name} stats to Graphite")
        return True


def normalize(name):
    """Normalize name for the Graphite convention"""

    # Name should not contain space
    return name.replace(' ', '_')

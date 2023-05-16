# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Statsd interface class."""

from numbers import Number

from glances.logger import logger
from glances.exports.export import GlancesExport

from statsd import StatsClient


class Export(GlancesExport):

    """This class manages the Statsd export module."""

    def __init__(self, config=None, args=None):
        """Init the Statsd export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        # N/A

        # Optional configuration keys
        self.prefix = None

        # Load the configuration file
        self.export_enable = self.load_conf('statsd', mandatories=['host', 'port'], options=['prefix'])
        if not self.export_enable:
            exit('Missing STATSD config')

        # Default prefix for stats is 'glances'
        if self.prefix is None:
            self.prefix = 'glances'

        # Init the Statsd client
        self.client = self.init()

    def init(self):
        """Init the connection to the Statsd server."""
        if not self.export_enable:
            return None
        logger.info("Stats will be exported to StatsD server: {}:{}".format(self.host, self.port))
        return StatsClient(self.host, int(self.port), prefix=self.prefix)

    def export(self, name, columns, points):
        """Export the stats to the Statsd server."""
        for i in range(len(columns)):
            if not isinstance(points[i], Number):
                continue
            stat_name = '{}.{}'.format(name, columns[i])
            stat_value = points[i]
            try:
                self.client.gauge(normalize(stat_name), stat_value)
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

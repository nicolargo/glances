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

"""Prometheus interface class."""

import sys
from numbers import Number

from glances.logger import logger
from glances.exports.glances_export import GlancesExport
from glances.compat import iteritems, listkeys

from prometheus_client import start_http_server, Gauge


class Export(GlancesExport):

    """This class manages the Prometheus export module."""

    METRIC_SEPARATOR = '_'

    def __init__(self, config=None, args=None):
        """Init the Prometheus export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Load the Prometheus configuration file section
        self.export_enable = self.load_conf('prometheus',
                                            mandatories=['host', 'port', 'labels'],
                                            options=['prefix'])
        if not self.export_enable:
            sys.exit(2)

        # Optionals configuration keys
        if self.prefix is None:
            self.prefix = 'glances'

        if self.labels is None:
            self.labels = 'src:glances'

        # Init the metric dict
        # Perhaps a better method is possible...
        self._metric_dict = {}

        # Init the Prometheus Exporter
        self.init()

    def init(self):
        """Init the Prometheus Exporter"""
        try:
            start_http_server(port=int(self.port), addr=self.host)
        except Exception as e:
            logger.critical("Can not start Prometheus exporter on {}:{} ({})".format(self.host, self.port, e))
            sys.exit(2)
        else:
            logger.info("Start Prometheus exporter on {}:{}".format(self.host, self.port))

    def export(self, name, columns, points):
        """Write the points to the Prometheus exporter using Gauge."""
        logger.debug("Export {} stats to Prometheus exporter".format(name))

        # Remove non number stats and convert all to float (for Boolean)
        data = {k: float(v) for (k, v) in iteritems(dict(zip(columns, points))) if isinstance(v, Number)}

        # Write metrics to the Prometheus exporter
        for k, v in iteritems(data):
            # Prometheus metric name: prefix_<glances stats name>
            metric_name = self.prefix + self.METRIC_SEPARATOR + str(name) + self.METRIC_SEPARATOR + str(k)
            # Prometheus is very sensible to the metric name
            # See: https://prometheus.io/docs/practices/naming/
            for c in ['.', '-', '/', ' ']:
                metric_name = metric_name.replace(c, self.METRIC_SEPARATOR)
            # Get the labels
            labels = self.parse_tags(self.labels)
            # Manage an internal dict between metric name and Gauge
            if metric_name not in self._metric_dict:
                self._metric_dict[metric_name] = Gauge(metric_name, k,
                                                       labelnames=listkeys(labels))
            # Write the value
            if hasattr(self._metric_dict[metric_name], 'labels'):
                # Add the labels (see issue #1255)
                self._metric_dict[metric_name].labels(**labels).set(v)
            else:
                self._metric_dict[metric_name].set(v)

#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Prometheus interface class."""

import sys
from numbers import Number

from prometheus_client import Gauge, start_http_server

from glances.exports.export import GlancesExport
from glances.globals import iteritems, listkeys
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the Prometheus export module."""

    METRIC_SEPARATOR = '_'

    def __init__(self, config=None, args=None):
        """Init the Prometheus export IF."""
        super().__init__(config=config, args=args)

        # Load the Prometheus configuration file section
        self.export_enable = self.load_conf('prometheus', mandatories=['host', 'port', 'labels'], options=['prefix'])
        if not self.export_enable:
            exit('Missing PROMETHEUS config')

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
            logger.critical(f"Can not start Prometheus exporter on {self.host}:{self.port} ({e})")
            sys.exit(2)
        else:
            logger.info(f"Start Prometheus exporter on {self.host}:{self.port}")

    def export(self, name, columns, points):
        """Write the points to the Prometheus exporter using Gauge."""
        logger.debug(f"Export {name} stats to Prometheus exporter")

        # Remove non number stats and convert all to float (for Boolean)
        data = {k: float(v) for (k, v) in iteritems(dict(zip(columns, points))) if isinstance(v, Number)}

        # Write metrics to the Prometheus exporter
        for k, v in iteritems(data):
            # Prometheus metric name: prefix_<glances stats name>
            metric_name = self.prefix + self.METRIC_SEPARATOR + str(name) + self.METRIC_SEPARATOR + str(k)
            # Prometheus is very sensible to the metric name
            # See: https://prometheus.io/docs/practices/naming/
            for c in ' .-/:[]':
                metric_name = metric_name.replace(c, self.METRIC_SEPARATOR)
            # Get the labels
            labels = self.parse_tags(self.labels)
            # Manage an internal dict between metric name and Gauge
            if metric_name not in self._metric_dict:
                self._metric_dict[metric_name] = Gauge(metric_name, k, labelnames=listkeys(labels))
            # Write the value
            if hasattr(self._metric_dict[metric_name], 'labels'):
                # Add the labels (see issue #1255)
                self._metric_dict[metric_name].labels(**labels).set(v)
            else:
                self._metric_dict[metric_name].set(v)

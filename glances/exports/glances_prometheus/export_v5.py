#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Prometheus export module.

Ported from the v4 module in this directory.

Prometheus is a PULL backend: ``start_http_server()`` runs once at init and
the export cycle only refreshes ``Gauge`` values. Metric names are built
exactly as in v4 — ``<prefix>_<plugin>_<field>``, every character in
``" .-/:[]"`` replaced by ``_`` — because users' recording rules and Grafana
queries are keyed on them.

One v5 adaptation: v4 resolved a plugin's primary key through
``stats.get_plugin(name).get_key()``. v5 reads ``plugin._primary_key``, which
``GlancesPluginBase`` resolves once from ``fields_description``.

``prometheus_client`` is imported inside the methods that need it, never at
module level: ``discover_exporters()`` imports this module only when the user
passes ``--export prometheus``, but keeping the import local also means the
module stays importable (for tests, for introspection) on a minimal install.
"""

from __future__ import annotations

import sys
from numbers import Number
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class Export(GlancesExportBase):
    """Expose Glances stats as Prometheus gauges."""

    export_name = "prometheus"

    METRIC_SEPARATOR = "_"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Optional key: load_conf() overwrites it only when [prometheus] prefix
        # is set, so the default has to be in place before the call.
        self.prefix: str = "glances"
        # Mandatory keys, set by load_conf(). `labels` has no default in v5:
        # load_conf() is fatal on a missing mandatory, unlike v4 which silently
        # continued with None and needed a fallback here.
        self.labels: str = ""

        if not self.load_conf("prometheus", mandatories=("host", "port", "labels"), options=("prefix",)):
            logger.critical("Missing prometheus config")
            sys.exit(2)

        # Metric name -> Gauge. Gauges are created once and reused: creating
        # the same metric name twice raises in prometheus_client.
        self._metric_dict: dict[str, Any] = {}
        # Plugin name -> primary key field name (None for scalar plugins).
        # Refreshed every cycle by update(), like v4.
        self.keys_name: dict[str, str | None] = {}

        self.init()

    def init(self) -> None:
        """Start the Prometheus HTTP endpoint."""
        from prometheus_client import start_http_server

        try:
            start_http_server(port=int(self.port), addr=self.host)
        except Exception as e:
            logger.critical("Can not start Prometheus exporter on %s:%s (%s)", self.host, self.port, e)
            sys.exit(2)
        logger.info("Start Prometheus exporter on %s:%s", self.host, self.port)

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Refresh the primary-key map, then run the standard export cycle."""
        self.keys_name = {plugin.plugin_name: getattr(plugin, "_primary_key", None) for plugin in plugins}
        super().update(plugins)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's numeric fields to their gauges."""
        from prometheus_client import Gauge

        logger.debug("Export %s stats to Prometheus exporter", name)

        # Only numbers reach Prometheus; booleans convert to 1.0/0.0.
        data = {str(k): float(v) for k, v in zip(columns, points) if isinstance(v, Number)}

        for metric, value in data.items():
            labels = self.labels
            metric_name = self.prefix + self.METRIC_SEPARATOR + name + self.METRIC_SEPARATOR
            try:
                # ValueError when the metric has no dot OR more than one: v4
                # relies on that to route both plain fields and multi-dot names
                # to the un-labelled branch. A `"." in metric` test would not
                # behave the same for a name such as `/media/data.percent`.
                obj, stat = metric.split(".")
            except ValueError:
                metric_name += metric
            else:
                metric_name += stat
                labels += f",{self.keys_name.get(name)}:{obj}"

            # Prometheus is very sensitive to metric names.
            # See: https://prometheus.io/docs/practices/naming/
            for c in " .-/:[]":
                metric_name = metric_name.replace(c, self.METRIC_SEPARATOR)

            parsed_labels = self.parse_tags(labels)
            if metric_name not in self._metric_dict:
                self._metric_dict[metric_name] = Gauge(metric_name, "", labelnames=list(parsed_labels.keys()))
            gauge = self._metric_dict[metric_name]
            if parsed_labels:
                # Add the labels (see issue #1255)
                gauge.labels(**parsed_labels).set(value)
            else:
                # parse_tags() returns {} on malformed input -- reachable when a
                # primary key value contains a comma, which breaks the
                # `k:v,k:v` label syntax. The gauge then carries no label
                # names, and calling labels() on it would raise.
                gauge.set(value)

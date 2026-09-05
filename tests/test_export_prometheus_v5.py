#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the Prometheus export module.

`prometheus_client` is mocked: these tests assert on metric names, labels
and values, not on a live HTTP endpoint.
"""

from __future__ import annotations

import sys
import types

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeGauge:
    """Stand-in for prometheus_client.Gauge."""

    def __init__(self, name, doc, labelnames=()):
        self.name = name
        self.labelnames = list(labelnames)
        self.values: list[float] = []
        self.last_labels: dict | None = None

    def labels(self, **kwargs):
        self.last_labels = kwargs
        return self

    def set(self, value):
        self.values.append(value)


@pytest.fixture
def prometheus_client(monkeypatch):
    """Install a fake `prometheus_client` module for the duration of a test."""
    created: dict[str, FakeGauge] = {}
    started: list[dict] = []

    def gauge_factory(name, doc, labelnames=()):
        gauge = FakeGauge(name, doc, labelnames)
        created[name] = gauge
        return gauge

    module = types.ModuleType("prometheus_client")
    module.Gauge = gauge_factory
    module.start_http_server = lambda port, addr: started.append({"port": port, "addr": addr})
    monkeypatch.setitem(sys.modules, "prometheus_client", module)
    module.created = created
    module.started = started
    return module


class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name = "fakescalar"
    IS_COLLECTION = False
    fields_description = {
        "percent": {"description": "p", "unit": "percent"},
        "label": {"description": "l", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 50.0, "label": "not-a-number"}


class FakeRatePlugin(GlancesPluginBase[dict]):
    """A plugin with a rate field: absent from the payload on cycle 0, and
    present with the value None -- never dropped (see `_compute_rates_in_dict`)."""

    plugin_name = "fakerate"
    IS_COLLECTION = False
    fields_description = {
        "total": {"description": "t", "unit": "number"},
        # Grabbed as a raw counter; converted in place to a per-second rate.
        "bytes_recv": {"description": "r", "unit": "bytespers", "rate": True},
    }

    async def _grab_stats(self) -> dict:
        return {"total": 10, "bytes_recv": 4096}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name = "fakecollection"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers"},
    }

    async def _grab_stats(self) -> list:
        return [{"name": "eth0", "rx": 10}]


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


PROM_SECTION = {"prometheus": {"host": "127.0.0.1", "port": "9091", "labels": "src:glances"}}


def test_prometheus_starts_the_http_server(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    Export(make_config(PROM_SECTION), args=None)

    assert prometheus_client.started == [{"port": 9091, "addr": "127.0.0.1"}]


def test_prometheus_exits_when_the_section_is_missing(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), args=None)
    assert excinfo.value.code == 2


def test_prometheus_exits_when_a_mandatory_key_is_missing(prometheus_client):
    """v4 continued with `labels = None` and fell back to a default; v5's
    load_conf() is fatal instead, which is why the v5 module has no fallback."""
    from glances.exports.glances_prometheus.export_v5 import Export

    sections = {"prometheus": {"host": "127.0.0.1", "port": "9091"}}
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(sections), args=None)
    assert excinfo.value.code == 2


def test_prometheus_exits_when_the_server_cannot_start(prometheus_client):
    def boom(port, addr):
        raise OSError("address already in use")

    prometheus_client.start_http_server = boom
    from glances.exports.glances_prometheus.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(PROM_SECTION), args=None)
    assert excinfo.value.code == 2


async def test_prometheus_metric_name_and_value(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "glances_fakescalar_percent" in prometheus_client.created
    assert prometheus_client.created["glances_fakescalar_percent"].values == [50.0]


async def test_prometheus_skips_non_numeric_fields(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "glances_fakescalar_label" not in prometheus_client.created


async def test_prometheus_skips_a_rate_field_still_at_none(prometheus_client):
    """On cycle 0 a rate field is present with the value None. `None` is not a
    Number, so it must be filtered out rather than crash `float()`."""
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeRatePlugin(store, config)
    await plugin.update()

    assert "bytes_recv" in plugin.get_export()
    assert plugin.get_export()["bytes_recv"] is None

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "glances_fakerate_total" in prometheus_client.created
    assert "glances_fakerate_bytes_recv" not in prometheus_client.created


async def test_prometheus_turns_the_primary_key_into_a_label(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    gauge = prometheus_client.created["glances_fakecollection_rx"]
    assert gauge.last_labels == {"src": "glances", "name": "eth0"}
    assert gauge.values == [10.0]


async def test_prometheus_reuses_the_same_gauge_across_cycles(prometheus_client):
    """prometheus_client raises when the same metric name is registered twice."""
    from glances.exports.glances_prometheus.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(PROM_SECTION)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])
    first = prometheus_client.created["glances_fakescalar_percent"]
    exporter.update([plugin])

    assert prometheus_client.created["glances_fakescalar_percent"] is first
    assert first.values == [50.0, 50.0]


async def test_prometheus_honours_a_custom_prefix(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    sections = {"prometheus": dict(PROM_SECTION["prometheus"], prefix="myhost")}
    store = StatsStoreV5()
    config = make_config(sections)
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert "myhost_fakescalar_percent" in prometheus_client.created


def test_prometheus_sanitises_characters_forbidden_in_metric_names(prometheus_client):
    from glances.exports.glances_prometheus.export_v5 import Export

    exporter = Export(make_config(PROM_SECTION), args=None)
    exporter.keys_name = {"fs": "mnt_point"}
    exporter.export("fs", ["/media/data.percent"], [42.0])

    assert "glances_fs_percent" in prometheus_client.created
    gauge = prometheus_client.created["glances_fs_percent"]
    assert gauge.last_labels == {"src": "glances", "mnt_point": "/media/data"}


def test_prometheus_sets_an_unlabelled_gauge_when_the_labels_are_malformed(prometheus_client):
    """A primary key value containing a comma breaks the `k:v,k:v` label
    syntax, so parse_tags() returns {}. Calling labels() on a gauge with no
    label names would raise, so the value is set directly instead."""
    from glances.exports.glances_prometheus.export_v5 import Export

    exporter = Export(make_config(PROM_SECTION), args=None)
    exporter.keys_name = {"containers": "name"}
    exporter.export("containers", ["a,b.cpu_percent"], [7.0])

    gauge = prometheus_client.created["glances_containers_cpu_percent"]
    assert gauge.labelnames == []
    assert gauge.last_labels is None
    assert gauge.values == [7.0]

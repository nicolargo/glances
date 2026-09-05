#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the InfluxDB 3.x export module."""

from __future__ import annotations

import sys
import types

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeClient3:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._database = kwargs.get("database")
        self.written: list[tuple] = []

    def write(self, record=None, time_precision=None):
        self.written.append((record, time_precision))


@pytest.fixture
def influxdb_client_3_module(monkeypatch):
    created: list[FakeClient3] = []

    def client_factory(**kwargs):
        client = FakeClient3(**kwargs)
        created.append(client)
        return client

    module = types.ModuleType("influxdb_client_3")
    module.InfluxDBClient3 = client_factory
    monkeypatch.setitem(sys.modules, "influxdb_client_3", module)
    module.created = created
    return module


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


SECTION = {
    "influxdb3": {
        "host": "localhost",
        "port": "8181",
        "org": "nicolargo",
        "database": "glances",
        "token": "apiv3_token",
    }
}


def test_influxdb3_connects_with_the_configured_database(influxdb_client_3_module):
    from glances.exports.glances_influxdb3.export_v5 import Export

    Export(make_config(SECTION), args=None)

    kwargs = influxdb_client_3_module.created[0].kwargs
    assert kwargs["host"] == "localhost"
    assert kwargs["database"] == "glances"
    assert kwargs["token"] == "apiv3_token"


def test_influxdb3_exits_when_the_section_is_missing(influxdb_client_3_module):
    from glances.exports.glances_influxdb3.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), args=None)
    assert excinfo.value.code == 2


def test_influxdb3_exits_when_a_mandatory_key_is_missing(influxdb_client_3_module):
    """load_conf() is fatal on a missing mandatory key — there is no fallback."""
    from glances.exports.glances_influxdb3.export_v5 import Export

    section = {"influxdb3": {k: v for k, v in SECTION["influxdb3"].items() if k != "token"}}
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(section), args=None)
    assert excinfo.value.code == 2


def test_influxdb3_exits_when_the_connection_raises(influxdb_client_3_module):
    def boom(**kwargs):
        raise RuntimeError("unreachable")

    influxdb_client_3_module.InfluxDBClient3 = boom
    from glances.exports.glances_influxdb3.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(SECTION), args=None)
    assert excinfo.value.code == 2


@pytest.mark.asyncio
async def test_influxdb3_writes_normalised_measurements(influxdb_client_3_module):
    from glances.exports.glances_influxdb3.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    record, precision = influxdb_client_3_module.created[0].written[0]
    assert precision == "s"
    assert record[0]["measurement"] == "fakecollection"
    assert record[0]["tags"]["name"] == "eth0"
    assert record[0]["fields"]["rx"] == 10.0


@pytest.mark.asyncio
async def test_influxdb3_applies_the_optional_prefix(influxdb_client_3_module):
    from glances.exports.glances_influxdb3.export_v5 import Export

    store = StatsStoreV5()
    config = make_config({"influxdb3": {**SECTION["influxdb3"], "prefix": "lab"}})
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    record, _ = influxdb_client_3_module.created[0].written[0]
    assert record[0]["measurement"] == "lab.fakecollection"


@pytest.mark.asyncio
async def test_influxdb3_logs_a_warning_when_the_write_fails(influxdb_client_3_module, caplog):
    from glances.exports.glances_influxdb3.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)

    def boom(record=None, time_precision=None):
        raise RuntimeError("write refused")

    exporter.client.write = boom

    with caplog.at_level("WARNING"):
        exporter.update([plugin])

    assert "write refused" in caplog.text


def test_influxdb3_accepts_the_shipped_configuration_file(influxdb_client_3_module):
    """The mandatory list must match what conf/glances.conf actually declares.

    v5's load_conf() aborts on a missing mandatory where v4 merely left it
    None, so a mandatory list copied from v4 can make `--export influxdb3`
    unstartable for every user who never edited the config. Both the 2.x and
    3.x ports shipped exactly that bug until this test was written.
    """
    import configparser
    import pathlib

    parser = configparser.RawConfigParser()
    conf = pathlib.Path(__file__).resolve().parent.parent / "conf" / "glances.conf"
    parser.read(conf)
    section = {"influxdb3": dict(parser["influxdb3"])}

    from glances.exports.glances_influxdb3.export_v5 import Export

    # Must not raise SystemExit.
    Export(make_config(section), args=None)

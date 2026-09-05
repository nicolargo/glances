#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the InfluxDB 2.x export module.

`influxdb_client` is mocked: these tests assert on the connection arguments,
the write-buffer options and the measurements handed to the write API, not on
a live InfluxDB server.
"""

from __future__ import annotations

import sys
import types

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeWriteApi:
    """Stand-in for the batching write API returned by InfluxDBClient.write_api()."""

    def __init__(self, write_options):
        self.write_options = write_options
        self.written: list[tuple] = []

    def write(self, bucket, org, record, time_precision=None):
        self.written.append((bucket, org, record, time_precision))


class FakeHealth:
    status = "pass"
    version = "2.7.0"
    message = "ready for queries and writes"


class FakeUnhealthy:
    """What influxdb_client really returns for an unreachable server: it does
    NOT raise -- health() answers with status "fail" and no version."""

    status = "fail"
    version = None
    message = "Failed to establish a new connection: [Errno 111] Connection refused"


class FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.api: FakeWriteApi | None = None

    def health(self):
        return FakeHealth()

    def write_api(self, write_options):
        self.api = FakeWriteApi(write_options)
        return self.api


@pytest.fixture
def influxdb_client_module(monkeypatch):
    """Install a fake `influxdb_client` module for the duration of a test."""
    created: list[FakeClient] = []

    def client_factory(**kwargs):
        client = FakeClient(**kwargs)
        created.append(client)
        return client

    class FakeWriteOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    module = types.ModuleType("influxdb_client")
    module.InfluxDBClient = client_factory
    module.WriteOptions = FakeWriteOptions
    monkeypatch.setitem(sys.modules, "influxdb_client", module)
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
    "influxdb2": {
        "host": "localhost",
        "port": "8086",
        "user": "glances",
        "password": "glances",
        "org": "nicolargo",
        "bucket": "glances",
        "token": "EjFUTWe8U",
    }
}


def test_influxdb2_connects_with_the_configured_org_and_token(influxdb_client_module):
    from glances.exports.glances_influxdb2.export_v5 import Export

    Export(make_config(SECTION), args=None)

    kwargs = influxdb_client_module.created[0].kwargs
    assert kwargs["url"] == "http://localhost:8086"
    assert kwargs["org"] == "nicolargo"
    assert kwargs["token"] == "EjFUTWe8U"


def test_influxdb2_exits_when_the_section_is_missing(influxdb_client_module):
    from glances.exports.glances_influxdb2.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), args=None)
    assert excinfo.value.code == 2


@pytest.mark.parametrize("missing", ["host", "port", "org", "bucket", "token"])
def test_influxdb2_exits_when_a_mandatory_key_is_missing(influxdb_client_module, missing):
    """v5 divergence: load_conf() is fatal on a missing mandatory key, where v4
    silently continued with None. That is why the module carries no `is None`
    fallback for any of them."""
    from glances.exports.glances_influxdb2.export_v5 import Export

    section = {"influxdb2": {k: v for k, v in SECTION["influxdb2"].items() if k != missing}}
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(section), args=None)
    assert excinfo.value.code == 2


def test_influxdb2_flush_interval_follows_the_export_refresh(influxdb_client_module):
    """v5 change: v4 sized this from args.time, which v5 does not have."""
    from glances.exports.glances_influxdb2.export_v5 import Export

    sections = dict(SECTION, **{"global": {"refresh": "2"}, "export": {"refresh": "10"}})
    exporter = Export(make_config(sections), args=None)

    assert exporter.client.write_options.kwargs["flush_interval"] == 10000


def test_influxdb2_flush_interval_falls_back_to_the_global_refresh(influxdb_client_module):
    """No [export] refresh: the export loop runs at the global cadence, so the
    write buffer is sized from it."""
    from glances.exports.glances_influxdb2.export_v5 import Export

    sections = dict(SECTION, **{"global": {"refresh": "5"}})
    exporter = Export(make_config(sections), args=None)

    assert exporter.client.write_options.kwargs["flush_interval"] == 5000


def test_influxdb2_explicit_interval_wins(influxdb_client_module):
    from glances.exports.glances_influxdb2.export_v5 import Export

    sections = dict(SECTION)
    sections["influxdb2"] = dict(SECTION["influxdb2"], interval="30")
    sections["export"] = {"refresh": "10"}
    exporter = Export(make_config(sections), args=None)

    assert exporter.client.write_options.kwargs["flush_interval"] == 30000


def test_influxdb2_non_numeric_interval_falls_back(influxdb_client_module, caplog):
    from glances.exports.glances_influxdb2.export_v5 import Export

    sections = dict(SECTION)
    sections["influxdb2"] = dict(SECTION["influxdb2"], interval="soon")
    sections["export"] = {"refresh": "10"}
    with caplog.at_level("WARNING"):
        exporter = Export(make_config(sections), args=None)

    assert exporter.client.write_options.kwargs["flush_interval"] == 10000
    assert "interval" in caplog.text


async def test_influxdb2_writes_normalised_measurements(influxdb_client_module):
    from glances.exports.glances_influxdb2.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    bucket, org, record, precision = influxdb_client_module.created[0].api.written[0]
    assert bucket == "glances"
    assert org == "nicolargo"
    assert precision == "s"
    assert record[0]["tags"]["name"] == "eth0"
    assert record[0]["fields"]["rx"] == 10.0


async def test_influxdb2_prefixes_the_measurement_name(influxdb_client_module):
    from glances.exports.glances_influxdb2.export_v5 import Export

    store = StatsStoreV5()
    sections = dict(SECTION)
    sections["influxdb2"] = dict(SECTION["influxdb2"], prefix="mycomputer")
    config = make_config(sections)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    _, _, record, _ = influxdb_client_module.created[0].api.written[0]
    assert record[0]["measurement"] == "mycomputer.fakecollection"


async def test_influxdb2_logs_a_warning_when_the_write_fails(influxdb_client_module, caplog):
    from glances.exports.glances_influxdb2.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)

    def boom(*args, **kwargs):
        raise RuntimeError("bucket missing")

    exporter.client.write = boom

    with caplog.at_level("WARNING"):
        exporter.update([plugin])

    assert "bucket missing" in caplog.text


def test_influxdb2_accepts_the_shipped_configuration_file(influxdb_client_module):
    """The mandatory list must match what conf/glances.conf actually declares.

    v5's load_conf() aborts on a missing mandatory where v4 merely left it
    None, so a mandatory list copied from v4 can make `--export influxdb2`
    unstartable for every user who never edited the config. Both the 2.x and
    3.x ports shipped exactly that bug until this test was written.
    """
    import configparser
    import pathlib

    parser = configparser.RawConfigParser()
    conf = pathlib.Path(__file__).resolve().parent.parent / "conf" / "glances.conf"
    parser.read(conf)
    section = {"influxdb2": dict(parser["influxdb2"])}

    from glances.exports.glances_influxdb2.export_v5 import Export

    # Must not raise SystemExit.
    Export(make_config(section), args=None)


def test_influxdb2_warns_instead_of_claiming_a_connection_when_unhealthy(influxdb_client_module, caplog):
    """v4 logged the failure message under "Connected to InfluxDB server
    version None (...)" -- the opposite of the truth. Start-up is deliberately
    NOT fatal here: WriteOptions retries, so a server slow to come up must not
    kill Glances."""
    from glances.exports.glances_influxdb2.export_v5 import Export

    monkey = influxdb_client_module.created

    def unhealthy_factory(**kwargs):
        client = FakeClient(**kwargs)
        client.health = lambda: FakeUnhealthy()
        monkey.append(client)
        return client

    influxdb_client_module.InfluxDBClient = unhealthy_factory

    with caplog.at_level("WARNING"):
        Export(make_config(SECTION), args=None)

    assert "is not healthy" in caplog.text
    assert "Connected to InfluxDB server" not in caplog.text

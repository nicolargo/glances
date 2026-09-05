#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the InfluxDB 1.x export module."""

from __future__ import annotations

import sys
import types

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._baseurl = "http://localhost:8086"
        self.written: list[list[dict]] = []

    def get_list_database(self):
        return [{"name": "glances"}]

    def write_points(self, points, time_precision=None):
        self.written.append(points)


@pytest.fixture
def influxdb_module(monkeypatch):
    """Install a fake `influxdb` package (module + `influxdb.client` submodule)."""
    created: list[FakeClient] = []

    def client_factory(**kwargs):
        client = FakeClient(**kwargs)
        created.append(client)
        return client

    class FakeClientError(Exception):
        pass

    module = types.ModuleType("influxdb")
    module.InfluxDBClient = client_factory
    client_submodule = types.ModuleType("influxdb.client")
    client_submodule.InfluxDBClientError = FakeClientError
    module.client = client_submodule

    monkeypatch.setitem(sys.modules, "influxdb", module)
    monkeypatch.setitem(sys.modules, "influxdb.client", client_submodule)
    module.created = created
    module.ClientError = FakeClientError
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
    "influxdb": {
        "host": "localhost",
        "port": "8086",
        "user": "root",
        "password": "root",
        "db": "glances",
    }
}


def test_influxdb_connects_with_the_configured_credentials(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    Export(make_config(SECTION), args=None)

    kwargs = influxdb_module.created[0].kwargs
    assert kwargs["host"] == "localhost"
    assert kwargs["username"] == "root"
    assert kwargs["database"] == "glances"
    assert kwargs["ssl"] is False


def test_influxdb_uses_ssl_when_protocol_is_https(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    sections = {"influxdb": dict(SECTION["influxdb"], protocol="https")}
    Export(make_config(sections), args=None)

    assert influxdb_module.created[0].kwargs["ssl"] is True


def test_influxdb_defaults_to_plain_http_when_the_protocol_is_absent(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    exporter = Export(make_config(SECTION), args=None)

    # An absent optional key leaves the subclass default in place — it is
    # NOT reset to None by load_conf().
    assert exporter.protocol == "http"
    assert influxdb_module.created[0].kwargs["ssl"] is False


def test_influxdb_exits_when_the_section_is_missing(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), args=None)
    assert excinfo.value.code == 2


def test_influxdb_exits_when_a_mandatory_key_is_missing(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    sections = {"influxdb": {k: v for k, v in SECTION["influxdb"].items() if k != "db"}}
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(sections), args=None)
    assert excinfo.value.code == 2


def test_influxdb_exits_when_the_database_does_not_exist(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    sections = {"influxdb": dict(SECTION["influxdb"], db="absent")}
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(sections), args=None)
    assert excinfo.value.code == 2


def test_influxdb_exits_when_the_server_is_unreachable(influxdb_module):
    """v4 caught only InfluxDBClientError. Measured against influxdb 5.3.2: an
    unreachable server raises requests.exceptions.ConnectionError, which escaped
    and killed the process with a traceback. Deliberate v5 divergence."""
    from glances.exports.glances_influxdb.export_v5 import Export

    class ConnectionError_(Exception):
        """Stands in for requests.exceptions.ConnectionError."""

    def boom(**kwargs):
        raise ConnectionError_("Failed to establish a new connection")

    influxdb_module.InfluxDBClient = boom

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(SECTION), args=None)
    assert excinfo.value.code == 2


def test_influxdb_exits_when_the_client_cannot_connect(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    def boom(**kwargs):
        raise influxdb_module.ClientError("unreachable")

    influxdb_module.InfluxDBClient = boom

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(SECTION), args=None)
    assert excinfo.value.code == 2


@pytest.mark.asyncio
async def test_influxdb_writes_normalised_measurements(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    written = influxdb_module.created[0].written
    assert len(written) == 1
    measurement = written[0][0]
    assert measurement["measurement"] == "fakecollection"
    assert measurement["tags"]["name"] == "eth0"
    assert measurement["fields"]["rx"] == 10.0


@pytest.mark.asyncio
async def test_influxdb_applies_the_prefix(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    store = StatsStoreV5()
    sections = {"influxdb": dict(SECTION["influxdb"], prefix="myhost")}
    config = make_config(sections)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)
    exporter.update([plugin])

    assert influxdb_module.created[0].written[0][0]["measurement"] == "myhost.fakecollection"


@pytest.mark.asyncio
async def test_influxdb_logs_a_warning_when_the_write_fails(influxdb_module, caplog):
    from glances.exports.glances_influxdb.export_v5 import Export

    store = StatsStoreV5()
    config = make_config(SECTION)
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    exporter = Export(config, args=None)

    def boom(points, time_precision=None):
        raise RuntimeError("server down")

    exporter.client.write_points = boom

    with caplog.at_level("WARNING"):
        exporter.update([plugin])

    assert "server down" in caplog.text
    assert "ERROR" not in [record.levelname for record in caplog.records]


def test_influxdb_accepts_the_shipped_configuration_file(influxdb_module):
    """The mandatory list must match what conf/glances.conf actually declares.

    v5's load_conf() aborts on a missing mandatory where v4 merely left it
    None, so a mandatory list copied from v4 can make `--export influxdb`
    unstartable for every user who never edited the config. Both the 2.x and
    3.x ports shipped exactly that bug until this test was written.
    """
    import configparser
    import pathlib

    parser = configparser.RawConfigParser()
    conf = pathlib.Path(__file__).resolve().parent.parent / "conf" / "glances.conf"
    parser.read(conf)
    section = {"influxdb": dict(parser["influxdb"])}

    from glances.exports.glances_influxdb.export_v5 import Export

    # Must not raise SystemExit.
    Export(make_config(section), args=None)

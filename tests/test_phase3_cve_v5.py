#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — P3-7: the Phase 3 CVEs, verified against the real code and the real drivers.

The chantier tests (P3-3 to P3-5) prove each fix with fakes. This pass
attacks the same code with the real libraries wherever they can run here:

- CVE-2026-30930 (TimescaleDB): the exporter's own SQL, rendered by the real
  psycopg and run on a real PostgreSQL when `GLANCES_TEST_PG` names one
  (`host=... port=... user=... dbname=...`). PostgreSQL rejects the
  `timescaledb.*` table options without the extension, so the harness
  removes that one clause from the exporter's CREATE and runs the rest
  unchanged: the identifiers, the placeholders and the values are the
  exporter's.
- CVE-2026-32611 (DuckDB): a real database, for a battery of hostile names.
- CVE-2026-35588 (Cassandra): the identifier allowlist, fuzzed.
- CVE-2026-32633 and -32634: the new routes behind the auth middleware, the
  client's URL never carrying credentials, and `/api/5/config` never
  serving `[passwords]` (a leak this pass found and fixed).
"""

from __future__ import annotations

import asyncio
import importlib.util
import os

import pytest

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5
from tests.export_fakes_v5 import make_config

# Strings drawn from monitored data: a process name, a mount point, an
# interface name. Each one tries to end a literal or an identifier and run
# its own statement against the canary table.
HOSTILE = [
    "x'); DROP TABLE canary; --",
    'x"); DROP TABLE canary; --',
    "x`); DROP TABLE canary; --",
    "x]); DROP TABLE canary; --",
    "line\nbreak'); DROP TABLE canary; --",
    "$$); DROP TABLE canary; $$",
    "\\'); DROP TABLE canary; --",
    "é ✓'); DROP TABLE canary; --",
    "%s %(x)s ? :1 {0}",
]


def _hostile_plugins(hostile: str, config) -> list[GlancesPluginBase]:
    """A scalar plugin whose FIELD NAME and value are hostile, and a collection whose item name is."""

    class Scalar(GlancesPluginBase[dict]):
        plugin_name = "hscalar"
        fields_description = {
            hostile: {"description": "h", "unit": "percent"},
            "label": {"description": "l", "unit": "string"},
        }

        async def _grab_stats(self) -> dict:
            return {hostile: 1.5, "label": hostile}

    class Collection(GlancesPluginBase[list]):
        plugin_name = "hcoll"
        IS_COLLECTION = True
        fields_description = {
            "name": {"description": "n", "unit": "string", "primary_key": True},
            "rx": {"description": "r", "unit": "bytes"},
        }

        async def _grab_stats(self) -> list:
            return [{"name": hostile, "rx": 7}]

    store = StatsStoreV5()
    built = [Scalar(store, config), Collection(store, config)]
    for plugin in built:
        asyncio.run(plugin.update())
    return built


requires = {
    name: pytest.mark.skipif(importlib.util.find_spec(name) is None, reason=f"{name} not installed")
    for name in ("duckdb", "psycopg")
}


# --------------------------------------------------- CVE-2026-32611 DuckDB


@requires["duckdb"]
@pytest.mark.parametrize("hostile", HOSTILE)
def test_duckdb_stores_hostile_names_as_data_on_a_real_database(tmp_path, hostile):
    import duckdb

    from glances.exports.glances_duckdb.export_v5 import Export

    path = str(tmp_path / "glances.db")
    setup = duckdb.connect(path)
    setup.execute("CREATE TABLE canary (a INT)")
    setup.close()
    config = make_config({"duckdb": {"database": path, "hostname": hostile}})
    exporter = Export(config)
    exporter.update(_hostile_plugins(hostile, config))
    exporter.exit()

    check = duckdb.connect(path)
    assert sorted(t[0] for t in check.sql("SHOW TABLES").fetchall()) == ["canary", "hcoll", "hscalar"]
    assert check.execute('SELECT "name", "rx" FROM "hcoll"').fetchall() == [(hostile, 7)]
    columns = [row[0] for row in check.execute("DESCRIBE hscalar").fetchall()]
    assert hostile in columns, "a hostile field name is a quoted column, not SQL"
    assert check.execute('SELECT "label", "hostname_id" FROM "hscalar"').fetchall() == [(hostile, hostile)]
    check.close()


# ---------------------------------------------- CVE-2026-30930 TimescaleDB

_PG = os.environ.get("GLANCES_TEST_PG")


class _PlainPostgres:
    """The exporter's connection, minus the `timescaledb.*` options PostgreSQL would reject."""

    def __init__(self, conn):
        self._conn = conn

    def transaction(self):
        return self._conn.transaction()

    def cursor(self):
        conn = self._conn
        cursor = conn.cursor()

        class Cursor:
            def __enter__(self):
                cursor.__enter__()
                return self

            def __exit__(self, *exc):
                return cursor.__exit__(*exc)

            def execute(self, query, params=None):
                if not isinstance(query, str):
                    text = query.as_string(conn)
                    if text.startswith("CREATE TABLE"):
                        query = text[: text.index(") WITH (") + 1]
                return cursor.execute(query, params)

            def executemany(self, query, rows):
                return cursor.executemany(query, rows)

            def fetchone(self):
                return cursor.fetchone()

        return Cursor()

    def close(self):
        self._conn.close()


@requires["psycopg"]
@pytest.mark.skipif(not _PG, reason="GLANCES_TEST_PG names no PostgreSQL server")
@pytest.mark.parametrize("hostile", HOSTILE)
def test_timescaledb_stores_hostile_names_as_data_on_a_real_postgresql(hostile):
    import psycopg

    from glances.exports.glances_timescaledb.export_v5 import Export

    params = dict(item.split("=", 1) for item in _PG.split())
    with psycopg.connect(**params, autocommit=True) as admin:
        for table in ("canary", "hscalar", "hcoll"):
            admin.execute(psycopg.sql.SQL("DROP TABLE IF EXISTS {}").format(psycopg.sql.Identifier(table)))
        admin.execute("CREATE TABLE canary (a INT)")
    section = {"host": params["host"], "port": params["port"], "db": params["dbname"], "user": params["user"]}
    config = make_config({"timescaledb": {**section, "hostname": hostile}})
    exporter = Export(config)
    exporter.client = _PlainPostgres(exporter.client)
    exporter.update(_hostile_plugins(hostile, config))
    exporter.exit()

    with psycopg.connect(**params) as check:
        tables = {
            row[0]
            for row in check.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ).fetchall()
        }
        assert tables == {"canary", "hscalar", "hcoll"}, "nothing dropped, nothing extra"
        assert check.execute('SELECT "key_id", "name", "rx" FROM "hcoll"').fetchall() == [("name", hostile, 7)]
        assert check.execute('SELECT "label", "hostname_id" FROM "hscalar"').fetchall() == [(hostile, hostile)]
        columns = {
            row[0]
            for row in check.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'hscalar'"
            ).fetchall()
        }
        # PostgreSQL truncates identifiers to 63 bytes; none of these is that long.
        assert hostile in columns


# ------------------------------------------------ CVE-2026-35588 Cassandra


@pytest.mark.parametrize(
    ("key", "value"),
    [
        *(("keyspace", h) for h in HOSTILE),
        *(("table", h) for h in HOSTILE),
        ("keyspace", "glances\n"),
        ("keyspace", "ｇlances"),  # fullwidth letter: not ASCII
        ("table", "g" + "́"),
        ("replication_factor", "١"),  # an Arabic-Indic digit is not [0-9]
        ("replication_factor", "1 OR 1"),
        ("port", "9042\n; x"),
        ("protocol_version", "-1"),
    ],
)
def test_cassandra_allowlist_refuses_every_hostile_identifier(monkeypatch, key, value):
    from glances.exports.glances_cassandra import export_v5

    monkeypatch.setattr(export_v5.Export, "init", lambda self: pytest.fail("no statement may run"))
    section = {"host": "c", "port": "9042", "keyspace": "glances", "table": "host", "replication_factor": "2"}
    with pytest.raises(SystemExit):
        export_v5.Export(make_config({"cassandra": {**section, key: value}}))


# ----------------------------------------- CVE-2026-32633 / -32634, routes


@pytest.fixture
def protected_config(tmp_path, monkeypatch):
    from glances.config_v5 import GlancesConfigV5
    from glances.security_v5 import hash_password

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    conf = tmp_path / "glances.conf"
    conf.write_text(
        f"[outputs]\npassword={hash_password('hunter2')}\n[passwords]\nalpha=alpha-s3cret\ndefault=default-s3cret\n"
    )
    return GlancesConfigV5(str(conf))


def test_the_browser_routes_sit_behind_the_auth_middleware(protected_config):
    import argparse

    from fastapi.testclient import TestClient

    from glances.servers_list_v5 import ServersPoller
    from glances.webserver_v5 import build_app

    app = build_app(
        config=protected_config, store=StatsStoreV5(), args=argparse.Namespace(disable_webui=False, browser=True)
    )
    app.state.servers_poller = ServersPoller([], protected_config, [])
    with TestClient(app) as client:
        assert client.get("/api/5/serverslist").status_code == 401
        assert client.get("/browser").status_code == 401
        assert client.get("/api/5/serverslist", auth=("glances", "hunter2")).status_code == 200


def test_config_route_never_serves_the_passwords_section(tmp_path, monkeypatch):
    """Found by this pass: `[passwords]` maps HOST NAMES to clear passwords, and
    the key-name rules of CVE-2026-32609 / 30928 saw nothing secret in `alpha`.
    v4 leaves the section out (`_SECURE_BLOCKED_SECTIONS`); the v5 port had not."""
    from fastapi.testclient import TestClient

    from glances.config_v5 import GlancesConfigV5
    from glances.webserver_v5 import build_app

    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "none.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    conf = tmp_path / "glances.conf"
    conf.write_text("[passwords]\nalpha=alpha-s3cret\ndefault=default-s3cret\n")
    with TestClient(build_app(config=GlancesConfigV5(str(conf)), store=StatsStoreV5())) as client:
        response = client.get("/api/5/config")
    assert "s3cret" not in response.text
    assert "passwords" not in response.json(), "left out, host names included"


@pytest.mark.parametrize(
    "target", ["http://glances:s3cret@alpha:61208", "https://u:s3cret@alpha/glances", "u:s3cret@alpha"]
)
def test_the_client_url_never_carries_credentials(target):
    """`-c` and the browser build every request URL from `parse_target`: userinfo is dropped."""
    from glances.client_v5 import parse_target

    try:
        base_url, _ = parse_target(target)
    except ValueError:
        return  # refused outright is fine too
    assert "s3cret" not in base_url and "@" not in base_url

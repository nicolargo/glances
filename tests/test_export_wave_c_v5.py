#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wave C exporters (P3-3): mongodb, couchdb, elasticsearch, clickhouse.

Each client library is faked: the tests assert on what reaches it.
"""

from __future__ import annotations

import importlib
import logging
import types
from datetime import datetime

import pytest

from tests.export_fakes_v5 import (
    HOSTILE_NAME,
    assert_plugins_untouched,
    fake_module,
    make_config,
    missing_module,
    plugins,
)

USER, PASSWORD = "the-db-user", "s3cr3t:p@ss/word"

SECTIONS = {
    "mongodb": {"host": "mongo", "port": "27017", "db": "glances", "user": USER, "password": PASSWORD},
    "couchdb": {"host": "couch", "port": "5984", "db": "glances", "user": USER, "password": PASSWORD},
    "elasticsearch": {"scheme": "https", "host": "es", "port": "9200", "index": "glances"},
    "clickhouse": {"host": "ch", "port": "8123", "db": "glances", "user": USER, "password": PASSWORD},
}
LIBRARIES = {
    "mongodb": "pymongo",
    "couchdb": "pycouchdb",
    "elasticsearch": "elasticsearch",
    "clickhouse": "clickhouse_connect",
}


class Backend:
    """What the fake clients saw — one instance per test."""

    def __init__(self):
        self.client_args: dict = {}
        self.writes: list = []
        self.collections: list[str] = []
        self.sql: list[str] = []
        self.closed = False
        self.fail: Exception | None = None

    def write(self, *items):
        if self.fail is not None:
            raise self.fail
        self.writes.extend(items)


def _fake_pymongo(monkeypatch, seen: Backend) -> None:
    class Collection:
        def insert_one(self, doc):
            seen.write(dict(doc))

    class MongoClient:
        def __init__(self, **kwargs):
            seen.client_args = kwargs
            self.admin = types.SimpleNamespace(command=lambda cmd: {"ok": 1})

        def __getitem__(self, db):
            assert db == "glances"
            return MongoDatabase()

        def close(self):
            seen.closed = True

    class MongoDatabase:
        def __getitem__(self, name):
            seen.collections.append(name)
            return Collection()

    fake_module(monkeypatch, "pymongo", MongoClient=MongoClient)


def _fake_pycouchdb(monkeypatch, seen: Backend) -> None:
    class CouchDatabase:
        def save(self, doc):
            seen.write(dict(doc))

    class Server:
        def __init__(self, url):
            seen.client_args = {"url": url}
            self.resource = types.SimpleNamespace(session=types.SimpleNamespace(close=self._close))
            self.databases: set[str] = set()

        def _close(self):
            seen.closed = True

        def info(self):
            return {"version": "3.3"}

        def database(self, name):
            if name not in self.databases:
                raise LookupError(name)
            return CouchDatabase()

        def create(self, name):
            self.databases.add(name)

    fake_module(monkeypatch, "pycouchdb", Server=Server)


def _fake_elasticsearch(monkeypatch, seen: Backend) -> None:
    class Elasticsearch:
        def __init__(self, **kwargs):
            seen.client_args = kwargs

        def ping(self):
            return True

        def close(self):
            seen.closed = True

    def bulk(client, actions):
        assert isinstance(client, Elasticsearch)
        seen.write(*actions)

    fake_module(monkeypatch, "elasticsearch", Elasticsearch=Elasticsearch, helpers=types.SimpleNamespace(bulk=bulk))


def _fake_clickhouse_connect(monkeypatch, seen: Backend) -> None:
    def quote_identifier(identifier):
        # The driver's own escaping: backslash before \ ' and `.
        escaped = "".join(f"\\{c}" if c in "\\'`" else c for c in identifier)
        return f"`{escaped}`"

    class ChClient:
        def command(self, sql):
            seen.sql.append(sql)

        def query(self, sql):
            seen.sql.append(sql)
            return types.SimpleNamespace(result_rows=[("time", "DateTime")])

        def insert(self, table, data, column_names):
            seen.write({"table": table, "columns": list(column_names), "rows": [list(r) for r in data]})

        def close(self):
            seen.closed = True

    def get_client(**kwargs):
        seen.client_args = kwargs
        return ChClient()

    fake_module(monkeypatch, "clickhouse_connect", get_client=get_client)
    fake_module(monkeypatch, "clickhouse_connect.driver.binding", quote_identifier=quote_identifier)


@pytest.fixture
def backend(monkeypatch):
    """Install a fake for all four client libraries."""
    seen = Backend()
    for install in (_fake_pymongo, _fake_pycouchdb, _fake_elasticsearch, _fake_clickhouse_connect):
        install(monkeypatch, seen)
    return seen


def run(name: str, extra: dict | None = None):
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    config = make_config({name: SECTIONS[name], **(extra or {})})
    exporter = module.Export(config)
    exporter.update(plugins(config))
    return exporter


# ---------------------------------------------------------------- mongodb


def test_mongodb_inserts_one_document_per_plugin_in_its_collection(backend):
    exporter = run("mongodb")
    assert backend.client_args == {"host": "mongo", "port": 27017, "username": USER, "password": PASSWORD}
    assert backend.collections == ["fakescalar", "fakecollection"]
    scalar, collection = backend.writes
    assert scalar["total"] == 12.5 and scalar["label"] == "busy host" and scalar["missing"] is None
    assert collection["eth0.rx"] == 10 and collection["eth0.name"] == "eth0"
    assert collection[f"{HOSTILE_NAME}.rx"] == 20
    exporter.exit()
    assert backend.closed


# ---------------------------------------------------------------- couchdb


def test_couchdb_creates_the_db_and_saves_typed_timestamped_documents(backend):
    exporter = run("couchdb")
    assert backend.client_args == {"url": "http://the-db-user:s3cr3t%3Ap%40ss%2Fword@couch:5984/"}
    scalar, collection = backend.writes
    assert scalar["type"] == "fakescalar" and scalar["total"] == 12.5 and scalar["label"] == "busy host"
    assert scalar["missing"] is None
    assert scalar["time"].endswith("Z") and datetime.fromisoformat(scalar["time"][:-1])
    assert collection["type"] == "fakecollection"
    assert collection["eth0.rx"] == 10 and collection[f"{HOSTILE_NAME}.rx"] == 20
    exporter.exit()
    assert backend.closed


# ---------------------------------------------------------- elasticsearch


def test_elasticsearch_bulks_one_stringified_action_per_plugin(backend):
    exporter = run("elasticsearch")
    assert backend.client_args == {"hosts": ["https://es:9200"]}
    scalar, collection = backend.writes
    stamp = scalar["_source"]["timestamp"]
    assert scalar["_index"] == f"glances-{stamp[:10].replace('-', '.')}"
    assert scalar["_id"] == f"fakescalar.{stamp}" and scalar["_type"] == "glances-fakescalar"
    assert scalar["_source"]["plugin"] == "fakescalar"
    assert scalar["_source"]["total"] == "12.5" and scalar["_source"]["label"] == "busy host"
    assert scalar["_source"]["missing"] == "None"
    assert collection["_source"]["eth0.rx"] == "10" and collection["_source"][f"{HOSTILE_NAME}.rx"] == "20"
    exporter.exit()
    assert backend.closed


# ------------------------------------------------------------- clickhouse


def test_clickhouse_creates_typed_tables_and_inserts_rows(backend):
    exporter = run("clickhouse", {"clickhouse": {**SECTIONS["clickhouse"], "hostname": "box"}})
    assert backend.client_args == {
        "host": "ch",
        "port": 8123,
        "username": USER,
        "password": PASSWORD,
        "database": "glances",
    }
    create = [s for s in backend.sql if s.startswith("CREATE TABLE IF NOT EXISTS `fakescalar`")]
    assert create and "`total` Nullable(Float64)" in create[0] and "`label` Nullable(String)" in create[0]
    assert "`time` DateTime" in create[0] and "`hostname_id` String" in create[0]
    scalar, collection = backend.writes
    assert scalar["table"] == "fakescalar"
    assert scalar["columns"][:5] == ["time", "hostname_id", "total", "label", "missing"]
    assert scalar["rows"][0][1:5] == ["box", 12.5, "busy host", None]
    assert collection["table"] == "fakecollection"
    assert collection["columns"][:5] == ["time", "hostname_id", "key_id", "name", "rx"]
    assert [row[1:5] for row in collection["rows"]] == [["box", "name", "eth0", 10], ["box", "name", HOSTILE_NAME, 20]]
    exporter.exit()
    assert backend.closed


def test_clickhouse_hostile_names_never_reach_the_sql(backend):
    # A monitored name is only ever data; a hostile config key (a column name) is refused.
    hostile_option = "x` Int8) ENGINE=Log; DROP TABLE cpu; --"
    run("clickhouse", {"fakescalar": {hostile_option: "1"}})
    assert backend.sql, "tables were created"
    assert not any(HOSTILE_NAME in sql or "DROP" in sql for sql in backend.sql)
    rows = [row for doc in backend.writes for row in doc["rows"]]
    assert any(HOSTILE_NAME in row for row in rows), "the hostile name arrives as a value"
    assert all(hostile_option not in doc["columns"] for doc in backend.writes)


def test_clickhouse_hostile_table_name_sends_no_sql(backend):
    """Port of GHSA-2hvx-g9v6-w29h: a table name with a backtick is refused, not escaped."""
    exporter = run("clickhouse")
    backend.sql.clear()
    backend.writes.clear()
    injection = "x` ENGINE = MergeTree() AS SELECT * FROM url('http://evil"
    exporter.export(injection, ["time", "hostname_id"], [[datetime.now(), "h"]])
    assert backend.sql == [] and backend.writes == []
    exporter.export("my plugin", ["time", "hostname_id"], [[datetime.now(), "h"]])
    assert backend.sql[0].startswith("CREATE TABLE IF NOT EXISTS `my plugin` (")


def test_clickhouse_update_leaves_the_plugin_view_and_the_store_untouched(backend):
    """Port of v4 #3767."""
    config = make_config({"clickhouse": SECTIONS["clickhouse"], "fakecollection": {"rx_careful": "60"}})
    built = plugins(config)
    importlib.import_module("glances.exports.glances_clickhouse.export_v5").Export(config).update(built)
    assert {"key_id", "history_size", "fakecollection_rx_careful"} <= set(backend.writes[1]["columns"])
    assert_plugins_untouched(built)


# ------------------------------------------------------------------ common


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_a_missing_section_or_library_is_fatal_and_says_so(monkeypatch, caplog, name):
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    with pytest.raises(SystemExit):
        module.Export(make_config({}))
    assert f"Missing {name} config" in caplog.text
    missing_module(monkeypatch, LIBRARIES[name])
    with pytest.raises(SystemExit):
        module.Export(make_config({name: SECTIONS[name]}))
    assert f"needs the {LIBRARIES[name]} library" in caplog.text


@pytest.mark.parametrize("name", ["mongodb", "clickhouse", "couchdb"])
def test_a_missing_mandatory_key_is_fatal(backend, name):
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    section = {k: v for k, v in SECTIONS[name].items() if k != "db"}
    with pytest.raises(SystemExit):
        module.Export(make_config({name: section}))


@pytest.mark.parametrize(
    ("name", "label"),
    [("mongodb", "MongoDB"), ("couchdb", "CouchDB"), ("elasticsearch", "ElasticSearch"), ("clickhouse", "ClickHouse")],
)
def test_a_failing_write_is_one_warning_per_plugin_not_a_crash(backend, caplog, name, label):
    backend.fail = OSError("network down")
    run(name)
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        f"Cannot export fakescalar stats to {label} (network down)",
        f"Cannot export fakecollection stats to {label} (network down)",
    ]


@pytest.mark.parametrize("failing", [False, True])
@pytest.mark.parametrize("name", ["mongodb", "couchdb", "clickhouse"])
def test_no_credential_is_logged(backend, caplog, name, failing):
    caplog.set_level(logging.DEBUG)
    if failing:
        # A driver error that quotes the credentials back.
        backend.fail = OSError(f"auth failed for {USER}:{PASSWORD}")
    run(name).exit()
    assert caplog.text, "something was logged"
    for secret in (USER, PASSWORD, "s3cr3t%3Ap%40ss%2Fword"):
        assert secret not in caplog.text


def test_couchdb_connection_error_does_not_log_the_url(monkeypatch, backend, caplog):
    import pycouchdb

    def unreachable(self):
        raise ConnectionError(f"cannot reach {backend.client_args['url']}")

    monkeypatch.setattr(pycouchdb.Server, "info", unreachable)
    with pytest.raises(SystemExit):
        run("couchdb")
    assert "Cannot connect to CouchDB server couch:5984" in caplog.text
    assert "s3cr3t" not in caplog.text and USER not in caplog.text


def test_the_exporters_are_discovered_by_export(backend):
    from glances.main_v5 import apply_export_flags, build_parser, discover_exporters

    args = build_parser().parse_args(["--export", "mongodb,couchdb,elasticsearch,clickhouse"])
    apply_export_flags(args)
    assert sorted(e.export_name for e in discover_exporters(make_config(SECTIONS), args)) == [
        "clickhouse",
        "couchdb",
        "elasticsearch",
        "mongodb",
    ]

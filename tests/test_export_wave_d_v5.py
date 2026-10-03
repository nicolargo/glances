#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wave D exporters (P3-3): timescaledb, duckdb, cassandra.

These carry CVE-2026-30930 (TimescaleDB), CVE-2026-32611 (DuckDB) and
CVE-2026-35588 (Cassandra). The client libraries are faked and every
statement is recorded as TEXT plus bound PARAMETERS: a string drawn from
monitored data (HOSTILE_NAME) may appear in the parameters, never in the
text. DuckDB is also exercised for real when it is installed.
"""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5
from tests.export_fakes_v5 import (
    HOSTILE_NAME,
    assert_plugins_untouched,
    fake_module,
    make_config,
    missing_module,
    plugins,
)


class HostileFieldPlugin(GlancesPluginBase[dict]):
    """A plugin whose field NAME is hostile: it becomes a column name."""

    plugin_name = "fakehostilefield"
    fields_description = {HOSTILE_NAME: {"description": "h", "unit": "percent"}}

    async def _grab_stats(self) -> dict:
        return {HOSTILE_NAME: 1.5}


def all_plugins(config):
    extra = HostileFieldPlugin(StatsStoreV5(), config)
    asyncio.run(extra.update())
    return [*plugins(config), extra]


def _flatten(values):
    for value in values:
        if isinstance(value, (list, tuple)):
            yield from _flatten(value)
        elif isinstance(value, dict):
            yield from value.keys()
            yield from value.values()
        else:
            yield value


# =========================================================== timescaledb


class _Composable:
    """psycopg.sql stand-in: renders the way psycopg quotes."""

    def __init__(self, text: str) -> None:
        self.text = text

    def as_string(self, context=None) -> str:
        return self.text


class _SQL(_Composable):
    def format(self, *args, **kwargs):
        return _Composable(
            self.text.format(*(a.as_string() for a in args), **{k: v.as_string() for k, v in kwargs.items()})
        )

    def join(self, seq):
        return _Composable(self.text.join(item.as_string() for item in seq))


def _identifier(name):
    return _Composable('"' + name.replace('"', '""') + '"')


def _literal(value):
    return _Composable("'" + str(value).replace("'", "''") + "'")


def _placeholder():
    return _Composable("%s")


class _PgCursor:
    def __init__(self, conn):
        self.conn = conn
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        text = query if isinstance(query, str) else query.as_string(None)
        self.conn.statements.append((text, params))
        if text.startswith("SELECT EXISTS"):
            self._result = (params[0] in self.conn.tables,)
        elif text.startswith("CREATE TABLE"):
            self.conn.tables.add(text.split('"')[1])

    def executemany(self, query, rows):
        self.conn.fail_if_asked()
        self.conn.statements.append((query.as_string(None), [list(r) for r in rows]))

    def fetchone(self):
        return self._result


class _PgTransaction:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *exc):
        self.conn.events.append("rollback" if exc_type else "commit")
        return False


class _PgConnection:
    instances: list[_PgConnection] = []
    fail = False

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.statements: list[tuple[str, object]] = []
        self.events: list[str] = []
        self.tables: set[str] = set()
        _PgConnection.instances.append(self)

    def fail_if_asked(self):
        if _PgConnection.fail:
            raise RuntimeError("disk full")

    def transaction(self):
        return _PgTransaction(self)

    def cursor(self):
        return _PgCursor(self)

    def close(self):
        self.events.append("close")


def _fake_psycopg(monkeypatch):
    _PgConnection.instances = []
    _PgConnection.fail = False
    fake_module(monkeypatch, "psycopg", connect=lambda **kw: _PgConnection(**kw))
    fake_module(
        monkeypatch, "psycopg.sql", SQL=_SQL, Identifier=_identifier, Literal=_literal, Placeholder=_placeholder
    )


TIMESCALE = {"host": "pg", "port": "5432", "db": "glances", "user": "postgres", "password": "p w'd"}


def test_timescaledb_connects_with_keyword_arguments(monkeypatch):
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    Export(make_config({"timescaledb": TIMESCALE}))
    assert _PgConnection.instances[0].kwargs == {
        "host": "pg",
        "port": "5432",
        "dbname": "glances",
        "user": "postgres",
        "password": "p w'd",
    }


def test_timescaledb_binds_every_value_and_quotes_every_identifier(monkeypatch):
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    config = make_config({"timescaledb": {**TIMESCALE, "hostname": HOSTILE_NAME}})
    Export(config).update(all_plugins(config))
    conn = _PgConnection.instances[0]
    texts = [text for text, _ in conn.statements]
    assert texts and all(HOSTILE_NAME not in text for text in texts)
    assert all("busy host" not in text and "eth0" not in text for text in texts), "values are never SQL text"
    # v4 layout: time, hostname_id, (key_id), then one column per field.
    create = next(t for t in texts if t.startswith('CREATE TABLE "fakecollection"'))
    assert '"time" TIMESTAMPTZ NOT NULL, "hostname_id" TEXT NOT NULL, "key_id" TEXT NOT NULL' in create
    assert "timescaledb.segmentby = 'hostname_id, key_id'" in create
    # The hostile field NAME is a quoted identifier, embedded quote doubled.
    assert '"' + HOSTILE_NAME.replace('"', '""') + '" DOUBLE PRECISION NULL' in "".join(texts)
    rows = {text.split('"')[1]: params for text, params in conn.statements if text.startswith("INSERT INTO")}
    assert set(rows) == {"fakescalar", "fakecollection", "fakehostilefield"}
    assert rows["fakescalar"][0][1:] == [HOSTILE_NAME, 12.5, "busy host", None, 28800.0]
    collection = rows["fakecollection"]
    assert [row[3:5] for row in collection] == [["eth0", 10], [HOSTILE_NAME, 20]]
    assert all(row[1] == HOSTILE_NAME and row[2] == "name" for row in collection), "key_id as v4 fills it"
    assert HOSTILE_NAME in list(_flatten(params for _, params in conn.statements))
    assert conn.events.count("commit") == 3


def test_timescaledb_collection_rows_match_their_columns(monkeypatch):
    """Port of v4 #3592: one value per column, `key` only as key_id, no field dropped."""
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    config = make_config({"timescaledb": {**TIMESCALE, "hostname": "box"}})
    Export(config).update(plugins(config))
    statements = _PgConnection.instances[0].statements
    create = next(t for t, _ in statements if t.startswith('CREATE TABLE "fakecollection"'))
    insert, rows = next((t, p) for t, p in statements if t.startswith('INSERT INTO "fakecollection"'))
    columns = [c.strip('"') for c in insert.split(" (", 1)[1].split(") VALUES")[0].split(", ")]
    assert '"key" ' not in create and "key" not in columns
    assert all(len(row) == len(columns) for row in rows)
    assert [dict(zip(columns[1:], row[1:])) for row in rows] == [
        {"hostname_id": "box", "key_id": "name", "name": name, "rx": rx, "history_size": 28800.0}
        for name, rx in (("eth0", 10), (HOSTILE_NAME, 20))
    ]


def test_timescaledb_does_not_recreate_an_existing_table(monkeypatch):
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    config = make_config({"timescaledb": TIMESCALE})
    exporter = Export(config)
    stats = plugins(config)
    exporter.update(stats)
    exporter.update(stats)
    texts = [text for text, _ in _PgConnection.instances[0].statements]
    assert sum(t.startswith("CREATE TABLE") for t in texts) == 2
    assert sum(t.startswith("INSERT INTO") for t in texts) == 4


def test_timescaledb_hostile_config_never_reaches_sql(monkeypatch):
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    config = make_config({"timescaledb": {**TIMESCALE, "db": "x; DROP TABLE y", "password": HOSTILE_NAME}})
    Export(config).update(plugins(config))
    conn = _PgConnection.instances[0]
    assert conn.kwargs["dbname"] == "x; DROP TABLE y" and conn.kwargs["password"] == HOSTILE_NAME
    assert all("DROP" not in text for text, _ in conn.statements)


def test_timescaledb_failing_write_is_one_warning_per_plugin(monkeypatch, caplog):
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    config = make_config({"timescaledb": TIMESCALE})
    exporter = Export(config)
    _PgConnection.fail = True
    exporter.update(plugins(config))
    assert caplog.text.count("Cannot export fakescalar stats to TimescaleDB (disk full)") == 1
    assert caplog.text.count("Cannot export fakecollection stats to TimescaleDB") == 1
    assert _PgConnection.instances[0].events == ["rollback", "rollback"]
    assert "p w'd" not in caplog.text


def test_timescaledb_exit_closes(monkeypatch):
    _fake_psycopg(monkeypatch)
    from glances.exports.glances_timescaledb.export_v5 import Export

    Export(make_config({"timescaledb": TIMESCALE})).exit()
    assert _PgConnection.instances[0].events == ["close"]


# ================================================================ duckdb


class _DuckConnection:
    instances: list[_DuckConnection] = []
    fail = False

    def __init__(self, database):
        self.database = database
        self.statements: list[tuple[str, object]] = []
        self.events: list[str] = []
        self.tables: list[str] = []
        _DuckConnection.instances.append(self)

    def sql(self, text):
        self.statements.append((text, None))
        tables = [(t,) for t in self.tables]
        return type("Result", (), {"fetchall": lambda _self: tables})()

    def execute(self, text, params=None):
        self.statements.append((text, params))
        if text.startswith("CREATE TABLE"):
            self.tables.append(text.split('"')[1])

    def executemany(self, text, rows):
        if _DuckConnection.fail:
            raise RuntimeError("read-only database")
        self.statements.append((text, [list(r) for r in rows]))

    def commit(self):
        self.events.append("commit")

    def close(self):
        self.events.append("close")


def _fake_duckdb(monkeypatch):
    _DuckConnection.instances = []
    _DuckConnection.fail = False
    fake_module(monkeypatch, "duckdb", connect=lambda database: _DuckConnection(database))


def test_duckdb_connects_to_the_configured_database(monkeypatch):
    _fake_duckdb(monkeypatch)
    from glances.exports.glances_duckdb.export_v5 import Export

    Export(make_config({"duckdb": {"database": "/var/lib/glances.db"}}))
    assert _DuckConnection.instances[0].database == "/var/lib/glances.db"


def test_duckdb_binds_every_value_and_quotes_every_identifier(monkeypatch):
    _fake_duckdb(monkeypatch)
    from glances.exports.glances_duckdb.export_v5 import Export

    config = make_config({"duckdb": {"database": ":memory:", "hostname": HOSTILE_NAME}})
    Export(config).update(all_plugins(config))
    conn = _DuckConnection.instances[0]
    texts = [text for text, _ in conn.statements]
    assert all(HOSTILE_NAME not in text for text in texts)
    assert all("busy host" not in text and "eth0" not in text for text in texts), "values are never SQL text"
    assert 'CREATE TABLE "fakecollection" ("time" TIMETZ, "hostname_id" VARCHAR, "key_id" VARCHAR, ' in "".join(texts)
    assert '"' + HOSTILE_NAME.replace('"', '""') + '" DOUBLE' in "".join(texts)
    rows = {text.split('"')[1]: params for text, params in conn.statements if text.startswith("INSERT INTO")}
    assert rows["fakescalar"][0][1:] == [HOSTILE_NAME, 12.5, "busy host", None, 28800.0]
    # v4 layout: key_id, then every field of the item, `key` included.
    assert [row[2:6] for row in rows["fakecollection"]] == [
        ["name", "eth0", 10, "name"],
        ["name", HOSTILE_NAME, 20, "name"],
    ]
    assert all(text.endswith("VALUES (?, ?, ?, ?, ?, ?, ?);") for text in texts if '"fakecollection" VALUES' in text)


def test_duckdb_failing_write_is_one_warning_per_plugin(monkeypatch, caplog):
    _fake_duckdb(monkeypatch)
    from glances.exports.glances_duckdb.export_v5 import Export

    config = make_config({"duckdb": {"database": ":memory:"}})
    exporter = Export(config)
    _DuckConnection.fail = True
    exporter.update(plugins(config))
    assert caplog.text.count("Cannot export fakecollection stats to DuckDB (read-only database)") == 1
    assert caplog.text.count("Cannot export fakescalar stats to DuckDB") == 1


def test_duckdb_normalize_keeps_false_values(monkeypatch):
    """Port of v4 #3755 -- bool('False') is True."""
    _fake_duckdb(monkeypatch)
    from glances.exports.glances_duckdb.export_v5 import normalize

    assert normalize(["False"]) is False
    assert normalize(["True"]) is True


@pytest.mark.parametrize(
    ("name", "quoted"),
    [('a"b"c', '"a""b""c"'), ("", '""'), (42, '"42"')],
)
def test_duckdb_quote_identifier(name, quoted):
    from glances.exports.glances_duckdb.export_v5 import quote_identifier

    assert quote_identifier(name) == quoted


@pytest.mark.parametrize("table", ["x (a INT); DROP TABLE important; --", HOSTILE_NAME, "my-plugin"])
def test_duckdb_quotes_the_table_name(monkeypatch, table):
    _fake_duckdb(monkeypatch)
    from glances.exports.glances_duckdb.export_v5 import Export, quote_identifier

    Export(make_config({"duckdb": {"database": ":memory:"}}))._write(table, ['"a" INTEGER'], [[1]])
    quoted = '"' + table.replace('"', '""') + '"'
    assert quote_identifier(table) == quoted
    assert _DuckConnection.instances[0].statements[1:] == [
        (f'CREATE TABLE {quoted} ("a" INTEGER);', None),
        (f"INSERT INTO {quoted} VALUES (?);", [[1]]),
    ]


def test_duckdb_exit_closes(monkeypatch):
    _fake_duckdb(monkeypatch)
    from glances.exports.glances_duckdb.export_v5 import Export

    Export(make_config({"duckdb": {"database": ":memory:"}})).exit()
    assert _DuckConnection.instances[0].events[-1] == "close"


def test_duckdb_real_database_stores_hostile_strings_as_data(monkeypatch, tmp_path):
    duckdb = pytest.importorskip("duckdb")
    from glances.exports.glances_duckdb.export_v5 import Export

    path = str(tmp_path / "glances.duckdb")
    setup = duckdb.connect(path)
    setup.execute("CREATE TABLE cpu (total DOUBLE)")
    setup.execute("CREATE TABLE y (a INT)")
    setup.close()

    config = make_config({"duckdb": {"database": path, "hostname": HOSTILE_NAME}})
    exporter = Export(config)
    exporter.update(all_plugins(config))
    exporter.exit()

    check = duckdb.connect(path)
    tables = sorted(t[0] for t in check.sql("SHOW TABLES").fetchall())
    assert tables == ["cpu", "fakecollection", "fakehostilefield", "fakescalar", "y"], "none created or dropped"
    names = [row[0] for row in check.sql('SELECT "name" FROM "fakecollection" ORDER BY "rx"').fetchall()]
    assert names == ["eth0", HOSTILE_NAME]
    assert check.sql('SELECT DISTINCT "hostname_id" FROM "fakescalar"').fetchall() == [(HOSTILE_NAME,)]
    assert check.sql('SELECT "label", "total" FROM "fakescalar"').fetchall() == [("busy host", 12.5)]
    columns = [row[0] for row in check.sql("DESCRIBE \"fakehostilefield\"").fetchall()]
    assert HOSTILE_NAME in columns, "the hostile field name is a column, not SQL"
    check.close()


def test_duckdb_real_database_hostile_table_name_keeps_the_canary(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    from glances.exports.glances_duckdb.export_v5 import Export

    path = str(tmp_path / "glances.duckdb")
    setup = duckdb.connect(path)
    setup.execute("CREATE TABLE canary (a INT)")
    setup.close()

    exporter = Export(make_config({"duckdb": {"database": path}}))
    for table in ("x (a INT); DROP TABLE canary; --", "my-plugin"):
        exporter._write(table, ['"a" INTEGER'], [[1]])
    exporter.exit()

    check = duckdb.connect(path)
    tables = sorted(t[0] for t in check.sql("SHOW TABLES").fetchall())
    assert tables == ["canary", "my-plugin", "x (a INT); DROP TABLE canary; --"]
    assert check.sql('SELECT "a" FROM "my-plugin"').fetchall() == [(1,)]
    check.close()


@pytest.mark.parametrize("name", ["duckdb", "timescaledb"])
def test_update_leaves_the_plugin_view_and_the_store_untouched(monkeypatch, name):
    """Port of v4 #3767."""
    _fake_duckdb(monkeypatch)
    _fake_psycopg(monkeypatch)
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    section = {"duckdb": {"database": ":memory:"}, "timescaledb": TIMESCALE}[name]
    config = make_config({name: section, "fakecollection": {"rx_careful": "60"}})
    built = plugins(config)
    module.Export(config).update(built)
    connection = {"duckdb": _DuckConnection, "timescaledb": _PgConnection}[name].instances[0]
    assert sum(text.startswith("INSERT INTO") for text, _ in connection.statements) == 2
    assert_plugins_untouched(built)


# ============================================================= cassandra


class _InvalidRequest(Exception):
    pass


class _Session:
    def __init__(self):
        self.statements: list[tuple[str, object]] = []
        self.keyspace = None
        self.events: list[str] = []
        self.fail = False

    def set_keyspace(self, keyspace):
        if not any(t.startswith("CREATE KEYSPACE") for t, _ in self.statements):
            raise _InvalidRequest("no keyspace")
        self.keyspace = keyspace

    def execute(self, statement, params=None):
        text = statement if isinstance(statement, str) else statement.text
        if params is not None and self.fail:
            raise RuntimeError("timeout")
        self.statements.append((text, params))

    def prepare(self, text):
        return type("Prepared", (), {"text": text})()

    def shutdown(self):
        self.events.append("shutdown")


class _Cluster:
    instances: list[_Cluster] = []

    def __init__(self, hosts, **kwargs):
        self.hosts, self.kwargs = hosts, kwargs
        self.session = _Session()
        self.events: list[str] = []
        _Cluster.instances.append(self)

    def connect(self):
        return self.session

    def shutdown(self):
        self.events.append("shutdown")


def _fake_cassandra(monkeypatch):
    _Cluster.instances = []
    fake_module(monkeypatch, "cassandra", InvalidRequest=_InvalidRequest)
    fake_module(monkeypatch, "cassandra.auth", PlainTextAuthProvider=lambda **kw: ("auth", kw))
    fake_module(monkeypatch, "cassandra.cluster", Cluster=_Cluster)
    fake_module(monkeypatch, "cassandra.util", uuid_from_time=lambda when: "uuid")


CASSANDRA = {"host": "scylla", "port": "9042", "keyspace": "glances", "table": "stats", "replication_factor": "3"}


def test_cassandra_connects_and_creates_keyspace_and_table(monkeypatch):
    _fake_cassandra(monkeypatch)
    from glances.exports.glances_cassandra.export_v5 import Export

    Export(make_config({"cassandra": {**CASSANDRA, "username": "u", "password": "p"}}))
    cluster = _Cluster.instances[0]
    assert cluster.hosts == ["scylla"]
    assert cluster.kwargs == {
        "port": 9042,
        "protocol_version": 3,
        "auth_provider": ("auth", {"username": "u", "password": "p"}),
    }
    texts = [t for t, _ in cluster.session.statements]
    assert texts[0] == (
        "CREATE KEYSPACE glances WITH replication = { 'class': 'SimpleStrategy', 'replication_factor': '3' }"
    )
    assert texts[1].startswith("CREATE TABLE stats (plugin text, time timeuuid, stat map<text,float>")
    assert cluster.session.keyspace == "glances"


def test_cassandra_table_defaults_to_host(monkeypatch):
    _fake_cassandra(monkeypatch)
    from glances.exports.glances_cassandra.export_v5 import Export

    config = {k: v for k, v in CASSANDRA.items() if k != "table"}
    assert Export(make_config({"cassandra": config})).table == "scylla"


def test_cassandra_binds_every_value(monkeypatch):
    _fake_cassandra(monkeypatch)
    from glances.exports.glances_cassandra.export_v5 import Export

    config = make_config({"cassandra": CASSANDRA})
    Export(config).update(plugins(config))
    session = _Cluster.instances[0].session
    assert all(HOSTILE_NAME not in text for text, _ in session.statements)
    inserts = {params[0]: params for text, params in session.statements if text.startswith("INSERT INTO stats")}
    assert all(t == "INSERT INTO stats (plugin, time, stat) VALUES (?, ?, ?)" for t, p in session.statements if p)
    assert inserts["fakescalar"][2] == {"total": 12.5, "history_size": 28800.0}, "numbers only, as floats"
    assert inserts["fakecollection"][2][f"{HOSTILE_NAME}.rx"] == 20.0
    assert inserts["fakecollection"][1] == "uuid"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("table", "x; DROP TABLE y"),
        ("keyspace", "glances'"),
        ("keyspace", "1glances"),
        # `$` alone also matches before a trailing newline.
        ("keyspace", "glances\n"),
        ("table", "host\n"),
        ("replication_factor", "1}; DROP"),
        ("replication_factor", "0"),
        ("protocol_version", "3 OR 1"),
        ("port", "9042; x"),
    ],
)
def test_cassandra_hostile_config_is_refused_before_any_statement(monkeypatch, caplog, key, value):
    _fake_cassandra(monkeypatch)
    from glances.exports.glances_cassandra.export_v5 import Export

    with pytest.raises(SystemExit):
        Export(make_config({"cassandra": {**CASSANDRA, key: value, "password": "s3cret"}}))
    assert _Cluster.instances == [], "refused before the driver is used"
    assert f"Invalid cassandra config: {key}=" in caplog.text
    assert "s3cret" not in caplog.text


def test_cassandra_failing_write_is_a_warning(monkeypatch, caplog):
    _fake_cassandra(monkeypatch)
    from glances.exports.glances_cassandra.export_v5 import Export

    config = make_config({"cassandra": CASSANDRA})
    exporter = Export(config)
    exporter.session.fail = True
    exporter.update(plugins(config))
    assert caplog.text.count("Cannot export fakescalar stats to Cassandra (timeout)") == 1
    assert caplog.text.count("Cannot export fakecollection stats to Cassandra") == 1


def test_cassandra_exit_shuts_down(monkeypatch):
    _fake_cassandra(monkeypatch)
    from glances.exports.glances_cassandra.export_v5 import Export

    Export(make_config({"cassandra": CASSANDRA})).exit()
    cluster = _Cluster.instances[0]
    assert cluster.session.events == ["shutdown"] and cluster.events == ["shutdown"]


# ================================================================ common


SECTIONS = {
    "timescaledb": {"host": "h", "port": "1", "db": "d"},
    "duckdb": {"database": ":memory:"},
    "cassandra": {"host": "h", "port": "1", "keyspace": "k", "table": "t"},
}


@pytest.mark.parametrize(
    ("name", "library", "logged"),
    [
        ("timescaledb", "psycopg", "psycopg"),
        ("duckdb", "duckdb", "duckdb"),
        ("cassandra", "cassandra", "cassandra-driver"),
    ],
)
def test_a_missing_section_or_library_is_fatal_and_says_so(monkeypatch, caplog, name, library, logged):
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    with pytest.raises(SystemExit):
        module.Export(make_config({}))
    assert f"Missing {name} config" in caplog.text
    missing_module(monkeypatch, library)
    with pytest.raises(SystemExit):
        module.Export(make_config({name: SECTIONS[name]}))
    assert f"Export {name} needs the {logged} library" in caplog.text


@pytest.mark.parametrize(
    ("name", "mandatory"), [("timescaledb", "db"), ("duckdb", "database"), ("cassandra", "keyspace")]
)
def test_a_missing_mandatory_key_is_fatal(caplog, name, mandatory):
    module = importlib.import_module(f"glances.exports.glances_{name}.export_v5")
    section = {k: v for k, v in SECTIONS[name].items() if k != mandatory}
    with pytest.raises(SystemExit):
        module.Export(make_config({name: section}))
    assert f"Missing {name} config" in caplog.text


def test_the_modules_import_without_their_library(monkeypatch):
    for library in ("psycopg", "duckdb", "cassandra"):
        missing_module(monkeypatch, library)
    for name in ("timescaledb", "duckdb", "cassandra"):
        monkeypatch.delitem(sys.modules, f"glances.exports.glances_{name}.export_v5", raising=False)
        importlib.import_module(f"glances.exports.glances_{name}.export_v5")


def test_the_exporters_are_discovered_by_export(monkeypatch):
    from glances.main_v5 import apply_export_flags, build_parser, discover_exporters

    _fake_psycopg(monkeypatch)
    _fake_duckdb(monkeypatch)
    _fake_cassandra(monkeypatch)
    args = build_parser().parse_args(["--export", "timescaledb,duckdb,cassandra"])
    apply_export_flags(args)
    assert sorted(e.export_name for e in discover_exporters(make_config(SECTIONS), args)) == [
        "cassandra",
        "duckdb",
        "timescaledb",
    ]

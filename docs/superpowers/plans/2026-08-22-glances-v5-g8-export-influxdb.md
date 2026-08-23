# G8-4 — InfluxDB exporters (1.x, 2.x, 3.x): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the three InfluxDB exporters — `influxdb` (1.x), `influxdb2`, `influxdb3` — onto the v5 export base.

**Architecture:** All three share `normalize_for_influxdb()` from the base class and differ only in their client library, their config keys and their write call. Each implements `export()` and inherits the base `update()`, so all three carry the merged limits. Each connects at init and dies loudly if it cannot (design §8).

**Tech Stack:** `influxdb` (1.x), `influxdb_client` (2.x), `influxdb_client_3` (3.x) — three distinct optional packages. Tests mock all three.

**Spec:** `docs/superpowers/specs/2026-08-22-glances-v5-g8-exporters-design.md` (§9, §10, §11)

**Depends on:** `docs/superpowers/plans/2026-08-22-glances-v5-g8-export-base.md` (all 8 tasks complete).

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.**
- **v4 code is read-only.** The three `glances/exports/glances_influxdb*/__init__.py` files must be byte-identical at the end of this plan.
- **Every client library is imported inside a method, never at module level.** Discovery imports these modules at every start-up; a minimal install has none of the three (spec §3).
- **`normalize_for_influxdb()` lives in the base and is never re-implemented.** All three exporters call `self.normalize_for_influxdb(...)`.
- Each exporter must set `self.tags` and `self.hostname` before the first `export()` — `normalize_for_influxdb()` reads both.
- A write failure logs at **WARNING**, not ERROR, and does not raise (issue #1561: an InfluxDB hiccup must not spam an operator's logs at error level).
- Fatal on init failure: `sys.exit(2)`, iso-v4 (design §8).
- Run the full suite with `uv run pytest -q`.
- SPDX header on every new file (copy the 8-line header from `glances/exports/export_base_v5.py`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/exports/glances_influxdb/export_v5.py` | `Export` for InfluxDB 1.x — `influxdb.InfluxDBClient`, `write_points()`, database existence check. |
| `glances/exports/glances_influxdb2/export_v5.py` | `Export` for InfluxDB 2.x — `influxdb_client`, batched `write_api`, buffer sized from `[export] refresh`. |
| `glances/exports/glances_influxdb3/export_v5.py` | `Export` for InfluxDB 3.x — `influxdb_client_3.InfluxDBClient3`, `write(record=…)`. |
| `tests/test_export_influxdb_v5.py` | 1.x: config, fatal paths, measurement shape. |
| `tests/test_export_influxdb2_v5.py` | 2.x: config, flush interval from `[export] refresh`, measurement shape. |
| `tests/test_export_influxdb3_v5.py` | 3.x: config, fatal paths, measurement shape. |

---

### Task 1: InfluxDB 1.x exporter

**Files:**
- Create: `glances/exports/glances_influxdb/export_v5.py`
- Test: `tests/test_export_influxdb_v5.py`

**Interfaces:**
- Consumes: `GlancesExportBase.__init__(config, args)`, `.load_conf(section, mandatories, options)`, `.normalize_for_influxdb(name, columns, points)`, `.update(plugins)` (inherited unchanged).
- Produces: `Export(GlancesExportBase)` with `export_name = "influxdb"`, `init()`, `export(name, columns, points)`.

Reference to port from: `glances/exports/glances_influxdb/__init__.py` (106 lines).

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_influxdb_v5.py` with the SPDX header, then:

```python
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


def test_influxdb_exits_when_the_section_is_missing(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    with pytest.raises(SystemExit) as excinfo:
        Export(make_config({}), args=None)
    assert excinfo.value.code == 2


def test_influxdb_exits_when_the_database_does_not_exist(influxdb_module):
    from glances.exports.glances_influxdb.export_v5 import Export

    sections = {"influxdb": dict(SECTION["influxdb"], db="absent")}
    with pytest.raises(SystemExit) as excinfo:
        Export(make_config(sections), args=None)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_influxdb_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.glances_influxdb.export_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/exports/glances_influxdb/export_v5.py` with the SPDX header, then:

```python
"""Glances v5 — InfluxDB 1.x export module.

Ported from the v4 module in this directory. The measurement shape is
produced by `GlancesExportBase.normalize_for_influxdb()`, shared with the
2.x and 3.x exporters — the three differ only in their client library and
their write call.

`influxdb` is imported inside `init()`, never at module level: discovery
imports this file on every start-up and the library is optional.
"""

from __future__ import annotations

import sys
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to an InfluxDB 1.x server."""

    export_name = "influxdb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Mandatory keys, in addition to host and port.
        self.user: str | None = None
        self.password: str | None = None
        self.db: str | None = None

        # Optional keys.
        self.protocol: str = "http"
        self.prefix: str | None = None
        self.tags: str | None = None
        self.hostname: str | None = None

        if not self.load_conf(
            "influxdb",
            mandatories=("host", "port", "user", "password", "db"),
            options=("protocol", "prefix", "tags"),
        ):
            logger.critical("Missing influxdb config")
            sys.exit(2)

        # The hostname is always added as a tag.
        self.hostname = node().split(".")[0]

        self.client = self.init()

    def init(self) -> Any:
        """Connect and verify the target database exists."""
        from influxdb import InfluxDBClient
        from influxdb.client import InfluxDBClientError

        # Correct issue #1530
        ssl = bool(self.protocol is not None and self.protocol.lower() == "https")

        try:
            db = InfluxDBClient(
                host=self.host,
                port=self.port,
                ssl=ssl,
                verify_ssl=False,
                username=self.user,
                password=self.password,
                database=self.db,
            )
            get_all_db = [i["name"] for i in db.get_list_database()]
        except InfluxDBClientError as e:
            logger.critical("Cannot connect to InfluxDB database '%s' (%s)", self.db, e)
            sys.exit(2)

        if self.db not in get_all_db:
            logger.critical("InfluxDB database '%s' did not exist. Please create it", self.db)
            sys.exit(2)

        logger.info("Stats will be exported to InfluxDB server: %s", db._baseurl)
        return db

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's measurements."""
        if self.prefix is not None:
            name = self.prefix + "." + name
        if not points:
            logger.debug("Cannot export empty %s stats to InfluxDB", name)
            return
        try:
            self.client.write_points(
                self.normalize_for_influxdb(name, columns, points),
                time_precision="s",
            )
        except Exception as e:
            # Warning, not error: a momentary outage must not read as a bug (#1561).
            logger.warning("Cannot export %s stats to InfluxDB (%s)", name, e)
        else:
            logger.debug("Export %s stats to InfluxDB", name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_influxdb_v5.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Stage**

```bash
git add glances/exports/glances_influxdb/export_v5.py tests/test_export_influxdb_v5.py
```

---

### Task 2: InfluxDB 2.x exporter

**Files:**
- Create: `glances/exports/glances_influxdb2/export_v5.py`
- Test: `tests/test_export_influxdb2_v5.py`

**Interfaces:**
- Consumes: everything Task 1 consumes, plus `glances.exports.export_base_v5.resolve_export_refresh(config)` (defined in the G8-1 plan, Task 6).
- Produces: `Export(GlancesExportBase)` with `export_name = "influxdb2"`, `init()`, `export(name, columns, points)`.

Reference to port from: `glances/exports/glances_influxdb2/__init__.py` (120 lines).

**The one behavioural change in G8** lives here. v4 sizes the client's
`flush_interval` from `args.time` — the CLI refresh rate — falling back to it
whenever `[influxdb2] interval` is 0 or unset. v5 has no `args.time`; the export
cadence is `[export] refresh`, so that is what the buffer is sized from. Visible
only to a deployment that leaves `[influxdb2] interval=0`, and the resulting
value is the same in the common case where both default to the global refresh.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_influxdb2_v5.py` with the SPDX header, then:

```python
"""Glances v5 — unit tests for the InfluxDB 2.x export module."""

from __future__ import annotations

import sys
import types

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class FakeWriteApi:
    def __init__(self, write_options):
        self.write_options = write_options
        self.written: list[tuple] = []

    def write(self, bucket, org, record, time_precision=None):
        self.written.append((bucket, org, record, time_precision))


class FakeHealth:
    version = "2.7.0"
    message = "ready for queries and writes"


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


def test_influxdb2_flush_interval_follows_the_export_refresh(influxdb_client_module):
    """v5 change: v4 sized this from args.time, which v5 does not have."""
    from glances.exports.glances_influxdb2.export_v5 import Export

    sections = dict(SECTION, **{"global": {"refresh": "2"}, "export": {"refresh": "10"}})
    exporter = Export(make_config(sections), args=None)

    assert exporter.client.write_options.kwargs["flush_interval"] == 10000


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_influxdb2_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.glances_influxdb2.export_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/exports/glances_influxdb2/export_v5.py` with the SPDX header, then:

```python
"""Glances v5 — InfluxDB 2.x export module (InfluxDB 1.8+ to <3.0).

Ported from the v4 module in this directory. One behavioural change: the
client's write buffer is flushed on the EXPORT cadence.

v4 read `args.time` — the CLI refresh rate — whenever `[influxdb2] interval`
was 0 or unset. v5 has no such argument; `[export] refresh` is what drives
the export loop, so the buffer is sized from it via the same resolver the
scheduler uses. In the common case where both fall back to the global
refresh the resulting value is identical to v4's.
"""

from __future__ import annotations

import sys
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase, resolve_export_refresh
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to an InfluxDB 2.x server."""

    export_name = "influxdb2"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Mandatory keys, in addition to host and port.
        self.org: str | None = None
        self.bucket: str | None = None
        self.token: str | None = None

        # Optional keys.
        self.protocol: str = "http"
        self.prefix: str | None = None
        self.tags: str | None = None
        self.hostname: str | None = None
        self.interval: Any = None

        if not self.load_conf(
            "influxdb2",
            mandatories=("host", "port", "user", "password", "org", "bucket", "token"),
            options=("protocol", "prefix", "tags", "interval"),
        ):
            logger.critical("Missing influxdb2 config")
            sys.exit(2)

        # Flush interval, in seconds. 0 / unset / unparseable → export cadence.
        export_refresh = int(resolve_export_refresh(self.config))
        if self.interval is None:
            self.interval = 0
        try:
            self.interval = int(self.interval)
        except ValueError:
            logger.warning("InfluxDB export interval is not an integer, use default value")
            self.interval = 0
        if self.interval <= 0:
            self.interval = export_refresh
        logger.debug("InfluxDB export interval is set to %s seconds", self.interval)

        # The hostname is always added as a tag.
        self.hostname = node().split(".")[0]

        self.client = self.init()

    def init(self) -> Any:
        """Connect and return a batched write API."""
        from influxdb_client import InfluxDBClient, WriteOptions

        url = f"{self.protocol}://{self.host}:{self.port}"
        try:
            # https://influxdb-client.readthedocs.io/en/stable/api.html#influxdbclient
            client = InfluxDBClient(
                url=url,
                enable_gzip=False,
                verify_ssl=False,
                org=self.org,
                token=self.token,
            )
        except Exception as e:
            logger.critical("Cannot connect to InfluxDB server '%s' (%s)", url, e)
            sys.exit(2)

        health = client.health()
        logger.info("Connected to InfluxDB server version %s (%s)", health.version, health.message)

        return client.write_api(
            write_options=WriteOptions(
                batch_size=500,
                flush_interval=self.interval * 1000,
                jitter_interval=2000,
                retry_interval=5000,
                max_retries=5,
                max_retry_delay=30000,
                exponential_base=2,
            )
        )

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's measurements."""
        if self.prefix is not None:
            name = self.prefix + "." + name
        if not points:
            logger.debug("Cannot export empty %s stats to InfluxDB", name)
            return
        try:
            self.client.write(
                self.bucket,
                self.org,
                self.normalize_for_influxdb(name, columns, points),
                time_precision="s",
            )
        except Exception as e:
            # Warning, not error (#1561).
            logger.warning("Cannot export %s stats to InfluxDB (%s)", name, e)
        else:
            logger.debug("Export %s stats to InfluxDB", name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_influxdb2_v5.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Stage**

```bash
git add glances/exports/glances_influxdb2/export_v5.py tests/test_export_influxdb2_v5.py
```

---

### Task 3: InfluxDB 3.x exporter

**Files:**
- Create: `glances/exports/glances_influxdb3/export_v5.py`
- Test: `tests/test_export_influxdb3_v5.py`

**Interfaces:**
- Consumes: same as Task 1.
- Produces: `Export(GlancesExportBase)` with `export_name = "influxdb3"`, `init()`, `export(name, columns, points)`.

Reference to port from: `glances/exports/glances_influxdb3/__init__.py` (98 lines).

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_influxdb3_v5.py` with the SPDX header, then:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_influxdb3_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.exports.glances_influxdb3.export_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/exports/glances_influxdb3/export_v5.py` with the SPDX header, then:

```python
"""Glances v5 — InfluxDB 3.x export module.

Ported from the v4 module in this directory. Same measurement shape as the
1.x and 2.x exporters — `GlancesExportBase.normalize_for_influxdb()` is the
single implementation.
"""

from __future__ import annotations

import sys
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to an InfluxDB 3.x server."""

    export_name = "influxdb3"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Mandatory keys, in addition to host and port.
        self.org: str | None = None
        self.database: str | None = None
        self.token: str | None = None

        # Optional keys.
        self.prefix: str | None = None
        self.tags: str | None = None
        self.hostname: str | None = None

        if not self.load_conf(
            "influxdb3",
            mandatories=("host", "port", "org", "database", "token"),
            options=("prefix", "tags"),
        ):
            logger.critical("Missing influxdb3 config")
            sys.exit(2)

        # The hostname is always added as a tag.
        self.hostname = node().split(".")[0]

        self.client = self.init()

    def init(self) -> Any:
        """Connect and verify the target database."""
        from influxdb_client_3 import InfluxDBClient3

        try:
            db = InfluxDBClient3(
                host=self.host,
                org=self.org,
                database=self.database,
                token=self.token,
            )
        except Exception as e:
            logger.critical("Cannot connect to InfluxDB database '%s' (%s)", self.database, e)
            sys.exit(2)

        if self.database != db._database:
            logger.critical("InfluxDB database '%s' did not exist. Please create it", self.database)
            sys.exit(2)

        logger.info(
            "Stats will be exported to InfluxDB server %s:%s in %s database",
            self.host,
            self.port,
            self.database,
        )
        return db

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's measurements."""
        if self.prefix is not None:
            name = self.prefix + "." + name
        if not points:
            logger.debug("Cannot export empty %s stats to InfluxDB", name)
            return
        try:
            self.client.write(
                record=self.normalize_for_influxdb(name, columns, points),
                time_precision="s",
            )
        except Exception as e:
            # Warning, not error (#1561).
            logger.warning("Cannot export %s stats to InfluxDB (%s)", name, e)
        else:
            logger.debug("Export %s stats to InfluxDB", name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_influxdb3_v5.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Stage**

```bash
git add glances/exports/glances_influxdb3/export_v5.py tests/test_export_influxdb3_v5.py
```

---

### Task 4: Cross-check the three exporters and run the hooks

**Files:** all files touched by Tasks 1-3.

- [ ] **Step 1: Confirm all three share one `normalize_for_influxdb`**

```bash
grep -c "def normalize_for_influxdb" glances/exports/glances_influxdb*/export_v5.py
```

Expected: `0` for each of the three files — the only definition lives in `glances/exports/export_base_v5.py`.

- [ ] **Step 2: Confirm no client library is imported at module level**

```bash
grep -n "^from influxdb\|^import influxdb" glances/exports/glances_influxdb*/export_v5.py
```

Expected: no output. Every import must sit inside `init()`.

- [ ] **Step 3: Prove discovery survives a missing library**

```bash
uv run python -c "
import argparse, importlib
from glances.config_v5 import GlancesConfigV5
from glances.main_v5 import discover_exporters
args = argparse.Namespace()
print(discover_exporters(GlancesConfigV5(), args))
"
```

Expected: `[]` and no traceback — no exporter was requested, so no client library is touched.

- [ ] **Step 4: Confirm the v4 modules are untouched**

```bash
git diff --stat HEAD -- glances/exports/glances_influxdb/__init__.py \
                        glances/exports/glances_influxdb2/__init__.py \
                        glances/exports/glances_influxdb3/__init__.py
```

Expected: empty output.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: no new failures.

- [ ] **Step 6: Run the hooks**

```bash
git add -A
make pre-commit
```

Expected: all hooks pass. Restage and re-run if `ruff` reformats.

- [ ] **Step 7: Stage the final state**

```bash
git add -A
git status --short
```

Do NOT commit. Report the staged file list, and flag for the maintainer that a
live InfluxDB smoke test (`make test-export-influxdb-v3`, adapted to
`python -m glances.main_v5`) is owed — the unit tests mock every client, so no
automated check proves a real server accepts these writes.

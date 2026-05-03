# Skill: Glances v5 — Authoring an export module (`GlancesExportBase`)

Use the v5 exporter base class (`GlancesExportBase`) for any new or
migrated export module in `develop-v5`. The v4 export modules under
`glances/exports/` are kept untouched during the transition and migrated
one by one.

> **Phase status.** `GlancesExportBase` itself lands in **Phase 1**
> alongside the first concrete v5 plugin. This skill captures the
> non-negotiable contract decided in Phase 0 (architecture §7) so that
> contributors and Claude agree on the rules before any export module is
> written or migrated.

## The two non-negotiable rules

### 1. `get_export()` is the only permitted access path

Exporters **never** read from the `StatsStore` directly. Every exporter
fetches plugin data via `plugin.get_export()` — which is implemented once
in `GlancesPluginBase` and applies field filtering consistently
(architecture §7.2, issue #3211).

```python
# CORRECT
data = plugin.get_export()

# FORBIDDEN — bypasses field filtering
data = self.store.get(plugin.plugin_name)
data = self.store.as_dict()[plugin.plugin_name]
```

`get_export()` returns:
- a `dict` for scalar plugins (cpu, mem, load, …)
- a `list[dict]` for collection plugins (network, fs, containers, …)

It strips internal keys (`_levels`, anything starting with `_`) and any
field whose `fields_description` carries `exportable: False`.

### 2. All v4 export modules must be migrated

No exporter is omitted (architecture §7.3). The v5 release ships with the
same exporter coverage as v4, period. No new exporter is added during the
v5 migration phase — the migration is the only goal.

## Async contract

`GlancesExportBase.update()` is **async**. Every exporter integrates into
the main asyncio loop. Blocking I/O (network sockets, DB drivers without
async support) must be wrapped with `asyncio.to_thread()`.

```python
# Pseudo-code — concrete base class lands in Phase 1.
class GlancesExportBase(ABC):
    export_name: ClassVar[str] = ""

    def __init__(self, config: GlancesConfigV5, store: StatsStoreV5) -> None:
        ...

    @abstractmethod
    async def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Push every plugin's get_export() output to the backend."""
```

A failure inside `update()` is logged at WARNING and swallowed — the
asyncio gather loop must never crash because of a misbehaving exporter
(same resilience contract as plugins, §1.2).

## `export_refresh_time`

Exporters can flush at a different cadence than plugins:

```ini
[exports]
refresh_time = 10
```

`export_refresh_time` must be **≥** the slowest plugin's `refresh_time`.
Otherwise the exporter would push duplicate data. The validation is a
WARNING at startup (Phase 1 implementation detail).

The default for headless server deployments is to bump
`[global] refresh_time` to lower the baseline CPU load (architecture §7.1)
— v5 server mode runs the asyncio scheduler continuously, unlike the
passive v4 server.

## Migration pattern (v4 → v5)

For every v4 export module under `glances/exports/<name>/`:

1. Subclass `GlancesExportBase` (Phase 1 base class), not the v4
   `GlancesExport` model.
2. Convert `update()` to `async def update(...)`.
3. Replace any direct `stats.get_<plugin>` / `glances_stats.get_all` call
   with `plugin.get_export()`.
4. Wrap blocking client calls in `asyncio.to_thread()` until an async
   driver exists.
5. Read configuration via `GlancesConfigV5.get(section, option, default)`
   — preserve the exact same `glances.conf` keys as v4 to avoid breaking
   user setups.
6. Add unit tests (`pytest` + `pytest-asyncio`) covering the round-trip
   `plugin.get_export()` → exporter formatting → mocked client.

## Security — CVE-2026-32611

The DuckDB exporter (and any future SQL-based exporter) **must** use
parameterized DDL. Plugin and metric names are user-controlled strings;
they must never be string-interpolated into SQL.

```python
# FORBIDDEN
con.execute(f"CREATE TABLE {plugin_name} (...)")  # SQL injection vector

# CORRECT — sanitize and parameterize
safe_name = sanitize_identifier(plugin_name)
con.execute("CREATE TABLE ? (...)", [safe_name])
```

`sanitize_identifier()` rejects anything that is not `[A-Za-z][A-Za-z0-9_]*`.

## What's deferred (out of scope right now)

- **`GlancesExportBase` concrete base class** — Phase 1 (alongside the first plugin)
- **First migrated exporter** — Phase 2 (priority order: InfluxDB, Prometheus, CSV, JSON)
- **Remaining exporters** — Phase 3 (MongoDB, MQTT, DuckDB, Apprise-based, etc.)
- **`export_refresh_time` enforcement / startup validation** — Phase 1
- **New exporters** — explicitly **not** in scope until v5.0.0 ships

## Testing an exporter

Test stack: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) +
`unittest.mock` (architecture decision §9). Style: pytest-native top-level
functions with fixtures and `assert` statements.

Pattern: instantiate the exporter against a real `GlancesConfigV5` and a
real `StatsStoreV5` populated with one fake plugin (use
`FakeScalarPlugin` / `FakeCollectionPlugin` from
`tests/test_plugin_base_v5.py` as inspiration). Mock the backend client
(SQL connection, HTTP client, …) and assert the exporter calls
`plugin.get_export()` — never the store directly.

## Module path (target — Phase 1+)

```
glances/exports_v5/<name>/__init__.py    # concrete exporter
glances/exports_v5/export_base.py        # GlancesExportBase (Phase 1)
tests/test_<name>_export_v5.py           # exporter unit tests
```

The v4 modules under `glances/exports/` are **not modified**, **not
imported**, **not subclassed** by v5. The two systems coexist through the
migration. At the end of the transition the `_v5` suffix is dropped.

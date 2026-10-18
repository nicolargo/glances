# Skill: Glances v5 — Authoring an export module (`GlancesExportBase`)

Use the exporter base class (`glances.exports.export_base.GlancesExportBase`)
for any export module. Every v4 exporter has been ported: each lives in
`glances/exports/glances_<name>/export.py` as a class named `Export`. This
skill captures the non-negotiable contract (architecture §7).

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

### 2. Same coverage and wire format as v4

No exporter is omitted (architecture §7.3): the v5 release ships with the
same exporter coverage as v4, and `build_export()` /
`normalize_for_influxdb()` keep v4's field names, so users' dashboards keep
working. No new exporter is added before v5.0.0 ships.

## Threading contract

`GlancesExportBase.update()` and `export()` are **synchronous** on purpose
(design §4.2 supersedes the async `update()` of architecture §7.3): every
backend client is blocking, so the coroutine boundary lives one level up.
`AsyncScheduler._export_loop()` calls
`await asyncio.to_thread(exporter.update, plugins)` once per exporter per
tick.

```python
class GlancesExportBase(ABC):
    export_name: ClassVar[str] = ""  # "csv", "influxdb2" — matches glances_<name>/

    def __init__(self, config: GlancesConfig, args: argparse.Namespace | None = None) -> None: ...

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """get_export() of every exportable plugin → build_export() → export()."""

    @abstractmethod
    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's flattened stats to the backend."""

    def exit(self) -> None:
        """Release backend resources — a subclass calls super().exit() FIRST."""
```

A subclass implements `export()` (and `exit()` when it holds resources).
A failure for one plugin inside `update()` is logged at WARNING and
swallowed — the other plugins still get their tick (same resilience
contract as plugins, §1.2).

## Export refresh

Exporters can flush at a different cadence than plugins:

```ini
[export]
refresh = 10
```

`resolve_export_refresh()` floors the value at the global refresh — a
faster export would only push duplicate points — and defaults to the
global cadence when the key is absent.

The default for headless server deployments is to bump
`[global] refresh_time` to lower the baseline CPU load (architecture §7.1)
— v5 server mode runs the asyncio scheduler continuously, unlike the
passive v4 server.

## Exporter pattern

Every exporter in `glances/exports/glances_<name>/export.py` follows the
same shape (see `glances_statsd/export.py` for a short one):

1. `class Export(GlancesExportBase)` with `export_name = "<name>"`.
2. In `__init__`, read the `[<name>]` section with
   `self.load_conf("<name>", mandatories=(...), options=(...))` — keep the
   `glances.conf` keys v4 used, to avoid breaking user setups. A missing
   section or mandatory key is fatal (`sys.exit(2)`).
3. Import the client library lazily (when the exporter starts), so the
   module stays importable without it.
4. Implement `export(name, columns, points)`; never read the store —
   `update()` already went through `plugin.get_export()`.
5. Add unit tests (`pytest`) covering the round-trip `plugin.get_export()`
   → exporter formatting → fake client.

## Security — CVE-2026-32611

The DuckDB exporter (and any SQL-based exporter) **must** never
string-interpolate monitored data into SQL. Plugin and field names are
identifiers, interface / process / container names are values; both are
attacker-influenced.

```python
# FORBIDDEN
con.execute(f"CREATE TABLE {plugin_name} (...)")  # SQL injection vector

# CORRECT — quote identifiers, bind values
quoted = quote_identifier(table)  # "…", embedded double quotes doubled
con.execute(f"CREATE TABLE {quoted} ({', '.join(columns)});")
con.executemany(f"INSERT INTO {quoted} VALUES ({placeholders});", rows)  # ? parameters
```

See `glances/exports/glances_duckdb/export.py`.

## What's deferred (out of scope right now)

- **New exporters** — explicitly **not** in scope until v5.0.0 ships

## Testing an exporter

Test stack: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) +
`unittest.mock` (architecture decision §9). Style: pytest-native top-level
functions with fixtures and `assert` statements.

Pattern: build a config and real plugins with the helpers of
`tests/export_fakes.py` (`make_config`, `plugins`, `FakeScalarPlugin` /
`FakeCollectionPlugin`), install a stand-in client library with
`fake_module(monkeypatch, ...)`, call `Export.update()`, and assert on
what reached the fake client. No live backend is involved. The
`tests/test_export_*.sh` scripts (`make test-exports`) run real backends
under Docker.

## Module path

```
glances/exports/export_base.py               # GlancesExportBase
glances/exports/glances_<name>/__init__.py   # package marker
glances/exports/glances_<name>/export.py     # concrete exporter (class Export)
glances/scheduler.py                         # _export_loop()
tests/export_fakes.py                        # shared fakes
tests/test_export_<name>.py                  # exporter unit tests (or tests/test_export_wave_*.py)
```

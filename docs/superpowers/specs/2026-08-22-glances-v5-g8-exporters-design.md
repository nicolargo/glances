# Glances v5 — G8 design: export modules

**Status:** Approved — ready for `writing-plans`
**Date:** 2026-08-22
**Branch:** `develop-v5`
**Predecessor:** G7 — alert block (`87b01aee`), Phase 2 plugin ports complete (34/34)
**Successor:** G9 — WebUI served by FastAPI, then Phase 3

---

## 1. Goals

Close the first of the two remaining Phase 2 slots (architecture §10, "Phase 2 —
All local plugins + core exporters"):

1. Introduce the v5 export contract — `GlancesExportBase` — and the loop that
   drives it.
2. Give `GlancesPluginBase.get_export()` its first consumer. The method has
   existed since Phase 1 and has never been called: dead code by the project's
   own rule.
3. Migrate six exporters: `csv`, `json`, `prometheus`, `influxdb` (1.x),
   `influxdb2`, `influxdb3`.
4. Preserve the v4 wire format byte for byte, with two deliberate divergences:
   a security one (§5.4) and a data-completeness one (§5.2).

## 2. Out of scope

- The other 18 v4 exporters (`mongodb`, `mqtt`, `kafka`, `statsd`, `graphite`,
  `elasticsearch`, `duckdb`, `timescaledb`, `clickhouse`, `nats`, `cassandra`,
  `couchdb`, `opentsdb`, `rabbitmq`, `restful`, `riemann`, `zeromq`, `graph`)
  — Phase 3, per architecture §10. §7.3 ("no exporter omitted") remains the
  end state; it is not this group's scope.
- `--export-process-filter` and the `--stdout*` family.
- WebUI served by FastAPI — G9.
- Any change to the v4 export code. `glances/exports/export.py` and every
  `glances/exports/glances_*/__init__.py` stay untouched until the Phase 4
  cleanup, like every other v4 file.

## 3. Constraints

- **No regression on the wire format.** Field names reaching InfluxDB,
  Prometheus, CSV and JSON must match v4 exactly, apart from §5. Users' Grafana
  panels and CSV pipelines are keyed on those names.
- **No v4 import leaks.** No v5 module imports `glances.exports.export` or any
  v4 exporter.
- **Optional dependencies stay optional.** `influxdb`, `influxdb_client` and
  `influxdb_client_3` are three distinct packages, none of them a hard
  dependency. A minimal install must still discover exporters without raising.
- **Perf.** One `asyncio.to_thread` handoff per exporter per tick — not per
  plugin. The handoff costs ~307 µs (see the v5 perf backlog); 34 plugins × N
  exporters per tick would be indefensible.

---

## 4. Components

```
glances/exports/export_base_v5.py                  GlancesExportBase
glances/exports/glances_csv/export_v5.py           Export(GlancesExportBase)
glances/exports/glances_json/export_v5.py
glances/exports/glances_prometheus/export_v5.py
glances/exports/glances_influxdb/export_v5.py      lib: influxdb
glances/exports/glances_influxdb2/export_v5.py     lib: influxdb_client
glances/exports/glances_influxdb3/export_v5.py     lib: influxdb_client_3
```

The exporter modules mirror the plugin layout — `glances/plugins/<name>/model_v5.py`
becomes `glances/exports/glances_<name>/export_v5.py` — so a contributor who has
written a v5 plugin recognises the shape of a v5 exporter.

The base does NOT mirror `glances/plugins/plugin/base_v5.py`. An earlier draft of
this spec put it in a `glances/exports/export/` sub-package; that is not
implementable. Python cannot resolve both `glances/exports/export.py` (the v4
base) and `glances/exports/export/` (a package) under one parent — the package
wins, `from glances.exports.export import GlancesExport` raises ImportError, and
all 24 v4 exporters break. The v5 base is therefore a flat module,
`glances/exports/export_base_v5.py`, until the Phase 4 cleanup removes the v4
file and frees the name.

### 4.1 Discovery

`discover_exporters(config, args)` in `main_v5.py`, mirroring
`discover_plugins()`: `pkgutil` walks `glances.exports`, imports
`glances.exports.glances_<name>.export_v5` where present, and instantiates its
`Export` class when `args.export_<name>` is true.

A module that fails to import (missing optional client library) is logged at
DEBUG and skipped — never fatal, since the user did not ask for that exporter.
An exporter the user *did* ask for that fails to import is fatal (§8).

### 4.2 GlancesExportBase

```python
class GlancesExportBase(ABC):
    export_name: ClassVar[str] = ""       # "csv", "influxdb2", ...

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace) -> None: ...

    # --- config helpers (ported from v4 GlancesExport) ---
    def load_conf(self, section, mandatories=("host", "port"), options=()) -> bool: ...
    def _limits_for(self, plugin: GlancesPluginBase) -> dict[str, Any]: ...   # §5.3

    # --- payload preparation (v5-specific) ---
    def _inject_key(self, plugin, payload): ...     # §5.2
    def _merge_limits(self, plugin, payload): ...   # §5.3, uses _limits_for

    # --- wire format (ported from v4 GlancesExport) ---
    def build_export(self, stats: dict | list) -> tuple[list[str], list[Any]]: ...
    def is_excluded(self, field: str) -> bool: ...
    def parse_tags(self, tags: str | None) -> dict[str, str]: ...
    def normalize_for_influxdb(self, name, columns, points) -> list[dict]: ...

    # --- lifecycle ---
    def update(self, plugins: list[GlancesPluginBase]) -> None:   # sync, runs in a thread
        ...
    @abstractmethod
    def export(self, name: str, columns: list[str], points: list[Any]) -> None: ...
    def exit(self) -> None: ...
```

`update()` and `export()` stay **synchronous**. Every backend client here is
blocking (file IO, `influxdb_client`, `prometheus_client`). The async boundary
lives in the scheduler, which calls `await asyncio.to_thread(exporter.update,
plugins)` once per tick — see §7.

This is a divergence from architecture §7.3 ("`GlancesExportBase.update()`
becomes async"). Making `update()` `async def` while its body is entirely
blocking would be async theatre: it would still need a `to_thread` inside, at a
finer grain, for no gain. The design keeps the coroutine boundary at the
scheduler, where it is real. Recorded here so §7.3 can be corrected.

---

## 5. Data model

### 5.1 Per-cycle flow

```
for each plugin in registry where plugin.EXPORTABLE:
    payload = plugin.get_export()            # dict | list[dict], _* and exportable:False stripped
    payload = self._inject_key(plugin, payload)     # §5.2
    payload = self._merge_limits(plugin, payload)   # §5.3
    names, values = self.build_export(payload)
    self.export(plugin.plugin_name, names, values)
```

Plugin selection needs no `disable` check: `discover_plugins()` never
instantiates a disabled plugin, so the registry handed to the exporters is
already the enabled set.

### 5.2 The missing `key` field

v4's `build_export()` reads `stats["key"]` to build the per-item prefix
(`eth0.rx`, `eth0.tx`) and to emit the `<pk_value>.key` column that
`normalize_for_influxdb()` looks for when deciding which fields become InfluxDB
tags.

**v5 payloads carry no `key` field.** The primary key lives in
`fields_description` as `primary_key: True` and is resolved by
`GlancesPluginBase._resolve_primary_key()`; only `time_since_update` is injected
as metadata (`_BASE_METADATA_FIELDS`).

`GlancesExportBase._inject_key()` therefore adds, for every item of a collection
plugin, `item["key"] = <primary key field name>` before calling
`build_export()`. Scalar plugins are passed through unchanged.

This is the one place in G8 where the port is not mechanical. Without it, two
things break silently: per-item prefixes disappear (every interface's `rx`
collapses onto a single `rx` series) and InfluxDB tagging degrades to
hostname-only.

**Second divergence: v5 injects `key` for every collection plugin; v4 omitted it for `programlist`.**
v4's `key` field was never a systematic property of a collection payload — it
was set by hand, per plugin, and not always inside the plugin's own directory
(`percpu`'s is set in `glances/cpu_percent.py:322`, not in
`glances/plugins/percpu/`). Some collection plugins set it; some never did.

Where v4 omitted it, the export was **actively lossy**, not merely
inconsistent. With no `<value>.key` column, `normalize_for_influxdb()` finds an
empty `keys_list`, falls back to `[None]`, and collapses every item of the
collection into ONE measurement built from `dict(zip(columns, points))` — which
keeps only the LAST item's values, because the same field name repeats once per
item with no per-item prefix to disambiguate. The operator received one
arbitrary item's numbers labelled as the whole plugin, and the CSV exporter
wrote a header with duplicate column names for the same reason.

v5's `_inject_key()` has no per-plugin list to consult — it keys off
`plugin._primary_key`, which every collection plugin resolves from
`fields_description` regardless of whether v4 happened to export a `key` for
it. Every collection plugin therefore now emits one distinct series per item.

This is a **user-visible change** for whichever plugins v4 omitted, and it
belongs in the release notes alongside the `_action` exclusion (§5.4).
Restoring literal v4 parity — deliberately omitting `key` for those plugins —
was rejected: it would knowingly reintroduce the data loss just described, for
the sake of matching a bug rather than the documented wire format.

**Resolved by measurement (2026-08-23).** The affected set is **one plugin:
`programlist`.** Every other v4 collection plugin does set `key`, several of
them outside their own plugin directory — which is why source grepping
under-reported it twice:

| Plugin | Where v4 sets `key` |
|---|---|
| amps, diskio, folders, fs, gpu, irq, network, ports, sensors, wifi | in the plugin's own `update()` |
| percpu | `glances/cpu_percent.py:322` |
| processlist | `glances/processes.py:543` |
| containers | `glances/plugins/containers/engines/docker.py:397`, `engines/lxd.py:292` |
| vms | `glances/plugins/vms/engines/virsh.py:264`, `engines/multipass.py:89` |
| **programlist** | **nowhere** — `create_program_dict()` (`glances/programs.py:15`) omits it |

Verified by instantiating the real v4 stack (`GlancesStats`) and inspecting each
plugin's `get_export()`, not by grepping. An earlier draft asserted "9 of 19,
including `percpu`"; that was wrong on both counts.

Measured impact on `programlist`, three programs, same payload through the same
`build_export()` / `normalize_for_influxdb()`:

```
v4 columns : name, cpu_percent, memory_percent          (x3, unprefixed)
             -> 9 columns, 3 distinct, 6 COLLIDE
v5 columns : claude.name, claude.cpu_percent, claude.memory_percent, claude.key,
             terminator.*, python3.*
             -> 12 columns, 12 distinct, 0 collide

InfluxDB measurements   v4: 1    v5: 3
v4 keeps only  {'cpu_percent': 7.4, 'memory_percent': 0.356}  tagged name=python3
   — `claude` and `terminator` are silently discarded.
```

So the release-notes entry names `programlist` only, and reads as a bug fix
rather than a regression: v4 exported one arbitrary program's numbers for the
whole plugin.

### 5.3 Limits merged into the payload

v4 merges the plugin's whole config section into the exported payload
(`glances/exports/export.py::update` → `all_stats[plugin].update(all_limits[plugin])`),
where `all_limits` is v4's `_limits` built by
`glances/plugins/plugin/model.py::load_limits`: every key of `[<plugin>]`
flattened to `<plugin>_<key>`, coerced to float or comma-split to a list, plus
`history_size` read from `[global]`. `<plugin>_disable` is popped before export.

The commented example in `conf/glances.conf:798`
(`exclude_fields=.*_critical,.*_careful,.*_warning,.*\.key$`) exists precisely
because those merged threshold fields reach the backend by default.

v5 reproduces this **in the export layer**, not in the plugin. The flat
`<plugin>_<key>` shape is an output-format convention, not a domain property of
a plugin — putting it on `GlancesPluginBase` would push a wire-format concern
into the model layer, and would sit confusingly next to `get_limits()`, which
answers a different question in a different shape.

`GlancesExportBase._limits_for(plugin)`:

- reads `config.items(plugin.plugin_name)`;
- coerces each value with `config.get_float_value()`, falling back to
  `config.get_value(...).split(",")` on `ValueError` — the v4 rule verbatim;
- adds `history_size` from `[global]` (default 28800), as v4 does;
- **skips every key containing `_action`** — see §5.4;
- caches the result per plugin name: the config does not change between ticks.

The caller then pops `<plugin>_disable`, exactly as v4's `update()` does.

`GlancesPluginBase.get_limits()` — the structured, effective-thresholds view
consumed by `/api/5/<plugin>/limits` and MCP — is **not** touched and **not**
used here. Two consumers, two shapes; each method's docstring points at the
other so the next reader does not "unify" them.

### 5.4 Security divergence: `*_action*` keys are not exported

v4 exports action templates as ordinary fields. A config carrying

```ini
[cpu]
critical_action=/usr/bin/mail -s "CPU critical on {{hostname}}" ops@example.com
```

sends that shell command, in clear text, into InfluxDB / Prometheus / the CSV
file, where it is retained as long as the retention policy says.

v5 excludes any limits key whose name contains `_action`. These keys are
command templates and Mustache payloads — never metrics. Nothing consumes them
downstream, so no legitimate dashboard breaks.

This aligns the export surface with the REST one: `get_limits()`'s docstring
already states that keeping `*_action` templates out of the payload is a design
objective (limits-routes design §7). Exporting them was the last hole.

**Documented as:** a security fix in the v5 release notes, listed under the
behaviour differences vs v4.

### 5.5 EXPORTABLE

```python
class GlancesPluginBase:
    EXPORTABLE: ClassVar[bool] = True
```

Set to `False` on `quicklook`, `version` and `psutilversion` — the three members
of v4's `non_exportable_plugins` that still exist as v5 plugins. `alert` is not
a plugin in v5 (the block is synthesized by the renderer — G7 design §4.1),
`help` was removed as a plugin in Phase 2, and `plugin` never existed.

A class flag rather than the v4 hard-coded list: adding a plugin must not
require editing a central list in the export layer. Consistent with
`DISPLAY_IN_TUI`, `EMITS_ALERTS`, `SCHEDULE_AT_GLOBAL_REFRESH`.

---

## 6. Configuration and CLI

| Key | Section | Status |
|---|---|---|
| `exclude_fields` | `[export]` | Unchanged. Read via `config.get("export", "exclude_fields", [])` — `GlancesConfigV5` has no `get_list_value()`, but its native list coercion covers the comma-separated form. |
| `refresh` | `[export]` | **New.** Export tick, in seconds. Default and floor: the global refresh. |
| — | `[influxdb]`, `[influxdb2]`, `[influxdb3]`, `[prometheus]` | Unchanged, read by the ported `load_conf()`. |

`[export] refresh` below the global refresh is clamped up to it, with a startup
warning: exporting faster than the data is collected duplicates points.

Architecture §7.1 proposes `[exports] refresh_time`. This design deliberately
uses `[export] refresh` instead — a second section one letter away from the
existing `[export]` is a configuration trap, and `refresh` is the key name every
other section already uses. **Architecture §7.1 to be corrected.**

CLI flags ported verbatim into `main_v5.build_parser()`:

```
--export a,b            comma-separated exporter list  → args.export_<name> = True
--export-csv-file PATH        (default ./glances.csv)
--export-csv-overwrite
--export-json-file PATH       (default ./glances.json)
```

`conf/glances.conf` gains a documented, commented `refresh` key in `[export]`.
No default behaviour changes: with no `--export` flag, nothing is instantiated
and no loop runs.

---

## 7. Scheduler integration

`AsyncScheduler` gains:

```python
def register_exporter(self, exporter: GlancesExportBase) -> None: ...
async def _export_loop(self) -> None: ...
```

`_export_loop()` is a sibling task of the per-plugin `_plugin_loop()` tasks,
started by `run_forever()` only when at least one exporter is registered. Each
tick:

```python
plugins = [entry.plugin for entry in self._entries]
for exporter in self._exporters:
    try:
        await asyncio.to_thread(exporter.update, plugins)
    except Exception as e:
        logger.warning("Export %s failed: %s", exporter.export_name, e)
await asyncio.sleep(self._export_refresh_time())
```

The scheduler passes the **whole** registry; filtering on `EXPORTABLE` happens
once, inside `GlancesExportBase.update()` (§5.1). One filter, one place — the
scheduler has no business knowing which plugins an exporter cares about.

One `to_thread` per exporter per tick, and one failing exporter never stops the
others or the loop — the same isolation rule `_plugin_loop()` already applies to
plugins and alerts.

`stop()` calls `exporter.exit()` for each registered exporter, next to the
existing `plugin.stop()` teardown, each guarded so one failure cannot block the
rest.

Export runs in **both** modes — TUI and `--server` — per architecture §7.1
("export is available in all modes"). `serve()` needs no change: the export loop
lives inside `scheduler.run_forever()`, which both modes already await.

`run_forever()` currently raises when no plugin is registered. With exporters
that stays correct: an exporter with an empty registry has nothing to export.

---

## 8. Failure modes

| Moment | Behaviour |
|---|---|
| Exporter requested but its module/library fails to import | **Fatal** — `sys.exit(2)`, iso-v4. |
| Exporter init fails (Prometheus port taken, unwritable CSV, InfluxDB unreachable) | **Fatal** — `sys.exit(2)`, iso-v4. |
| `export()` raises during a cycle | Log WARNING, continue. Iso-v4 (`influxdb2` already downgrades to warning per issue #1561). |
| `exit()` raises at teardown | Log WARNING, continue tearing the others down. |
| Exporter module present but not requested | Not imported, not instantiated. |

The fatal-on-init choice is the maintainer's: an operator who passes `--export
influxdb2` wants the export, and discovering three hours later that Glances came
up with a silently disabled exporter is worse than failing loudly at startup.

---

## 9. Per-exporter notes

| Exporter | Port notes |
|---|---|
| `csv` | Overrides `update()` (header management, `first_line`, `old_header` compatibility check). Ported as an `update()` override on the v5 base, same logic. Writes `timestamp` first, then `<plugin>.<field>` columns. |
| `json` | Buffers per cycle and flushes when the first plugin of the list comes round again. v5 simplifies: `update()` builds the whole buffer in one pass and writes once — no sentinel needed, since the v5 base owns the plugin loop. Same output file, same one-JSON-object-per-line format. |
| `prometheus` | Needs the per-plugin primary key (`stats.get_plugin(k).get_key()` in v4). v5 reads `plugin._resolve_primary_key()` — the same value §5.2 injects, so it is resolved once and shared. `start_http_server()` in `__init__`, fatal on failure. |
| `influxdb` (1.x) | `influxdb.InfluxDBClient`. Mechanical port. |
| `influxdb2` | `influxdb_client`. Its `flush_interval` derives from `args.time` in v4 (the CLI refresh); v5 has no such arg, so it is wired to `[export] refresh`. Visible only to a deployment setting `[influxdb2] interval=0`. |
| `influxdb3` | `influxdb_client_3`. Mechanical port. |

Every client library is imported **inside** `__init__`, never at module level:
module-level imports would make discovery raise on a minimal install (§3).

**Behaviour difference the csv/json port must handle.** `GlancesExportBase.update()`
(§5.1, §4.2) does `if not payload: continue` — a plugin with nothing to export
this tick (cycle 0 before its first publish, or a genuinely empty collection)
is skipped entirely, and `self.export(name, ...)` is never called for it. v4's
loop still called `export(plugin, [], [])` for that plugin, with empty
`columns`/`points` lists. For `influxdb`/`prometheus`-style exporters this is a
no-op either way. For `csv`, it is not: v4's header is fixed on the first
write and every subsequent row must align column-for-column, so a row that
silently omits a plugin's columns (instead of writing them empty) misaligns
every column to their right for that row. The `csv` (and, for the JSON Lines
shape, `json`) port must account for this — e.g. writing the plugin's known
columns with empty values on a skip, rather than reproducing v5's `continue`
verbatim — as part of `update()`'s header/row-alignment logic (§9 above).

---

## 10. Testing

`tests/test_export_base_v5.py` — the contract:

- `build_export()` on a scalar payload and on a collection payload;
- `_inject_key()`: per-item prefixes (`eth0.rx`) and the `eth0.key` column;
- `_limits_for()`: thresholds present, `history_size` present,
  `<plugin>_disable` absent, **`*_action` keys absent**;
- `EXPORTABLE=False` plugins skipped;
- `[export] refresh` clamped up to the global refresh, with the warning;
- one exporter raising in `update()` does not stop the loop or the others;
- `exit()` called for every exporter on `scheduler.stop()`.

One file per exporter, backend client mocked:
`test_export_csv_v5.py`, `test_export_json_v5.py`,
`test_export_prometheus_v5.py`, `test_export_influxdb_v5.py`,
`test_export_influxdb2_v5.py`, `test_export_influxdb3_v5.py`. CSV and JSON write
to `tmp_path` and assert on real file content, including the CSV
header-mismatch-on-append path.

The v4 `tests/test_export_*.sh` Docker scripts stay on v4, untouched. Rewriting
them against v5 belongs to Phase 4 hardening.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| A wire-format detail diverges and breaks a user's dashboard silently | `build_export()`, `normalize_for_influxdb()`, `parse_tags()` are ported verbatim, not rewritten. The `key` injection (§5.2) is the only behavioural addition and is directly tested. |
| Export adds measurable CPU in TUI mode | One `to_thread` per exporter per tick, default tick = global refresh. Nothing runs when no `--export` flag is passed. |
| Three optional client libraries make CI coverage partial | Backends mocked; the import path itself is tested by asserting discovery skips a module whose library is absent. |
| `[export] refresh` vs architecture `[exports] refresh_time` drift | Architecture §7.1 to be corrected in the same cycle; noted in §6. |
| `async def update()` divergence from §7.3 | Documented in §4.2; §7.3 to be corrected. |

---

## 12. Deliverables

1. `glances/exports/export_base_v5.py`
2. Six `export_v5.py` modules
3. `EXPORTABLE` on `GlancesPluginBase` + three plugin overrides
4. `discover_exporters()` and the CLI flags in `main_v5.py`
5. `register_exporter()` / `_export_loop()` / `exit()` teardown in
   `scheduler_v5.py`
6. `[export] refresh` documented in `conf/glances.conf`
7. Seven test modules (§10)
8. Corrections to architecture §7.1 and §7.3

Not in this cycle, per the maintainer's standing rule: no `NEWS.rst` entry. The
§5.4 security divergence and the `[export] refresh` key are recorded here for
the release changelog, written at release time.

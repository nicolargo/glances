# Glances v5 — vms plugin port (G6A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `vms` plugin to the v5 asyncio architecture — a collection of virtual machines fetched from two synchronous CLI engines (multipass, virsh), disabled by default, with **no alerts** (`EMITS_ALERTS=False`, mirroring v4's dead alert decorations).

**Architecture:** A collection plugin (`model_v5.py::PluginModel`, `IS_COLLECTION=True`, primary key `name`) whose `_grab_stats()` self-gates on `[vms] disable` (default True — mirrors the v4 default via the established `npu` pattern), then wraps the v4 CLI pipeline in `asyncio.to_thread`: it iterates the two v4 engine extensions (`multipass`, `virsh`) verbatim, injects `engine`/`engine_version`, sorts the list via the v4 `sort_vm_stats` rule (driven by the dynamic `glances_processes.sort_key`), and exposes the configured `max_name_size` through payload metadata. The base class turns the cumulative `cpu_time` counter into a per-second rate (`rate: True`). A dedicated `render_curses_v5.py` mirrors v4 `msg_curse()` (a `VMs` title line, a column header, one coloured row per VM), rendered full-width in the MAIN (RIGHT) column; it underlines the active sort column from the global `view["sort_key"]`, exactly like the processlist renderer.

**Tech Stack:** Python, multipass/virsh CLI (reused v4 engines), asyncio (to_thread), curses renderer v5, pytest

## Global Constraints

- **Mirror v4**: read the v4 `msg_curse()` + `update`/`update_local` + `vm_alert` before writing the renderer/model; divergent "clean generic" layouts are regressions.
- **Reuse the v4 CLI engines verbatim** (`glances/plugins/vms/engines/multipass.py`, `engines/virsh.py`) via `asyncio.to_thread`. Do **not** rewrite their parsing. The virsh **CVE-2026-46606** hardening (`_run_virsh` with `shell=False` + explicit arg lists) is inherited unchanged — do not touch it.
- **MAIN / RIGHT column, full-width** (not the 34-char LEFT-sidebar budget). `vms` is already registered in `RIGHT_SLOT` in `curses_renderer_v5.py` — no layout/orchestrator change is needed. There is **no** responsive column-drop logic in v4 `vms` (unlike processlist); mirror v4's fixed column set + conditional Engine/LOAD columns.
- **Disabled by default preserved**: v4 ships `[vms] disable=True`. v5's `discover_plugins` has **no per-plugin disable gate**, so the model self-gates in `_grab_stats` (mirror `glances/plugins/npu/model_v5.py::_is_enabled`). Absent / `disable=True` → the plugin yields an empty collection (renders nothing via the build_frame empty-collection rule).
- **`EMITS_ALERTS = False`** (mirror v4 dead alert decorations — no watched fields, no `_levels`, no history/action). Status colour is a rendering concern and stays.
- **Empty registry / empty stats must stay valid** (no engine binary present → empty collection, not a crash).
- **No dead code** — do not port v4's `items_history_list`, `sort_for_human` beyond the keys the derived sort key can take, or `get_export` override (the base `get_export` covers it).
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only (`git add`), never `git commit`.
- Tests: `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` + `ruff format`.

---

## Key implementation findings (decided, not open)

1. **Disabled-by-default has no v5 plumbing.** `glances/main_v5.py::discover_plugins` (lines 235–281) discovers and instantiates every `model_v5.PluginModel` unconditionally — it never reads `[<plugin>] disable`. v4 `vms` defaults to `disable=True`. To preserve that default **without** inventing a global v5 feature, the model self-gates in `_grab_stats`, exactly like the already-shipped `npu` plugin (`glances/plugins/npu/model_v5.py::_is_enabled`, lines 97–104): `str(self.config.get("vms","disable","True")).strip().lower() in ("false","0","no")`. This is a per-plugin, surgical honouring of the v4 default, tested by `test_disabled_by_default_returns_empty`.

2. **`cpu_time` rate keeps the same key name.** Declaring `cpu_time` with `rate: True` makes the base `_compute_rates_in_dict` (`base_v5.py` line 348: `stats[field_name] = max(0.0, delta / float(elapsed))`) **replace `cpu_time` in place** with the per-second rate — it does **not** create a `cpu_time_rate_per_sec` suffix key (that was the v4 `@_manage_rate` behaviour). On the first cycle, `elapsed<=0`, or when the raw value is non-numeric (multipass reports `cpu_time=None`), the base **deletes** `cpu_time` for that item (line 341/346). So the renderer reads `cpu_time` and shows `-` when absent — which is exactly the v4 outcome for multipass VMs. The renderer and tests use `cpu_time`, never the `_rate_per_sec` name.

3. **Sort underline is processlist-aligned via `view["sort_key"]` (payload carries NO sort_key).** The TUI passes a single global `view["sort_key"]` to every renderer (`glances_curses_v5.py::_render_view`, line 618) — the *process* sort key (`glances_processes.sort_key`), which is **dynamic** (default `auto` resolves to cpu/mem under load). The renderer reads `view.get("sort_key")` and underlines the matching column through a header→process-sort-key map (`_HEADER_SORT_FIELD`), exactly like `processlist`'s `_HEADER_SORT_KEY`. The mapping mirrors how `sort_vm_stats` maps the process key to a vms field: `Name → "name"`, `MEM/MAX → "memory_percent"`, `CPU% → "cpu_percent"` (the process key that sorts VMs by `cpu_time`); columns with no process-sort equivalent (Core, LOAD) are never underlined. The **model still pre-sorts** the data via `sort_vm_stats(glances_processes.sort_key)` (dynamic default preserved), but it does **not** expose a derived sort key — the payload shape carries no `sort_key`. Only `max_name_size` (a config value the pure renderer needs) is exposed via `_add_metadata`; it is not exportable (base `get_export` returns only `data` items), so it never leaks to exporters. This keeps vms and containers sort behaviour identical to processlist.

---

## File Structure

```
glances/plugins/vms/
  __init__.py            (v4 — untouched; kept for v4 runtime)
  engines/__init__.py    (v4 Protocol — untouched, reused)
  engines/multipass.py   (v4 — untouched, reused via to_thread)
  engines/virsh.py       (v4 — untouched, reused; CVE-2026-46606 hardening inherited)
  model_v5.py            (NEW — PluginModel: self-gate, engines, _collect, sort, metadata)
  render_curses_v5.py    (NEW — VMs title + header + per-VM rows)
tests/
  test_plugin_vms_v5.py               (NEW — model: identity/fields/gate/merge/rate/sort/metadata)
  test_plugin_vms_render_curses_v5.py (NEW — renderer: title/header/rows/conditional cols/status colour/underline)
docs/aoa/vms.rst         (update for v5; already in docs/aoa/index.rst — do NOT re-add)
conf/glances.conf        ([vms] disable=True / max_name_size=20 / all=False already shipped — verify only)
```

---

### Task 1 — Model: identity, fields, self-gate, engines, `_collect`, sort, metadata

**Files:** `glances/plugins/vms/model_v5.py`, `tests/test_plugin_vms_v5.py`

**Interfaces:**
- Consumes: `StatsStoreV5`, `GlancesConfigV5`, v4 engines `MultipassVmExtension`/`VirshVmExtension` (`update(all_tag) -> (version:str, list[dict])`), `glances.processes.glances_processes` + `sort_stats`.
- Produces: `PluginModel` (`plugin_name="vms"`, `IS_COLLECTION=True`, `EMITS_ALERTS=False`, primary key `name`); payload `{"data":[...], "time_since_update":…, "max_name_size":…, "_levels":{}}` (**no `sort_key`** — the renderer reads the global `view["sort_key"]`, processlist-aligned); module-level `sort_vm_stats(stats) -> tuple[str, list]` (its returned key is consumed only to order the data, not exposed).

fields_description (from v4 — every field top-level, one primary key, `cpu_time` is the only rate; no watched fields):
```python
fields_description: ClassVar[dict[str, dict[str, Any]]] = {
    "name": {"description": "VM name.", "unit": "string", "primary_key": True},
    "id": {"description": "VM ID.", "unit": "string"},
    "release": {"description": "VM release.", "unit": "string"},
    "status": {"description": "VM status.", "unit": "string"},
    "cpu_count": {"description": "VM CPU count.", "unit": "number"},
    "cpu_time": {"description": "VM CPU time (per-second rate).", "unit": "percent", "rate": True},
    "memory_usage": {"description": "VM memory usage.", "unit": "byte"},
    "memory_total": {"description": "VM memory total.", "unit": "byte"},
    "load_1min": {"description": "VM load, last 1 min (None if unsupported by the engine).", "unit": "float"},
    "load_5min": {"description": "VM load, last 5 min (None if unsupported by the engine).", "unit": "float"},
    "load_15min": {"description": "VM load, last 15 min (None if unsupported by the engine).", "unit": "float"},
    "ipv4": {"description": "VM IPv4 address.", "unit": "string"},
    "engine": {"description": "VM engine name.", "unit": "string"},
    "engine_version": {"description": "VM engine version.", "unit": "string"},
}
```

`sort_vm_stats` — port **verbatim** from v4 (`glances/plugins/vms/__init__.py` lines 328–350):
```python
def sort_vm_stats(stats: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    # Make VM sort follow the process sort (v4 parity).
    if glances_processes.sort_key == "memory_percent":
        sort_by, sort_by_secondary = "memory_usage", "cpu_time"
    elif glances_processes.sort_key == "name":
        sort_by, sort_by_secondary = "name", "cpu_time"
    else:
        sort_by, sort_by_secondary = "cpu_time", "memory_usage"
    sort_stats_processes(
        stats,
        sorted_by=sort_by,
        sorted_by_secondary=sort_by_secondary,
        reverse=glances_processes.sort_key != "name",
    )
    return sort_by, stats
```

Model body (self-gate mirrors `npu`; `_collect` mirrors v4 `update_local`; `_add_metadata` exposes the derived key + name width):
```python
_DEFAULT_MAX_NAME_SIZE = 20

class PluginModel(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "vms"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {...}  # as above

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        # Mirror v4: build both engines unconditionally; each self-guards on
        # its import_*_error_tag inside update() (returns ('', []) when the
        # binary is absent). No construction gating — matches v4 __init__.
        self.watchers: dict[str, VmsExtension] = {
            "multipass": MultipassVmExtension(),
            "virsh": VirshVmExtension(),
        }
        self._max_name_size = int(self.config.get("vms", "max_name_size", _DEFAULT_MAX_NAME_SIZE))

    def _is_enabled(self) -> bool:
        # Mirror v4 [vms] disable=True default (see npu/model_v5.py).
        raw = self.config.get("vms", "disable", "True")
        return str(raw).strip().lower() in ("false", "0", "no")

    def _all_tag(self) -> bool:
        raw = self.config.get("vms", "all", "False")
        return str(raw).strip().lower() in ("true", "1", "yes")

    def _collect(self) -> list:
        stats: list[dict[str, Any]] = []
        all_tag = self._all_tag()
        for engine, watcher in self.watchers.items():
            try:
                version, vms = watcher.update(all_tag=all_tag)
            except Exception as exc:  # noqa: BLE001 — one bad engine must not kill the others
                logger.debug("vms: engine %s update failed: %s", engine, exc)
                continue
            for vm in vms:
                vm["engine"] = engine
                vm["engine_version"] = version
            stats.extend(vms)
        # Pre-sort the list to follow the dynamic process sort key (v4
        # parity). The returned key is not exposed — the renderer underlines
        # from the global view["sort_key"], processlist-aligned.
        _, stats = sort_vm_stats(stats)
        return stats

    async def _grab_stats(self) -> list:
        if not self._is_enabled():
            return []
        return await asyncio.to_thread(self._collect)

    def _add_metadata(self) -> None:
        super()._add_metadata()
        self._metadata["max_name_size"] = self._max_name_size
```

Steps:
- [ ] Write `tests/test_plugin_vms_v5.py` with `store` + `config` fixtures copied from an existing v5 collection test (`tests/test_plugin_diskio_v5.py` or `tests/test_plugin_wifi_v5.py`: `store()` → `StatsStoreV5()`; `config(tmp_path, monkeypatch)` writing an XDG-discovered `glances.conf` then `GlancesConfigV5()`), plus a `_cfg_with(tmp_path, monkeypatch, body)` helper that writes an arbitrary `[vms]` section. Add:
  - `test_plugin_identity` — `plugin_name == "vms"`, `IS_COLLECTION is True`, `EMITS_ALERTS is False`, `_primary_key == "name"`.
  - `test_fields_description` — keys equal the 14 declared names; `fd["name"]["primary_key"] is True`; `fd["cpu_time"]["rate"] is True`; no field has `"watched": True`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_vms_v5.py::test_plugin_identity -v` → expect **FAIL** (module missing).
- [ ] Write COMPLETE `glances/plugins/vms/model_v5.py`: SPDX header (2026), `from __future__ import annotations`, imports (`asyncio`, `logging`, `typing`, `GlancesPluginBase`, the three engine imports mirroring v4 lines 16–18, `glances_processes`, `sort_stats as sort_stats_processes`), `logger`, `_DEFAULT_MAX_NAME_SIZE`, the `fields_description`, the class body above, and the module-level `sort_vm_stats`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_vms_v5.py -v` → expect **PASS**.
- [ ] Add `test_disabled_by_default_returns_empty` — plain `config` (no `[vms]` section) → `await p._grab_stats() == []` and `p._sort_key is None`.
- [ ] Add `test_enabled_merges_engines` — `_cfg_with(..., "[vms]\ndisable=False\n")`; monkeypatch `p.watchers = {"multipass": _FakeEngine("1.13", [ {"name":"vm-a","status":"running","cpu_count":2,"cpu_time":None,"memory_usage":1024,"memory_total":4096,"load_1min":None} ]), "virsh": _FakeEngine("9.0", [ {"name":"vm-b","status":"running","cpu_count":4,"cpu_time":1000,"memory_usage":2048,"memory_total":8192,"load_1min":None} ])}` (where `_FakeEngine(version, rows)` has `update(all_tag)` returning `(version, [dict(r) for r in rows])`). Await `_grab_stats()`; assert two items, each carrying its `engine`/`engine_version` (`vm-a`→`multipass`/`1.13`, `vm-b`→`virsh`/`9.0`).
  - `test_one_engine_unavailable_still_returns_other` — one fake engine's `update` raises; assert the other engine's VM is still returned (non-empty).
  - `test_no_engine_returns_empty` — both fake engines return `("", [])`; assert `await _grab_stats() == []` (with `disable=False`).
- [ ] Add `test_max_name_size_exposed_in_metadata` — enabled, one engine; run a full `await p.update()`; `payload = p.get_stats()`; assert `payload["max_name_size"] == 20` and `"sort_key" not in payload` (the payload carries no derived sort key — the renderer uses `view["sort_key"]`). The sort-underline behaviour is covered by the renderer tests in Task 2.
- [ ] Add `test_cpu_time_rate_derived` — enabled; a fake virsh engine whose `update` returns increasing cumulative `cpu_time` across calls (`1000` then `3000`) for `name="vm-b"`; monkeypatch `time.monotonic` (or drive two `await p.update()` calls with a controlled `time_since_update`) so `elapsed == 2.0`; after the **second** cycle assert `p.get_stats()["data"][0]["cpu_time"] == 1000.0` (`(3000-1000)/2`). Assert that after the **first** cycle `cpu_time` is **absent** from the item (base strips the rate field on the first sample). Mirror the rate-test pattern used in `tests/test_plugin_diskio_v5.py` for `read_bytes`.
  - `test_multipass_cpu_time_none_absent` — a multipass fake returning `cpu_time=None`; after any cycle assert `"cpu_time"` not in the item (base deletes the non-numeric rate field).
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_vms_v5.py -v` → expect **PASS**.
- [ ] `.venv/bin/python -m ruff check glances/plugins/vms/model_v5.py tests/test_plugin_vms_v5.py && .venv/bin/python -m ruff format glances/plugins/vms/model_v5.py tests/test_plugin_vms_v5.py`.
- [ ] `git add glances/plugins/vms/model_v5.py tests/test_plugin_vms_v5.py` — then STOP (no commit).

---

### Task 2 — Curses renderer (`VMs` title + header + per-VM rows)

**Files:** `glances/plugins/vms/render_curses_v5.py`, `tests/test_plugin_vms_render_curses_v5.py`

**Interfaces:**
- Consumes: collection payload `{"data":[...], "max_name_size":…}` (no `_levels` — `EMITS_ALERTS=False`; no `sort_key`) and the TUI `view` dict carrying the global `view["sort_key"]`.
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — a title Row, a column-header Row, one Row per VM. Sort-column underline is driven by `view["sort_key"]`, processlist-aligned.

Layout (mirror v4 `msg_curse`, `glances/plugins/vms/__init__.py` lines 204–314; reference the processlist renderer for the header-underline pattern):
- Import `Cell`, `ColorRole`, `Row`, `title_role` from `glances.outputs.curses_renderer_v5`; `auto_unit` from `glances.globals` (`auto_unit(x)` returns `-` for None via `none_symbol='-'`).
- `_DEFAULT_MAX_NAME_SIZE = 20`. `_STATUS_WIDTH=10`, `_CORE_WIDTH=6`, `_CPU_WIDTH=6`, `_MEM_WIDTH=7`, `_LOAD_HEADER_WIDTH=17`, `_ENGINE_MIN_WIDTH=8`.
- `_sorted_by_label(process_sort_key) -> str` — maps the global process sort key to the vms human label, mirroring `sort_vm_stats`: `"memory_percent"`→`"memory consumption"`, `"name"`→`"VM name"`, else→`"CPU time"`. Used only for the title's "sorted by …" text (keeps the label consistent with the underlined column).
- `_HEADER_SORT_FIELD = {"Name":"name","CPU%":"cpu_percent","MEM/MAX":"memory_percent"}` — underline the header whose value equals the global `view["sort_key"]` (processlist-aligned; the map holds **process** sort keys, mirroring how `sort_vm_stats` maps `glances_processes.sort_key` to a vms field: `name`→Name, `memory_percent`→MEM, everything-else→CPU%). Columns with no process-sort equivalent (`Core`, `LOAD 1/5/15min`) are never underlined. (Note: v4 underlines only the `MEM` sub-cell; here MEM and MAX are one glued cell so the underline spans `MEM/MAX` — a cosmetic, intentional simplification.)
- `_status_role(status) -> ColorRole` (mirror v4 `vm_alert`): `"running"`→`ColorRole.OK`; `{"starting","restarting","delayed shutdown"}`→`ColorRole.WARNING`; else `ColorRole.DEFAULT` (v4 `INFO` — there is no `INFO` role in v5, DEFAULT is neutral). Compare case-insensitively on `str(status or "").lower()`.
- `render`:
  - `items = [i for i in payload.get("data", []) if isinstance(i, dict)]` when `payload` is a dict, else `[]`. If `not items` → return `[]` (empty collection renders nothing — matches the build_frame rule; do not emit a bare title).
  - `sort_key = (view or {}).get("sort_key")` (global process key, processlist-aligned — NOT from payload); `max_name_size = payload.get("max_name_size", _DEFAULT_MAX_NAME_SIZE)`.
  - `show_engine = len({str(i.get("engine","")) for i in items}) > 1`.
  - `name_w = min(max_name_size, max(len(str(i.get("name",""))) for i in items))` (mirror v4 line 231–234; guard empty → `max_name_size`).
  - `engine_w = max(_ENGINE_MIN_WIDTH, max(len(str(i.get("engine",""))) for i in items))` when `show_engine`.
  - `show_load = items[0].get("load_1min") is not None` (v4 gates the LOAD columns on the first VM, line 253).
  - **Title Row** (mirror v4 lines 214–225): `Cell("VMs", color=ColorRole.HEADER, bold=True)`; if `len(items) > 1`: append `Cell(f"{len(items)}")` and `Cell(f"sorted by {_sorted_by_label(sort_key)}")`; if `not show_engine`: append `Cell(f"(served by {items[0].get('engine','')})")`.
  - **Header Row** — a `_header(label, width, *, ljust=False)` helper building `Cell(text=label.ljust/​rjust(width), color=ColorRole.HEADER, bold=True, underline=_HEADER_SORT_FIELD.get(label)==sort_key)`: `Engine`(ljust engine_w, only if `show_engine`), `Name`(ljust name_w), `Status`(rjust 10), `Core`(rjust 6), `CPU%`(rjust 6), `MEM/MAX`(the glued header `f"{'MEM':>7}/{'MAX':<7}"`), `LOAD 1/5/15min`(rjust 17, only if `show_load`), `Release`(plain).
  - **Data Rows** — per VM (already sorted by the model): 
    - `Engine`(ljust engine_w) only if `show_engine`.
    - `Name`: `Cell(str(vm.get("name",""))[:name_w].ljust(name_w))`.
    - `Status`: `Cell(str(vm.get("status") or "")[:10].rjust(10), color=_status_role(vm.get("status")))`.
    - `Core`: `Cell(_fmt(vm.get("cpu_count")).rjust(6))` where `_fmt(v)` = `str(v)` if `v` is not None else `"-"`.
    - `CPU%`: `Cell(_fmt(vm.get("cpu_time")).rjust(6))` (absent for multipass / first cycle → `-`).
    - `MEM/MAX`: one glued cell `Cell(f"{auto_unit(vm.get('memory_usage')):>7}/{auto_unit(vm.get('memory_total')):<7}")` (`auto_unit(None)` → `-`).
    - `LOAD` only if `show_load`: try `Cell(f"{vm['load_1min']:>5.1f}/{vm['load_5min']:>5.1f}/{vm['load_15min']:>5.1f}")`; on `KeyError`/`TypeError` skip the cell (mirror v4 lines 300–306).
    - `Release`: `Cell(str(vm["release"]) if vm.get("release") is not None else "-")`.
  - Return `[title_row, header_row, *data_rows]`.

Steps:
- [ ] Write `tests/test_plugin_vms_render_curses_v5.py` with `_payload(items, sort_key=None, max_name_size=20)` and `_flat(rows)` (concatenate every cell text) helpers, and a `_vm(**over)` factory returning a valid VM dict (defaults: `name="vm-a"`, `status="running"`, `cpu_count=2`, `cpu_time=None`, `memory_usage=1024`, `memory_total=4096`, `load_1min=None`, `engine="multipass"`, `release="24.04"`). Add:
  - `test_empty_returns_nothing` — `render(_payload([])) == []`.
  - `test_title_and_header_and_row` — one VM → flat text contains `"VMs"`, `"Name"`, `"Status"`, `"Core"`, `"CPU%"`, `"MEM"`, `"MAX"`, `"Release"`, and the VM name/status.
  - `test_engine_column_hidden_single_engine` — two VMs both `engine="virsh"` → `"Engine"` **not** in the header; and title contains `"served by virsh"`.
  - `test_engine_column_shown_multi_engine` — one `engine="multipass"`, one `engine="virsh"` → `"Engine"` in the header; title does **not** contain `"served by"`.
  - `test_load_columns_hidden_when_load_none` — VM with `load_1min=None` → `"LOAD 1/5/15min"` not in header.
  - `test_load_columns_shown_when_load_present` — VM with `load_1min=0.5, load_5min=0.4, load_15min=0.3` → `"LOAD 1/5/15min"` in header and `"0.5"` in a data row.
  - `test_status_colour_running_ok` — `status="running"` → the status cell `.color == ColorRole.OK`.
  - `test_status_colour_starting_warning` — `status="starting"` → status cell `.color == ColorRole.WARNING`.
  - `test_status_colour_other_default` — `status="stopped"` → status cell `.color == ColorRole.DEFAULT`.
  - `test_cpu_time_absent_shows_dash` — VM without a `cpu_time` key → the CPU% cell text stripped `== "-"`.
  - `test_name_truncated_to_max_name_size` — `max_name_size=5`, VM `name="a-very-long-vm-name"` → the name cell text stripped has length ≤ 5.
  - `test_sort_underline_name` — `render(_payload([_vm()]), view={"sort_key": "name"})` → the `Name` header cell `.underline is True`, `CPU%` header `.underline is False`.
  - `test_sort_underline_cpu` — `view={"sort_key": "cpu_percent"}` → the `CPU%` header cell `.underline is True`, `Name` header `.underline is False`.
  - `test_sort_underline_mem` — `view={"sort_key": "memory_percent"}` → the `MEM/MAX` header cell `.underline is True`.
  - `test_no_view_no_underline` — `render(_payload([_vm()]))` (no `view`) → no header cell has `.underline is True`.
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_vms_render_curses_v5.py::test_title_and_header_and_row -v` → expect **FAIL** (module missing).
- [ ] Write COMPLETE `glances/plugins/vms/render_curses_v5.py` per the layout above (SPDX header 2026, module docstring naming the v4 `msg_curse` reference + the MEM/MAX glue, the `view["sort_key"]` processlist-aligned underline, and the `max_name_size` metadata; the constants, `_HEADER_SORT_FIELD`, `_sorted_by_label`, `_status_role`, `_header`, `_fmt`, `render`).
- [ ] Run: `.venv/bin/python -m pytest tests/test_plugin_vms_render_curses_v5.py -v` → expect **PASS**.
- [ ] `.venv/bin/python -m ruff check glances/plugins/vms/render_curses_v5.py tests/test_plugin_vms_render_curses_v5.py && .venv/bin/python -m ruff format glances/plugins/vms/render_curses_v5.py tests/test_plugin_vms_render_curses_v5.py`.
- [ ] `git add glances/plugins/vms/render_curses_v5.py tests/test_plugin_vms_render_curses_v5.py` — then STOP (no commit).

---

### Task 3 — Config verification + docs + full-suite green

**Files:** `conf/glances.conf` (verify only), `docs/aoa/vms.rst`

**Interfaces:** none new — verification and documentation.

Steps:
- [ ] Verify `conf/glances.conf` `[vms]` already ships `disable=True`, `max_name_size=20`, `all=False` (confirmed present — do NOT re-add or change the default). Only touch it if a diff shows a key missing.
- [ ] Read `docs/aoa/vms.rst`. Update it for v5: confirm it states the plugin is **disabled by default** (`[vms] disable=True`), lists the columns (Engine/Name/Status/Core/CPU%/MEM/MAX/LOAD/Release), and notes there are **no thresholds/alerts** (`EMITS_ALERTS=False`). Do not add REST/threshold sections that do not apply. Confirm `vms` is already in `docs/aoa/index.rst` (line 47 — do NOT re-add).
- [ ] Run the v5 vms test set: `.venv/bin/python -m pytest tests/test_plugin_vms_v5.py tests/test_plugin_vms_render_curses_v5.py -v` → expect **PASS**.
- [ ] Run the full suite to confirm no regression: `.venv/bin/python -m pytest -q` → expect **PASS** (green, count unchanged aside from the new vms tests; a single pre-existing unrelated failure `tests/test_actions_sanitize.py::TestSecurePopen::test_pipe` may remain — it references none of the vms modules).
- [ ] `.venv/bin/python -m ruff check glances/plugins/vms/ tests/test_plugin_vms_v5.py tests/test_plugin_vms_render_curses_v5.py && .venv/bin/python -m ruff format --check glances/plugins/vms/ tests/test_plugin_vms_v5.py tests/test_plugin_vms_render_curses_v5.py`.
- [ ] `git add glances/plugins/vms/ tests/test_plugin_vms_v5.py tests/test_plugin_vms_render_curses_v5.py docs/aoa/vms.rst` (include `conf/glances.conf` only if it was edited) — then STOP (no commit).

---

## Final self-check (spec §6.2 / §7 coverage map)

| Spec requirement | Task |
| --- | --- |
| `PluginModel` collection, primary key `name`, `EMITS_ALERTS=False` | Task 1 |
| fields (14) incl. `cpu_time` `rate:True` → base-derived per-second rate (same key) | Task 1 |
| Reuse v4 multipass+virsh engines verbatim via `to_thread`; virsh CVE hardening inherited | Task 1 |
| Disabled by default preserved (self-gate mirroring `npu`, no v5 disable plumbing) | Task 1 + Key finding 1 |
| Merge engines + inject `engine`/`engine_version`; one-engine-failure tolerant; empty when no binary | Task 1 |
| Model pre-sort via `sort_vm_stats` (dynamic process-sort parity); `max_name_size` in metadata; payload carries no `sort_key` | Task 1 + Key finding 3 |
| Renderer: MAIN column full-width; Engine(>1)/Name/Status/Core/CPU%/MEM-MAX/LOAD(cond)/Release | Task 2 |
| Status colour via `vm_alert` mapping → `ColorRole` (running OK / starting… WARNING / else DEFAULT) | Task 2 |
| LOAD columns only when `load_1min is not None`; active sort-column header underlined from `view["sort_key"]` (processlist-aligned) | Task 2 |
| `cpu_time` absent (multipass/first cycle) → `-` | Task 2 + Key finding 2 |
| Config `[vms]` (disable/max_name_size/all) already shipped — verify | Task 3 |
| Docs `docs/aoa/vms.rst` updated for v5 (already in index) | Task 3 |
| Tests: identity/fields, gate, merge/partial-failure, rate, `max_name_size` metadata, renderer columns/colour/`view`-driven underline | Tasks 1–2 |

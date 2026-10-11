# Glances v5 — G6A design (containers + vms)

**Date:** 2026-07-14
**Phase:** 2, group **G6A** (execution order G0→G1→G2→G3→G4A→G4B→G5→**G6A**→G6B→G6C→G7)
**Status:** design (approved decisions baked in; awaiting spec review before plans)

## 1. Goal & scope

Port the two v4 **external-integration** plugins `containers` and `vms` to the
Glances v5 asyncio architecture, mirroring v4 behaviour (per the "TUI v5 must
mirror v4" rule).

`containers` is the largest, most complex plugin of Phase 2: a 610-line
orchestrator plus three engine backends (`docker` 456, `podman` 466, `lxd`
367 lines) driven by per-container **background streaming threads**. `vms` is
far simpler: two synchronous CLI engines (multipass, virsh), disabled by
default, no threads.

The two plugins are independent; this single design doc covers both, with
**one execution plan per plugin** (mirrors G4B; keeps review checkpoints crisp,
especially for the thread-lifecycle work in `containers`).

## 2. Global constraints (apply to every task)

- **Mirror v4**: read the v4 `msg_curse()` + grabbers before writing each
  renderer/model; divergent "clean generic" layouts are regressions.
- **Preserve v4 fetch performance for `containers`** (non-negotiable). The v4
  streaming-thread + `ThreadPoolExecutor` architecture (issue #3559 perf fix)
  must be reused **unchanged**. No per-cycle blocking-fan-out rewrite.
- **`containers`/`vms` render in the MAIN (RIGHT) column**, full-width and
  responsive like `processlist` — **NOT** the 34-char LEFT-sidebar budget.
  Both names are already registered in `RIGHT_SLOT` in `curses_renderer_v5.py`
  (above `processlist`), so no layout/orchestrator change is needed.
- **Empty registry / empty stats must stay valid** (no engine available →
  empty collection, not a crash).
- **Alerts fire on `warning`+ only**; `careful` is colour-only (v5 engine
  already collapses sub-warning levels — see `alerts_v5`).
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only.
- Tests: `.venv/bin/python -m pytest`; lint `ruff check` + `ruff format`.

## 3. Common porting pattern (from G4A/G4B)

Each plugin provides, under `glances/plugins/<name>/`:

- `model_v5.py::PluginModel(GlancesPluginBase[list])` — `plugin_name`,
  `IS_COLLECTION = True`, `primary_key = "name"`, `fields_description`,
  `async _grab_stats()` (wraps the v4 grabber in `asyncio.to_thread`), and —
  where colouring/alerts apply — the base's `_derived_parameters()` threshold
  machinery (per-primary-key overrides included).
- `render_curses_v5.py::render(payload, fields_desc=None, view=None)
  -> list[Row]` — a header row then per-item rows, using
  `Cell`/`Row`/`ColorRole`/`_LEVEL_TO_ROLE`/`title_role` from
  `glances.outputs.curses_renderer_v5`.
- `tests/test_plugin_<name>_v5.py` and
  `tests/test_plugin_<name>_render_curses_v5.py`.

Collection payload shape: `{"data": [...], **metadata, "_levels": {...}}` with
`_levels = {pk_value: {field: {level, prominent}}}`.

## 4. Fetch architecture — decision (Option A)

**`containers` reuses the v4 engine machinery unchanged.** The v4 fetch is what
gives the plugin its performance and cannot be swapped for a v5-native
per-cycle fan-out without regressing:

- Each engine (`DockerExtension`/`PodmanExtension`/`LxdExtension`) keeps its
  `Protocol` contract (`stop()`, `update(all_tag) -> tuple[dict, list[dict]]`),
  its module-level `disable_plugin_<engine>` import-error flag, and its inner
  `*StatsFetcher` classes.
- **Streaming threads stay**: `ThreadedIterableStreamer` continuously pulls
  `container.stats(stream=True)` per container in a background thread; the
  update cycle only reads the **latest cached snapshot under lock — O(1),
  non-blocking**. No N-blocking-calls-per-cycle.
- **`ThreadPoolExecutor(max_workers=6)`** for the concurrent `reload()` inspect
  (issue #3559) stays.
- **Rate computation** (cpu% via `system_cpu_delta`, io/net cumulative-byte
  deltas over `time_since_update`) stays inside the `StatsFetcher` classes —
  it is **not** re-expressed as base-class `rate: True` fields (the base rate
  mechanism cannot supply Docker's host-jiffies `system_cpu_delta`).
- The v5 `_grab_stats()` is a thin async wrapper: `await
  asyncio.to_thread(self._update_watchers)` where `_update_watchers` runs the
  v4 flatten/merge/inject-engine/sort pipeline over `self.watchers`.

**Considered and rejected:** (B) plain per-cycle snapshot with base
`rate: True` — regresses cpu% semantics (loses `system_cpu_delta`) and
reintroduces N blocking calls/cycle; (C) engines-without-persistent-threads
hybrid — keeps exact rates but still N blocking calls/cycle, perf "to be
validated" = risk. Both discarded to honour the non-regression constraint.

**`vms` engines** (multipass, virsh) are synchronous CLI callers with no
threads; they are reused as-is via `asyncio.to_thread`. The virsh
CVE-2026-46606 hardening (`_run_virsh` with `shell=False` + explicit arg
lists) is inherited unchanged.

## 5. New base_v5 mechanisms required by the port

The port needs two small, independent extension points on
`GlancesPluginBase`. Both are generic (default behaviour unchanged for every
other plugin) and delivered as the first tasks of the `containers` plan.

### 5.1 Plugin `stop()` teardown (required by Option A)

`GlancesPluginBase` (`base_v5.py`) currently has **no teardown hook**, and
`GlancesScheduler.stop()` (`scheduler_v5.py:157`) only cancels the per-plugin
loop tasks — it never lets a plugin release resources. Option A's streaming
threads would otherwise leak on shutdown. Minimal addition:

1. **`GlancesPluginBase.stop(self) -> None`** — a **no-op by default**
   (extension point; future resource-holding plugins reuse it).
2. **`GlancesScheduler.stop()`** — after cancelling and draining the loop
   tasks, call `entry.plugin.stop()` for every registered plugin, each guarded
   (`try/except` + `logger.warning`) so one failing teardown cannot block the
   rest.
3. **`containers` overrides `stop()`** to iterate `self.watchers` and call each
   `watcher.stop()`; because `watcher.stop()` joins background threads
   (blocking), the override runs them via `asyncio.to_thread`. **`vms` keeps
   the base no-op** (no threads).

This is a base-level extension point, not a `containers`-specific hack — it
matches the "extensibility without touching the core repeatedly" principle and
is delivered as **the first task of the `containers` plan** (prerequisite for
A), with its own scheduler test (`stop()` is called on shutdown) before the
plugin work.

### 5.2 `threshold_field` schema alias (config non-regression)

The base resolves thresholds **strictly by field name**: for a watched field
`f`, `read_thresholds(field=f)` looks up `f_careful` / `f_warning` /
`f_critical` (plus per-pk `<pk>_f_<level>` and, non-strict, bare `<level>`).

But v4 `containers` decouples the **value field** from the **threshold key
prefix**: the values live under `cpu_percent` / `memory_usage`, while
`update_views` reads thresholds via `get_alert(header='cpu'|'mem')`, i.e. from
the shipped config keys `cpu_careful` / `mem_warning` / `<name>_cpu_critical`.
Ported naively (field `cpu_percent` → base looks up `cpu_percent_careful`),
**every existing `[containers] cpu_careful=…` config would silently stop being
read** — a threshold non-regression.

**Fix** — add an optional field-schema key **`threshold_field`**: when present,
the base passes it to `read_thresholds` / `read_thresholds_categorical` /
`_scan_pk_override_fields` **in place of the field name** for config-key
resolution (value lookup still uses the real field name). Default = the field
name, so every other plugin is unaffected. This preserves **both** the v4 API
field names (`cpu_percent` / `memory_usage`) **and** the v4 config keys
(`cpu_*` / `mem_*`, global and per-container).

Touched methods in `base_v5.py` (all currently key on `field_name`):
`_precompute_plugin_thresholds`, `_resolve_numeric_thresholds`,
`_resolve_categorical_mapping`, `_scan_pk_override_fields` — each reads the
schema's `threshold_field` (falling back to `field_name`) for the config-key
prefix. `containers` declares `threshold_field: "cpu"` on `cpu_percent` and
`threshold_field: "mem"` on `memory_usage`. Unit-tested in isolation
(alias-prefixed keys resolve; per-pk `<name>_cpu_warning` resolves; absence of
the key preserves the field-name default for existing plugins).

Delivered as the **second base task of the `containers` plan** (before the
model), independently reviewable from the `stop()` hook.

## 6. Per-plugin design

### 6.1 containers (collection)

- **Engines**: reuse v4 `docker`/`podman`/`lxd` extension modules verbatim.
  `self.watchers` built in `__init__` gated on `disable_plugin_<engine>`
  (docker → `DockerExtension()`, podman → `PodmanExtension(podman_sock=…)`,
  lxd → `LxdExtension(poll_interval=…)`). Missing SDK → engine skipped, plugin
  still valid (empty if all skipped).
- **primary_key** = `name` (mirror v4 `get_key()`).
- **fields_description** (from v4): `name`(pk), `id`, `image`, `status`,
  `created`, `command`, `cpu_percent`, `cpu_limit`, `memory_usage`,
  `memory_usage_no_cache`, `memory_percent`, `memory_inactive_file`,
  `memory_limit`, `io_rx`, `io_wx`, `network_rx`, `network_tx`, `ports`,
  `uptime`, `engine`, `pod_name`, `pod_id`. The engines' internal working
  dicts (`cpu`/`memory`/`io`/`network`, `key`, `memory_percent`) are kept for
  computation and excluded from export (v4 `export_exclude_list`); the flat v5
  field filter keeps only declared top-level keys.
- **Watched fields / levels** (`EMITS_ALERTS = True`, mirror v4 `update_views`):
  - `cpu_percent`: `watched`, `watch_direction: "high"`,
    **`threshold_field: "cpu"`** (§5.2). Thresholds from `[containers]
    cpu_careful/cpu_warning/cpu_critical`; **per-container override**
    `<name>_cpu_careful/…` resolved by the base's per-primary-key mechanism via
    the `cpu` alias prefix.
  - **Memory — three distinct surfaces** (do NOT collapse; preserves v4 export
    parity). The base's `normalize_by` was rejected: it yields a fraction
    (`usage/limit ∈ [0,1]`) while the shipped `mem_*` thresholds are percents
    and v4 alerts on the percent → would misfire ×100.
    - `memory_usage` (**export**): the exact value v4 stores in its flat
      `memory_usage` field — unchanged export semantics, no dashboard
      regression.
    - `memory_usage_no_cache` (**display**): `usage − inactive_file` (v4
      `memory_usage_no_cache`), shown in the MEM column, `/MAX = memory_limit`.
    - `memory_percent` (**alert**): `watched`, `watch_direction: "high"`,
      **`threshold_field: "mem"`** (§5.2), computed
      `= memory_usage_no_cache / memory_limit * 100`. Thresholds from
      `[containers] mem_careful/mem_warning/mem_critical` + per-container
      `<name>_mem_careful/…` via the `mem` alias prefix (exact v4
      `get_alert(…, maximum=memory.limit)` parity). `memory_inactive_file` is
      kept for v4 API parity.
  - Value used for memory is `usage - inactive_file` (v4
    `memory_usage_no_cache`), computed at grab time.
- **Sort — processlist-aligned** (maintainer decision 2026-07-14): the model
  pre-sorts `data` via `glances.processes.glances_processes.sort_key` (v4
  `sort_docker_stats` → `sort_stats_processes`), and the renderer reads the
  global `view["sort_key"]` and underlines the matching column via a
  header→sort-key map (mirrors `processlist`'s `_HEADER_SORT_KEY`). The process
  sort key is **dynamic by default** (`auto` → cpu/mem per load, resolved
  before the getter returns) — do NOT hardcode a static default that overrides
  it. The active sort column is NOT passed via payload metadata (only
  `disable_stats`/`max_name_size` are). `vms` uses the identical mechanism.
- **Renderer** (mirror v4 `msg_curse`, MAIN column, responsive full-width):
  columns, each gated by `[containers] disable_stats`
  (`name,status,uptime,cpu,mem,diskio,networkio,ports,command`): **Engine**
  (only if >1 engine present), **Pod** (only if any container carries a
  `pod_name`), **Name** (width `max_name_size`, default 20), **Status**,
  **Uptime**, **CPU%**, **MEM/MAX**, **IOR/s IOW/s**, **Rx/s Tx/s** (bits
  unless `--byte`), **Ports**, **Command**. cpu/mem cell colour from
  `_levels`; **status** colour via a `container_alert(status)` mapping
  (running/healthy→OK, dead/unhealthy→CRITICAL/ERROR, created/exited→WARNING,
  paused/restarting→CAREFUL, else INFO) → `ColorRole`. Active sort column
  header underlined.
- **`stop()` override** (see §5).
- **Config** (`[containers]`): `disable`, `show=`/`hide=` (regex filters via
  base), `max_name_size` (20), `disable_stats` (CSV), `all` (show stopped),
  `podman_sock`, thresholds `cpu_*`/`mem_*` (global + per-container). All
  already shipped in v4 conf — no new keys.

### 6.2 vms (collection)

- **Engines**: reuse v4 `multipass` (`/snap/bin/multipass`) and `virsh`
  (`/usr/bin/virsh`) CLI extensions verbatim, via `asyncio.to_thread`.
  Availability = binary exists + executable (`import_<engine>_error_tag`).
  virsh CVE-2026-46606 hardening inherited.
- **primary_key** = `name` (mirror v4 `get_key()`).
- **fields_description** (from v4): `name`(pk), `id`, `release`, `status`,
  `cpu_count`, `cpu_time`, `memory_usage`, `memory_total`, `load_1min`,
  `load_5min`, `load_15min`, `ipv4`, `engine`, `engine_version`. v4 derives
  `cpu_time_rate_per_sec` via `@_manage_rate`; the v5 model declares
  `cpu_time` with `rate: True` so the base derives the per-second rate.
- **Levels**: none. **`EMITS_ALERTS = False`** — mirrors v4's *actual*
  behaviour: v4 `msg_curse` reads cpu/mem/load decorations but `update_views`
  never populates them, so VM alerts never fire. No threshold config exists in
  `[vms]`; adding one would be a speculative feature (YAGNI). Status colour is
  a rendering concern and stays.
- **Sort**: model pre-sorts via the process sort key (v4 `sort_vm_stats`),
  same `view["sort_key"]` underline pattern as `containers`/`processlist`.
- **Renderer** (mirror v4 `msg_curse`, MAIN column, responsive full-width):
  **Engine** (only if >1 engine), **Name** (`max_name_size`), **Status**,
  **Core** (`cpu_count`), **CPU%** (`cpu_time` rate), **MEM/MAX**, **LOAD
  1/5/15min** (only if `load_1min is not None`), **Release**. Status colour via
  a `vm_alert(status)` mapping (running→OK, starting/restarting/delayed
  shutdown→WARNING, else INFO) → `ColorRole`. Active sort column underlined.
- **`stop()`**: base no-op (no threads).
- **Config** (`[vms]`): `disable` (default `True` — plugin OFF by default,
  preserved), `max_name_size` (20), `all`. No threshold keys. No new keys.

## 7. Testing strategy

Per plugin: identity/fields tests; grab-merge + partial-failure (one engine
raises → others still returned, plugin non-empty); renderer layout (header +
rows) with column-visibility toggles; sort-column underline.

- **base `stop()` hook** (containers plan, Task 1): base default is a no-op;
  `scheduler.stop()` calls `plugin.stop()` for every plugin; a plugin whose
  `stop()` raises does not prevent the others' teardown.
- **containers**: engine flatten/merge + engine injection; `all` tag; show/hide
  filter; `memory_usage_no_cache` computation; cpu/mem level mapping incl.
  per-container threshold override; `disable_stats` column hiding; Engine/Pod
  conditional columns (1 vs >1 engine, pod vs no-pod); status→colour mapping;
  sort underline; `stop()` override joins/stops each watcher; empty when no
  engine available.
- **vms**: multipass + virsh parse/merge; `cpu_time` rate derivation
  (`rate: True`); load columns present only when `load_1min` non-None;
  status→colour mapping; `EMITS_ALERTS is False`; disabled-by-default honoured;
  empty when no binary present.

## 8. Deliberate divergences from v4 (documented)

1. **`stop()` teardown hook** added to `GlancesPluginBase` + wired into
   `GlancesScheduler.stop()`. New base extension point required by the async
   port of `containers`' streaming threads; harmless no-op for every other
   plugin. (§5.1)
1b. **`threshold_field` schema alias** added to `GlancesPluginBase` threshold
   resolution — decouples the config-key prefix from the value-field name so
   the shipped `[containers] cpu_*`/`mem_*` keys keep working with
   `cpu_percent`/`memory_usage` fields. Defaults to the field name → no change
   for any other plugin. (§5.2)
2. **`containers` fetch runs under `asyncio.to_thread`** (the streaming
   threads and thread-pool themselves are unchanged v4 code); this is an
   integration wrapper, not a behavioural change.
3. **`vms` `EMITS_ALERTS = False`** makes explicit what v4 already did in
   practice (dead alert decorations) — no functional change, removes the
   dead read path.

## 9. Accepted limitations / out of scope

- **Cross-engine `name` collision**: `primary_key = name`; if two engines
  expose the same container/VM name, their `_levels` entries collide (last
  wins). This is **v4 parity** (v4 keys `self.views` by `name` too) — accepted,
  documented, not fixed in G6A.
- **No shared base** between `containers` and `vms`: v4 shares patterns but no
  code; two consumers do not justify a speculative common base (YAGNI). Each
  plugin is self-contained.
- SNMP input method (never implemented in v4 for either plugin).
- LXD/podman pod nuances beyond v4 behaviour; no new engine support.
- Any `NEWS.rst` entry (maintainer, release-time).

## 10. Plan decomposition

- **Plan 1 — `containers`** (`docs/superpowers/plans/2026-07-14-glances-v5-g6a-containers.md`):
  Task 1 = base `stop()` hook + scheduler wiring + tests (§5.1); Task 2 = base
  `threshold_field` alias + tests (§5.2); both prerequisites, independently
  reviewable. Then model (engine reuse, fields with `threshold_field` aliases,
  levels via `normalize_by`, memory computation, sort), `stop()` override,
  renderer (full column set + `disable_stats` + Engine/Pod conditionals +
  status colour + sort underline), `docs/aoa/containers.rst`.
- **Plan 2 — `vms`** (`docs/superpowers/plans/2026-07-14-glances-v5-g6a-vms.md`):
  model (CLI engine reuse, fields, `cpu_time` rate, `EMITS_ALERTS=False`,
  sort), renderer (columns incl. conditional LOAD + status colour + sort
  underline), `docs/aoa/vms.rst`.

Each plan updates the plugin's `docs/aoa/*.rst` doc.

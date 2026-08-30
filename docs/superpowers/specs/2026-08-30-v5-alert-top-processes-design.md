# Glances v5 — Top processes on alerts

Design document.
Date: 2026-08-30.
Branch: `develop-v5`.

Follow-up to `2026-08-01-glances-v5-g7-alert-design.md` §10.1, which deferred
this feature as option **[B]**.

## 1. Problem

Neither the v5 TUI alert block nor `GET /api/5/alert` carries the top
processes associated with an alert. A user seeing `Cpu total  CRITICAL` has
no way, from the alert itself, to learn *what* was consuming the CPU.

v4 has the feature (`GlancesEvent.top`, rendered by
`glances/plugins/alert/__init__.py:181`); v5 dropped it when G7 rebuilt the
block as an incident grid.

## 2. Current state

### 2.1 v4

`GlancesEvent` (`glances/event.py`) carries `top: list` and `sort: str`.
`GlancesEvent.update()` accumulates, **only while `state == "CRITICAL"`**, a
`Counter`-like `top_dict` over the 6 highest processes of the current cycle,
and exposes the 3 most frequent names. Any non-critical cycle **wipes** the
accumulator. The sort key comes from `EventsList.get_event_sort_key()`:
`MEM*` -> `memory_percent`, `CPU_IOWAIT` -> `io_counters`, everything else
-> `cpu_percent`.

Two v4 behaviours we deliberately do **not** carry over:

- **Empty column on warning.** v5 alerts fire on `warning` and above only
  (`_ALERTABLE_LEVELS`, see `project_v5_alerts_warning_and_above`), so a
  critical-only accumulation would leave the majority of v5 rows blank.
- **Top on unrelated alerts.** v4's `glances_events.add()` is generic
  (`glances/plugins/plugin/model.py:886`), so an `fs` or `sensors` alert also
  received a `cpu_percent`-sorted top 3, which explains nothing.

### 2.2 v5

`GlancesAlerts._build_event()` (`glances/alerts_v5.py:508`) produces
`{ts, plugin, key, field, level, previous_level, value, prominent,
is_initial, hostname}` — no process information at all.

`glances_processes` (the shared v4 process engine) is **already injected**
into `GlancesAlerts` (`glances/main_v5.py:563`) for the auto-sort parity
feature, so the raw material is in place and no new wiring is required.

## 3. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Semantics for a long-running incident | **Accumulated** over the incident's lifetime (v4 `top_dict` model): the top 3 are the most *persistent* processes, not a snapshot |
| 2 | Levels, and de-escalation | Accumulate from **`warning`** upwards; **never reset**, not even on `critical -> warning` |
| 3 | Which alerts | **Allowlist**: `cpu`, `mem`, `memswap`, `load` only, per field |
| 4 | TUI column order | `GLYPH · TIME · DURATION · TARGET · TOP · LEVEL` |
| 5 | Payload shape | `top: [names]` + `top_sort: <sort key>` (v4's `top` + `sort`) |
| 6 | Where the accumulation lives | **In-place mutation** of the incident's opening event, exactly as v4 mutates its `GlancesEvent` |

## 4. Scope declaration — per field, no central table

A new optional key in `fields_description`, declared where the field itself
is declared:

```python
"iowait": {
    ...
    "top_processes_sort": "io_counters",
},
```

`GlancesAlerts` reads
`type(plugin).fields_description.get(field_name, {}).get("top_processes_sort")`.
Absent -> the field never carries a top. No allowlist constant lives in
`alerts_v5.py`; adding a plugin to the feature later touches only that
plugin. `base_v5.py` never validates the schema key set (`schema.get(...)`
throughout), so the new key is inert for every other consumer.

Complete allowlist — 5 fields:

| Plugin | Field | `top_processes_sort` |
|---|---|---|
| `cpu` | `total` | `cpu_percent` |
| `cpu` | `iowait` | `io_counters` |
| `mem` | `percent` | `memory_percent` |
| `memswap` | `percent` | `memory_percent` |
| `load` | `min15` | `cpu_percent` |

Explicitly **not** annotated, though they are `watched: True`:
`cpu.system`, `cpu.user`, `cpu.dpc`, `cpu.steal`, `cpu.ctx_switches`,
`load.min5`. Rationale: `cpu.total` and `load.min15` are the aggregate
signals a user reacts to; annotating their components would produce three
near-identical top-3 rows for a single episode of CPU pressure, and
`load.min5`/`min15` would double every load incident.

Consequence on cost: at most **two** distinct sort keys per plugin cycle
(`cpu`), one for the other three plugins.

## 5. Engine — the accumulator

### 5.1 State

`_AlertState` gains three fields, all `None` while the tuple is `ok`:

```python
top_counter: Counter[str] | None = None
top_sort: str | None = None
top_event: dict[str, Any] | None = None   # the incident's opening event
```

`top_event` is a reference to the dict already appended to `_history`.
Mutating it in place is the v4 model: `EventsList` holds `GlancesEvent`
objects and `update()` rewrites `top` on the live object every cycle.

### 5.2 Lifecycle

- **Incident opens** (transition to non-`ok` where `state.committed_since is
  None`): `top_counter = Counter()`, `top_event = <the event just built>`,
  `top_sort = <the field's declared key>`.
- **Escalation** (`warning -> critical`): nothing is reset; `top_event`
  keeps pointing at the *opening* event. The escalation event itself carries
  no `top`.
- **Every ingest cycle while `committed_level != "ok"`** and the field
  declares a sort key: accumulate, then rewrite the opening event.
- **Incident closes** (`-> ok`): `top_counter = top_sort = top_event = None`.
  The last accumulated value stays frozen in the opening event dict, which is
  what both the API and `_derive_incidents` read for a resolved incident.

### 5.3 Accumulation step

```python
for proc in sort_stats(glances_processes.get_list(), sort_key)[:6]:
    state.top_counter[proc["name"]] += 1
state.top_event["top"] = [name for name, _ in state.top_counter.most_common(3)]
state.top_event["top_sort"] = sort_key
```

- Depth 6 in / 3 out is v4's, kept hard-coded. No new config key.
- `Counter.most_common(3)` is exactly equivalent to v4's
  `sorted(items, key=count, reverse=True)[0:3]` — `Counter` preserves
  insertion order and Python's sort is stable, so ties break identically —
  and it runs in O(n) rather than O(n log n).
- `sort_stats(list, key)` is called positionally, matching v4, so
  `sorted_by_secondary` keeps its `memory_percent` default.
- The counter is **bounded**: once it holds more than
  `_TOP_COUNTER_MAX_KEYS = 128` distinct names it is trimmed to the
  `_TOP_COUNTER_TRIM_TO = 32` most common. v4's per-cycle wipe was accidentally
  this bound; the "never reset" decision (§3) removed it, and a multi-day
  incident on a host with variable-named workers (`kworker/uNN:M`, CI runners)
  would otherwise grow the dict without limit. Trimming by FREQUENCY, not by
  insertion order, is what makes it safe: a genuinely persistent name is by
  construction always among the most common, so it is never evicted — only the
  long tail is, which is exactly what "most persistent" wants to discard.
  Rebinding the counter here is safe only because `get_ongoing_top()` no longer
  reads it (§5.4); do not reintroduce a counter read.
- The sorted list is computed **once per ingest call per distinct sort key**,
  in a dict built lazily inside `ingest_plugin`. No active alert on an
  annotated field -> no sort at all.
- `glances_processes.get_list()` returns the cached list maintained by the
  `processcount` plugin (`glances/plugins/processcount/model_v5.py:71`). If
  the process plugins are disabled the list is empty, the counter does not
  move, and no `top` key is ever written. That is the correct degradation:
  the field is absent, not empty.

### 5.4 New public accessor

```python
def get_ongoing_top(self) -> dict[tuple[str, str | None, str], dict[str, Any]]:
```

Twin of `get_ongoing_since()`: for every currently non-`ok` tuple with a
non-empty accumulation, returns `{"top": [...], "top_sort": "..."}`.

It exists for the same reason `get_ongoing_since()` does — `_history` is a
bounded ring buffer, so a long-running incident eventually loses its own
opening event, and with it the only copy of its `top` in the history. The
engine's `_state` is unbounded and remains the authority.

Read-only, allocates a fresh dict, never called from the ingest path.

## 6. Payload, REST and MCP

Two new keys on the incident's opening event:

```json
{
  "ts": "2026-08-30T14:02:11+00:00",
  "plugin": "cpu", "key": null, "field": "total",
  "level": "critical", "previous_level": "warning",
  "value": 96.4, "prominent": true, "is_initial": false,
  "hostname": "myhost",
  "top": ["python3", "chrome", "node"],
  "top_sort": "cpu_percent"
}
```

The keys are **absent**, never `null` and never `[]`, for events outside the
allowlist. Absence here is structural (this field can never have a top), not
a variable value — which is why the `project_v5_rate_fields_none` rule
("rate fields are `None`, never absent") does not apply: consumers must
branch on presence, and a renderer that emitted an empty column for every
`fs` alert would be lying about the schema.

No route changes. `GET /api/5/alert` (`glances/routes_v5.py:142`) and the
synthetic MCP `alert` plugin (`glances/outputs/mcp_adapter_v5.py:204`) both
return `get_history()` and inherit the fields for free.

## 7. TUI — grid geometry

### 7.1 Column

New top-processes column between `TARGET` and `LEVEL`, so `LEVEL` stays the
right-aligned anchor. Its header reads `TOP PROCESSES` — plural, because the
column shows three, and the same wording v4 used. At 13 characters it always
fits: the column's floor is `_ALERT_MIN_TOP = 22`.

```
  TIME      DURATION  TARGET       TOP PROCESSES                         LEVEL
● 14:02:11     4m12s  Cpu total    python3, chrome, node              CRITICAL
● 13:58:03    12m20s  Mem          chrome, python3, code               WARNING
○ 11:40:55     2m01s  Fs /                                             WARNING
```

- Left aligned, and **elastic**: see §7.2 — `TOP` absorbs the block's free
  width so that its text begins immediately after `TARGET`'s content.
- Content: `", ".join(incident["top"])`, fitted with `_fit_text(...,
  ellipsis="…" if unicode_ok else ".")` — same treatment as `TARGET`.
- Neutral colour (no `ColorRole`), like `TIME` and `DURATION`. The row's
  severity is already carried by the glyph and `LEVEL`.
- An incident with no top renders a blank cell of the same width, so the grid
  stays aligned.

**The column is data-conditional.** It is emitted only when at least one
VISIBLE incident carries a non-empty `top`. A host whose only alerts are
`fs` or `sensors` ones therefore never pays 23 columns for an empty `TOP`
header, and — critically — every existing caller and test that renders
events without a `top` key produces byte-identical output. This is what
makes the change a strict addition rather than a re-layout.

### 7.2 Which column is elastic, and the shrink ladder

`TARGET` used to be the only elastic column, which on a wide block padded it
to its full share and pushed `TOP` sixty columns away from the target it
describes. The elasticity therefore sits on **`TOP`**:

- `TARGET` takes the natural width of its content — the longest visible
  target — floored at `_ALERT_MIN_TARGET = 12` and never so wide that `TOP`
  would fall below its own floor.
- `TOP`, being left aligned, takes the remainder, so its text starts right
  after `TARGET` and the slack lands between `TOP` and the right-aligned
  `LEVEL`.

The consequence to accept: on a narrow block a long target no longer gets the
whole remainder. `TARGET` is capped at `pair - _ALERT_MIN_TOP` and truncates
there, while `TOP` is held at its 22-column floor. Below 66 the `TOP` column
drops entirely and `TARGET` recovers the full elastic width it has today, so
the narrow end of the ladder is unchanged.

A useful property of the formula: when the longest visible target is already
wide, `min(natural_target, pair - _ALERT_MIN_TOP)` saturates and the layout
degenerates to exactly the previous one. The two differ only when `TARGET` is
short — which is precisely the case the change is about.

`TOP` is still the **first column to drop entirely**. Every pre-existing
threshold is untouched, so no terminal that renders the block correctly today
changes behaviour.

```python
_ALERT_MIN_TOP = 22  # a floor now, not a fixed width
_ALERT_W_WITH_TOP = _ALERT_W_WITH_LEVEL + 1 + _ALERT_MIN_TOP  # 66
```

| Block width | Columns |
|---|---|
| >= 66 | GLYPH · TIME · DURATION · TARGET · TOP · LEVEL (only if some visible incident has a top) |
| >= 43 | GLYPH · TIME · DURATION · TARGET · LEVEL (pre-feature behaviour) |
| >= 34 | GLYPH · TIME · DURATION · TARGET |
| < 34 | GLYPH · TIME · TARGET |

Arithmetic. The painter puts one space between adjacent non-glued cells.
With `TOP` shown there are 6 cells (GLYPH 1, TIME 9, DURATION 9, TARGET *t*,
TOP *p*, LEVEL 8) and 5 separators, so `1+9+9+8+5 = 32` fixed columns and
`t + p = width - 32`. Then:

```
pair         = width - 32
target_width = max(_ALERT_MIN_TARGET, min(natural_target, pair - _ALERT_MIN_TOP))
top_width    = pair - target_width
```

At `width = 66` with a `Cpu total` target: `pair = 34`, `target_width = 12`,
`top_width = 22` — both floors met exactly, which is where the 66 comes from.

Without `TOP` there are 5 cells and 4 separators, `t = width - 31`, which is
the pre-feature formula, unchanged.

`width is None` (export, direct callers, tests) sizes BOTH columns to their
natural content, as before.

### 7.3 Vertical budget — unchanged

One row per incident is preserved (design G7 §5.4), so
`_alert_block_height()` and `plan_right_column()` need no change and the
shrink ladder in `glances/outputs/curses_renderer_v5.py:1067` keeps its
current step costs.

## 8. Plumbing

Modelled line for line on the existing `ongoing_since` path:

1. `glances_curses_v5.py:546` — `ongoing_top = self.alerts.get_ongoing_top()
   if self.alerts is not None else {}`.
2. `build_frame(..., alerts_ongoing_top=ongoing_top)`.
3. `_derive_incidents(history, ongoing, ongoing_since, ongoing_top)`:
   - the opening event seeds `incident["top"]` / `incident["top_sort"]`;
   - for `ongoing` incidents, `ongoing_top` overrides (the engine is the
     authority, per §5.4);
   - incidents synthesized from `ongoing` alone (no surviving history) get
     their top from `ongoing_top` too.
4. `render_alert_block()` reads `incident.get("top")`.

## 9. Cost

The only work added to the hot path is, per ingest call of an annotated
plugin **with at least one active alert on an annotated field**:

- one `sort_stats()` over the cached process list per distinct sort key
  (1 for `mem`/`memswap`/`load`, at most 2 for `cpu`);
- 6 `Counter` increments and one `most_common(3)` per active incident.

The memoisation cache is local to one `ingest_plugin` call, so it does **not**
span plugins. `mem` and `memswap` both declare `memory_percent`, and
`cpu.total` and `load.min15` both declare `cpu_percent`, so a host under
simultaneous CPU and memory pressure performs **5 sorts per full refresh
cycle**, two pairs of which are strictly redundant — not "one sort every 2 s".

Measured: `sort_stats` costs 0.100 ms at 580 processes and 0.249 ms at 1200,
so the worst case is ~0.5 ms per 2 s cycle, about **0.025 % of one core**.
Immaterial, and not worth a cross-plugin cache — but the real figure belongs
here rather than the optimistic one.

The quiet path (no annotated field in alert) performs **zero** process
sorts and zero `get_list()` calls: `_accumulate_top` is only reached for a
tuple whose committed level is non-`ok` AND whose field declared a sort key.
It does allocate one empty dict per `ingest_plugin` call for the cache
(~40 ns). Both invariants — lazy sampling and per-sort-key memoisation — are
pinned by a test, because this cost argument is the whole reason the design
was accepted.

## 10. Tests

`tests/test_alerts_v5.py`:

- accumulation grows across cycles and the top 3 reflect persistence, not the
  last sample;
- `critical -> warning` does **not** reset the counter;
- `-> ok` freezes the value in the opening event and releases the state;
- the escalation event carries no `top`;
- a non-annotated field (`fs`, `sensors`) never receives `top` / `top_sort`;
- empty process list -> no key written, no exception;
- `get_ongoing_top()` reports only active tuples and returns a fresh dict.

Renderer tests:

- column order and offsets at a wide width;
- `TOP` dropped at `width=65`, present at `width=66`;
- blank, correctly sized cell for an incident with no top;
- `ongoing_top` overrides a stale value from the history;
- `unicode_ok=False` truncates with `.` and never emits a non-ASCII byte.

## 11. Out of scope

- **Web UI** (`glances/outputs/static/js/components/plugin-alert.vue`) — not
  touched.
- **Config key** for the 6-in / 3-out depth — hard-coded, as in v4.
- **`min` / `avg` / `max` per incident** — the other half of G7 §10.1 option
  [B]. Independent, and not addressed here.
- **`/api/5/alert` returning incidents instead of transitions** — the v4
  payload shape. Considered and rejected as a breaking change beyond this
  request; revisit separately.

## 12. Regression watch

- `fields_description` is exposed by the plugin description surface; a new
  schema key appears there. Verify it is inert for the REST description
  route and the MCP tool schemas.
- `_derive_incidents` is called by direct callers (export, tests) with
  `ongoing_top=None`; that path must keep working and simply read the
  history.
- Mutating an event already appended to `_history` means a `GET /api/5/alert`
  served concurrently with an ingest can observe a top mid-update. The value
  is a freshly built list assigned atomically, so a reader sees either the
  previous or the new list, never a partial one.

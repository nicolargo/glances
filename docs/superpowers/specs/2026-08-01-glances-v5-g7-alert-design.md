# Glances v5 — G7 design (alert presentation)

**Date:** 2026-08-01, revised 2026-08-16
**Phase:** 2, group **G7** (order G0→G1→G2→G3→G4A→G4B→G5→G6A→G6B→G6C→**G7**)
**Status:** design — **approved** (2026-08-16). §4.1 is decided (option **C**),
which makes §10.1 moot for this cycle. §5.6 (incident model), §6.2/§6.3 (the
[A] grid), §6.5 (unicode), §8, §9 and §10.3 are resolved below. Ready for the
plans pass.
**Predecessor:** G6C (amps + irq + cloud + mpp) — **landed** (`f40067c5`).

## 0. Revision log — 2026-08-16

Terminology, fixed once: this document says **MAIN column** where the code
says `frame.right` / `RIGHT_SLOT`. They are the same thing.

The `develop-v5` state of §2 was read at `80167a35`. Two things moved since,
both from the right-column vertical-fit work (`55e68387`):

**0.1** — `alerts_limit` is no longer dead surface. It feeds
`row_budget(view, "alert", alerts_limit)` (`curses_renderer_v5.py:991`) and
acts as the fallback used when `view["row_budget"]` is absent (export, tests,
direct renderer calls). The effective cap is the dynamic budget, whose
nominal is `_NOMINAL_ALERTS = 10`. This retires §8 point 2 — see §8.

**0.2** — Line references in §2 have drifted (`render_alert_block` is now
`:521`). They are indicative; re-read before editing.

Still true as written: `[alerts]` is **absent** from `conf/glances.conf`, and
`glances_curses_v5.py:529` still does not pass `alerts_limit`.

One assumption in §6.5 turned out to be **false** and is resolved there: the
v5 renderer has no unicode flag, and no `render_curses_v5.py` emits a single
non-ASCII character today.

## 1. Goal & scope

G7 is the last plugin slot of Phase 2. It closes the alert surface: the block
rendered at the bottom of the MAIN column, answering *what happened* on this
host.

**G7 is not a plugin port.** Unlike every other Phase 2 group, there is
nothing to migrate: v5 never had an `alert` plugin. `glances/plugins/alert/`
contains only the v4 `__init__.py`, and it is not reachable from the v5 entry
point. The alert block is already rendered in v5 — synthesized directly from
the engine by the renderer (§2.2). G7 therefore *redesigns an existing v5
surface* rather than porting a v4 one.

This changes the shape of the group and must be reflected in the plans pass:
no `model_v5.py`, no `fields_description`, no scheduler registration, no
`_grab_stats`. The per-PR template of the Phase 2 spec §5 does not apply
verbatim.

## 2. Current state on `develop-v5`

Read before designing anything. Line references are `develop-v5` at
`80167a35`.

### 2.1 Engine — `glances/alerts_v5.py`

`GlancesAlerts` is a **transition** state machine, not an episode recorder.

- Per-`(plugin, key, field)` hysteresis state (`_AlertState`:
  `committed_level`, `pending_level`, `pending_since`, `has_committed`).
- A level change must hold for `min_duration_seconds` before it commits;
  only the commit produces a `_Transition` and an event.
- `_ALERTABLE_LEVELS = {"warning", "critical"}`. `_alert_level()` collapses
  every sub-warning level (notably `careful`) to `ok`, so `careful` colours
  the owning plugin's cell but never enters the history. **This matches v4**,
  which logs `WARNING`/`CRITICAL` only.
- Per-plugin warmup: ingestion is skipped for the first `warmup_cycles`
  (default 3) cycles of each plugin.
- History is a `deque(maxlen=history_size)` of **flat dicts** built by
  `_build_event()` (`alerts_v5.py:453`):

  ```python
  {"ts", "plugin", "key", "field", "level", "previous_level", "value", "prominent", "is_initial", "hostname"}
  ```

- `get_history()` returns it as a list, most-recent-**last**.
- `is_initializing()` — `True` only while no plugin has cleared warmup.

What the engine does **not** have: no `begin`/`end`, no episode identity, no
sample accumulation (`sum`/`count`/`min`/`max`), no top-process capture, no
coalescing window, no `clean()`.

### 2.2 Rendering — `glances/outputs/curses_renderer_v5.py`

`render_alert_block()` (`:517`) returns `list[Row]`:

- Header row: `ALERT (n ongoing / m total)`.
- Empty history collapses to a **single** header-styled line:
  `ALERT (initializing)` or `ALERT (no alert detected)`.
- *Ongoing* = the most-recent event per `(plugin, key, field)` tuple whose
  `level != "ok"`. Older events for the same tuple are superseded.
- Each row: `ts` · `plugin[key]` · `field` · `previous → level`, the level
  cell coloured from `_LEVEL_TO_ROLE` and carrying `prominent`.
  `is_initial` events show the bare level instead of a misleading arrow.
- Ongoing rows are suffixed `(ongoing for <duration>)`, the duration being
  `str(timedelta)` — `0:02:04`.
- Rows are `history[-limit:]` reversed: newest first, insertion order.

Placement: `build_frame()` **unconditionally appends** the block to
`frame.right` after the slot sort (`:782`). The `"alert"` entry in
`RIGHT_SLOT` (`:82`) is therefore inert — no discovered plugin carries that
name. Any G7 change to placement must touch the append, not the tuple.

Emission primitives in v5 are `Row` / `Cell` / `ColorRole` — **not** v4's
`curse_add_line` / `curse_new_line`.

### 2.3 REST — `glances/routes_v5.py:122`

`GET /api/5/alert` returns `alerts.get_history()` raw. No plugin, no
`fields_description`, no `/info` sibling. Any event-shape change is a
**breaking API change** on this route.

### 2.4 Configuration

Section `[alerts]`, read in `GlancesAlerts.__init__`:

| Key | Default | Effect |
|---|---|---|
| `min_duration_seconds` | `_DEFAULT_MIN_DURATION_SECONDS` | Debounce before a level commits |
| `history_size` | `_DEFAULT_HISTORY_SIZE` | `deque` bound |
| `warmup_cycles` | 3 | Cycles skipped per plugin at startup |

**None of these three keys exist in `conf/glances.conf`.** They are
code-defaults only. Compare v4's documented `[alert]` section
(`max_events` / `min_duration` / `min_interval`) — the v5 section is
undocumented and its names do not overlap.

Note the semantic drift on the shared word: v4 `min_duration` *discards a
finished event shorter than the threshold*; v5 `min_duration_seconds`
*debounces a transition before it commits*. Same intent (suppress flapping),
different mechanism, different observable behaviour.

The renderer's `alerts_limit` parameter (default 10) is still never passed by
`glances_curses_v5.py`, but it is no longer a hardcoded cap — see §0.1.

### 2.5 Key bindings

`_HOTKEYS` (`glances_curses_v5.py:136`) binds
`a c m i t p u o 1 4 / j h q`. **`w` and `x` are both free.** There is no
history-clearing action of any kind in v5.

### 2.6 v4 reference behaviours (parity baseline)

Confirmed by reading `glances/plugins/alert/__init__.py`,
`glances/events_list.py`, `glances/event.py`. These are the v4 semantics the
redesign was originally written against; they are the parity target, not the
current v5 state:

- `state` is monotonic — `GlancesEvent.update()` assigns `self.state` only on
  `CRITICAL`, so an event that reached `CRITICAL` never falls back.
- `avg` is computed over above-threshold samples only; the `OK|CAREFUL`
  branch closes the event without touching `sum` / `count`.
- Episode coalescing already exists and is **on by default**:
  `__event_exist()` matches a finished event when
  `event_time - end < min_interval` (6 s) and reopens it, preserving `begin`.
- `min_duration` (6 s) discards events shorter than the threshold at close.

## 3. Problems to fix

The original critique targeted v4's `msg_curse()`. Re-evaluated against the
**v5** renderer of §2.2, it splits in two.

### 3.1 Still true in v5

1. **The line is a sentence, not a record.** `previous → level`,
   `(ongoing for 0:02:04)` and the `plugin[key]` target all have variable
   width, so no column can align. Scanning the block requires reading it.
2. **The level text duplicates the colour.** `warning → critical` restates
   what `_LEVEL_TO_ROLE` already encodes.
3. **`str(timedelta)` is the wrong duration format.** `0:02:04` costs 6–8
   columns and reads as a clock, not an elapsed time.
4. **Truncation is uncontrolled.** `render_alert_block` emits cells with no
   width budget; the frame fitter cuts wherever it lands.
5. **Sorting is insertion order** (newest first). A long-running ongoing
   event sinks below newer resolved ones and can fall outside the 10-row
   window — precisely the event that must stay visible.
6. **Resolution is invisible.** v5 records the `→ ok` transition as just
   another event, so a resolved condition occupies a row indistinguishable
   in structure from an active one, and the same incident consumes two rows.

### 3.2 v4-only — do not carry over

- "`WARNING on` duplicates the colour" — v5 already dropped that phrasing.
- "Coalescing is silent" — v5 has **no coalescing at all** (§2.1). The v5
  problem is the opposite: every transition is a separate row.

## 4. The blocking gap

The redesign's centrepiece — a column record carrying `MAX`, `AVG`, `MIN`,
`TOP PROCESSES` and a `×N` episode counter — presupposes an **episode**
model: an object with a start, an end, accumulated samples and a captured
process snapshot. v4 has one. **v5 has none** (§2.1). v5 knows only that a
field crossed a threshold at an instant.

None of those five columns can be rendered from the current v5 event dict.
`value` is a single sample at commit time — neither the peak nor a mean.

So G7 cannot be presentation-only *and* deliver the redesign. That is the
decision below.

### 4.1 DECIDED (2026-08-16) — G7 scope = option **C**

| Option | Delivers | Cost | Consequence |
|---|---|---|---|
| **A — presentation-only** | §6 grid minus `MAX`/`AVG`/`MIN`/`TOP`/`×N`: glyph, time, duration, source, field, level | renderer only, ~1 plan | Honours the Phase 2 spec §4.1 scope. Fixes 3.1.1–3.1.6. Does **not** deliver §5.1's journal semantics — the block stays a transition log with no peak or mean. |
| **B — engine + presentation** | the full §6 grid | episode aggregation in `alerts_v5.py` + renderer, 2–3 plans, breaks `/api/5/alert` | Delivers the design. Enlarges G7 well beyond "presentation-only" and touches the one module every plugin's alerts flow through — regression surface is the whole product, not one plugin. |
| **C — A now, B as a Phase 2.X follow-up** | A's scope, with §5.5/§7 kept as the recorded target | A's cost now | Ships the legibility fix inside Phase 2 without putting `alerts_v5.py` on the Phase 2 critical path. |

**Decision: C.** The engine work is genuinely valuable but it is not plugin
migration, and Phase 2's goal is v4 feature parity for local monitoring.
Landing B inside the final Phase 2 slot puts a rewrite of the shared alert
engine between the branch and the end of the phase.

Everything marked **[B]** is therefore deferred to Phase 2.X and is recorded
here as the target, not as work to execute now. Everything marked **[A]** is
G7 scope.

One qualification on "renderer only": §5.6 adds a **read-only** accessor to
`alerts_v5.py`. It reads existing state, writes nothing, is not on the ingest
path, and changes neither the event shape nor `/api/5/alert`. It is not the
episode model of B.

## 5. Decisions

### 5.1 The block is a journal, not a gauge — **[A]**

The instantaneous value of a stat is already displayed live by the owning
plugin. The alert block answers "what happened", not "where are we now". It
must never display the current sample; under **[B]** it displays `MAX`, the
peak reached during the episode.

### 5.2 Column record replacing the sentence — **[A]**

Fixed-width columns ordered left to right by decreasing usefulness, so that
narrowing the terminal degrades gracefully. See §6.

### 5.3 Ongoing events pinned to the top — **[A]**

Two-key sort `(is_finished, -begin)`. Ongoing first, reverse-chronological
within each group. Fixes 3.1.5.

"is_finished" is derived per §5.6, from `get_ongoing()` — **not** from the
current renderer's "latest event per tuple" heuristic (§2.2), which cannot
see an incident whose transitions have aged out of the history.

### 5.4 One row per incident — **[A]**

A `→ ok` transition must not occupy its own row. It closes the incident
already open for its tuple, flipping its glyph and freezing its duration.
This is the §3.1.6 fix. Note the distinction §5.6 makes precise: one row per
**incident**, not one row per tuple — a tuple that alerted, recovered and
alerted again contributes two rows.

### 5.5 Episode model and `×N` — **[B]**

`min_interval`-style coalescing does not exist in v5 and **must not be
introduced as a new config key**. If B lands, the coalescing window is a new
`[alerts]` key with a default of 0 — *disabled* — so no existing deployment
changes behaviour. `×N` renders only when `episodes > 1`, i.e. never at the
default.

This inverts the original proposal, which reused v4's `min_interval=6`
default. That default cannot be carried into v5: v5 has never coalesced, so
enabling it by default would silently merge events that deployments and the
REST API currently see as distinct.

### 5.6 Incident derivation — **[A]**

§5.3 and §5.4 both need a notion of *incident* that the engine does not
store. Under [A] the incident is **derived at render time** and never
persisted. This section is the contract; it replaces the renderer's current
"latest event per tuple" heuristic (§2.2).

**Two inputs, two roles.**

1. `GlancesAlerts.get_ongoing()` — **new, read-only**. Returns
   `{(plugin, key, field): committed_level}` restricted to entries whose
   `committed_level != "ok"`, derived from `self._state` (§2.1). It is the
   authority on *what is active right now*.
2. `get_history()` — unchanged. Supplies the *chronology*: when each incident
   opened, and which levels it went through.

Why both: `_state` is unbounded, the history `deque` is not. An incident that
is still active but whose transitions have aged out of the 200-event ring is
invisible in today's block — which is exactly the failure mode §3.1.5 sets
out to fix. Deriving "ongoing" from the history alone would leave that hole
open.

`get_ongoing()` is plumbed to the renderer as an `alerts_ongoing` parameter
of `build_frame`, symmetric with `alerts_history`.

**Segmentation.** Walk the history chronologically. For each
`(plugin, key, field)` tuple: an incident **opens** on the first transition
to a non-`ok` level while no incident is open for that tuple, and **closes**
on the transition to `ok`. `begin` is the opening transition's `ts`; `end` is
the closing transition's `ts`. A tuple may therefore contribute several rows
— one per incident, not one per tuple. Intermediate escalations
(`warning → critical`) mutate the open incident; they never open a new one.

**Level shown = the maximum reached during the incident**, i.e.
`max(levels of the incident's transitions, committed_level if still open)`.
This is v4 parity (§2.6, monotonic `state`). Accepted consequence: an
incident that de-escalated from `critical` to `warning` and is still active
keeps showing `CRITICAL` in the block while the owning plugin's cell shows
the warning colour. The block is a journal of what happened, not a gauge of
where we are (§5.1).

**Accepted loss:** `previous → level` is no longer displayed. That is the
§3.1.2 fix, and it means an escalation is visible only through the final
level. `is_initial` consequently needs no special case — no row shows an
arrow any more, so the §11 guarantee holds by construction.

**Reconciliation, when `get_ongoing()` and the history disagree.** The
authority is `get_ongoing()`; the history only degrades what can be shown:

| Case | Rendered |
|---|---|
| Opening transition present | exact `begin`, exact duration |
| Tuple ongoing, opening transition evicted, later ones survive | duration prefixed `>`, measured from the oldest surviving transition |
| Tuple ongoing, all transitions evicted | `TIME` = `--:--:--`, duration blank, level = `committed_level` |
| Closed incident | never reconciled — the history is complete for it by definition |

The empty-history early return of §2.2 stays as-is: a commit always produces
an event, so an empty history implies an empty `get_ongoing()`.

## 6. TUI rendering specification — **[A]** unless noted

### 6.1 Width budget — corrected for v5

The original grid was specified against *terminal* width. In v5 the alert
block lives in the MAIN column, whose width is
`terminal_width − LEFT_SIDEBAR (34) − separator`. A 96-column terminal gives
the block ~61 columns, not 96. **Every threshold in §6.3 is a block width.**

**Where the width comes from.** §3.1.4 is real: `render_alert_block` receives
no width. The RIGHT column already computes exactly this number —
`_fit_proclist_width` (`glances_curses_v5.py:621`) publishes
`right_width = max_x − left_width − _SIDEBAR_SEPARATOR_GAP` as
`view["proclist_width"]`, and rebuilds once when it changes.

G7 generalises it rather than adding a second mechanism: rename the key to
`view["right_width"]` and widen the guard from "a processlist block exists"
to "the right column is non-empty", since the alert block is always present.
One call site to adjust in `processlist/render_curses_v5.py:356`. Pure
rename, no behaviour change: the rebuild still fires only when the value
actually changes (first frame, resize).

### 6.2 Column grid — **[A]**, the grid G7 ships

Zero-based offsets within a block of width `W`:

| Offset | Width | Content | Align |
|---|---|---|---|
| 0 | 1 | State glyph | — |
| 2 | 8 | `TIME` | left |
| 12 | 8 | `DURATION` | right |
| 22 | elastic | `TARGET` = `plugin[key].field`, `…` on truncation | left |
| `W − 8` | 8 | `LEVEL` | right |

`TARGET` takes whatever is left: `W − 22 − 1 − 8` with `LEVEL` present,
`W − 22` without.

```
ALERTS  2 ongoing · 3 resolved ─────────────────────────
  TIME      DURATION  TARGET                      LEVEL
● 14:02:11     2m58s  Cpu total                 CRITICAL
● 14:01:03     4m06s  Containers nginx mem usa…  WARNING
○ 13:58:40       43s  Fs /                       WARNING
```

Source and field are one column, not two. Both have wildly variable width in
practice (`cpu` vs `containers[nginx]`, `total` vs
`bytes_sent_rate_per_sec`); fixing them separately means either heavy
truncation or broken alignment — the §3.1.1 defect this grid exists to fix.
Merged, every column but one is fixed, so the block aligns at any width.

**`TARGET` is prose, not an identifier (revised 2026-08-18).** It was first
specified as the raw `plugin[key].field` triple. That reads as something to
paste into a query, not as something to understand at a glance, so it is now
humanised by `_humanise_target`:

| Incident | Rendered |
|---|---|
| `cpu` / — / `system` | `Cpu system` |
| `sensors` / `i915 0` / `value` | `Sensors i915 0` |
| `fs` / `/` / `percent` | `Fs /` |
| `containers` / `nginx` / `mem_usage` | `Containers nginx mem usage` |

Rules: only the plugin name is capitalised, and only its first letter — there
is deliberately no acronym table, so `gpu` renders `Gpu`. The key is kept
verbatim: mountpoints, device names and container names are already
human-readable, and rewriting them would misreport what the engine watched.
Underscores in the field become spaces.

A field whose **whole** name is in `_ALERT_GENERIC_FIELDS` (`value`,
`percent`) is dropped — the plugin and key already say what the alert is
about. The match is on the entire name, never a suffix, so
`memory_usage_percent` keeps every word. That list is closed and grounded on
the fields that can actually raise an alert; widening it erases information
from a row, so it does not grow without redoing that check.

Deliberately NOT done: threading `fields_by_plugin` into `render_alert_block`
to use `field_label()`. No plugin schema in the codebase populates `label`, so
the lookup would return the raw field name for every field that matters here.

`TIME` stays 8 columns wide: `HH:MM:SS` for an event from today, `MM-DD`
otherwise. **Divergence from current v5 behaviour** — `_format_alert_time`
returns 14 characters for an older event, which no fixed grid can absorb.
The information it carried is now covered by `DURATION` (`2d04h`).

### 6.2b Column grid — **[B]**, the Phase 2.X target

Recorded so Phase 2.X does not re-litigate it. The [B] columns are
**inserted into the §6.2 grid**, between `TARGET` and `LEVEL`, so the
migration adds columns without moving the ones already shipped:

| Order | Width | Content | Align |
|---|---|---|---|
| … | … | glyph, `TIME`, `DURATION` as §6.2 | |
| 4 | elastic | `TARGET` + `×N` | left / `×N` right |
| 5 | 7 | `MAX` | right |
| 6 | 7 | `AVG` | right |
| 7 | 7 | `MIN` | right |
| 8 | rest | Top processes | left, `…` on truncation |
| 9 | 8 | `LEVEL` | right |

`×N` renders only when `episodes > 1` (§5.5), i.e. never at the default.

### 6.2c Title row and the empty case — **[A]**

Block title row, replacing `ALERT (n ongoing / m total)`:

```
ALERTS  2 ongoing · 3 resolved ──────────────
```

`ongoing` is `len(get_ongoing())`; `resolved` counts the **closed incidents**
derived from the whole history (§5.6), not the events in it and not only the
rows displayed.

The empty-history collapse of §2.2 (`ALERT (initializing)` /
`ALERT (no alert detected)`) is **existing behaviour and must be preserved** —
it is not a placeholder to be replaced by an empty grid.

The column header row (`  TIME      DURATION  TARGET …`) is a second
non-data row. `row_budget`'s contract excludes *the* header row, singular.
Confirm in plans that emitting two non-data rows does not break the vertical
fit's accounting; if it does, fold the column labels into the title row
rather than changing the budget contract.

### 6.3 Width degradation — **[A]**

Columns are dropped right to left. Glyph, `TIME` and `TARGET` are never
dropped — they are the minimum that still identifies an alert.

`TARGET` has a floor of 12 columns; a step is taken as soon as the next
column down would starve it below that.

| Block width `W` | Rendered |
|---|---|
| ≥ 43 | full grid, `TARGET` = `W − 31` |
| 34 ≤ `W` < 43 | `LEVEL` dropped, `TARGET` = `W − 22` |
| < 34 | `DURATION` dropped, `TARGET` = `W − 12` |

Dropping `LEVEL` first is only acceptable because the glyph carries the level
colour (§6.5) — below 43 columns the block degrades to colour-only severity.

The title row shortens in the same order: separator dashes first, then the
`resolved` counter.

Under **[B]** the ladder gains its own steps above 43 (top processes
truncated, then dropped, then `MIN`, then `AVG`), leaving §6.3 as the tail.

### 6.4 Duration format

Replaces `str(timedelta)` (§3.1.3).

| Elapsed | Rendered |
|---|---|
| < 60 s | `43s` |
| < 60 min | `2m58s` |
| ≥ 60 min | `1h13m` |
| ≥ 24 h | `2d04h` |

Ongoing rows show elapsed time since the start, not the word `ongoing` — the
glyph carries that state, which is what frees the column.

### 6.5 Glyphs and decoration

| Element | Ongoing | Resolved |
|---|---|---|
| Glyph (Unicode) | `●` | `○` |
| Glyph (ASCII) | `*` | `-` |
| Glyph colour | level | level |
| `MAX` colour **[B]** | level | level |
| `TARGET`, `TIME`, `DURATION` | default | default |
| `LEVEL` | level | **default** |

**Revised 2026-08-18: colour in the `LEVEL` column means "still happening".**
It first carried the level colour for resolved incidents too, which left the
whole block coloured end to end and drowned the active rows among the settled
ones. A resolved incident's level text is now `DEFAULT`; its **glyph keeps the
level colour**, so the severity it reached stays readable. That split is
deliberate — the glyph answers "how bad was it", the level colour answers "is
it still going".

**Correction (2026-08-16): no dimming.** Earlier revisions of this table
called for dimmed cells. `ColorRole` (`curses_renderer_v5.py:110`) offers
`DEFAULT / OK / CAREFUL / WARNING / CRITICAL / HEADER` and nothing else — a
dim attribute does not exist in the v5 renderer, and adding one means new
colour-pair infrastructure, which is out of G7 scope. Severity is carried by
the glyph colour and the `LEVEL` cell; ongoing versus resolved is carried by
the glyph shape. Revisit only if a `DIM` role is introduced for other
reasons.

`prominent` is forwarded onto the `LEVEL` cell. When `LEVEL` is dropped by
§6.3, it moves onto the glyph cell so the flag is never silently lost — the
G6B defect class named in §11.

**Unicode — resolved (2026-08-16).** The assumption that a global unicode
flag exists in the v5 renderer is **false**: there is none, and no
`render_curses_v5.py` emits a non-ASCII character today. `●`/`○` and the
title-row rule `─` would be the first.

Decision: **mirror v4** — Unicode by default, ASCII (`*`, `-`, `-`) when
`--disable-unicode` is passed. `args.disable_unicode` already exists
(`main.py:658`) and reaches `main_v5`; what is missing is publishing it into
`view` and reading it in the renderer, ~5 lines. This is still "no new
option" as §6.5 required, and it establishes in v5 the mechanism v4 has in
`glances/outputs/glances_unicode.py` — the next screen that wants a glyph
will need it. Rendering Unicode unconditionally was rejected: it silently
breaks a documented v4 option on restricted terminals.

G7 wires the flag; it does **not** port `glances_unicode.py`. Only the alert
block consumes it for now.

**The title's state signal — revised 2026-08-18.** The standing TUI rule was
written as "the block title is always `ColorRole.HEADER`". Its *purpose* is
that an alert must never escalate a heading — the alert lives on the value.
The rule is therefore restated in the form that actually carries that intent:

> No element of a block title may ever carry an alert level colour
> (`careful` / `warning` / `critical`).

That leaves room for the block's one at-a-glance state signal, which the
"always HEADER" phrasing forbade for no benefit: the title is emitted as
glued cells, and the **ongoing-count fragment alone** is coloured — `OK`
(green) when `n_ongoing == 0`, `DEFAULT` otherwise. `ALERTS`, the `resolved`
clause and the trailing rule stay `HEADER`, so the block still reads as a
titled block rather than a coloured banner. Green is reassurance, not
escalation.

The empty-history collapse of §2.2 is split the same way, for the same
reason: `ALERT ` keeps `HEADER`, and only the parenthesised state fragment is
coloured. `(no alert detected)` is `OK` — a settled engine with nothing to
report *is* the all-clear. `(initializing)` stays `DEFAULT`: warmup is not an
all-clear, and colouring it green would claim a healthy system before the
engine can fire at all.

Because the title is now several cells, `glue=True` on every fragment after
the first is load-bearing: without it the painter inserts a separator and the
rendered title shifts. §6.3's degradation ladder is unchanged but now cuts
across cells at its hard-truncation step.

## 7. Data model — **[B]**

Deferred to Phase 2.X by the §4.1 decision. Recorded, not executed in G7.
Retargeted from the original v4 proposal (`GlancesEvent.episodes`), which
does not apply: there is no `GlancesEvent` in v5.

The v5 change is to `alerts_v5.py`: the history stops being a log of
transitions and becomes a list of **incident records**, one per
`(plugin, key, field)` occurrence, mutated in place while open:

```python
{
    "ts",
    "plugin",
    "key",
    "field",
    "level",
    "previous_level",
    "value",
    "prominent",
    "is_initial",
    "hostname",  # unchanged, additive below
    "begin",
    "end",
    "max",
    "avg",
    "min",
    "count",
    "episodes",
    "top",
}
```

Constraints on the plans pass:

- **Additive only.** Every existing key keeps its name, type and meaning, so
  `/api/5/alert` stays a superset. `ts` remains the transition timestamp.
- `begin` is the first episode's start; `end` is the last episode's end, so
  duration is wall-clock span. Cumulative above-threshold time is recoverable
  from `count` and is API-only.
- Sample accumulation runs in the ingest path, which executes for **every
  watched field of every plugin on every cycle**. It is on the hot path.
  A perf check is mandatory, not optional (Phase 2 spec §5.1 item 6).
- `avg` accumulates over above-threshold samples only (v4 parity, §2.6).
- `level` stays monotonic within an incident (v4 parity, §2.6).

## 8. Configuration

**[A]** — no new key. One gap to close in this slot:

1. Add the `[alerts]` section to `conf/glances.conf` with its three real keys
   (§2.4), **commented** at their current defaults so no existing deployment
   changes behaviour. They are undocumented today. Same treatment in
   `docs/config.rst`.

Point 2 of the original §8 — "wire `alerts_limit` to config or delete it" —
is **withdrawn** (§0.1). The parameter is no longer dead surface: it is the
fallback used when `view["row_budget"]` is absent. The real knob is
`_NOMINAL_ALERTS`, which belongs to the right-column vertical-fit design, not
to G7. Adding an `[alerts]` row-cap key on top of the vertical budget would
give the block two competing height authorities.

**[B]** — one new key, coalescing window, default `0` = disabled (§5.5).

## 9. Key bindings

v5 has no history-clearing action and **`w` / `x` are both free** (§2.5). The
original proposal — "`x` clears resolved, `w` becomes a deprecated alias" —
is a v4 migration concern with no v5 equivalent: there is nothing to
deprecate and nothing to preserve muscle memory *from*, since neither key has
ever done anything in v5.

The real question is whether a clear action is warranted at all. The history
is a bounded `deque`; it self-trims. Under §5.4 a resolved incident already
collapses into one row, and under §5.3 ongoing incidents are pinned above
resolved ones, so a saturated block drops resolved rows first — which is the
right thing to lose.

**Decided (2026-08-16): no new key binding in G7.** Revisit only if the block
is observed saturating with resolved rows in practice.

Any binding added must also be added to `_HOTKEYS` with its `group` / `desc`
so the `h` help overlay stays complete.

## 10. Open questions

### 10.1 Top processes on `warning` events — **[B]**, deferred with §7

v4 accumulates `top_dict` only when `state == "CRITICAL"` and resets it
otherwise, so a v4 `WARNING` event always renders an empty `TOP` column, and
an event that escalates then de-escalates has its accumulation wiped.

If B lands, v5 must choose: replicate the v4 behaviour (column empty on
warnings, i.e. misleading), accumulate on `warning` too, or accumulate on
`warning` and never reset on de-escalation. The last is the coherent choice,
but it costs one process-sort per warning incident per cycle on the hot path
(§7), for every plugin — v5 has no `alert`-plugin-local place to put that
cost. **Quantify before deciding.**

Moot for G7 under the §4.1 decision. It becomes blocking again the moment
Phase 2.X starts.

### 10.2 Vertical budget of the MAIN column — **largely answered since**

Superseded in part by the right-column vertical fit that landed in
`55e68387`
(`docs/superpowers/specs/2026-08-05-tui-v5-right-column-vertical-fit-design.md`):
`plan_right_column` now turns the available height into a per-block row
budget, the alert block is in `_ELASTIC_RIGHT`, its nominal is
`_NOMINAL_ALERTS = 10`, and the shrink ladder gives it explicit steps
(10 → 5 → 3 → header only). The questions below are therefore **answered**
for the budget itself; what remains open for G7 is only whether the pinning
of §5.3 makes the shrink ladder's behaviour undesirable, which the plans pass
should check but not redesign.

Original wording kept for the record:

The alert block shares the MAIN column with `containers`, `vms`,
`processcount`, `processlist`, `programlist` and (after G6C) `amps`. Each
claims vertical space independently. Pinning ongoing events to the top
(§5.3) makes the saturation case *worse*: if ongoing events fill the block,
no resolved event is ever visible.

To settle in a dedicated plan, not in G7:

- Fixed budget per plugin, proportional to height, or priority-based with a
  guaranteed minimum?
- Does the alert block get a guaranteed minimum (e.g. 3 rows) when
  `processlist` is under pressure?
- Is overflow indicated (`… 4 more`) or silently truncated?
- Is per-block scroll/fold acceptable in a curses TUI, or refused as
  complexity?

Until settled, the block keeps its 10-row cap and §6 assumes it renders
whatever height it is given.

### 10.3 Does the `"alert"` entry in `RIGHT_SLOT` stay? — **decided**

It stays, and becomes the single mechanism: move the `frame.right.append(...)`
of the synthesized block to **before** the slot sort
(`curses_renderer_v5.py:982`). `"alert"` is already last in `RIGHT_SLOT`, so
the rendered order is unchanged and the duplicate mechanism disappears. The
alternative — deleting the `RIGHT_SLOT` entry — was rejected because
`slot_for("alert")` and `row_budget(view, "alert", …)` both key on that name.

## 11. Non-regression checklist

Applied before merge, in addition to the standard checklist:

- [ ] The set of events produced under default configuration is unchanged —
      only rendering differs. **[A]**
- [ ] `careful` still never enters the history (§2.1).
- [ ] Warmup and `is_initializing()` placeholders still render exactly as in
      §2.2, including the single-line collapse on empty history.
- [ ] `min_duration_seconds` debounce untouched. **[A]**
- [ ] `is_initial` events never render a `→` arrow — holds by construction
      under §5.6, but assert it.
- [ ] `prominent` is still forwarded onto the level cell — the G6B defect
      class (a renderer silently dropping `prominent`) must not reappear.
- [ ] `GET /api/5/alert` payload is **byte-identical**, not merely a superset:
      §5.6 adds no field. (The superset wording applies to **[B]** only.)
- [ ] `get_ongoing()` writes nothing and is not called from the ingest path.
- [ ] The block still renders last in the RIGHT column and still collapses to
      one line when the history is empty.
- [ ] No emitted row exceeds the block width at any tested width.
- [ ] `--disable-unicode` produces a pure-ASCII block.
- [ ] The `view["proclist_width"]` → `view["right_width"]` rename leaves the
      processlist responsive columns byte-identical at every tested width.
- [ ] The vertical shrink ladder still degrades the block as designed
      (10 → 5 → 3 → header only) with incident rows instead of event rows.
- [ ] No new dependency.
- [ ] **[B]** perf check on the ingest path, all plugins, blocking at +20%.

## 12. Out of scope

- WebUI parity — follow-up, per the Phase 2 spec §2 (WebUI is the final slot).
- The MAIN-column vertical budget (§10.2) — dedicated plan.
- Exporters consuming alert history.
- Any `NEWS.rst` entry — release-time, maintainer, never during development.
- v4 `glances/plugins/alert/__init__.py`, `events_list.py`, `event.py` — left
  untouched until the Phase 4 cleanup, like every other v4 file.

## 13. Plan decomposition (after §4.1 is decided)

Under the decided option C:

- **Plan 1 — alert block rendering.** §5.1–5.4, §5.6, §6, §8.1, §10.3.
  Closes G7 **and** Phase 2 on its own. Touches:
  - `alerts_v5.py` — `get_ongoing()` only, read-only (§5.6).
  - `curses_renderer_v5.py` — incident derivation, grid, degradation,
    duration format, glyphs, `alerts_ongoing` parameter, append-before-sort.
  - `glances_curses_v5.py` — pass `alerts_ongoing`, publish the unicode flag,
    generalise `_fit_proclist_width` → `right_width`.
  - `processlist/render_curses_v5.py` — the `right_width` rename, one line.
  - `conf/glances.conf` + `docs/` — the `[alerts]` section.
  - Tests: golden output at block widths 96 / 61 / 43 / 30 / 24; segmentation
    (single incident, escalation, several incidents on one tuple, evicted
    opener, fully evicted ongoing tuple, `is_initial`); ASCII fallback;
    `/api/5/alert` unchanged.

  Sequencing note for the plans pass: the `right_width` rename and the
  unicode plumbing are independent of the alert grid and can land as their
  own steps first, keeping the grid change reviewable on its own.

- **Plan 2 — Phase 2.X, engine episodes.** §5.5, §6.2b, §7, §10.1. Gated on a
  perf measurement of the ingest path and on the `/api/5/alert` break being
  acceptable at that point in the release cycle. Not part of Phase 2.

## 14. Release-note material (maintainer, release-time only)

Not an execution step. Recorded here so it is not lost:

- Alert block redesigned as an aligned column record with graceful
  degradation on narrow terminals.
- Ongoing alerts pinned to the top; a resolved alert updates its row instead
  of adding one.
- The level transition (`warning → critical`) is no longer displayed; the row
  shows the highest level the incident reached.
- An alert older than today shows `MM-DD` instead of the full
  `MM-DD HH:MM:SS` timestamp; its age is now carried by the duration column.
- The block honours `--disable-unicode` (first v5 screen to do so).
- `[alerts]` configuration section documented in `glances.conf` for the first
  time; key names differ from v4's `[alert]` section
  (`min_duration_seconds` / `history_size` / `warmup_cycles` vs
  `min_duration` / `max_events` / `min_interval`) and the semantics of
  `min_duration` differ (§2.4) — **breaking change for v4 configs**.
- v4's `w` / `x` alert-clearing keys have no v5 equivalent — **breaking
  change**.

# Glances v5 — G7 design (alert presentation)

**Date:** 2026-08-01
**Phase:** 2, group **G7** (order G0→G1→G2→G3→G4A→G4B→G5→G6A→G6B→G6C→**G7**)
**Status:** design — **not approved**. Two decisions block the plans pass: §4.1
(scope: presentation-only vs engine enrichment) and §10.1 (top processes).
**Predecessor:** G6C (amps + irq + cloud + mpp) — must land first.

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

The renderer's `alerts_limit` parameter (`:681`, default 10) is **never
passed** by `glances_curses_v5.py:489-495`, so the block cap is hardcoded at
10 with no config path.

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

### 4.1 DECISION REQUIRED — G7 scope

| Option | Delivers | Cost | Consequence |
|---|---|---|---|
| **A — presentation-only** | §6 grid minus `MAX`/`AVG`/`MIN`/`TOP`/`×N`: glyph, time, duration, source, field, level | renderer only, ~1 plan | Honours the Phase 2 spec §4.1 scope. Fixes 3.1.1–3.1.6. Does **not** deliver §5.1's journal semantics — the block stays a transition log with no peak or mean. |
| **B — engine + presentation** | the full §6 grid | episode aggregation in `alerts_v5.py` + renderer, 2–3 plans, breaks `/api/5/alert` | Delivers the design. Enlarges G7 well beyond "presentation-only" and touches the one module every plugin's alerts flow through — regression surface is the whole product, not one plugin. |
| **C — A now, B as a Phase 2.X follow-up** | A's scope, with §5.5/§7 kept as the recorded target | A's cost now | Ships the legibility fix inside Phase 2 without putting `alerts_v5.py` on the Phase 2 critical path. |

**Recommendation: C.** The engine work is genuinely valuable but it is not
plugin migration, and Phase 2's goal is v4 feature parity for local
monitoring. Landing B inside the final Phase 2 slot puts a rewrite of the
shared alert engine between the branch and the end of the phase.

Everything below marked **[B]** applies only if B or the follow-up half of C
is approved. Everything marked **[A]** is in scope under all three options.

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

Under **[A]** "is_finished" is derived exactly as the current renderer
derives *ongoing* (§2.2): latest event per `(plugin, key, field)` with a
non-`ok` level.

### 5.4 One row per incident — **[A]**

A `→ ok` transition must not occupy its own row. It resolves the row already
present for its tuple, flipping its glyph and freezing its duration. This is
the §3.1.6 fix and it is achievable without engine work: the renderer already
groups by tuple.

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

## 6. TUI rendering specification — **[A]** unless noted

### 6.1 Width budget — corrected for v5

The original grid was specified against *terminal* width. In v5 the alert
block lives in the MAIN column, whose width is
`terminal_width − LEFT_SIDEBAR (34) − separator`. A 96-column terminal gives
the block ~61 columns, not 96. **Every threshold in §6.3 is a block width.**

### 6.2 Column grid

Zero-based offsets within the block, at full width:

| Offset | Width | Content | Align | Scope |
|---|---|---|---|---|
| 0 | 1 | State glyph | — | A |
| 2 | 8 | Start time `HH:MM:SS` | left | A |
| 12 | 8 | Duration | right | A |
| 22 | 9 | Source (`plugin[key]`) + `×N` | left / `×N` right | A (`×N` = B) |
| 31 | 7 | `MAX` | right | **B** |
| 40 | 7 | `AVG` | right | **B** |
| 49 | 7 | `MIN` | right | **B** |
| 58 | rest | Top processes | left, `…` on truncation | **B** |

Under **[A]** the columns after `Source` are the `field` name and the level
text; the numeric block and top-process column are absent, so the full-width
grid ends around offset 45.

Header row, same offsets:

```
  TIME      DURATION  SOURCE       MAX     AVG     MIN  TOP PROCESSES
```

Block title row, replacing `ALERT (n ongoing / m total)`:

```
ALERTS  2 ongoing · 4 resolved ──────────────
```

The empty-history collapse of §2.2 (`ALERT (initializing)` /
`ALERT (no alert detected)`) is **existing behaviour and must be preserved** —
it is not a placeholder to be replaced by an empty grid.

### 6.3 Width degradation

Columns are dropped right to left. Glyph, `TIME` and `SOURCE` are never
dropped; `MAX` is never dropped when present.

| Block width | Rendered up to |
|---|---|
| ≥ 96 | full |
| 78–95 | `TOP PROCESSES` truncated to `width − 58`, `…` suffix |
| 62–77 | `TOP PROCESSES` dropped |
| 47–61 | `MIN` dropped |
| 38–46 | `AVG` dropped |
| < 38 | `DURATION` dropped |

The title row shortens in the same order: separator dashes first, then the
`resolved` counter.

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
| `SOURCE` | default | dimmed |
| `TIME`, `DURATION`, `AVG`, `MIN`, `TOP` | dimmed | dimmed |

ASCII fallback must reuse the existing global unicode flag; **no new option**.
Confirm during plans that such a flag exists in the v5 renderer — if it does
not, the ASCII variant is an open question, not an assumption.

Per the standing TUI rule: the block title is always `ColorRole.HEADER` and
is never escalated by a level. The alert lives on the value.

## 7. Data model — **[B]**

Only if B is approved. Retargeted from the original v4 proposal
(`GlancesEvent.episodes`), which does not apply: there is no `GlancesEvent`
in v5.

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

**[A]** — no new key. Two existing gaps to close in the same slot:

1. Add the `[alerts]` section to `conf/glances.conf` with its three real keys
   (§2.4), commented at their current defaults so behaviour is unchanged.
   They are undocumented today.
2. Wire `alerts_limit` to config instead of the hardcoded 10 (§2.4), or
   delete the parameter. A parameter no caller passes is dead surface.

**[B]** — one new key, coalescing window, default `0` = disabled (§5.5).

## 9. Key bindings

v5 has no history-clearing action and **`w` / `x` are both free** (§2.5). The
original proposal — "`x` clears resolved, `w` becomes a deprecated alias" —
is a v4 migration concern with no v5 equivalent: there is nothing to
deprecate and nothing to preserve muscle memory *from*, since neither key has
ever done anything in v5.

The real question is whether a clear action is warranted at all. The history
is a bounded `deque`; it self-trims. Under §5.4 a resolved incident already
collapses into one row. **Default position: no new key in G7.** Bind `x` to
"clear resolved" only if the plans pass shows the block still saturating with
resolved rows under §5.4.

Any binding added must also be added to `_HOTKEYS` with its `group` / `desc`
so the `h` help overlay stays complete.

## 10. Open questions

### 10.1 Top processes on `warning` events — **[B]**, DECISION REQUIRED

v4 accumulates `top_dict` only when `state == "CRITICAL"` and resets it
otherwise, so a v4 `WARNING` event always renders an empty `TOP` column, and
an event that escalates then de-escalates has its accumulation wiped.

If B lands, v5 must choose: replicate the v4 behaviour (column empty on
warnings, i.e. misleading), accumulate on `warning` too, or accumulate on
`warning` and never reset on de-escalation. The last is the coherent choice,
but it costs one process-sort per warning incident per cycle on the hot path
(§7), for every plugin — v5 has no `alert`-plugin-local place to put that
cost. **Quantify before deciding.**

This question is moot under option A.

### 10.2 Vertical budget of the MAIN column — out of scope, blocking final tuning

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

### 10.3 Does the `"alert"` entry in `RIGHT_SLOT` stay?

It is inert today (§2.2). Either remove it as dead surface, or make the
append respect it. Decide in plans; do not leave both mechanisms.

## 11. Non-regression checklist

Applied before merge, in addition to the standard checklist:

- [ ] The set of events produced under default configuration is unchanged —
      only rendering differs. **[A]**
- [ ] `careful` still never enters the history (§2.1).
- [ ] Warmup and `is_initializing()` placeholders still render exactly as in
      §2.2, including the single-line collapse on empty history.
- [ ] `min_duration_seconds` debounce untouched. **[A]**
- [ ] `is_initial` events still render a bare level, never a `→` arrow.
- [ ] `prominent` is still forwarded onto the level cell — the G6B defect
      class (a renderer silently dropping `prominent`) must not reappear.
- [ ] `GET /api/5/alert` payload is a superset of the current payload.
- [ ] The block still renders last in the MAIN column and still collapses to
      one line when the history is empty.
- [ ] No emitted row exceeds the block width at any tested width.
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

Under the recommended option C:

- **Plan 1 — alert block rendering** — §5.1–5.4, §6, §8.1–8.2, §10.3.
  Renderer + tests + `conf/glances.conf` + `docs/`. Golden-output tests at
  several block widths; no `alerts_v5.py` change.
- **Plan 2 — Phase 2.X, engine episodes** — §5.5, §7, §10.1, plus the §6
  columns marked **[B]**. Gated on a perf measurement, and on the API break
  being acceptable at that point in the release cycle.

Under option A, Plan 1 alone closes G7 and Phase 2.

## 14. Release-note material (maintainer, release-time only)

Not an execution step. Recorded here so it is not lost:

- Alert block redesigned as an aligned column record with graceful
  degradation on narrow terminals.
- Ongoing alerts pinned to the top; a resolved alert updates its row instead
  of adding one.
- `[alerts]` configuration section documented in `glances.conf` for the first
  time; key names differ from v4's `[alert]` section
  (`min_duration_seconds` / `history_size` / `warmup_cycles` vs
  `min_duration` / `max_events` / `min_interval`) and the semantics of
  `min_duration` differ (§2.4) — **breaking change for v4 configs**.
- v4's `w` / `x` alert-clearing keys have no v5 equivalent — **breaking
  change**.

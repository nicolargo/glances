# G9-9B — v5 WebUI right column, batch 2 (`processlist`, `programlist`, `alert`) and the two process CLI options: Design

**Status:** approved (2026-09-19)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessor:** `2026-09-19-glances-v5-g9-9a-webui-right-column-design.md`
**Closes:** G9

---

## 1. Goals

G9-9A took the WebUI to 29 of 32 plugins and left the right column three
blocks short. G9-9B ports them and **closes G9**:

    RIGHT_SLOT = vms, containers, processcount, amps, processlist, programlist, alert
                                                     ^^^^^^^^^^^  ^^^^^^^^^^^  ^^^^^

It also closes two parity gaps that G9-9A had to record as divergences
because no server signal existed: `--programs` and `--sort-processes`.

Two things make this group different from 9A. It is the first to **touch
code the TUI runs** (the incident synthesis moves, and an alert accessor is
made safe to call from another thread), and it is the first to **add CLI
options**, which are user-facing surface rather than WebUI-internal.

## 2. Out of scope

- **Browser hotkeys.** Still out, as in G9-5…G9-9A. The WebUI mirrors server
  state; it does not gain its own runtime toggles.
- **A vertical row budget in the browser.** Settled in G9-9A §4.
- **Retiring the v4 bundle** — Phase 4.
- **The `max_processes_display` dead read in v4** (`glances_restful_api.py`
  reads the key into a local and only logs it). Found while designing this
  group; it belongs in a v4 issue, not here. See §6.2.

## 3. Decisions taken before design (2026-09-19)

| # | Decision | Where |
|---|---|---|
| D0 | **G9-9A's parked debt opens this group** — the two measuring caps move to the token file before anything else | §4 |
| D1 | **The incident synthesis is EXTRACTED**, not duplicated: one function, served to both UIs | §5.1 |
| D2 | **A new route `/api/5/alert/incidents`** serves it | §5.2 |
| D3 | **The `get_ongoing_top()` race is closed in this group**, not deferred | §5.3 |
| D4 | **The footer keeps the cadence only** | §5.5 |
| D5 | **`processlist` caps in the BROWSER**, from `[outputs] max_processes_display` — v4 parity | §6.2 |
| D6 | **`Command` is the protected TAIL of `processlist`'s cascade** — the opposite of `containers`, deliberately | §6.1 |
| D7 | **Both `--programs` and `--sort-processes` are added**, retiring two G9-9A divergences | §7 |

## 4. The parked debt opens this group (D0)

G9-9A parked one finding, and `processlist` is exactly the plugin that
would trip on it.

`css/v5.css` excludes two classes from the measuring pass —
`.gl-measuring .gl-truncate:not(.gl-name):not(.gl-command):not(.gl-ports)` —
but **both caps those exclusions justify are scoped to
`PluginContainers.vue`**. `.gl-name`'s cap, by contrast, is global.

`processlist` has a `Command` column and reuses `fit_block.js`. Written the
obvious way, it would inherit the global exclusion **without** the cap, so
its command cell would be measured at its ellipsized width — and its
cascade would silently UNDER-fire, the mirror image of the `ports` bug
measured on 2026-09-19 (an uncapped span measured 3042px and pushed the
table 1525px past its container).

**Task 1 of this group** therefore moves `.gl-command` and `.gl-ports` into
`css/v5.css` next to `.gl-name`, with their `display: block`. Nothing else
changes; the containers tests must stay green untouched.

## 5. `alert`

### 5.1 The synthesis moves out of the curses renderer (D1)

`_derive_incidents(history, ongoing, ongoing_since, ongoing_top)`
(`curses_renderer_v5.py:576`) is **pure**: four data inputs, a list of
incidents out. So is `_incident_duration` (`:527`). Moving them to a shared
module is a relocation, not a rewrite — no behaviour changes, and the TUI
keeps importing them.

This is what makes the WebUI's grid honest. An incident is not a payload
field anywhere: it is a *collapse* of a transition log, and its rules
(escalations mutate the open incident, they never open a new one) live in
that function. A JS twin would be a second implementation of a subtle rule
with nothing to keep the two aligned — precisely the shape of bug the drift
tests exist to prevent, and which a drift test cannot catch here because
the output is data, not a constant.

Destination: a new `glances/alerts_incidents_v5.py`, imported by both
`curses_renderer_v5.py` and `routes_v5.py`. The renderer keeps everything
that paints — `render_alert_block` (`:876`), `_alert_block_height` (`:807`)
and the title/shrink ladder — because those are curses geometry.

### 5.2 The route (D2)

`/api/5/alert/incidents`, declared next to the existing `/alert`
(`routes_v5.py:166`), calls the engine's four accessors and returns the
synthesis. It 404s when the alerts subsystem is disabled, exactly as
`/alert` does.

The existing `/alert` (raw history) **stays**: it is the export/REST
contract, and the incident view is a second projection of the same data,
not a replacement.

### 5.3 Closing the `get_ongoing_top()` race (D3)

This is the one place in G9-9B that makes a live TUI safer rather than only
adding surface, and the hazard is already documented in the code.

The three `get_ongoing*` accessors snapshot the mapping they walk
(`list(self._state.items())`, `alerts_v5.py:194`, `:218`, `:238`), so a
concurrent insertion cannot raise during iteration. But `get_ongoing_top`
(`:238`) returns the `top` **list object stored on the history event, not a
copy** — its own docstring says so, and says that the current consumer
copies it before use, so "a future caller must not mutate it in place".

A REST route is that future caller, and it is worse than a mutator: it
**serializes** the list while `_accumulate_top` may be appending to it from
the asyncio side. A list mutated during serialization yields either a
`RuntimeError` or torn output, and the same read from the TUI thread is
what the project already recorded as "a raise there kills the TUI thread
for good".

Fix: `get_ongoing_top()` copies `names` before putting it in its result.
One line, plus a test that mutates the engine's stored list after the
accessor returns and asserts the returned value is unchanged. The
docstring's warning becomes obsolete and goes with it.

### 5.4 The grid, and the two fields that must not be dropped

The WebUI renders the same incident grid the TUI paints. An incident
carries `begin, end, plugin, key, field, level, prominent, ongoing,
partial, ok, top, top_sort`.

`ongoing` and `partial` are **not cosmetic**: `partial` marks an incident
whose opening event has aged out of the bounded history, which is why the
TUI renders `>2h04m` rather than a duration it cannot know. A WebUI that
dropped `partial` would print that same figure as if it were exact — a
number that lies. `ongoing` reaches the DOM directly, through the glyph;
`partial` does not — it never becomes its own DOM state, only the
server-formatted `>` prefix already baked into `duration`. A test pins
that prefix.

### 5.5 The footer (D4)

The footer's alert list (`AppShell.vue:27`, filled at `:297`) is replaced
by the cadence alone. The incident grid is the alert surface from now on.

Accepted consequence: on a page scrolled away from the right column, no
alert is visible. That is the TUI's behaviour too — its alert block is a
block like any other, not a status bar.

## 6. `processlist`

### 6.1 Columns and the cascade (D6)

Twelve fixed columns (`_FIXED_COL_KEYS`, `:91`) plus `Command`, and a
`_DROP_ORDER` of eight (`:89`):

    VIRT → TIME+ → RES → USER → PID → THR → S → NI

`CPU%`, `MEM%`, `R/s`, `W/s` and `Command` are absent from that order and
always survive. **`Command` is the protected tail here, while `containers`
drops `command` FIRST** — the two blocks make opposite choices, and both
are their own terminal renderer's choice. Recording it because a reviewer
reading the two components side by side will otherwise read it as an
inconsistency.

`fit_block.js` is reused unchanged: this is the second consumer it was
designed for, and the first outside `containers`.

### 6.2 The cap (D5)

v4 caps **in the browser**: `plugin-processlist.vue:590` reads
`config.outputs.max_processes_display` and slices. The server-side read in
`glances_restful_api.py` assigns a local and only logs it — dead code, and
a v4 issue rather than something to reproduce.

v5 mirrors the working half: the component reads the same key from
`/api/5/config` and caps at render. The payload keeps every process, so the
REST contract is unchanged and the total for the counter is free.

The TUI's own `_MAX_ROWS = 20` (`:66`) is a separate, terminal-side bound
and is not ported — the browser's cap is the config key.

### 6.3 The counter lives on the `processcount` line

In the TUI the `30/215` truncation counter is **not** on the list: it is on
the `TASKS` line above it (`processcount/render_curses_v5.py:37`), because
that line already carries the total. G9-9A deferred it for want of a
budget; the browser cap now supplies one.

So `PluginProcesscount.vue` gains the counter, and its rule is the TUI's:
shown only when the list is actually cut, and **never in the programs
view**, where the total counts processes while the list shows programs —
two different things.

## 7. `programlist` and the two CLI options (D7)

### 7.1 `--programs`

Added to `main_v5.py`, mirroring v4. The WebUI then picks between the two
lists on `serverArgs.programs`, exactly as it picks between `cpu` and
`percpu` on `serverArgs.percpu` (G9-8). The TUI keeps its own runtime
toggle on top (`glances_curses_v5.py:574`).

Exactly one of the two blocks renders, never both — the same exclusivity
rule, and the same failure mode if it is forgotten (two process tables on
one page).

### 7.2 `--sort-processes`

Added with v4's own spelling: `dest="sort_processes_key"`, and
`choices=sort_processes_stats_list` = `cpu_percent, memory_percent,
username, cpu_times, io_counters, name, cpu_num`. Importing that list
rather than retyping it is what keeps the two CLIs from drifting.

This retires **two** G9-9A divergences at once:
- divergence 3, the sorted column carrying no underline — the WebUI can now
  underline the active sort column, as the TUI does through
  `_HEADER_SORT_KEY` (`:97`);
- the missing half of the `processcount` sort indicator (§6.3), which needs
  both `programs` and the sort key.

What stays out: the TUI's **live** sort (hotkeys, `_LIVE_SORT_PLUGINS`,
`glances_curses_v5.py:759`) changes the key at runtime with no server
mirror. The WebUI reflects the key the server was STARTED with. A session
where the operator re-sorts in the terminal will show a different
underline in the browser — recorded as divergence 1 below.

## 8. Registry and layout

Three entries appended to `js/v5/plugins/index.js` in `RIGHT_SLOT` order,
after `amps`: `processlist`, `programlist`, `alert`. `processlist` and
`programlist` are `collection` (key `pid`, `name`).

`alert` is the first block NOT fed by `/api/5/all`, and it needs no new
plumbing: `AppShell.tick()` already fetches `/api/5/alert` on its own, in
its own try/catch, to fill the footer list (`AppShell.vue:297`). That call
is REPOINTED at `/api/5/alert/incidents` and its result handed to the alert
component as that component's payload, instead of to the footer. The
per-tick fetch count is unchanged, the failure isolation is unchanged (a
failing alert endpoint must not disturb the plugins above it), and the
footer simply stops consuming it.

The registry entry therefore declares no `shape`: the service layer's
payload validation applies to `/all` plugins, and `alert` has no envelope
to validate. The registry's own test asserts that it renders, which is the
invariant that matters.

The registry reaches **32 of 32**.

## 9. Tests

1. **Extraction is behaviour-preserving**: the existing alert tests must
   pass with no edit after the move. An edited alert test in Task 2 is a
   signal the move was not pure.
2. **The race fix**: mutate the engine's stored `top` list after
   `get_ongoing_top()` returns; the returned value must not change.
3. **The route**: incidents for a seeded engine, 404 when alerts are off,
   and — the one that matters — a payload whose `partial` incident is
   serialized as such.
4. **Render probe**: 32 registered plugins; the cap applied at
   `max_processes_display` with the `N/M` counter on the `TASKS` line;
   `processlist`/`programlist` mutual exclusion under `serverArgs.programs`;
   the sort underline following `serverArgs.sort_processes_key`.
5. **Cascade**: `Command` survives the full `_DROP_ORDER`, and a
   pathological command line does not widen the measuring pass (the §4 cap,
   asserted the way `.gl-ports` is).
6. **CLI**: both options parse, and `--sort-processes` rejects a value
   outside the shared choices list.

## 10. Divergences to record for the release changelog

| # | Divergence | Why |
|---|---|---|
| 1 | The sort underline follows the STARTUP key, not the TUI's live sort | The live key is TUI runtime state with no server mirror (§7.2) |
| 2 | No alert in the footer | The grid is the alert surface; the TUI has no status bar either (§5.5) |
| 3 | The TUI's `_MAX_ROWS = 20` is not ported | The browser's bound is the config key (§6.2) |
| 4 | `processcount`'s sort indicator is omitted entirely when `--sort-processes` was not given, where the terminal always renders `Threads sorted automatically by X` | The live/auto-sorted key is TUI runtime state with no server-args mirror — same root cause as #1, this time on `processcount` rather than `processlist` |
| 5 | `VIRT`/`RES` keep a decimal at ≥100 (the shared `formatBytes`), where the renderer's local `_format_bytes` drops it to fit the fixed 5-char column | The browser column is not width-constrained the way the TUI's is |
| 6 | `USER` is not truncated to the terminal's width with a `+` marker | The browser column scrolls instead of cropping (same rule as the alert grid, §5.4) |
| 7 | `NI` renders raw Win32 priority-class numbers on Windows, where the terminal maps them to short labels (`_format_nice`'s `_WINDOWS_NICE_LABELS`, `processlist/render_curses_v5.py:72-79`) | The mapping was never ported to the browser formatter — verified: no `nice`/priority-class handling exists anywhere under `glances/outputs/static/js/v5/` |
| 8 | The browser renders every incident in the alert grid; the terminal caps at its row budget | The browser has no vertical fit pass (like `_MAX_ROWS`, #3) — it scrolls instead |

## 11. Risks

- **The extraction is the riskiest step**, because it is the only one that
  can break a TUI that works today. It is Task 2 for that reason: early,
  alone, and behind a test suite that must not need editing.
- **The route exposes engine state to a second reader.** §5.3 closes the
  one documented hazard; a review should look for a second one rather than
  assume there is none.
- **Two CLI options are user-facing surface.** They must be documented and
  behave exactly as v4's, including the `dest` names, or a script that
  works against v4 breaks against v5.

## 12. Success criteria

- The WebUI renders 32 of 32 plugins; the right column matches the TUI's
  order and content.
- The alert grid is built from the same function the TUI calls, and the
  existing alert tests were not edited to make it pass.
- `get_ongoing_top()` returns data no longer aliased to engine state.
- `--programs` and `--sort-processes` behave as v4's, and the browser
  reflects both.
- The full suite is green, `make pre-commit` no worse than it is today.

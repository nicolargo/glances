# G9-4 — `cpu`, `load`, `memswap` and `gpu` in the v5 WebUI: Design

**Status:** approved (2026-09-06)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-05-glances-v5-g9-1-webui-serving-design.md`, `2026-09-06-glances-v5-g9-2-webui-foundation-design.md`, `2026-09-06-glances-v5-g9-3-webui-scaling-design.md`

---

## 1. Goals

G9-3 built the pattern — one request per tick, a plugin registry, a column
model, labels from the schema — and proved it on `mem` and `network`. Its
decision D1 stated the consequence: *"G9-4…N become mechanical."*

G9-4 is the first group to test that claim, on four plugins chosen because
three of them are mechanical and one is not:

1. **`cpu`, `load`, `memswap`** — scalar plugins the pattern should absorb with
   no new infrastructure. If they need any, D1 was wrong and we learn it now on
   three cheap components instead of thirty.
2. **`gpu`** — the first collection after `network`, and the first component
   whose title is computed from data, whose layout switches on data, and which
   drops a column on data. It is the stress test.
3. **The `serverArgs` channel** — `gpu`'s TUI mode switch is driven by the
   `--meangpu` CLI flag and its temperature unit by `--fahrenheit`. Neither
   reaches the WebUI today.
4. **Closing the schema's double-source gap** — G9-3 left `network` with its
   labels in two places. This group makes the schema the single source and
   retrofits `network`.

## 2. Out of scope

- **Responsive column dropping.** Still deferred. Note that `gpu`'s `mem`
  column drop is **data-driven** (no card reports memory), not width-driven —
  the two are unrelated mechanisms and must not be conflated. The `priority`
  seam was removed in G9-3's final review; when width-driven dropping arrives
  it will mirror the TUI's `_DROP_ORDER` ordered list
  (`glances/plugins/containers/render_curses_v5.py`,
  `glances/plugins/processlist/render_curses_v5.py`), not an integer tier.
- **Sorting.** Same reasoning as G9-3: `processlist` makes it necessary and
  `processlist` is not in this group.
- **`fetch` timeouts and a staleness indicator.** Still deferred; revisit when
  the page shows enough plugins to look authoritative.
- **Fixing `cpu`'s `core`/`cpucore` field-name bug.** Reported in §10, not
  fixed here — see that section for why, and for the tracking obligation.
- **Retiring the v4 Vue app** — Phase 4.

## 3. Decisions taken before design (2026-09-06)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Strict TUI layout parity**, including `cpu`'s 3-column grid and `gpu`'s summary/multi switch | Terminal-born layout compromises are reproduced deliberately; a reader moving between the TUI and the browser finds the same map |
| D2 | **The schema is the single source for labels** | `load` and `gpu` TUI renderers are refactored to read `field_label()`; `network` is retrofitted; the string exists in exactly one place per field |
| D3 | **One label form: the short one** | `labelFor()` is unchanged, `mem` ships as-is, and the browser shows the terminal's abbreviations. Closes the G9-3 deferred minor "labels.js mirrors only the `prefer_short=True` branch" as **decided, not fixed** |
| D4 | **The WebUI reads `/api/5/args`** and honours `--meangpu` and `--fahrenheit` | A new global-configuration channel, reaching components as a fourth prop (see D5) |
| D5 | **Cross-cutting state travels as props**, not `provide`/`inject` | `serverArgs` becomes a fourth prop. Revisit at the third or fourth global concern, not the second |

## 4. Measured inputs

Read from the repository on 2026-09-06, not assumed:

| Plugin | Shape | TUI label source | Schema today |
|---|---|---|---|
| `cpu` | scalar | `field_label(prefer_short=True)` | 3 `short_name` (`ctx_sw`, `inter`, `sw_int`) — **sufficient** |
| `load` | scalar | **hardcoded** `[("min1","1 min"), ("min5","5 min"), ("min15","15 min")]` | empty |
| `memswap` | scalar | `field_label(prefer_short=True)` | empty, and the field names *are* the TUI's strings — **sufficient** |
| `gpu` | **collection** | **hardcoded** (`"proc:"`, `"mem:"`, `"temperature:"`) | empty |

So D2's refactor cost falls on `load` and `gpu` only. `cpu` and `memswap`
already satisfy it.

Every plugin has a dedicated TUI renderer test file
(`tests/test_plugin_<name>_render_curses_v5.py`), including `load`, `gpu` and
`network`. This is what makes D2's renderer refactor safe.

`--fahrenheit` and `--meangpu` are **CLI arguments** (`glances/main_v5.py`),
not config keys. `/api/5/args` exists (added in G9-2) and is never called by
the WebUI; `resolveConfig()` deliberately reads `/api/5/config` instead,
because the argument namespace carries no `refresh` key.

## 5. The `serverArgs` channel

`resolveArgs()` in `api.js`, fetched once at mount in parallel with the
labels, following `resolveLabels()`'s existing contract: an unreachable
`/api/5/args` degrades to `{}` rather than blanking the page, and the result
is cached for the tab's life because CLI arguments cannot change while the
server runs.

It reaches components as a fourth prop, `serverArgs`.

**The cost D5 carries, stated so it is not discovered:** Vue turns an
undeclared prop into a fallthrough attribute, so a component that does not
declare `serverArgs` renders `serverargs="[object Object]"` into the DOM.
Every component must declare it, including `PluginMem` and `PluginNetwork`,
which do not use it. Three lines each, six components now and thirty-two
later. This is the pressure that will eventually justify `provide`/`inject`;
D5 says it has not built up yet.

## 6. `data-plugin`: identifying a component in the DOM

The render probe keys `pluginText`, `pluginColumnHeaders` and
`pluginColumnClasses` by the `<h2>` text. That worked while every title was a
constant. `gpu`'s title is `GeForce RTX 3080` / `3 GeForce RTX 3080` /
`3 GPUs` depending on the hardware, so the key becomes unstable, and
`test_the_registry_renders_every_registered_plugin`'s assertion on the ordered
list of `<h2>` texts would become a test of the machine it runs on.

`AppShell` binds `:data-plugin="plugin.name"` on `<component :is>`. Vue's
fallthrough lands it on each component's single root `<article>`, so **no
plugin component changes**. The probe re-keys on that attribute; the `<h2>`
texts stay available as their own list for tests that genuinely assert on
titles.

This is infrastructure `gpu` forces and the remaining 28 ports inherit.

## 7. Formatting

Two additions to `format.js`, both used by this group — nothing speculative:

- **`formatCount(value)`** — for counters (`ctx_switches`, `interrupts`,
  `soft_interrupts`, `syscalls`). Below 1024 it is a plain integer; at or above
  it, one decimal with a `K`/`M` symbol.

  **Correction to an earlier draft of this section**, which claimed base 1000
  on the reasoning that a count is not a size. The TUI does **not** do that:
  `_ctx_sw_value_cell()` (`glances/plugins/cpu/render_curses_v5.py:52-70`)
  scales at `>= 1024` and `>= 1_048_576`, matching v4's `auto_unit`. Under D1
  the TUI is the authority, so `formatCount` is **base 1024** — the same
  scaling as `formatBytes`, without the `B`. Whether counting in powers of two
  is *right* is a separate question from whether the two outputs agree, and
  this group only owns the second. If the maintainer wants base 1000, it is a
  TUI change first and a WebUI change second, never the WebUI alone.

- **`toFahrenheit(celsius)`** — mirrors `glances.globals.to_fahrenheit`
  exactly (`celsius * 1.8 + 32`), and nothing more.

  A `formatTemperature()` that also renders the value was the earlier draft's
  plan. It does not survive contact with `gpu`, whose missing marker is `N/A`
  (`_format_value()` in its renderer) while every other v5 formatter returns
  `-`. Rather than give a shared formatter a per-caller missing-value
  parameter on its first day, `gpu` keeps its own two-line value formatter and
  `format.js` keeps only the pure conversion.

`load` uses `toFixed(2)` inline. A named formatter for one call site in one
component is an abstraction this group does not need.

## 8. The four components

### 8.1 `cpu`

Four rows by three columns, rendered with `.gl-stat-grid` and three `<dl>`s —
the utility is already a flex over `<dl>`s, so **no CSS change**.

Row 1 carries `CPU` + `total`, then `idle`, then `ctx_sw`. Rows 2-4 follow the
TUI's own selection rules, which branch on **payload content, never on the
operating system** (`glances/plugins/cpu/render_curses_v5.py:181-200`):

| Column | Rule |
|---|---|
| 1 | `user`/`system`/`iowait`, or `idle`/**`cpucore`**/`dpc` when `"user" not in payload` — the TUI says `core` there, which is the bug of §10; port against `cpucore` and comment |
| 2 | `irq`/`nice`/`steal`, always |
| 3 | `interrupts`; then `soft_interrupts` if `is not None` else `ctx_switches`; then `guest` if `"guest" in payload`, else `syscalls` if `is not None`, else an empty cell |

**The two kinds of check are not interchangeable and must be ported
field-by-field.** `guest` is tested for **key presence**; `soft_interrupts`
and `syscalls` are tested for **value**. A `rate` field in v5 is `null` but
present — the plugin base keeps the key rather than dropping it — so
collapsing these into one test silently changes which column renders. This
exact confusion has already corrupted a v5 export path once.

Column 3's counter values use `formatCount`; everything else is a percentage.

### 8.2 `load`

One column. Header row: `LOAD` plus `{N}core` derived from `cpucore`, which is
`internal: true` and must **never** become a row of its own. Then `min1`,
`min5`, `min15`, two decimals.

Colours: `min15` and `min5` from their `_levels` entries; `min1` stays neutral,
matching v4, which has no alert on it.

### 8.3 `memswap`

Header row `SWAP` plus the percentage, coloured from `_levels.percent`. Then
`total`, `sin`, `sout`.

`used` and `free` are **deliberately absent** — v5 already trades that
redundant pair for the live paging rates, and reintroducing them in the WebUI
would be a divergence from v5, not a return to v4. `sin`/`sout` are `null`
until the second cycle and render `-`. Neither is coloured unless the user has
configured thresholds in `[memswap]`; there is no default ladder.

### 8.4 `gpu`

The stress test. Three behaviours no earlier component has.

**A computed title.** One card → its `name`; several cards all reporting the
same name → `{N} {name}`; otherwise `{N} GPUs`.

**A layout switch.** Summary when there is one card **or** `--meangpu` is set;
the per-card table otherwise. In summary mode with several cards the labels
become `proc mean:` / `mem mean:` / `temp mean:` — so the schema carries the
bare word and **the renderer composes** the colon and the `mean` suffix. A
schema cannot hold two forms of the same label (D3).

**A data-driven column drop.** The `mem` column disappears only when *no* card
reports memory. A card that reports nothing still shows `N/A`: hiding it
per-card would drop a cell and misalign heterogeneous rows (#3631).

Two v4 quirks that strict parity requires reproducing, both worth a comment in
the component so a later reader does not "fix" them:

- Summary mode averages across cards but takes its **colour from the first
  card's** `_levels`, not from the mean.
- Multi mode shows **no temperature at all** — only name, `proc`, and the
  conditional `mem`.

Temperature honours `--fahrenheit` through `serverArgs` (D4).

The TUI truncates the title to 17 characters and card names to 9. Those are
terminal-width constraints, not layout logic, and are **not reproduced** — the
browser has the room.

**This decision is gated on a manual smoke test, and the maintainer flagged it
as such.** A real card name can be far longer than the TUI's budget —
`NVIDIA GeForce RTX 3080 Ti Laptop GPU` is 37 characters, and the multi-card
title adds a count prefix on top. The `<h2>` is inside the plugin grid, so an
over-wide title can stretch its column and push the layout around.

The smoke test must look at `gpu` with a long card name, not just the short
one a test fixture happens to carry. If the title does distort the layout, the
fix is a **CSS constraint** — `max-width` with `text-overflow: ellipsis`, and
the full name in a `title` attribute so it stays readable on hover — never a
character count copied from the terminal. A browser truncates with the layout;
a terminal truncates with a slice.

## 9. The schema refactor (D2)

| File | Change |
|---|---|
| `glances/plugins/load/model_v5.py` | add `short_name`: `1 min`, `5 min`, `15 min` |
| `glances/plugins/load/render_curses_v5.py` | read `field_label()` instead of the hardcoded tuple list |
| `glances/plugins/gpu/model_v5.py` | add `short_name`: `proc`, `mem`, `temperature` |
| `glances/plugins/gpu/render_curses_v5.py` | read `field_label()`; keep composing the `:` and the `mean` suffix |
| `glances/plugins/network/render_curses_v5.py` | retrofit: read the schema instead of its hardcoded strings |

**Known exception, accepted for now:** D2 asks for one copy of each string, and
`gpu`'s `mem` ends up with three — the literal inside `_multi_rows()`
(`gpu/render_curses_v5.py`), the literal inside `PluginGpu.vue`'s memory cell,
and the `short_name` in the schema. The multi-card layout writes the word
*inside* each cell rather than in a header, so neither renderer can reach it
through `field_label()` without restructuring the row. Recorded rather than
fixed; the two literals happen to agree with the schema today, and only
`test_schema_declares_the_tui_short_names` pins the third copy.

**The non-regression proof is free and must be treated as binding:** every one
of these plugins has a `tests/test_plugin_<name>_render_curses_v5.py` that
pins its rendered strings. Those files must pass **unmodified**. If one needs
adjusting, the refactor changed the TUI's output — that is a stop signal, not
a test to update.

## 10. Reported, not fixed: `cpu`'s `core` field does not exist

`glances/plugins/cpu/render_curses_v5.py:183` builds the `idle_tag` (Windows)
branch of column 1 as `idle` / **`core`** / `dpc`. The schema declares no
`core` field — it declares `cpucore` — and v4 stores the value as
`stats['cpucore']` (`glances/plugins/cpu/__init__.py:231`). So on a platform
where `user` is absent, that cell resolves its label to the bare field name
and its value to nothing.

It is pre-existing and outside this group's scope. It is recorded here rather
than in a ledger because ledgers are deleted when a group closes, and this
must outlive G9-4.

**Obligation on G9-4:** the WebUI component reproduces the column *structure*,
but must not hardcode a `core` field it knows does not exist. Port the branch
against `cpucore` and leave a comment pointing at this section and at the TUI
line, so the two are fixed together. Porting a bug verbatim under the banner
of parity is not parity, it is propagation.

**Follow-up:** open an issue against the TUI renderer. Whoever fixes it should
check whether v4's own `msg_curse` shows a core count in that branch, and
whether any platform actually reaches it.

## 11. Failure modes

| Condition | Behaviour |
|---|---|
| `/api/5/all` omits a plugin (cycle 0) | `null` payload → the component's loading branch, per G9-3 |
| `/api/5/args` unreachable | `{}` — Celsius, and `gpu`'s mode decided by card count alone |
| `gpu` reports zero cards | The component renders nothing beyond its title, matching the TUI's early return |
| A card reports `null` for a field | `N/A`, never a hidden cell (#3631) |
| `sin`/`sout` before cycle 2 | `-` |
| A label missing from the schema | The field name, per `labelFor()` — degraded, never blank |

## 12. Testing

- **`node --test` units** for `formatCount` and `toFahrenheit`, including
  `formatCount`'s 1024 boundary in both directions (1023 stays an integer,
  1024 becomes `1.0K`) and the `1_048_576` step up to `M`.
- **Render assertions** through the probe for each of the four components,
  keyed by `data-plugin` (§6).
- **`gpu` needs both branches tested**: one card (summary), several cards
  (table), several cards with `--meangpu` (summary with `mean` labels), and no
  card reporting memory (the `mem` column absent). A single-fixture `gpu` test
  proves nothing about the component that has two layouts.
- **`cpu` needs both column-1 branches and all three column-3 variants**, with
  fixtures that distinguish key-absence from `null` — otherwise the two kinds
  of check in §8.1 are untested and interchangeable in practice.
- **The five TUI renderer test files of §9 must pass unmodified.**
- The probe's `/info` stub is keyed by plugin name (added in G9-3): each new
  plugin needs its own entry, or its labels resolve off another plugin's
  schema and the assertion observes an accident.
- **Manual UI smoke test, owed to the maintainer**, with `gpu`'s title width
  as its named point of attention (§8.4). The probe asserts text, not layout —
  only a human looking at the page catches a title that stretches its column.

## 13. Risks

| Risk | Mitigation |
|---|---|
| The D2 refactor changes TUI output | The five renderer test files must pass unmodified; any edit to them is a stop signal |
| `gpu`'s two layouts hide a bug in the untested branch | Both branches are required test cases (§12), not optional |
| The fourth prop starts a list that keeps growing | D5 names the trigger for revisiting: the third or fourth global concern |
| `serverArgs` is cached for the tab's life | Correct — CLI arguments cannot change while the server runs. Documented in `resolveArgs()` so nobody "fixes" it into a per-tick fetch |
| The `core` bug is ported into the WebUI | §10 makes the correct field explicit and requires a pointer comment |
| A long GPU card name distorts the layout, the TUI's 17-char truncation having been dropped | Named point of attention for the manual smoke test (§8.4); the fix if needed is CSS ellipsis, not a character count |

## 14. Deliverables

New: `PluginCpu.vue`, `PluginLoad.vue`, `PluginMemswap.vue`, `PluginGpu.vue`,
their registry entries, `resolveArgs()`, `formatCount`, `toFahrenheit`.

Modified: `AppShell.vue` (args fetch, `serverArgs` prop, `data-plugin` bind),
`PluginMem.vue` and `PluginNetwork.vue` (declare `serverArgs`), `api.js`,
`format.js`, the probe fixture, `test_webserver_v5.py`, and the five Python
files of §9.

Also modified: `css/v5.css`. `.gl-stat-grid` already generalised to three
columns, but the group still had to add `.gl-plugin-title` (the flex title row
the new components share) and `font-variant-numeric: tabular-nums` on
`.gl-stat-grid dd` — the scalar grids need jitter-free digits without
`.gl-num`'s 9ch floor, which is calibrated for a collection table.

Unchanged, and deliberately so: `levels.js`, `columns.js`, `labels.js`.

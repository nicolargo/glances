# G9-9A — v5 WebUI right column, batch 1 (`vms`, `containers`, `processcount`, `amps`): Design

**Status:** approved (2026-09-19)
**Sub-project of:** G9 (see the G9-1 spec §2.1 for the decomposition)
**Predecessors:** `2026-09-11-glances-v5-g9-6-webui-left-sidebar-design.md`,
`2026-09-12-glances-v5-g9-7-webui-left-sidebar-2-design.md`,
`2026-09-12-glances-v5-g9-8-webui-top-slot-design.md`,
`2026-09-12-glances-v5-webui-horizontal-degradation-design.md`
**Successor:** G9-9B — `processlist`, `programlist`, `alert`, and the
`--programs` CLI option (separate spec)

---

## 1. Goals

G9-8 closed the top row at 25 of the 32 plugins. Only `RIGHT_SLOT` remains:

    RIGHT_SLOT = vms, containers, processcount, amps, processlist, programlist, alert
                 ^^^  ^^^^^^^^^^  ^^^^^^^^^^^^  ^^^^

G9-9 is split in two because those seven plugins hold two very different
risk profiles. **G9-9A (this spec)** ports the four blocks that follow the
collection pattern G9-6/G9-7 already established, and takes the WebUI from
25 to **29 of 32** plugins. G9-9B ports the process list, its program
variant and the alert grid — column cascades, a capped row count, a
synthesized incident grid and a new CLI option.

One new mechanism is introduced here and is the reason `containers` leads
the batch: **per-block horizontal degradation**. `processlist` needs the
exact same mechanism in G9-9B, so it is built generic and proven on
`containers` first.

## 2. Out of scope

- **`processlist`, `programlist`, `alert`** — G9-9B.
- **A vertical row budget in the browser.** See D1.
- **The sort-column underline.** See D8.
- **Browser hotkeys.** Still out of scope for the WebUI, as in G9-5…G9-8.
- **Touching the TUI renderers.** This group reads them as the reference;
  it changes none of them.

## 3. Decisions taken before design (2026-09-19)

| # | Decision | Where |
|---|---|---|
| D0 | **G9-9 ships as two groups**, 9A (this spec) then 9B | §1 |
| D1 | **No vertical cap, no truncation counter, in 9A** | §4 |
| D2 | **`containers` ports the width-driven column cascade**, measured in the browser, rather than scrolling or using CSS breakpoints | §5 |
| D3 | **The cascade state lives in the component, not in `AppShell`** | §5.2 |
| D4 | **`Command` is excluded from `.gl-measuring`**, like `.gl-name` already is | §5.3 |
| D5 | **`vms` gets no width cascade** — the TUI has none either | §6.1 |
| D6 | **An AMP's multi-line result renders in ONE cell** (`white-space: pre-line`), not one `<tr>` per line | §6.2 |
| D7 | **`processcount` renders as a text line, not a table**; its `N/M` counter and sort indicator are deferred to 9B | §6.3 |
| D8 | **No sort-column underline** — `sort_key` is TUI runtime state with no server mirror | §9 |

## 4. No vertical budget in the browser (D1)

Three of the four TUI renderers cut their output with `row_budget()`:

- `containers/render_curses_v5.py:270-279` — truncates the list and relabels
  the name column `CONTAINER 7/25`;
- `vms/render_curses_v5.py:165-171` — same, `Name 3/12`;
- `amps/render_curses_v5.py:88-96` — truncates and appends `… +N lines`.

That budget is the output of the TUI's vertical fit pass, which exists
because a terminal has a fixed number of rows. A browser page scrolls, so
there is no budget to read and **nothing to derive one from**. The WebUI
therefore renders every row and every AMP line, and shows **no `N/M`
counter and no `… +N lines` marker** — inventing a cap in order to display
a ratio would be a fabricated mechanism, not parity.

This is a scope decision, not a permanent one: `processlist` in G9-9B does
get a cap and a counter, because hundreds of rows justify one. Container,
VM and AMP counts are bounded by what the host actually runs.

## 5. `containers`: two families of hidden columns

The TUI hides a `containers` column for two unrelated reasons. The WebUI
must keep them unrelated too, because only one of them needs measurement.

### 5.1 Data-driven columns (no measurement)

Ported as-is, computed from the payload on every render:

| Column | Shown when | TUI reference |
|---|---|---|
| `Engine` | more than one distinct `engine` among the items | `containers/render_curses_v5.py:264` |
| `Pod` | any item has a `pod_name` | `:265` |
| `/MAX` | not hidden by `disable_stats` (never by the data — see below) | `:295-298` |
| any | NOT listed in the payload's `disable_stats` | `:80` (the `hidden` seed) |

`show_mem_max` (`:298`) reads only `hidden` — the config's `disable_stats`
plus the `mem` → `memory_max` cascade (`:287-288`, disabling `mem` also
disables `/MAX`) plus the width cascade. Nothing reads `memory_limit` to
gate the column: a host where no container declares a limit still shows
`/MAX`, with the placeholder in every row. An earlier draft of this table
listed "a memory limit exists" as the rule; that was an invented mechanism,
found and removed during execution (`test_containers_shows_max_even_when_no_container_has_a_limit`).

`disable_stats` (config `[containers] disable_stats`) and `max_name_size`
reach the browser already: the model publishes both as metadata
(`containers/model_v5.py:220-221`) and `get_api_payload()` merges metadata
into the payload at top level. No new endpoint, no new config read.

Network units follow `serverArgs.byte`, as the TUI reads `view["byte"]`
(`:208`).

### 5.2 The width-driven cascade (D2, D3)

`_DROP_ORDER` (`containers/render_curses_v5.py:60`) drops the lowest-value
column first, one at a time, until the row fits:

    command → ports → memory_max → pod → engine → diskio → networkio → uptime → status

`CONTAINER`, `CPU%` and `MEM` are absent from the order and therefore
always survive.

- The order is copied into a new pure module, `js/v5/drop_order.js`,
  exporting `CONTAINERS_DROP_ORDER`, and is turned into a cascade of
  `{key: "drop_command", value: true}` entries.
- It is resolved by **the existing `resolveDegrade()`**
  (`js/v5/degrade.js:55`), which already takes a cascade plus a measure
  function and owns the "start from no flag every time, so a widening
  window gives the columns back" rule. `degrade.js` is not modified.
- The measurement lives in a new mixin, `js/v5/fit_block.js`: apply the
  candidate flags, `await nextTick()`, add `.gl-measuring`, read the
  `<table>`'s `scrollWidth` against the `<article>`'s `clientWidth`, remove
  the class. A `ResizeObserver` on the `<article>` re-runs the pass.

**Why the component and not `AppShell` (D3):** `AppShell` measures *zones*
(`[data-slot="…"]`) because the top and header cascades hide whole blocks —
that is the shell's business. A cascade that hides columns *inside* one
block is the component's business; `AppShell.vue` already states that split
as spec D7 ("a block that disappears is the shell's business; a block that
merely shrinks is the component's"). Putting the state in the component is
also what makes `fit_block.js` reusable verbatim by `processlist` in G9-9B,
which has the same shape of cascade (`_DROP_ORDER` a→h).

### 5.3 `Command` must not be measured at its natural width (D4)

`.gl-measuring` (`css/v5.css:252`) lets text expand to `max-content` so an
overflow is seen before anything is ellipsized. `.gl-name` is already
excluded, because its width cap is deliberate.

`Command` needs the same exclusion, and for a stronger reason: the TUI
budgets it at `_MIN_COMMAND_WIDTH = 8` precisely because the data is
unbounded (`_COL_GEOMETRY`, `:65`). Measured at its natural width, a single
200-character command line would push the row over the limit and drop every
droppable column on a window that has room for them. The rule becomes:

```css
.gl-measuring .gl-truncate:not(.gl-name):not(.gl-command) { … }
```

`.gl-command` carries a `max-width` floor of `24ch` (`PluginContainers.vue`),
not the TUI's 8-character (`_MIN_COMMAND_WIDTH`) budget — the two are not
equivalent. Consequence: the WebUI starts dropping columns at a wider window
than the terminal does, since `Command` is measured against a floor three
times as wide before the cascade even begins. This is the one CSS change in
the group.

### 5.4 Row shape

One `<table>`, header row first, no separate title row — `CONTAINER` **is**
the title in the TUI (`_build_header_row`, `:124`), exactly as `FILE SYS`
is for `fs` (G9-6 D6). Columns, in order: `Engine?` `Pod?` `CONTAINER`
`Status` `Uptime` `CPU%` `MEM` `/MAX?` `IOR/s` `IOW/s` `Rx/s` `Tx/s`
`Ports` `Command`.

Cell values and their tiers follow the TUI cell builders: `status` keeps
its own `_STATUS_ROLE` mapping (never `_levels`), `CPU%` takes
`_levels[name].cpu_percent`, `MEM` takes `_levels[name].memory_percent`,
and the `/MAX` limit is never coloured. The `status` map is reproduced
component-side as a `gl-level-*` class on the value `<span>`, resolving to
the same four tiers `_levels`-driven cells use — a status the map does not
list gets no class, exactly as the TUI's `ColorRole.DEFAULT` paints
nothing. A missing value renders `-`, the
WebUI's placeholder (`format.js` `MISSING`), NOT the `_` the containers
renderer uses: all 25 ported blocks already show `-`, the v5 TUI itself is
inconsistent here (`vms/render_curses_v5.py` `_fmt` returns `-`,
`containers` returns `_`), and a per-block placeholder would be a WebUI
inconsistency visible on one screen. Divergence 5.

## 6. The three other blocks

### 6.1 `vms` (D5)

A table with `Engine?` `Name` `Status` `Core` `CPU%` `MEM/MAX`
`LOAD 1/5/15min?` `Release`. `Engine` appears only with more than one
distinct engine (`vms/render_curses_v5.py:157`), `LOAD` only when the
engine publishes it (`:162`).

**No width cascade**, because the TUI defines none for `vms`: there is no
`_DROP_ORDER` to port, and inventing one would diverge. When the table is
wider than the column, the block scrolls horizontally — the browser's floor,
where the TUI's painter simply crops. Documented as divergence 4.

`MEM/MAX` is one cell carrying the `memory_percent` tier over both halves,
which is what the TUI already does deliberately (its docstring calls the
glued cell an intentional simplification of v4).

### 6.2 `amps` (D6)

No title, no column header — deliberate v4 parity
(`amps/render_curses_v5.py` module docstring). `CollectionBlock` already
supports this: a block that passes no `#head` slot gets no `<thead>` at all
(`CollectionBlock.vue:18`, the `ports` case from G9-7 D4).

Three columns: name (16ch), count, result. The count is hidden for a
regex-less AMP — there is nothing to count (`:76`). The name cell carries
the `count` tier and its prominent badge; on the TUI's continuation lines
it carries neither.

**Structural divergence:** the TUI emits one `Row` per result line with the
name and count cells blanked after the first (`:82`). The WebUI renders one
`<tr>` per AMP with the whole result in a single cell using
`white-space: pre-line`. The painted result is identical; the DOM is
smaller and the text stays selectable as one block. An AMP that produced
nothing yet (`result is None`) is skipped entirely, as in v4.

### 6.3 `processcount` (D7)

Not a table — one text line, mirroring
`processcount/render_curses_v5.py:73-113`:

    TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth

with the same omission rules: `(N thr)` only when `thread` is known
(issue #1463), `oth` computed as `total − running − sleeping`, and only the
`TASKS` title when `total` is absent (scheduler cycle 0) — never `TASKS 0`.

Two parts of the TUI line are **deferred to G9-9B**:

- the `30/215` truncation counter (`_count_text`, `:37`) — it reads
  `row_budget(view, "processlist", …)`, which does not exist until the
  process list is ported and capped;
- the `Threads sorted automatically by cpu_percent` indicator
  (`_sort_indicator_cell`, `:58`) — it reads `sort_key`, `auto_sort` and
  `programs` from the TUI's runtime view. `programs` gets a server mirror in
  9B (`--programs`); the sort key does not (D8).

## 7. Registry and layout

Four entries in `js/v5/plugins/index.js` with `slot: "right"`, in the TUI's
`RIGHT_SLOT` order (`curses_renderer_v5.py:75`) — `vms`, `containers`,
`processcount`, `amps`. `test_every_slot_orders_its_plugins_like_the_tui`
already fails on a wrong slot or a wrong order, and
`test_the_registry_renders_every_registered_plugin` on a misspelled slot.

Specs: `vms`, `containers` and `amps` are `collection` with `required:
["name"]`; `processcount` is `scalar` with `required: []` (at cycle 0 the
payload carries no `total`, and that is a hide rule, not a shape error).

The three collections pass `hidden = !!payload && rows.length === 0`: their
TUI renderers return `[]` on an empty collection, which is the G9-7 rule
for `ports`/`folders`/`irq`/`raid`/`smart`.

`AppShell` needs no change: the `right` slot is already declared in `ZONES`
and already styled (`.gl-slot-right`).

## 8. Tests

1. **Drift test** `tests/test_webui_v5_containers_drop_order_drift.py`:
   `containers._DROP_ORDER` against `CONTAINERS_DROP_ORDER`, evaluated
   through `node`, on the model of `test_webui_v5_smart_keys_drift.py`.
   Order and membership both compared; an empty JS list fails.
2. **`node --test`** on `drop_order.js` and on the pure column-visibility
   helpers (`showEngine`, `showPod`, `showMemMax`, `disable_stats`), which
   are extracted out of the `.vue` file precisely so they can be tested.
3. **Render probe** (`tests/test_webui_v5_render.py`): the four blocks
   render against real payload fixtures, the registry reports 29 plugins,
   an empty collection renders no block, and a `None` `result` AMP is
   skipped.
4. **Cascade through the probe:** forced widths produce the expected
   surviving column set, including the `Command` floor of D4 — the probe
   already drives the top-row cascade this way.

Fixtures use the real schema, not hand-written dicts (G9-6 lesson).

## 9. Divergences to record for the release changelog

| # | Divergence | Why |
|---|---|---|
| 1 | No `N/M` counter, no `… +N lines` | No vertical budget in a browser (§4) |
| 2 | A multi-line AMP result is one cell | Identical paint, simpler DOM (§6.2) |
| 3 | The sorted column is not underlined | `sort_key` is TUI runtime state; `--sort-processes` does not exist in `main_v5.py`. Same family as `--programs`, which G9-9B adds |
| 4 | `vms` scrolls instead of cropping | The TUI defines no cascade for `vms` (§6.1) |
| 5 | A missing `containers` value shows `-`, not `_` | The WebUI's single placeholder, used by all 25 ported blocks; the v5 TUI is itself inconsistent between `vms` (`-`) and `containers` (`_`) (§5.4) |

## 10. Risks

- **The `Command` measurement (D4) is the one place this group can go
  visibly wrong**: get the exclusion wrong and a wide window loses columns
  it has room for. The probe test in §8, item 4, exists for exactly this.
- **Per-block `ResizeObserver` feedback loops.** `AppShell.refit()` guards
  against re-entry with a `refitting` flag; `fit_block.js` must carry the
  same guard and the same "only re-render when the flag set actually
  changed" comparison, or a block can oscillate between two column sets.
- **`disable_stats` reaching the payload** is asserted from the model
  source here; the plan verifies it against a live `/api/5/containers`
  before the component relies on it.

## 11. Success criteria

- The four blocks render in the right column, in the TUI's order, with the
  same columns, the same values and the same tiers as their TUI renderers,
  and the WebUI's own `-` placeholder everywhere (divergence 5, §5.4) — not
  the `_` these TUI renderers print.
- Narrowing the window drops `containers` columns in `_DROP_ORDER`'s order;
  widening it gives them back.
- The drift test fails if either copy of the drop order is edited alone.
- The registry renders 29 of 32 plugins; the full suite is green.

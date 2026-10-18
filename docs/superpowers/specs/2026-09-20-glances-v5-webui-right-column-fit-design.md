# Glances v5 WebUI — right-column vertical fit and static column widths

**Date:** 2026-09-20
**Branch:** `develop-v5`, on top of the G9-9B commit
**Origin:** browser smoke test of G9-9B. Six defects reported by the maintainer,
none of them findable by the unit suite: four on `processlist`, two on the
`alert` grid.

---

## 1. The six reported defects

| # | Block | Reported |
|---|---|---|
| P1 | processlist | Every process is rendered, so the alert block is below the fold. The block's height must adapt to what the rest of the column needs, alerts first — with the TUI's own priority system. |
| P2 | processlist | `Command` must grow into whatever width is left instead of cropping while space is free. |
| P3 | processlist | Column widths are not sized to their data and change between refreshes. They must be static AND sized to what they hold — `S` never shows more than one character and must not be as wide as `USER`. |
| P4 | processlist | A long user name wraps the row onto two lines. `USER` must crop. |
| A1 | alert | Column widths let a row wrap onto several lines. Not acceptable. |
| A2 | alert | Same rule as everywhere: static widths, each sized to its data. |

P1 is not a setting: the browser has no vertical fit pass at all. The G9-9B spec
records this twice, in its §10 divergence table (#3 and #8), as a deliberate
omission — "the browser has no vertical fit pass (…) it scrolls instead". That
omission is what this design reverses.

P3/A2 and P2 pull in opposite directions under the current mechanism, which is
why they are one design and not two fixes: today every width is content-driven
(`table-layout: auto`), so widths jitter (P3) *and* `.gl-command`'s cap crops a
column that has room (P2). Making widths static is also what lets `Command` be
the one elastic column.

## 2. The reference, and why it is not negotiable

Every value below already exists, decided, in the terminal renderer. Nothing in
this design invents a width, a threshold or a priority order. Each is cited with
its `file:line` so an implementer can verify the claim rather than trust it.

### 2.1 Vertical budget

`plan_right_column()` — `glances/outputs/curses_renderer_v5.py:969`. A pure,
analytic solver: given the available body height and the real item counts, it
returns `{plugin: max data rows}` with no frame rebuild needed to evaluate a
candidate.

- Nominals `curses_renderer_v5.py:877-879` — workloads 10, alerts 10,
  processes 20. Growth ceiling `_MAX_WORKLOADS = 20` at `:881`.
- Shrink ladder `_SHRINK_STEPS` `:947-959` — a→k.
- Terminal steps l and m `:961-966`, unlocked only when an alert is active.
- Active-alert floor `floor_alerts` `:1028`, and the steps that honour it
  `:1085-1093`.
- Max-min workload split `_split_workloads` `:923-942`.
- Alert block row cost `_alert_block_height` `:610-627`.
- Slack refund to the process block `grow_processes` `:1053-1058`, applied on
  BOTH branches (`:1068`, `:1097`).
- Blocks under the budget: `_ELASTIC_RIGHT` — `glances_curses_v5.py:710` —
  `{vms, containers, processlist, programlist, alert, amps}`. `processcount` is
  the only non-elastic right-column block.

### 2.2 processlist column widths

`glances/plugins/processlist/render_curses_v5.py:54-66`, annotated in the source
as v4 parity:

```
CPU% 5   MEM% 5   VIRT 5   RES 5   PID 7   USER 10
THR 3    NI 3     S 1      TIME+ 8   R/s 5   W/s 5
```

`Command` has no fixed width; its floor is `_MIN_COMMAND_WIDTH = 8` (`:87`).
`_MAX_ROWS = 20` (`:66`) is only the fallback used when no budget is published
(`:414`, `row_budget(view, "processlist", _MAX_ROWS)`).

`_format_username` (`:158-162`) crops **only when the name is longer than
`_W_USER`**: a 10-character name is shown whole, an 11-character one becomes its
first 9 characters plus `+`. `None` renders `?`. The boundary is off by one from
the obvious reading and §7.3 pins it.

### 2.3 alert grid geometry

`glances/outputs/curses_renderer_v5.py:525-540`:

```
GLYPH 1   TIME 8   DURATION 8   LEVEL 8
TARGET  floor 12   (elastic: takes its natural width when TOP is hidden)
TOP     floor 22   (the elastic column once shown)
```

Drop thresholds, in block columns: TOP below `_ALERT_W_WITH_TOP = 66`, LEVEL
below `_ALERT_W_WITH_LEVEL = 43`, DURATION below `_ALERT_W_WITH_DURATION = 34`.
TOP drops first, by construction (`:538-540`), so no terminal that renders the
block correctly today changes behaviour.

## 3. Decisions taken with the maintainer

| # | Decision | Rejected alternative, and why |
|---|---|---|
| D1 | `body_height` is the **viewport** minus the chrome, and budgets the **right column only**. The left column keeps its natural height; the page scrolls when it is taller. | Budgeting both columns: the TUI never budgets its left sidebar (`_build_fitted_frame:607-630` calls `_fit_right_column` alone; `_paint_sidebar` simply clips), and the 11 left blocks have no defined priority order to copy. |
| D2 | `plan_right_column` is **ported to JS**, pinned by a **behavioural** drift test that runs both solvers over a case matrix. | A server endpoint: the pass re-runs on every resize and every payload, so a layout decision would wait on the network. Sharing only the constants: the subtlety is in the loop, which would stay duplicated and unverified. |
| D3 | The TUI's widths are adopted **verbatim**, and the browser's byte formatter adopts the terminal's decimal-drop so `VIRT`/`RES` fit in 5. | Widening VIRT/RES to 7 for the shared `formatBytes`: keeps divergence §10 #5 open, shows a different string from the terminal for the same datum, and spends 4 columns that P2 wants for `Command`. Measuring widths from live data: not static — a wider PID at the next refresh re-lays the table out, which P3 forbids in as many words. |
| D4 | The alert grid gets the TUI's width cascade (TOP → LEVEL → DURATION) through the existing `fitBlockMixin`. | Crop-and-scroll only: `TARGET` — the column that says what the alert is about — would crop while `TOP PROCESSES` stayed on screen, the exact inverse of what the terminal does. |
| D5 | The vertical rhythm is pinned: an explicit `--gl-row` line-height token, and the right column's inter-block gap set to exactly one row. | Fractional row arithmetic to absorb the real gap: `cost()` stops being integral and can no longer be drift-tested against Python. |
| D6 | `programlist` is in scope although only `processlist` was reported. | The two render the same columns through the same shared helpers (`process_shared.js`); fixing one leaves two divergent process tables in the same column. |
| D7 | The width cascade keeps **measuring**; the threshold is expressed in CSS through a `min-width` fed by a column count (§5.1). | Computing `content` in JavaScript, which this spec originally specified and the maintainer approved: it forces a column→pixel conversion in JS that the render probe cannot cover. Amended during planning, on the maintainer's approval. |

## 4. The vertical budget

### 4.1 Ownership

The budget lives in `AppShell`, not in the components. `AppShell.vue`'s own D7
rule decides it: *"a block that disappears is the shell's business; a block that
merely shrinks is the component's"*. A row budget does both — a quota of 0 hides
`vms`, `containers` or `processlist` outright (ladder steps g and l, mirroring
`cost()`'s own `if n_processes and candidate["processes"]` at
`curses_renderer_v5.py:1044`) — and it arbitrates *between* blocks, which no
single component can do. It descends as a prop, exactly like `degrade`.

### 4.2 New module: `js/v5/row_budget.js`

Pure — no DOM, no fetch, no imports — so `node --test` can load it, the same
contract `degrade.js` and `processlist_columns.js` already state in their
headers. It exports the port of `plan_right_column`, plus `splitWorkloads` and
`alertBlockHeight`, plus the constants of §2.1.

### 4.3 Inputs

| `plan_right_column` argument | Browser source |
|---|---|
| `n_vms`, `n_containers`, `n_processes` | `results[<plugin>].data.length` |
| `n_alerts`, `n_ongoing` | the `/api/5/alert/incidents` envelope (`{is_initializing, incidents}`) |
| `amps_height` | computed, see §4.6 |
| `static_heights` | `{processcount: 1}` |
| `body_height` | measured, see §4.4 |

### 4.4 Measurement, and why it cannot oscillate

This is the one genuinely delicate point. `body_height` must be derived from
something the budget itself does **not** change:

```
bodyHeightPx  = viewportHeight − slotTop − footerHeight − padding
availableRows = floor(bodyHeightPx / rowPx)
```

Never `slot.clientHeight`: the slot's height is this pass's own output, and the
feedback loop would be immediate. This is the same reasoning `fit_block.js`
already spells out on the horizontal axis — the right slot is the body grid's
`1fr` track, so its width comes from the remaining grid space and never from its
content — transposed to the vertical axis, where it is not free and has to be
engineered.

`slotTop` does depend on the header and top-row heights, which the horizontal
cascade may change. The TUI has the identical dependency and resolves it by
ordering: the vertical fit runs **last**, and `glances_curses_v5.py:617-619`
says why — "the body height it budgets against depends on the TOP row height,
which the horizontal cascade above is free to change". The browser keeps that
order: horizontal cascades first, vertical budget last.

An in-flight guard mirrors `fitBlockMixin.fitting` and `AppShell.refitting`, so
a resize fired by the pass's own DOM writes is a no-op re-entrant call.

### 4.5 The row unit (D5)

`cost()` charges one blank line between blocks
(`curses_renderer_v5.py:1051`: `sum(heights) + max(0, len(heights) - 1)`). For
the TUI's integer arithmetic to stay exact in the browser, the right column's
inter-block gap must be exactly one row.

Today the gap is `calc(var(--gl-gap) * 2)` = `1rem` while a row is
`normal` line-height on `--gl-size-base: 0.88rem` — font-dependent, and
therefore resolved only by a browser. An earlier draft of this section called
`1.056rem` a measured value; it was not, it was `0.88 × 1.2` derived from the
usual `normal` ratio, and no browser was involved. Treat the mismatch as real
but its size as unknown: the point stands either way, because a gap that is not
*exactly* one row drifts by a fraction of a row per block boundary, and the
right column stacks up to sixteen of them. §7.4's browser smoke is what settles
the number.

Remedy: declare `--gl-row` on `:root` next to `--gl-col`, apply it as an
explicit `line-height`, and set `.gl-slot-right`'s gap from it.

**Accepted consequence:** this pins the global vertical rhythm, left column
included. The expected visual delta is under 5 % of a line, but it is a change
outside the six reported defects and is recorded here as such.

### 4.6 `amps`

The TUI emits one row per result line, blanking the name and count after the
first; the browser puts the whole multi-line result in one `pre-line` cell
(G9-9A spec D6, `PluginAmps.vue:26-29`). The row cost is the same either way:

```
ampsHeight = 1 + Σ over visible items of max(1, lines(item.result))
```

Ladder step j truncates `amps` to what is left, keeping at least a `+N lines`
marker. In the browser that means clamping the rendered lines inside the
`pre-line` cell rather than dropping whole rows.

### 4.7 Consumption

Each elastic component slices its payload to `rowBudget[<its name>]`.
`processlist` and `programlist` compose that with the existing config cap:

```
effective = min(rowBudget ?? Infinity, maxProcessesDisplay ?? Infinity)
```

`[outputs] max_processes_display` stays a hard ceiling that available height may
never raise. This is the browser's counterpart of the TUI's
`row_budget(view, "processlist", _MAX_ROWS)` fallback chain
(`processlist/render_curses_v5.py:414`).

### 4.8 When measurement is unavailable

Render probe, hidden tab, detached node: **no budget**, everything renders up to
`maxProcessesDisplay`. This is `degrade.js`'s existing rule, applied verbatim —
"an unusable reading means *cannot measure*, and the answer is always `true`: a
DOM without layout, a hidden tab or a detached node must never hide the user's
stats" (`degrade.js`, `fits()`).

### 4.9 Stacked layout

Below the `48rem` breakpoint `.gl-zone-body` stacks the columns
(`AppShell.vue:488-494`): the right column is no longer beside the left one but
underneath it, so budgeting it to viewport height would hide processes for no
reason. **The vertical budget is disabled below the breakpoint**; the page
scrolls, as it does today. The TUI has no equivalent case, so this is a new
divergence and §9 records it.

## 5. The width model

### 5.1 The cascade keeps measuring; CSS supplies the threshold

Under `table-layout: fixed` a table never overflows its container — the columns
absorb the shortfall instead — so `scrollWidth > clientWidth` would stop
becoming true and the cascade would never start. The trigger has to become the
TUI's own: `Command` falling below `_MIN_COMMAND_WIDTH = 8`.

The obvious way to express that is to have `measure(flags)` compute `content`
from the column widths instead of reading it. **Rejected**, after the maintainer
approved it and this plan's detail work showed why: the widths are character
columns and `available` is pixels, so that design forces a column→pixel
conversion in JavaScript — a run-time measurement of `--gl-col` through a ruler
element. That is precisely the ground the WebUI has already lost once: `ch`
resolved to `0.5em` under the shipped font stack and nothing caught it before a
browser smoke test. A second hand-rolled unit conversion, which the render probe
cannot cover because it has no layout engine, is not worth a performance bonus
nobody asked for.

**Adopted instead:** let the browser do the conversion and hand it a plain
integer. The component sets a custom property; the stylesheet turns it into a
width:

```css
.gl-process-table {
  table-layout: fixed;
  min-width: calc(var(--gl-fixed-cols) * var(--gl-col));
}
```

`--gl-fixed-cols` = Σ of the still-visible fixed widths + separators + 8. The
table then overflows its container **exactly** when `Command` would fall below
its floor, so `scrollWidth > clientWidth` becomes true at the terminal's own
threshold.

Consequences:

- `degrade.js`, `fit_block.js`, `resolveDegrade` and `fits()` are **untouched**,
  along with their existing coverage.
- The only arithmetic in JavaScript is a sum of integers. No unit conversion.
- The render probe keeps driving the cascade through its
  `available`/`content` fixtures exactly as today.
- `Command` takes `width: auto` under fixed layout, so it grows into whatever is
  left (defect P2) and can never drop below 8, because the `min-width` reserves
  it.

**Accepted cost:** the pass still re-renders once per notch, up to nine DOM
cycles. That was a secondary benefit of the rejected design, never a
requirement.

The alert grid uses the same mechanism, with its three thresholds (§2.3).

`PROCESSLIST_DROP_ORDER` (`processlist_columns.js`) is unchanged, and so is
`tests/test_webui_v5_processlist_drop_order_drift.py`.

### 5.2 New module: `js/v5/process_widths.js`

Pure, same contract. Holds the twelve widths of §2.2 and `MIN_COMMAND_WIDTH`,
expressed as character counts. The CSS derives from them in `--gl-col` units —
never `ch`, which resolves to `0.5em` under the shipped font stack and would
render 0.83 of every intended character (`css/v5.css:299-303`, and the
per-declaration allowlist in `tests/test_webui_v5_tokens.py`).

### 5.3 Separator arithmetic

The TUI's inter-cell separator is one character. The current padding is
`var(--gl-gap)` = `0.5rem` ≈ 0.57 column (`css/v5.css:357-360`). Setting it to
`var(--gl-col)` makes `Σ widths + (n − 1)` exactly the terminal's formula — the
same trick as the vertical gap in §4.5, on the other axis.

### 5.4 `width: 100%` on the last cell

`[data-slot="right"] .gl-table td:last-child { width: 100% }`
(`css/v5.css:375-378`) must be excluded from the fixed-layout tables: under
`table-layout: fixed` it would claim the whole width. It stays for `amps` and
`containers`, which keep the automatic layout and still need it — that rule was
introduced for exactly those blocks, measured.

`tests/test_webui_v5_tokens.py::test_the_right_column_gives_its_slack_to_the_last_cell`
pins that rule and will need its selector updated. Its assertions must not be
weakened: the rule must still be shown to apply to the automatic-layout blocks.

### 5.5 Two formatter ports

| Port | Source | Closes |
|---|---|---|
| username crop (see §2.2 for the boundary) | `processlist/render_curses_v5.py:158-162` | §10 #6, defect P4 |
| byte decimal-drop at ≥ 100 | `processlist/render_curses_v5.py:199-212` | §10 #5, makes VIRT/RES fit in 5 |

The byte formatter is more than its headline rule: it also renders `?` for an
unparseable or negative value and `<n>B` below 1 K
(`processlist/render_curses_v5.py:205-212`). Port the whole function, not the
one branch that motivates it.

Port the **crop and the rounding, never the padding**. Both terminal functions
end in `ljust`/`rjust` because curses has no columns; here the `<colgroup>` and
`text-align` do that job, and copied padding would ship trailing spaces into the
DOM and defeat the ellipsis.

The crop is the real cause of P4's two-line rows — not a missing `nowrap`. A
`nowrap` alone would hide the symptom and leave the column wider than its
neighbours' content for one outlier user name.

`format.js` already carries two byte formatters (G9-7 added a second one for
`smart`, because `globals.auto_unit` is not the one `formatBytes` mirrors);
this is a third, and the module comment must say which surface each serves.

### 5.6 `.gl-command`

**Not removed.** `containers` depends on it and keeps its measure-driven
cascade, and `css/v5.css:296-299` states why the cap has to live globally: the
`.gl-measuring` exclusion exempts `.gl-command` for every consumer, so the cap
that makes the exclusion safe cannot live in one component's scoped style.

Only `processlist` and `programlist` stop using the class; their truncation now
comes from the column width itself.

### 5.7 The alert grid

A `<colgroup>` carrying GLYPH 1 / TIME 8 / DURATION 8 / LEVEL 8, TARGET floor
12, TOP floor 22 and elastic; `fitBlockMixin` with the three thresholds of §2.3.
Rows stop wrapping because the layout is fixed and each cell truncates, which is
A1; the widths are the terminal's, which is A2.

## 6. Files

**New**

- `glances/outputs/static/js/v5/row_budget.js`
- `glances/outputs/static/js/v5/process_widths.js`
- `tests/test_webui_v5_row_budget_drift.py`
- `tests/test_webui_v5_width_drift.py`
- `tests/js/row_budget.test.mjs`

**Modified**

- `AppShell.vue` — measurement, solver call, `rowBudget` prop, pass ordering
- `PluginProcesslist.vue`, `PluginProgramlist.vue` — colgroup, budget, formatters
- `PluginAlert.vue` — colgroup, cascade, budget
- `PluginAmps.vue` — natural height, step-j clamping
- `css/v5.css` — `--gl-row`, separator, fixed-layout exclusions
- `format.js` — the two ported formatters
- `tests/fixtures/webui_render_probe.js` — height model (§7)
- `tests/test_webui_v5_tokens.py`, `tests/test_webui_v5_render.py`

## 7. Tests

### 7.1 Drift tests

| File | Pins | Against |
|---|---|---|
| `test_webui_v5_row_budget_drift.py` | solver behaviour over the case matrix | `plan_right_column` |
| `test_webui_v5_width_drift.py` | 12 process widths + `MIN_COMMAND_WIDTH`; 4 alert widths + 2 floors + 3 thresholds | `render_curses_v5.py:54-66,87`; `curses_renderer_v5.py:525-540` |

The row-budget test is **behavioural**, not textual: the existing drift tests
compare constant lists, which cannot express an algorithm. It runs both solvers
over the cartesian product of `body_height` × `n_vms` × `n_containers` ×
`n_processes` × `n_alerts` × `n_ongoing` × `amps_height` and asserts identical
output dicts, in one `node` invocation with JSON in and out.

### 7.2 Node tests

`tests/js/row_budget.test.mjs` covers the readable edge cases by name: the
active-alert floor, terminal steps l and m, the slack refund on both branches,
the max-min split with a sparse block beside a crowded one.

### 7.3 Formatters

Each ported formatter tested against its reference strings, including the
boundary (decimal kept below 100, dropped at 100) and a user name exactly at the
crop length.

### 7.4 The render probe — the real cost centre

`tests/fixtures/webui_render_probe.js` has no layout engine; its `FakeElement`
models `scrollWidth` and nothing else. Consequences, stated plainly:

1. The solver itself is fully testable — it is pure, which is the whole point of
   the split.
2. The **measurement** (`viewportHeight − slotTop − footerHeight`) is not,
   without adding a height model to the probe.
3. This design adds one (`clientHeight` / `getBoundingClientRect` on
   `FakeElement`) rather than shipping half the mechanism uncovered.

This is harness surgery the G9-9B ledger already deferred once, for the
untested intra-tick carry-over. **It is the least predictable estimate in this
batch**, and the most likely place for the plan to be wrong.

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Vertical oscillation: budget → height → resize → budget | §4.4 — measure from the viewport, never from the slot; in-flight guard; vertical pass ordered last |
| R2 | Probe height model costs more than estimated | §7.4 — named as the batch's weakest estimate; it is the first task, so the cost is known before anything depends on it |
| R3 | `--gl-row` changes the left column's rhythm | §4.5 — accepted and recorded; expected under 5 % of a line, verified by browser smoke |
| R4 | `table-layout: fixed` interacting with rules written for automatic layout | §5.4 — one known rule, its pinning test named |
| R5 | A width claimed from the TUI that is not actually the TUI's | Every value in §2 carries its `file:line`; each task must verify its own claims against the source and is entitled to contradict this spec with evidence rather than comply |

R5 is procedural and deliberate. Six factual errors in the controller's briefs
were caught this way during G9-9B, none shipped; two further defects were
stopped because a suggestion was phrased as a question rather than an
instruction. Both practices carry over.

## 9. Divergences after this batch

**Closed:** §10 #3 and #8 (a vertical fit pass now exists), #5 (byte formatter
aligned), #6 (`USER` crops).

**Still open:** #1 and #4 (the live sort key is TUI runtime state with no server
mirror), #2 (no alert in the footer, by design), #7 (Windows `nice` labels).

**New:** the vertical budget is inactive in the stacked layout below `48rem`
(§4.9). The TUI has no equivalent case.

## 10. Out of scope

- The left column's vertical behaviour (D1).
- `containers`' width mechanism, which keeps its measure-driven cascade (§5.6).
- The `--percpu` flag defect recorded in the G9-9B handoff: a separate issue,
  one layer below, and unrelated to layout.
- `.gl-sorted`'s duplication across the two process components, pending
  `containers`/`vms` closing their own underline gap.

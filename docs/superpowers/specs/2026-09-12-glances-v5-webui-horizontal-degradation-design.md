# Horizontal degradation in the v5 WebUI: Design

**Status:** approved (2026-09-12)
**Predecessors:** `2026-09-06-glances-v5-g9-3-webui-scaling-design.md`, `2026-09-06-glances-v5-g9-4-webui-plugins-design.md`, `2026-09-11-glances-v5-g9-5-webui-layout-header-design.md`, `2026-09-11-glances-v5-g9-6-webui-left-sidebar-design.md`

---

## 1. Goals

When the browser narrows, the v5 WebUI wraps: the header blocks and the top
row fall onto extra lines (`flex-wrap: wrap`). The TUI never wraps. It
degrades — hiding the least useful detail first, then whole blocks — and
finally lets curses clip what still overflows.

This group gives the WebUI the TUI's behaviour:

1. **A plugin never moves to another line.**
2. **Stats are hidden progressively, in the TUI's own priority order**, driven
   by measurement, not by invented breakpoints.
3. **Then the stats are cropped**, as curses clips.
4. **Then the zone scrolls horizontally** — the browser's floor, where a
   terminal user would have resized the window (D4).

## 2. Out of scope

- **The body columns.** `left` and `right` do not wrap; they switch to one
  column under `48rem` (G9-5 D3's `@media` rule). Unchanged here.
- **The vertical fit.** The TUI's row budget and its `N/M` truncation counter
  stay out of the browser (G9-6 §2); the page scrolls vertically.
- **Porting `quicklook`, `percpu`, `npu`, `mpp`.** Two TUI cascade steps act on
  `quicklook` and are therefore inert here — declared, not omitted (D5).
- **`--full-quicklook`.** The TUI exempts that mode from the cascade because it
  owns the whole width through its own sibling-hiding; the WebUI has no such
  mode yet.
- **The `ch` / font-stack defect** (G9-6, `[[project_v5_webui_ch_unit_font_stack]]`):
  this group measures rendered pixels, so it is unaffected — but the maintainer's
  decision on `--gl-font` is still pending.

## 3. Decisions taken before design (2026-09-12)

| # | Decision | Consequence |
|---|---|---|
| D1 | **Scope: the header zone and the top row** | The two zones that wrap today |
| D2 | **Measure-driven, like `_build_fitted_frame`** — never threshold-driven | A long hostname, a long alias or a long GPU name degrades at the right moment; CSS container queries with fixed breakpoints were rejected for the reason G9-3 and G9-4 rejected invented cascades |
| D3 | **The TUI's cascades, in the TUI's order**, guarded against drift by a test that imports the Python tuples | §4.1 |
| D4 | **Floor: crop, then scroll horizontally** | Nothing is lost on a phone: what overflows is reachable, and no plugin wraps |
| D5 | **The two `quicklook` steps are declared "not applicable"**, not omitted | The drift test compares 1:1 with the TUI; porting `quicklook` later fails the test instead of silently skipping its steps |
| D6 | **`degrade` travels as a fifth prop**, not `provide`/`inject` | G9-4 D5 said to revisit at the third or fourth cross-cutting concern; this is the third, and the prop stays — explicit, and the render probe observes it. Revisit at the fourth |
| D7 | **Hiding a whole block is the shell's job; shrinking a block is the component's** | Mirrors the TUI, where `_build_fitted_frame` filters `frame.top` while `mem`/`cpu` read `view["mem_cols"]`/`view["cpu_cols"]` |

## 4. Measured inputs

### 4.1 The TUI cascades

`glances/outputs/glances_curses_v5.py`:

```python
_DEGRADE_STEPS = [                    # TOP row, lines 62-70
    ("mem_cols", 1),                  # (a) hide MEM 2nd column
    ("cpu_cols", 2),                  # (b) hide CPU 3rd column
    ("cpu_cols", 1),                  # (c) hide CPU 2nd column
    ("quicklook_freq_only", True),    # (d) "Frequency" header + shrink quicklook
    ("hide_quicklook", True),         # (e) hide quicklook block
    ("hide_memswap", True),           # (f) hide swap block
    ("hide_gpu", True),               # (g) hide gpu block (last resort)
]
_HEADER_DEGRADE_STEPS = [             # header, lines 87-94
    ("hide_cloud", True),             # (0) opt-in block, first to go
    ("hide_ip_location", True),       # (1) drop the ip geolocation string
    ("hide_os_info", True),           # (2) drop the system OS/kernel string
    ("hide_now", True),               # (3)
    ("hide_ip", True),                # (4)
    ("hide_uptime", True),            # (5) last resort
]
```

- **The loop** (`_build_fitted_frame`, `_fit_header`): rebuild the frame with
  one more flag, re-measure the real block widths, stop as soon as the row
  fits. The two cascades are independent and their flags coexist in one `view`.
- **The fit tests** (`_top_fits`, `_header_fits`):
  `sum(widths) + (n - 1) * gap <= max_x`, with `_TOP_GAP_MIN = 1` and
  `_HEADER_GAP = 3`. Zero or one block always fits.
- **The floor** (`_top_row_gaps`, `_paint_top_row`): when even the minimum gaps
  do not fit, every gap collapses to the minimum and curses clips the overflow.
  Blocks are never moved to another line.
- **The shrink flags**: `mem_cols` (default 2, clamped 1..2 — at 1 the second
  column *and* the line-1 `active` pair go, `mem/render_curses_v5.py:92-100`);
  `cpu_cols` (default 3, clamped 1..3, `cpu/render_curses_v5.py:127-138`).

### 4.2 The WebUI today

`AppShell.vue`: `.gl-zone-header` is `flex-wrap: wrap` with `column-gap: 3ch`;
`.gl-slot-top` is `flex-wrap: wrap` with `justify-content: space-between` and
`gap: calc(var(--gl-gap) * 2)`; the body grid switches to one column under
`48rem`. No test pins any of it (checked: no `flex-wrap`, `48rem` or
`space-between` assertion under `tests/`).

The `top` slot holds `cpu`, `gpu`, `mem`, `memswap`, `load`; the header holds
`system`, `ip` (left) and `uptime`, `cloud`, `now` (right). `quicklook`,
`percpu`, `npu` and `mpp` are not ported.

### 4.3 Browser measurement (spiked 2026-09-12, headless Chrome)

`.superpowers/sdd/2026-09-12-glances-v5-webui-horizontal-degradation/spikes/measure.html`
(git-ignored): a `flex-wrap: nowrap` row of four blocks
(`flex: 0 0 auto`, `white-space: nowrap`) in a 400px container.

| Measurement | Value |
|---|---|
| container `clientWidth` | 400 |
| per-block `scrollWidth` | 354, 354, 346, 354 |
| natural sum (+ 3 gaps of 8px) | 1432 |
| after hiding one block | 1070 |
| after hiding two | 716 |

So: a block's **natural** width is readable with `scrollWidth` even while the
row overflows, the sum updates synchronously when a block is hidden, and the
row overflows instead of wrapping — which is already the "crop" behaviour.

## 5. `degrade.js` — the cascade module

New pure module, `glances/outputs/static/js/v5/degrade.js`: no DOM, no fetch,
testable under `node --test`.

```js
export const TOP_CASCADE = [
	{ key: "mem_cols", value: 1 },
	{ key: "cpu_cols", value: 2 },
	{ key: "cpu_cols", value: 1 },
	{ key: "quicklook_freq_only", value: true, notApplicable: "quicklook is not ported" },
	{ key: "hide_quicklook", value: true, notApplicable: "quicklook is not ported" },
	{ key: "hide_memswap", value: true },
	{ key: "hide_gpu", value: true },
];
export const HEADER_CASCADE = [ /* hide_cloud … hide_uptime, same shape */ ];

export function fits({ content, available }) { … }              // content <= available
export async function resolveDegrade(cascade, measure) { … }    // returns the flags to apply
```

- `fits` compares the zone's content width with its available width. The TUI
  computes `sum(widths) + (n - 1) * gap` because curses has no layout engine;
  the browser has one, so the shell reads `scrollWidth` and `clientWidth` and
  asks it. Same rule, measured instead of recomputed — and no gap constant to
  keep in sync with the CSS.
- An unusable reading (`0`, `NaN`, a detached node) returns `true`: never
  degrade on a bad measurement.
- `resolveDegrade` starts from **no flags**, calls `measure(flags)` — which the
  caller implements by applying the flags, letting the view update and
  measuring — and applies one cascade entry at a time until `fits` holds or the
  cascade is exhausted. Steps marked `notApplicable` are applied like any other
  (they change nothing today), so the order and the count stay identical to the
  TUI's.
- `measure` is injected, which is what makes the loop testable without a DOM
  and what lets the render probe drive it (§10).

## 6. The loop in `AppShell`

- One `ResizeObserver` per zone (header, top), created on mount, disconnected on
  unmount. `ResizeObserver` absent (the render probe's sandbox, an old browser)
  → no observer, no flags, everything renders: the pre-group behaviour.
- On a size change, and after **every** payload update — the TUI re-fits every
  frame, and a value widening from `0b` to `10.2Mb` changes the row — the shell
  runs `resolveDegrade` for each zone with a `measure` that writes the candidate
  flags into reactive state, `await nextTick()`, then reads the zone's
  `scrollWidth` and `clientWidth`. Two numbers per pass, no gap constant, no
  `getComputedStyle`.
- The resolved flags are stored per zone and passed down as the `degrade` prop.
  The shell re-renders only when the resolved flag set differs from the current
  one, which also stops an observer feedback loop.
- **Restart from zero on every resize**, like the TUI rebuilding from
  `_build_view`: widening the window brings hidden stats back.

## 7. Component contracts

| Flag | Applied by | Effect |
|---|---|---|
| `hide_cloud`, `hide_now`, `hide_ip`, `hide_uptime`, `hide_memswap`, `hide_gpu` | `AppShell` | The block is not rendered at all (like the TUI filtering `frame.top`) |
| `mem_cols: 1` | `PluginMem` | The second `<dl>` is dropped — `active`, `inacti`, `buffer`, `cached`. Net effect identical to the TUI, whose line-1 `active` pair lives in this column since G9-5 A1 |
| `cpu_cols: 2` then `1` | `PluginCpu` | At 2 the third column (`ctx_sw`, `inter`, `sw_int`, `guest`) is dropped; at 1 the second (`idle`, `irq`, `nice`, `steal`) as well. The existing selection rules (`idle_tag`, the conditional third column) are untouched: only the number of rendered columns changes |
| `hide_ip_location` | `PluginIp` | `public_info_human` is dropped; both addresses stay |
| `hide_os_info` | `PluginSystem` | `hr_name` is dropped; the hostname stays |
| `quicklook_freq_only`, `hide_quicklook` | nobody | Declared, inert (D5) |

Every component declares the prop, as it declares `serverArgs` — an undeclared
prop becomes a fallthrough attribute (G9-4 §5).

## 8. CSS

| Rule | Before | After |
|---|---|---|
| `.gl-zone-header` | `flex-wrap: wrap` | `flex-wrap: nowrap`, `overflow-x: auto` |
| `.gl-slot-header-left`, `.gl-slot-header-right` | `flex-wrap: wrap` | `flex-wrap: nowrap` |
| `.gl-slot-top` | `flex-wrap: wrap`, `justify-content: space-between` | `flex-wrap: nowrap`, `justify-content: space-between` kept, `overflow-x: auto` on the zone |
| each block | — | `flex: 0 0 auto`, so a block keeps its natural width and the row overflows rather than squeezing |

`space-between` stays: it is the TUI's own distribution rule (first block flush
left, last flush right, gaps shared). The body's `48rem` rule is untouched.

## 9. Failure modes

| Condition | Behaviour |
|---|---|
| `ResizeObserver` missing | The shell still fits once at mount and on every payload update — measurement is what drives the cascade; `ResizeObserver` only makes it react to a resize. A browser without it therefore gets a correctly degraded layout that stops following window changes. (Amended 2026-09-12: an earlier draft said "no degradation, everything renders", which described the render probe's environment — that case is covered by the row below, an unusable measurement, not by the observer's absence.) |
| A measurement returns 0 or `NaN` (hidden tab, detached node) | Treated as "cannot measure": no flag change this pass |
| The cascade is exhausted and the row still overflows | Blocks crop, the zone scrolls horizontally (D4) |
| A plugin is disabled server-side | Absent from the registry pass, so absent from the widths — the cascade measures what is actually rendered |
| Cycle 0 (no payload) | Blocks render their loading state; the cascade runs on those widths and re-runs when the first payload changes them |

## 10. Testing

- **`node --test` (`tests/js/degrade.test.mjs`)**: `fits` (zero, one, exact
  boundary, off by one); `resolveDegrade` (fits immediately → no flag; needs
  two notches; exhausts the cascade; restarts from zero; applies the cascade in
  order; `notApplicable` entries are applied like the others). The injected
  `measure` returns scripted widths, so no DOM is involved.
- **Drift guard (pytest)**: import `_DEGRADE_STEPS` and `_HEADER_DEGRADE_STEPS`
  from `glances.outputs.glances_curses_v5` and compare them, in order and
  value, against the two JS cascades parsed from `degrade.js`. Porting
  `quicklook` without revisiting the WebUI cascade fails here.
- **Render probe**: `FakeElement` gains `scrollWidth` / `clientWidth` fed by a
  per-`data-plugin` fixture table, and the sandbox gains a `ResizeObserver`
  stub, so a scenario can drive the cascade end to end and assert the resulting
  DOM: which blocks rendered, how many `<dl>` columns `mem` and `cpu` kept,
  whether `ip`'s geolocation and `system`'s OS string are present. Scenarios:
  wide (nothing degraded), medium (a few notches), narrow (cascade exhausted).
- **Existing probe tests must pass unchanged**: with no measurement available
  the shell applies no flag.
- **CSS tests** (`tests/test_webui_v5_tokens.py`): the two zones are
  `nowrap` and scroll horizontally.
- **Headless-Chrome screenshots** of a real server at 1500, 1000, 720 and
  400 px, both themes: the behavioural evidence, since the probe has no layout
  engine.
- **Owed to the maintainer, in his manual smoke test:** resizing the window
  live — that no block ever wraps, that stats come back when it widens again,
  and whether any intermediate state flickers while the loop runs (§11).

## 11. Risks

| Risk | Mitigation |
|---|---|
| An intermediate state is painted (flicker) while the loop applies notches | **Settled by the maintainer's manual smoke test** (his call, 2026-09-12) — no implementation task gates on it. Vue's `nextTick` is a microtask, so the loop should settle before paint: believed, not proven, and a headless capture cannot prove it either (it samples one frame). If his smoke shows flicker, the named fallback is to measure off-screen instead of apply-then-measure |
| `ResizeObserver` feedback loop | Only zone widths are observed (imposed by the page, not by their content), and a re-render happens only when the flag set changes |
| The JS cascade drifts from the TUI's | The drift guard (§10) |
| The probe grows again (it is already flagged for splitting before G9-7) | Stated; the split stays recommended |
| Degradation on a wide screen because one block is abnormally wide (a very long GPU name) | That is the TUI's behaviour too — measure-driven, not threshold-driven (D2) |

## 12. Deliverables

**New:** `degrade.js`, `tests/js/degrade.test.mjs`, the drift test.

**Modified:** `AppShell.vue` (observers, loop, block filtering, `degrade`
prop), `PluginMem.vue`, `PluginCpu.vue`, `PluginIp.vue`, `PluginSystem.vue`
(and the `degrade` prop declaration in every other plugin component),
`css/v5.css` and the zone styles, `tests/fixtures/webui_render_probe.js` and
its fixtures, `tests/test_webui_v5_tokens.py`, the rebuilt `public/glances5.js`.

**Release-notes items** (never written to `NEWS.rst` during development):

- The v5 WebUI no longer wraps its header or its top row: as the window
  narrows it hides stats in the same order as the terminal interface, then
  crops them, then scrolls horizontally.
- `mem` drops its second column and `cpu` its third, then its second, before
  any block is hidden — the terminal's own priority.
- `swap` and `gpu` are the first blocks hidden in the top row; in the header,
  `cloud`, then the IP geolocation, the OS string, `now`, `ip` and `uptime`.

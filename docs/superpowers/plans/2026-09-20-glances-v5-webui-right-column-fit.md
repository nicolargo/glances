# WebUI v5 — right-column vertical fit and static widths — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the v5 WebUI's right column the TUI's vertical row budget and its
static, TUI-derived column widths, so the alert block is visible without
scrolling and the process tables stop jittering and wrapping.

**Architecture:** `plan_right_column` is ported to a pure JS module and driven by
`AppShell`, which measures the viewport (never the slot's own height) and hands
each elastic block a row quota as a prop. Column widths become static through
`table-layout: fixed` plus a `<colgroup>` in `--gl-col` units; the existing
width cascade keeps measuring, with the TUI's threshold expressed as a CSS
`min-width` fed by an integer column count.

**Tech Stack:** Vue 3 SFC (no build step beyond the existing bundle), plain ES
modules, `node --test`, pytest, the existing DOM-less render probe.

**Spec:** `docs/superpowers/specs/2026-09-20-glances-v5-webui-right-column-fit-design.md`

## Global Constraints

- **Never commit, push, or open a PR.** Each task **stages** its files and
  stops. The maintainer does every commit personally. Never add a
  `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.** It is updated at release time only.
- **Never unstage anything.** After every task run
  `git status --short | grep -v '^[AM] '` and report any line it prints.
- **Verify every parity claim against its source before building.** Every width,
  threshold and ordering in this plan carries a `file:line`. Open it. If the
  source disagrees with this plan, **say so and stop** — do not comply. Six
  factual errors in the controller's briefs were caught this way during G9-9B
  and none shipped.
- **If you cannot explain a mechanism, write that you cannot.** Never
  synthesise a plausible explanation for behaviour you did not trace.
- **Run whole test files, never a `-k` slice.** A slice is chosen with the same
  mental model as the change. After touching a visible surface (a CLI option, an
  API response shape, a config key, a CSS token), also run the file that pins
  *that* surface.
- **No `ch` for a width that means "N characters of the TUI".** `ch` resolves to
  `0.5em` under the shipped font stack. Use `calc(N * var(--gl-col))`.
  `tests/test_webui_v5_tokens.py` enforces this with a per-declaration
  allowlist.
- **No comment before a template's root element.** Two Vue roots silently drop
  `data-plugin` / `aria-label`. Keep every comment inside the root.
- **Each task writes a report to disk** at `.superpowers/sdd/2026-09-20-webui-right-column-fit/task-N-report.md`.
  A missing report is a task failure, not a detail.

---

## File Structure

**New**

| File | Responsibility |
|---|---|
| `glances/outputs/static/js/v5/row_budget.js` | Pure port of `plan_right_column` + helpers + constants. No DOM, no imports. |
| `glances/outputs/static/js/v5/process_widths.js` | Pure column-width constants for processlist / programlist / alert. |
| `tests/js/row_budget.test.mjs` | Readable edge cases of the solver. |
| `tests/test_webui_v5_row_budget_drift.py` | Behavioural Python↔JS equivalence over a case matrix. |
| `tests/test_webui_v5_width_drift.py` | Width/threshold constants vs the two terminal renderers. |

**Modified**

| File | Change |
|---|---|
| `tests/fixtures/webui_render_probe.js` | Height model on `FakeElement`; `window.innerHeight`. |
| `tests/fixtures/webui_render_fixtures.js` | Height fixtures per scenario. |
| `glances/outputs/static/css/v5.css` | `--gl-row`, right-column gap, cell separator, fixed-layout rules and exclusions. |
| `glances/outputs/static/js/v5/AppShell.vue` | Vertical measurement, solver call, `rowBudget` prop, pass ordering. |
| `glances/outputs/static/js/v5/CollectionBlock.vue` | Optional `#cols` slot and `tableClass` prop. |
| `glances/outputs/static/js/v5/format.js` | `formatProcessBytes`, `formatUsername`. |
| `glances/outputs/static/js/v5/PluginProcesslist.vue` | colgroup, fixed layout, `--gl-fixed-cols`, row budget, formatters. |
| `glances/outputs/static/js/v5/PluginProgramlist.vue` | Same, minus the cascade (the TUI renderer has none). |
| `glances/outputs/static/js/v5/PluginAlert.vue` | colgroup, fixed layout, width cascade, row budget. |
| `glances/outputs/static/js/v5/PluginAmps.vue` | Natural height, ladder step j clamping. |
| `glances/outputs/static/public/glances5.js` | Rebuilt bundle. |
| `tests/test_webui_v5_tokens.py`, `tests/test_webui_v5_render.py` | Updated / added assertions. |

---

## Task 1: Probe height model

The spec names this the least predictable estimate in the batch (§7.4). It is
first so its real cost is known before anything depends on it.

**Files:**
- Modify: `tests/fixtures/webui_render_probe.js:97-150` (`FakeElement`)
- Modify: `tests/fixtures/webui_render_fixtures.js:1509-1534`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `FakeElement` gains `getBoundingClientRect()` returning
  `{ top, left: 0, width, height, bottom }`, the expandos `_top`, `_height`,
  `_rowPx`, and `window.innerHeight`. A new fixture map
  `HEIGHT_FIXTURES = { [scenario]: { viewport, rowPx, slots: { [dataSlot]: { top, height } } } }`
  exported from `webui_render_fixtures.js`.

- [ ] **Step 1: Write the failing test**

In `tests/test_webui_v5_render.py`, next to the existing width-cascade tests:

```python
def test_the_probe_models_vertical_geometry():
    """The vertical budget reads viewport height, the right slot's top edge and
    one row's height. The probe has no layout engine, so it models all three --
    the same harness-hook pattern `_notches` already uses for scrollWidth.
    """
    payload = _render("budget-tall")
    geometry = payload["geometry"]
    assert geometry["viewport"] > 0
    assert geometry["rowPx"] > 0
    assert geometry["slotTop"] >= 0
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`
Expected: FAIL — the `budget-tall` scenario does not exist.

- [ ] **Step 3: Add the geometry model to `FakeElement`**

In `tests/fixtures/webui_render_probe.js`, inside `FakeElement`'s constructor,
beside `this._width = 0;`:

```js
		// Vertical layout, faked, exactly as `_width`/`_content` fake the
		// horizontal axis. Unset -> 0, which AppShell reads as "cannot
		// measure" and never budgets on (design section 4.8).
		this._top = 0;
		this._height = 0;
		// One text row, in px. A real browser resolves this from the computed
		// line-height; there is none here, so the harness supplies it.
		this._rowPx = 0;
```

And, next to the `scrollWidth` getter:

```js
	get clientHeight() {
		return this._height;
	}

	// AppShell.measureBodyRows() reads the right slot's top edge to work out
	// how much of the viewport is left below it. A real Element computes this
	// from layout; the harness supplies `_top`/`_height` per scenario.
	getBoundingClientRect() {
		return {
			top: this._top,
			left: 0,
			width: this._width,
			height: this._height,
			bottom: this._top + this._height,
		};
	}
```

- [ ] **Step 4: Give the fake `window` a viewport height**

In the same file, where `window` is stubbed, add `innerHeight`. It must be a
plain writable property so a scenario can set it:

```js
	// AppShell.measureBodyRows() reads window.innerHeight. 0 means "cannot
	// measure", which is the safe answer (design section 4.8).
	innerHeight: 0,
```

- [ ] **Step 5: Add the height fixtures**

In `tests/fixtures/webui_render_fixtures.js`, after `BLOCK_WIDTH_FIXTURES`:

```js
// Vertical geometry per scenario. Same contract as WIDTH_FIXTURES: these are
// the numbers a browser would report. `rowPx` is one text row; `top` is the
// slot's distance from the viewport's top edge. The budget is computed from
// viewport - top - footer, never from the slot's own height (design 4.4).
const HEIGHT_FIXTURES = {
	// 900 - 100 - 20 = 780 px of body, 20 px rows -> 39 rows: everything fits
	// and the solver takes its growth branch.
	"budget-tall": {
		viewport: 900,
		rowPx: 20,
		slots: { right: { top: 100, height: 0 }, footer: { top: 880, height: 20 } },
	},
	// 400 - 100 - 20 = 280 px -> 14 rows: the shrink ladder runs.
	"budget-short": {
		viewport: 400,
		rowPx: 20,
		slots: { right: { top: 100, height: 0 }, footer: { top: 380, height: 20 } },
	},
	// No viewport: "cannot measure" -> no budget at all.
	"budget-unmeasurable": {
		viewport: 0,
		rowPx: 0,
		slots: { right: { top: 0, height: 0 }, footer: { top: 0, height: 0 } },
	},
};
```

Add `HEIGHT_FIXTURES` to the `module.exports` block.

- [ ] **Step 6: Apply the fixtures in the probe and expose the reading**

Wherever the probe applies `WIDTH_FIXTURES` / `BLOCK_WIDTH_FIXTURES` to the
rendered tree, apply `HEIGHT_FIXTURES` the same way: set `window.innerHeight`,
set `_top`/`_height` on the element matching each `data-slot` key (and on
`.gl-alerts` for the `footer` key), and set `_rowPx` on the right slot. Add the
resulting reading to the probe's output payload under `geometry`:

```js
	geometry: {
		viewport: window.innerHeight,
		rowPx: rightSlot ? rightSlot._rowPx : 0,
		slotTop: rightSlot ? rightSlot.getBoundingClientRect().top : 0,
	},
```

- [ ] **Step 7: Run the test**

Run: `python -m pytest tests/test_webui_v5_render.py -v`
Expected: PASS, and every pre-existing test in the file still passes.

- [ ] **Step 8: Stage and report**

```bash
git add tests/fixtures/webui_render_probe.js tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' || true
```

Write the report. It must state the **actual** cost of this task against the
spec's warning that it is the batch's weakest estimate.

---

## Task 2: `row_budget.js` and its drift test

**Files:**
- Create: `glances/outputs/static/js/v5/row_budget.js`
- Create: `tests/js/row_budget.test.mjs`
- Create: `tests/test_webui_v5_row_budget_drift.py`
- Read only: `glances/outputs/curses_renderer_v5.py:877-1109`

**Interfaces:**
- Consumes: nothing. The module is pure — no DOM, no fetch, no imports — so
  `node --test` can load it, the same contract `degrade.js` states in its
  header.
- Produces:
  `planRightColumn({ bodyHeight, staticHeights, ampsHeight, nVms, nContainers, nProcesses, nAlerts, nOngoing })`
  → `{ vms, containers, processlist, programlist, alert, amps? }`.
  Also `splitWorkloads(quota, nVms, nContainers)` → `[vms, containers]` and
  `alertBlockHeight(nIncidents, quota)` → `number`.
  `amps` is present **only** when the ladder truncated it, mirroring
  `curses_renderer_v5.py:1107-1108`.

- [ ] **Step 1: Verify the source before writing anything**

Open `glances/outputs/curses_renderer_v5.py` and confirm each of these. If any
line says something different, stop and report rather than following this plan:

| Claim | Line |
|---|---|
| nominals 10 / 10 / 20 | `:877-879` |
| `_MAX_WORKLOADS = 20` | `:881` |
| ladder a→k, in this order: workloads 5, alerts 5, processes 10, workloads 3, alerts 3, processes 5, workloads 0, alerts 0, processes 3, amps None, processes 1 | `:947-959` |
| `floor_alerts = min(max(0, n_ongoing), _NOMINAL_ALERTS)` | `:1028` |
| `cost` = `sum(heights) + max(0, len(heights) - 1)` | `:1051` |
| a zero `processes` quota hides the block header included | `:1044` |
| the alert block is **always** appended to `heights` | `:1050` |
| `grow_processes` runs on **both** branches | `:1068`, `:1097` |
| terminal steps: `processes = 0` then decrement `alerts` | `:1085-1093` |
| `alertBlockHeight` = 1 when `n<=0 or quota<=0`, else `2 + min(n, quota)` | `:610-627` |
| `splitWorkloads` gives the odd leftover to vms first | `:923-942` |

- [ ] **Step 2: Write the failing node test**

`tests/js/row_budget.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { planRightColumn, splitWorkloads, alertBlockHeight } from "../../glances/outputs/static/js/v5/row_budget.js";

const BASE = {
	bodyHeight: 40,
	staticHeights: { processcount: 1 },
	ampsHeight: 0,
	nVms: 0,
	nContainers: 0,
	nProcesses: 200,
	nAlerts: 0,
	nOngoing: 0,
};

test("a sparse block beside a crowded one keeps its rows (max-min fairness)", () => {
	assert.deepEqual(splitWorkloads(10, 2, 30), [2, 8]);
});

test("an odd leftover goes to vms first", () => {
	assert.deepEqual(splitWorkloads(5, 10, 10), [3, 2]);
});

test("an empty alert block costs one row, a populated one costs two plus its rows", () => {
	assert.equal(alertBlockHeight(0, 10), 1);
	assert.equal(alertBlockHeight(5, 0), 1);
	assert.equal(alertBlockHeight(5, 3), 5);
});

test("processes absorb the slack on a tall viewport", () => {
	const budget = planRightColumn({ ...BASE, bodyHeight: 60 });
	assert.ok(budget.processlist > 20, "the nominal 20 is a floor to grow from, not a cap");
	assert.equal(budget.processlist, budget.programlist);
});

test("an active alert holds its floor while everything else gives way", () => {
	const budget = planRightColumn({ ...BASE, bodyHeight: 8, nAlerts: 6, nOngoing: 3 });
	assert.ok(budget.alert >= 3, "three ongoing incidents must stay visible");
	assert.equal(budget.processlist, 0, "step l drops the process block for them");
});

test("with no active alert the floor never fires and the historical cascade holds", () => {
	const budget = planRightColumn({ ...BASE, bodyHeight: 8, nAlerts: 6, nOngoing: 0 });
	assert.equal(budget.alert, 0, "step h leaves the header only");
});

test("amps is reported only when the ladder truncated it", () => {
	assert.equal("amps" in planRightColumn({ ...BASE, bodyHeight: 60, ampsHeight: 3 }), false);
	assert.equal("amps" in planRightColumn({ ...BASE, bodyHeight: 6, ampsHeight: 9 }), true);
});
```

- [ ] **Step 3: Run it and watch it fail**

Run: `node --test tests/js/`
Expected: FAIL — `row_budget.js` does not exist.

- [ ] **Step 4: Write the module**

`glances/outputs/static/js/v5/row_budget.js` — a line-by-line port of
`plan_right_column`. Pure: no DOM, no fetch, no imports.

```js
// Glances v5 WebUI -- the right column's vertical row budget.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it -- the same
// contract degrade.js and processlist_columns.js state in their own headers.
//
// A port of glances/outputs/curses_renderer_v5.py's `plan_right_column`
// (:969), `_split_workloads` (:923) and `_alert_block_height` (:610).
// tests/test_webui_v5_row_budget_drift.py runs BOTH solvers over a case matrix
// and requires identical output -- the existing drift tests compare constant
// lists, which cannot express an algorithm. Never edit one side alone.

const NOMINAL_WORKLOADS = 10; // curses_renderer_v5.py:877
const NOMINAL_ALERTS = 10; // :878
const NOMINAL_PROCESSES = 20; // :879
const MAX_WORKLOADS = 20; // :881

// Shrink ladder a->k (:947-959). `null` marks the "truncate amps to whatever
// is left" step (j).
const SHRINK_STEPS = [
	["workloads", 5], // a
	["alerts", 5], // b
	["processes", 10], // c
	["workloads", 3], // d
	["alerts", 3], // e
	["processes", 5], // f
	["workloads", 0], // g -- block hidden entirely
	["alerts", 0], // h -- header only
	["processes", 3], // i
	["amps", null], // j -- truncated, "+N lines" marker kept
	["processes", 1], // k -- beyond this the terminal clips
];

// Max-min fairness: an equal share first, then whatever one block does not use
// goes to the other, so 2 VMs beside 30 containers still show both. The odd
// leftover is offered to vms first, matching RIGHT_SLOT order.
export function splitWorkloads(quota, nVms, nContainers) {
	const share = Math.floor(quota / 2);
	let vms = Math.min(nVms, share);
	let containers = Math.min(nContainers, share);
	let leftover = quota - vms - containers;
	if (leftover > 0) {
		const take = Math.min(leftover, nVms - vms);
		vms += take;
		leftover -= take;
	}
	if (leftover > 0) containers += Math.min(leftover, nContainers - containers);
	return [vms, containers];
}

// Title row + column-header row + data rows, collapsing to a single line when
// there is nothing to show or the ladder took every row (step h).
export function alertBlockHeight(nIncidents, quota) {
	if (nIncidents <= 0 || quota <= 0) return 1;
	return 2 + Math.min(nIncidents, quota);
}

export function planRightColumn({
	bodyHeight,
	staticHeights = {},
	ampsHeight = 0,
	nVms = 0,
	nContainers = 0,
	nProcesses = 0,
	nAlerts = 0,
	nOngoing = 0,
}) {
	const state = {
		workloads: NOMINAL_WORKLOADS,
		alerts: NOMINAL_ALERTS,
		processes: NOMINAL_PROCESSES,
		amps: ampsHeight,
	};
	// Rows the alert block may never give up while the cascade still has
	// anything else to take (:1028).
	const floorAlerts = Math.min(Math.max(0, nOngoing), NOMINAL_ALERTS);

	// Mirrors `_paint_sidebar`: the visible block heights plus one blank line
	// between blocks (:1030-1051).
	const cost = (candidate) => {
		const [vmsQ, containersQ] = splitWorkloads(candidate.workloads, nVms, nContainers);
		const heights = [];
		if (nVms && vmsQ) heights.push(1 + vmsQ);
		if (nContainers && containersQ) heights.push(1 + containersQ);
		for (const h of Object.values(staticHeights)) if (h) heights.push(h);
		if (candidate.amps) heights.push(candidate.amps);
		// A zero quota hides the block outright, header included (step l).
		if (nProcesses && candidate.processes) heights.push(1 + Math.min(nProcesses, candidate.processes));
		// The alert block is ALWAYS emitted, if only as a header line.
		heights.push(alertBlockHeight(nAlerts, candidate.alerts));
		return heights.reduce((a, b) => a + b, 0) + Math.max(0, heights.length - 1);
	};

	// One row at a time, so the result provably fills the viewport without
	// overflowing it. A no-op once the ladder is exhausted.
	const growProcesses = () => {
		while (state.processes < nProcesses && cost({ ...state, processes: state.processes + 1 }) <= bodyHeight) {
			state.processes += 1;
		}
	};

	if (cost(state) <= bodyHeight) {
		while (state.workloads < MAX_WORKLOADS && cost({ ...state, workloads: state.workloads + 1 }) <= bodyHeight) {
			state.workloads += 1;
		}
		growProcesses();
	} else {
		for (const [key, value] of SHRINK_STEPS) {
			if (key === "amps") {
				if (!state.amps) continue;
				// Truncate to what remains, keeping at least the marker line.
				const deficit = cost(state) - bodyHeight;
				state.amps = Math.max(1, state.amps - deficit);
			} else {
				const target = key === "alerts" ? Math.max(value, floorAlerts) : value;
				if (target >= state[key]) continue;
				state[key] = target;
			}
			if (cost(state) <= bodyHeight) break;
		}
		if (floorAlerts && cost(state) > bodyHeight) {
			// The floor made steps b/e/h no-ops and what is left did not cover
			// the deficit. Step l, then step m: the floor itself gives way one
			// row at a time, so the block keeps as many active alerts as fit.
			state.processes = 0;
			while (state.alerts > 0 && cost(state) > bodyHeight) state.alerts -= 1;
		}
		// The step that made it fit usually freed more than the deficit; refund
		// that slack rather than leaving blank rows at the bottom.
		growProcesses();
	}

	const [vmsQ, containersQ] = splitWorkloads(state.workloads, nVms, nContainers);
	const budget = {
		vms: vmsQ,
		containers: containersQ,
		processlist: state.processes,
		programlist: state.processes,
		alert: state.alerts,
	};
	if (state.amps !== ampsHeight) budget.amps = state.amps;
	return budget;
}
```

- [ ] **Step 5: Run the node test**

Run: `node --test tests/js/`
Expected: PASS, all files.

- [ ] **Step 6: Write the behavioural drift test**

`tests/test_webui_v5_row_budget_drift.py`:

```python
"""Behavioural drift guard for the row-budget solver.

The other WebUI drift tests compare constant LISTS -- an ordering, a set of
widths. This one cannot: `plan_right_column` is an algorithm, and a textual
comparison of two languages' source would prove nothing. So it runs both
solvers over a case matrix and requires identical output dicts.

One `node` invocation for the whole matrix: JSON in, JSON out.
"""

from __future__ import annotations

import itertools
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import plan_right_column

_MODULE = Path("glances/outputs/static/js/v5/row_budget.js").resolve()

_BODY_HEIGHTS = (4, 8, 10, 20, 24, 30, 40, 60, 100)
_VMS = (0, 1, 3, 12)
_CONTAINERS = (0, 1, 3, 30)
_PROCESSES = (0, 5, 20, 200)
_ALERTS = (0, 1, 5, 12)
_ONGOING = (0, 1, 3, 8)
_AMPS = (0, 3, 9)


def _cases():
    for body, vms, containers, procs, alerts, ongoing, amps in itertools.product(
        _BODY_HEIGHTS, _VMS, _CONTAINERS, _PROCESSES, _ALERTS, _ONGOING, _AMPS
    ):
        # `n_ongoing` counts a SUBSET of `n_alerts` -- an impossible pair would
        # test a state the engine cannot produce.
        if ongoing > alerts:
            continue
        yield {
            "bodyHeight": body,
            "staticHeights": {"processcount": 1},
            "ampsHeight": amps,
            "nVms": vms,
            "nContainers": containers,
            "nProcesses": procs,
            "nAlerts": alerts,
            "nOngoing": ongoing,
        }


_RUNNER = """
import {{ planRightColumn }} from {module};
const cases = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(cases.map((c) => planRightColumn(c))));
"""


def test_the_js_solver_matches_the_python_one():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not available")
    cases = list(_cases())
    assert len(cases) > 1000, "a shrunken matrix would make this guard vacuous"

    script = _RUNNER.format(module=json.dumps(_MODULE.as_uri()))
    out = subprocess.run(
        [node, "--input-type=module", "-e", script, json.dumps(cases)],
        capture_output=True,
        text=True,
        check=True,
    )
    js_results = json.loads(out.stdout)

    for case, js in zip(cases, js_results, strict=True):
        py = plan_right_column(
            body_height=case["bodyHeight"],
            static_heights=case["staticHeights"],
            amps_height=case["ampsHeight"],
            n_vms=case["nVms"],
            n_containers=case["nContainers"],
            n_processes=case["nProcesses"],
            n_alerts=case["nAlerts"],
            n_ongoing=case["nOngoing"],
        )
        assert py == js, f"divergence on {case}: python={py} js={js}"
```

- [ ] **Step 7: Run the drift test**

Run: `python -m pytest tests/test_webui_v5_row_budget_drift.py -v`
Expected: PASS. **If it fails, the JS port is wrong — fix the port, never the
matrix.** Narrowing the matrix to make it pass is a task failure.

- [ ] **Step 8: Stage and report**

```bash
git add glances/outputs/static/js/v5/row_budget.js tests/js/row_budget.test.mjs tests/test_webui_v5_row_budget_drift.py
git status --short | grep -v '^[AM] ' || true
```

The report must give the matrix size actually executed.

---

## Task 3: The row unit

**Files:**
- Modify: `glances/outputs/static/css/v5.css` (the `:root` token block, and
  `.gl-slot-right`'s gap, currently in `AppShell.vue:474-480`)
- Test: `tests/test_webui_v5_tokens.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `--gl-row` on `:root`, a unitless line-height; the right column's
  inter-block gap expressed from it.

- [ ] **Step 1: Write the failing test**

In `tests/test_webui_v5_tokens.py`, beside the existing `--gl-col` test:

```python
def test_the_row_unit_is_defined_once_and_drives_the_right_column_gap():
    """`plan_right_column.cost()` charges exactly one blank line between blocks
    (curses_renderer_v5.py:1051). For that integer arithmetic to hold in the
    browser, the right column's inter-block gap must be exactly one row -- so
    the line-height has to be a known number, not the font-dependent `normal`
    it was before this batch (design 4.5).
    """
    css = _strip_comments(_TOKENS.read_text())
    assert len(re.findall(r"--gl-row:", css)) == 1, "--gl-row is defined exactly once"
    assert re.search(r":root\s*\{[^}]*--gl-row:\s*1\.25\b", css, re.S), "--gl-row lives on :root"
    assert re.search(r"line-height:\s*var\(--gl-row\)", css), "the token is actually applied"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_webui_v5_tokens.py -v`
Expected: FAIL — `--gl-row` is not defined.

- [ ] **Step 3: Add the token**

In `glances/outputs/static/css/v5.css`, in the `:root` block beside
`--gl-col: 0.6em`:

```css
  /* One text row, as a unitless line-height. The vertical budget
   * (js/v5/row_budget.js) is an INTEGER row count ported from the TUI, whose
   * cost() charges one blank line between blocks; the browser's inter-block
   * gap therefore has to be exactly one row, and a row has to be a known
   * number. Before this batch line-height was `normal` -- font-dependent, and
   * measured at roughly 1.056rem against a 1rem gap: six percent, invisible
   * across one block, a full row of drift across sixteen. Unitless so nested
   * elements inherit the RATIO, not a fixed px value. */
  --gl-row: 1.25;
```

And on the body rule that already sets `font-family`/`font-size`
(`css/v5.css:71-74`):

```css
  line-height: var(--gl-row);
```

- [ ] **Step 4: Move the right column's gap onto the token**

`.gl-slot-right`'s gap is in `AppShell.vue`'s scoped style, shared with
`.gl-slot-left` (`AppShell.vue:474-480`). Split the two rules so only the right
column changes:

```css
.gl-slot-left,
.gl-slot-right {
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.gl-slot-left {
	gap: calc(var(--gl-gap) * 2);
}
/* Exactly one text row, because the vertical budget's cost() charges one
 * blank line between blocks (row_budget.js). Any other value makes the
 * ported arithmetic wrong by a fraction of a row per block boundary. */
.gl-slot-right {
	gap: calc(var(--gl-row) * var(--gl-size-base));
	grid-column: 2;
}
```

- [ ] **Step 5: Run the token tests, then the render tests**

Run: `python -m pytest tests/test_webui_v5_tokens.py tests/test_webui_v5_render.py -v`
Expected: PASS.

- [ ] **Step 6: Rebuild the bundle and stage**

Rebuild `glances/outputs/static/public/glances5.js` the way this repo already
does (the same step every previous WebUI task used — read the G9-9B ledger if
unsure; do not invent a build command).

```bash
git add glances/outputs/static/css/v5.css glances/outputs/static/js/v5/AppShell.vue glances/outputs/static/public/glances5.js tests/test_webui_v5_tokens.py
git status --short | grep -v '^[AM] ' || true
```

The report must state the measured visual delta on the left column, which the
spec accepts as under 5 % of a line (design 4.5, risk R3) — and say so if it is
not.

---

## Task 4: AppShell — measure, solve, distribute

**Files:**
- Modify: `glances/outputs/static/js/v5/AppShell.vue` (template binding near
  `:degrade`, `data()`, `methods`, `mounted()`'s observer block)
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `planRightColumn` from Task 2; the probe geometry from Task 1.
- Produces: a `row-budget` prop bound on every slotted component, carrying
  `{ vms, containers, processlist, programlist, alert, amps? }` or `{}` when
  measurement is unavailable. Also `measureBodyRows()` → `number | null` and
  `refitVertical()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_tall_viewport_grows_the_process_block_past_its_nominal():
    payload = _render("budget-tall")
    assert payload["rowBudget"]["processlist"] > 20


def test_a_short_viewport_shrinks_it():
    payload = _render("budget-short")
    assert payload["rowBudget"]["processlist"] < 20


def test_an_unmeasurable_viewport_budgets_nothing():
    """degrade.js's rule, applied on the vertical axis: a DOM without layout, a
    hidden tab or a detached node must never hide the user's stats."""
    assert _render("budget-unmeasurable")["rowBudget"] == {}
```

- [ ] **Step 2: Run them and watch them fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`
Expected: FAIL — `rowBudget` is not in the payload.

- [ ] **Step 3: Add the state and the measurement**

First the import, beside the existing `resolveDegrade` one:

```js
import { planRightColumn } from "./row_budget.js";
```

In `data()`:

```js
			// The row quota each elastic right-column block may use. {} = no
			// budget, which is what an environment without measurement keeps --
			// degrade.js's rule on the vertical axis (design 4.8).
			rowBudget: {},
			// Same guard shape as `refitting`: the vertical pass mutates
			// rowBudget and therefore the DOM.
			refittingVertical: false,
```

In `methods`:

```js
		// Rows available below the right slot's top edge.
		//
		// Derived from the VIEWPORT, never from the slot's own height: the
		// slot's height is this pass's own output, so reading it would close a
		// feedback loop immediately. This is fit_block.js's documented
		// horizontal reasoning -- the right slot is the body grid's `1fr`
		// track, so its width never comes from its content -- transposed to the
		// vertical axis, where it is not free and has to be engineered
		// (design 4.4).
		//
		// `null` means "cannot measure", and the caller must then budget
		// nothing.
		measureBodyRows() {
			if (typeof window === "undefined") return null;
			const slot = this.$el?.querySelector?.('[data-slot="right"]');
			if (!slot || typeof slot.getBoundingClientRect !== "function") return null;
			const viewport = window.innerHeight || 0;
			// Harness hook, like `_notches`: a real element ignores this
			// expando and the computed line-height answers instead.
			const rowPx = slot._rowPx || this.computedRowPx(slot);
			if (!(viewport > 0) || !(rowPx > 0)) return null;
			const footer = this.$el?.querySelector?.(".gl-alerts");
			const footerHeight = footer?.getBoundingClientRect ? footer.getBoundingClientRect().height : 0;
			const top = slot.getBoundingClientRect().top;
			const rows = Math.floor((viewport - top - footerHeight) / rowPx);
			return rows > 0 ? rows : null;
		},
		computedRowPx(element) {
			if (typeof window.getComputedStyle !== "function") return 0;
			const value = parseFloat(window.getComputedStyle(element).lineHeight);
			return Number.isFinite(value) ? value : 0;
		},
```

- [ ] **Step 4: Add the solver call**

Still in `methods`:

```js
		// The vertical pass. Runs LAST, after both horizontal cascades: the
		// TUI orders it the same way and says why -- the body height it budgets
		// against depends on the TOP row height, which the horizontal cascade
		// above is free to change (glances_curses_v5.py:617-619).
		async refitVertical() {
			if (this.refittingVertical) return;
			this.refittingVertical = true;
			try {
				// Stacked layout (css `@media (max-width: 48rem)`): the right
				// column sits BELOW the left one rather than beside it, so
				// budgeting it to viewport height would hide processes for no
				// reason. The TUI has no equivalent case (design 4.9).
				if (this.isStacked()) {
					this.rowBudget = {};
					return;
				}
				const bodyHeight = this.measureBodyRows();
				if (bodyHeight === null) {
					this.rowBudget = {};
					return;
				}
				const count = (name) => (this.results[name]?.data || []).length;
				// `tick()` fetches `this.plugins`, NOT the `slots()`-filtered
				// list (AppShell.vue:283), so BOTH process payloads are always
				// present even though only one is rendered. Summing them would
				// tell the solver there are twice as many processes as exist.
				// The visible one is chosen by the same flag `slots()` uses.
				const processes = this.serverArgs.programs ? count("programlist") : count("processlist");
				const alert = this.results.alert || {};
				const incidents = Array.isArray(alert.incidents) ? alert.incidents : [];
				const next = planRightColumn({
					bodyHeight,
					staticHeights: { processcount: 1 },
					ampsHeight: this.ampsHeight(),
					nVms: count("vms"),
					nContainers: count("containers"),
					nProcesses: processes,
					nAlerts: incidents.length,
					nOngoing: incidents.filter((incident) => incident.ongoing).length,
				});
				if (!sameFlags(next, this.rowBudget)) this.rowBudget = next;
			} finally {
				this.refittingVertical = false;
			}
		},
		isStacked() {
			if (typeof window.matchMedia !== "function") return false;
			return window.matchMedia(`(max-width: ${STACK_BREAKPOINT})`).matches;
		},
		// The TUI emits one row per result LINE, blanking the name and count
		// after the first; this WebUI puts the whole multi-line result in one
		// `pre-line` cell (G9-9A spec D6). Same row cost either way.
		ampsHeight() {
			const rows = this.results.amps?.data || [];
			if (!rows.length) return 0;
			return 1 + rows.reduce((total, item) => total + Math.max(1, String(item.result || "").split("\n").length), 0);
		},
```

At module scope, beside `HIDDEN_BY`:

```js
// The browser's own stacking threshold, not a TUI rule (G9-5 D3). Kept next to
// the media query that owns it -- test_webui_v5_tokens.py pins the two
// together so the constant cannot drift from the stylesheet.
const STACK_BREAKPOINT = "48rem";
```

- [ ] **Step 5: Bind the prop and call the pass**

In the template, beside `:degrade="degrade"`:

```html
					:row-budget="rowBudget"
```

In `mounted()`, immediately after `await this.refit();`:

```js
		await this.refitVertical();
```

In `refit()`'s `finally`, after `this.refitting = false;` — no: call it from the
same places `refit()` is called from, always after it. In `tick()`'s `finally`
and in the ResizeObserver callback, chain it:

```js
					this.refit().then(() => this.refitVertical()).catch(() => {});
```

Also observe the right slot for resize, alongside `header-left` and `top`:
change the observed list to `["header-left", "top", "right"]`.

Republish through the probe hook so the harness can read the settled value:

```js
			window.__glancesRefit = async () => {
				await this.refit();
				await this.refitVertical();
				window.__glancesDegrade = this.degrade;
				window.__glancesRowBudget = this.rowBudget;
			};
			window.__glancesRowBudget = this.rowBudget;
```

- [ ] **Step 6: Expose it in the probe payload**

Add `rowBudget: window.__glancesRowBudget || {}` to the probe's output payload,
beside the existing `degrade` entry.

- [ ] **Step 7: Run the tests**

Run: `python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -v`
Expected: PASS, including every pre-existing test.

- [ ] **Step 8: Add the breakpoint drift assertion**

In `tests/test_webui_v5_tokens.py`:

```python
def test_the_stacking_breakpoint_matches_the_stylesheet():
    """AppShell reads the breakpoint to disable the vertical budget in the
    stacked layout (design 4.9). Two copies of `48rem` that can drift silently
    would leave the budget active while the columns are stacked.
    """
    shell = (_V5_JS / "AppShell.vue").read_text()
    assert 'STACK_BREAKPOINT = "48rem"' in shell
    assert re.search(r"@media\s*\(max-width:\s*48rem\)", shell)
```

- [ ] **Step 9: Rebuild, stage, report**

```bash
git add glances/outputs/static/js/v5/AppShell.vue glances/outputs/static/public/glances5.js tests/fixtures/webui_render_probe.js tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py
git status --short | grep -v '^[AM] ' || true
```

---

## Task 5: `process_widths.js` and the width drift test

**Files:**
- Create: `glances/outputs/static/js/v5/process_widths.js`
- Create: `tests/test_webui_v5_width_drift.py`
- Read only: `glances/plugins/processlist/render_curses_v5.py:54-66,87`,
  `glances/plugins/programlist/render_curses_v5.py:58`,
  `glances/outputs/curses_renderer_v5.py:525-540`

**Interfaces:**
- Consumes: nothing. Pure module.
- Produces: `PROCESS_COL_WIDTHS` (label → integer columns), `NPROCS_WIDTH`,
  `MIN_COMMAND_WIDTH`, `ALERT_COL_WIDTHS`, `ALERT_MIN_TARGET`, `ALERT_MIN_TOP`,
  `ALERT_W_WITH_TOP`, `ALERT_W_WITH_LEVEL`, `ALERT_W_WITH_DURATION`.

- [ ] **Step 1: Verify the source before writing anything**

Confirm, and stop and report on any mismatch:

| Constant | Value | Source |
|---|---|---|
| CPU%, MEM%, VIRT, RES | 5 each | `processlist/render_curses_v5.py:55-58` |
| USER | 10 | `:59` |
| THR, NI | 3 each | `:60-61` |
| S | 1 | `:62` |
| TIME+ | 8 | `:63` |
| R/s, W/s | 5 each | `:64` |
| PID | 7 | `:65` |
| `_MIN_COMMAND_WIDTH` | 8 | `:87` |
| NPROCS | 7 | `programlist/render_curses_v5.py:58` |
| GLYPH / TIME / DURATION / LEVEL | 1 / 8 / 8 / 8 | `curses_renderer_v5.py:525-528` |
| TARGET floor | 12 | `:529` |
| TOP floor | 22 | `:537` |
| thresholds | 66 / 43 / 34 | `:532-533,540` |

- [ ] **Step 2: Write the failing drift test**

`tests/test_webui_v5_width_drift.py`:

```python
"""The browser cannot import Python, so the TUI's column widths exist twice.
This test is the only thing keeping the copies honest -- never edit one side
alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from glances.outputs import curses_renderer_v5 as renderer
from glances.plugins.processlist import render_curses_v5 as processlist
from glances.plugins.programlist import render_curses_v5 as programlist

_MODULE = Path("glances/outputs/static/js/v5/process_widths.js")


def _int_const(name: str) -> int:
    match = re.search(rf"export const {name}\s*=\s*(\d+)\s*;", _MODULE.read_text())
    assert match, f"{name} is not exported from {_MODULE}"
    return int(match.group(1))


def _width_map(name: str) -> dict[str, int]:
    body = re.search(rf"export const {name}\s*=\s*\{{(.*?)\}};", _MODULE.read_text(), re.S)
    assert body, f"{name} is not exported from {_MODULE}"
    return {k: int(v) for k, v in re.findall(r'"([^"]+)"\s*:\s*(\d+)', body.group(1))}


def test_the_processlist_widths_match_the_terminal_renderer():
    assert _width_map("PROCESS_COL_WIDTHS") == {
        "CPU%": processlist._W_CPU,
        "MEM%": processlist._W_MEM,
        "VIRT": processlist._W_VIRT,
        "RES": processlist._W_RES,
        "PID": processlist._W_PID_DEFAULT,
        "USER": processlist._W_USER,
        "THR": processlist._W_THR,
        "NI": processlist._W_NI,
        "S": processlist._W_STATUS,
        "TIME+": processlist._W_TIME,
        "R/s": processlist._W_IO,
        "W/s": processlist._W_IO,
    }


def test_the_command_floor_matches():
    assert _int_const("MIN_COMMAND_WIDTH") == processlist._MIN_COMMAND_WIDTH


def test_the_fixed_column_order_matches():
    """A <colgroup> is positional: a different order silently mis-sizes every
    column, and no width assertion would catch it.
    """
    body = re.search(r"export const FIXED_COL_KEYS\s*=\s*\[(.*?)\];", _MODULE.read_text(), re.S)
    assert body, "FIXED_COL_KEYS is not exported"
    assert re.findall(r'"([^"]+)"', body.group(1)) == processlist._FIXED_COL_KEYS


def test_the_programlist_nprocs_width_matches():
    assert _int_const("NPROCS_WIDTH") == programlist._W_NPROCS


def test_the_alert_grid_geometry_matches():
    assert _width_map("ALERT_COL_WIDTHS") == {
        "GLYPH": renderer._ALERT_W_GLYPH,
        "TIME": renderer._ALERT_W_TIME,
        "DURATION": renderer._ALERT_W_DURATION,
        "LEVEL": renderer._ALERT_W_LEVEL,
    }
    assert _int_const("ALERT_MIN_TARGET") == renderer._ALERT_MIN_TARGET
    assert _int_const("ALERT_MIN_TOP") == renderer._ALERT_MIN_TOP
    assert _int_const("ALERT_W_WITH_TOP") == renderer._ALERT_W_WITH_TOP
    assert _int_const("ALERT_W_WITH_LEVEL") == renderer._ALERT_W_WITH_LEVEL
    assert _int_const("ALERT_W_WITH_DURATION") == renderer._ALERT_W_WITH_DURATION
```

- [ ] **Step 3: Run it and watch it fail**

Run: `python -m pytest tests/test_webui_v5_width_drift.py -v`
Expected: FAIL — the module does not exist.

- [ ] **Step 4: Write the module**

```js
// Glances v5 WebUI -- static column widths, in CHARACTER COLUMNS.
//
// Pure: no DOM, no fetch, no imports. Every value is a copy of a terminal
// renderer's constant, because the browser cannot import Python;
// tests/test_webui_v5_width_drift.py compares the two sides. Never edit one
// alone.
//
// These are character counts, so the CSS derived from them uses
// `calc(N * var(--gl-col))` and never `ch` -- `ch` resolves to 0.5em under the
// shipped font stack and would render 0.83 of every intended character
// (css/v5.css, and the per-declaration allowlist in test_webui_v5_tokens.py).

// glances/plugins/processlist/render_curses_v5.py:55-65
export const PROCESS_COL_WIDTHS = {
	"CPU%": 5,
	"MEM%": 5,
	VIRT: 5,
	RES: 5,
	PID: 7,
	USER: 10,
	THR: 3,
	NI: 3,
	S: 1,
	"TIME+": 8,
	"R/s": 5,
	"W/s": 5,
};

// The fixed columns in DISPLAY order -- what a <colgroup> needs, and not the
// same thing as PROCESS_COL_WIDTHS' key order, which no test would catch if it
// changed. Copy of `_FIXED_COL_KEYS`
// (glances/plugins/processlist/render_curses_v5.py:91).
export const FIXED_COL_KEYS = ["CPU%", "MEM%", "VIRT", "RES", "PID", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s"];

// programlist replaces PID with NPROCS -- same width, different meaning
// (glances/plugins/programlist/render_curses_v5.py:58).
export const NPROCS_WIDTH = 7;

// The floor below which the width cascade drops another column
// (processlist/render_curses_v5.py:87). Command is never dropped.
export const MIN_COMMAND_WIDTH = 8;

// glances/outputs/curses_renderer_v5.py:525-528. TARGET and TOP are elastic
// and carry floors instead of fixed widths.
export const ALERT_COL_WIDTHS = { GLYPH: 1, TIME: 8, DURATION: 8, LEVEL: 8 };
export const ALERT_MIN_TARGET = 12; // :529
export const ALERT_MIN_TOP = 22; // :537

// Block widths at or above which each column still fits without starving
// TARGET below its floor (:532-533, :540). TOP drops FIRST, by construction.
export const ALERT_W_WITH_TOP = 66;
export const ALERT_W_WITH_LEVEL = 43;
export const ALERT_W_WITH_DURATION = 34;
```

- [ ] **Step 5: Run the drift test**

Run: `python -m pytest tests/test_webui_v5_width_drift.py -v`
Expected: PASS.

- [ ] **Step 6: Stage and report**

```bash
git add glances/outputs/static/js/v5/process_widths.js tests/test_webui_v5_width_drift.py
git status --short | grep -v '^[AM] ' || true
```

---

## Task 6: The two formatter ports

**Files:**
- Modify: `glances/outputs/static/js/v5/format.js`
- Test: `tests/js/` (a new `format_process.test.mjs`, or the existing format
  test file if one already covers `format.js` — check before creating)

**Interfaces:**
- Consumes: nothing.
- Produces: `formatProcessBytes(value)` → string; `formatUsername(value)` →
  string. Neither pads.

- [ ] **Step 1: Verify the source**

Open `glances/plugins/processlist/render_curses_v5.py:158-162` and `:199-212`.
Confirm both of these, and stop and report on a mismatch:

- `_format_username` crops **only when `len(text) > _W_USER`** — a 10-character
  name is shown whole, an 11-character one becomes its first 9 plus `+`.
  `None` renders `?`.
- `_format_bytes` keeps one decimal below 100 and drops it at 100 and above;
  renders `?` for an unparseable or negative value; renders `<int>B` below 1 K.

- [ ] **Step 2: Write the failing test**

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { formatProcessBytes, formatUsername } from "../../glances/outputs/static/js/v5/format.js";

test("a name at the width is shown whole; one past it crops", () => {
	assert.equal(formatUsername("0123456789"), "0123456789");
	assert.equal(formatUsername("01234567890"), "012345678+");
	assert.equal(formatUsername(null), "?");
});

test("the decimal is kept below 100 and dropped at 100", () => {
	assert.equal(formatProcessBytes(99.4 * 1024 ** 3), "99.4G");
	assert.equal(formatProcessBytes(100 * 1024 ** 3), "100G");
});

test("sub-kilobyte values are plain bytes, bad values are a question mark", () => {
	assert.equal(formatProcessBytes(512), "512B");
	assert.equal(formatProcessBytes(-1), "?");
	assert.equal(formatProcessBytes("nope"), "?");
});

test("nothing is padded -- the colgroup does that job", () => {
	assert.equal(formatProcessBytes(512), formatProcessBytes(512).trim());
	assert.equal(formatUsername("ab"), "ab");
});
```

- [ ] **Step 3: Run it and watch it fail**

Run: `node --test tests/js/`
Expected: FAIL — neither function is exported.

- [ ] **Step 4: Implement**

Append to `glances/outputs/static/js/v5/format.js`:

```js
// The processlist renderer's OWN byte formatter
// (glances/plugins/processlist/render_curses_v5.py:199-212), not the shared
// `formatBytes` above. It drops the decimal at 100 and over, which is what
// lets VIRT/RES fit the terminal's 5-column budget -- and this WebUI now uses
// that same budget, so it needs the same string. This is the THIRD byte
// formatter in this module: `formatBytes` mirrors the WebUI's own rule,
// `formatAutoUnit` mirrors globals.auto_unit, and this one mirrors one
// plugin's local renderer. Say which surface you mean before reaching for one.
//
// The terminal's `rjust(width)` is deliberately NOT ported: the <colgroup> and
// `text-align` do that job here, and copied padding would ship trailing spaces
// into the DOM and defeat the ellipsis.
export function formatProcessBytes(value) {
	// `Number(null)` is 0, which is finite and non-negative -- without this
	// explicit guard a missing memory_info would render a confident "0B" where
	// the terminal says "?" (Python's float(None) raises and is caught).
	// `_memory_info_field` returns None for an access-denied process, so this
	// is reachable, not theoretical. Same shape as formatUsername below.
	if (value === null || value === undefined) return "?";
	const n = Number(value);
	if (!Number.isFinite(n) || n < 0) return "?";
	for (const [suffix, scale] of [
		["T", 1024 ** 4],
		["G", 1024 ** 3],
		["M", 1024 ** 2],
		["K", 1024],
	]) {
		if (n >= scale) {
			const v = n / scale;
			// toFixedHalfEven, NOT toFixed: Python breaks an exact tie to even
			// and JS breaks it away from zero (format.js:155-164 documents
			// this). `v = n / scale` with an integer byte count and a
			// power-of-two scale makes exact ties ordinary, not adversarial --
			// 1280 bytes renders " 1.2K" in the terminal and "1.3K" under
			// toFixed.
			return v < 100 ? `${toFixedHalfEven(v, 1)}${suffix}` : `${Math.trunc(v)}${suffix}`;
		}
	}
	return `${Math.trunc(n)}B`;
}

// `_format_username` (processlist/render_curses_v5.py:158-162). The boundary is
// off by one from the obvious reading: the crop fires only when the name is
// LONGER than the column, so a 10-character name is shown whole and an
// 11-character one becomes its first 9 plus `+`. The terminal's trailing
// `ljust` is not ported, for the same reason as above.
export function formatUsername(value) {
	const text = value === null || value === undefined ? "?" : String(value);
	return text.length > USER_WIDTH ? `${text.slice(0, USER_WIDTH - 1)}+` : text;
}
```

Import `PROCESS_COL_WIDTHS` at the top of `format.js` and derive
`const USER_WIDTH = PROCESS_COL_WIDTHS.USER;` so the crop length cannot drift
from the column width.

- [ ] **Step 5: Run the tests**

Run: `node --test tests/js/`
Expected: PASS.

- [ ] **Step 6: Stage and report**

```bash
git add glances/outputs/static/js/v5/format.js tests/js/
git status --short | grep -v '^[AM] ' || true
```

---

## Task 7: `CollectionBlock` — colgroup slot and table class

**Files:**
- Modify: `glances/outputs/static/js/v5/CollectionBlock.vue:1-43`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an optional `#cols` slot rendered immediately inside `<table>`, and
  an optional `tableClass` prop appended to the table's class list. Both
  default to nothing, so all 20-odd existing consumers are unaffected.

- [ ] **Step 1: Write the failing test**

```python
def test_a_block_may_supply_a_colgroup_and_a_table_class():
    """Fixed-layout tables need both: the <colgroup> carries the widths and the
    class carries `table-layout: fixed`. Optional, so every block that does not
    pass them renders exactly as before.
    """
    payload = _run_render_probe("collection-colgroup")
    assert payload["pluginColWidths"]["processlist"][:3] == [
        "calc(5 * var(--gl-col))",
        "calc(5 * var(--gl-col))",
        "calc(5 * var(--gl-col))",
    ]
    assert "gl-process-table" in payload["pluginTableClasses"]["processlist"]
```

**The probe does not expose either of these yet, and this task must add them.**
Its payload has `pluginColumnHeaders`, `pluginColumnClasses`, `pluginTableCells`
and friends, but nothing for `<col>` elements or the `<table>`'s own class. Add
two entries beside those, named and commented in the same style:

- `pluginColWidths` — each rendered `<col>`'s inline width, in document order,
  keyed by `data-plugin`. `[]` for a table with no `<colgroup>`, so a test can
  assert the absence, the same distinction `pluginHeaderCells` exists to make.
- `pluginTableClasses` — the `<table>`'s own class list, keyed by `data-plugin`.

A test asserting the widths through `pluginColWidths` is what pins the colgroup
to the TUI's character counts; without it Tasks 8, 9 and 10 have no way to
observe a `<col>` at all.

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

In `CollectionBlock.vue`, replace the `<table>` line:

```html
		<table v-else class="gl-table" :class="tableClass">
			<!-- Optional <colgroup>, rendered before <thead> as the HTML
			grammar requires. Only the fixed-layout blocks pass it; a block that
			does not renders exactly as before. -->
			<slot name="cols"></slot>
```

And in `props`:

```js
		// Extra class on the <table>, for blocks that need `table-layout:
		// fixed`. A prop rather than a fallthrough attribute: fallthrough
		// lands on the <article> root, and the rule has to reach the table.
		tableClass: { type: String, default: "" },
```

- [ ] **Step 4: Run the whole render and token suites**

Run: `python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -v`
Expected: PASS — including every block that passes neither new input.

- [ ] **Step 5: Rebuild, stage, report**

```bash
git add glances/outputs/static/js/v5/CollectionBlock.vue glances/outputs/static/public/glances5.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' || true
```

---

## Task 8: `PluginProcesslist` — fixed widths, elastic Command, row budget

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginProcesslist.vue`
- Modify: `glances/outputs/static/css/v5.css`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `PROCESS_COL_WIDTHS`, `MIN_COMMAND_WIDTH` (Task 5);
  `formatProcessBytes`, `formatUsername` (Task 6); `#cols` / `tableClass`
  (Task 7); the `rowBudget` prop (Task 4).
- Produces: nothing other tasks read.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_row_budget_caps_the_process_block():
    payload = _render("budget-short")
    rows = _rows(payload, plugin="processlist")
    assert len(rows) == payload["rowBudget"]["processlist"]


def test_the_config_cap_still_wins_when_it_is_lower():
    """`[outputs] max_processes_display` is a hard ceiling that available
    height may never raise (design 4.7)."""
    payload = _render("budget-tall-with-config-cap")
    assert len(_rows(payload, plugin="processlist")) == 5


def test_the_process_table_declares_the_terminal_column_widths():
    """The point of the batch: the <colgroup> carries the TUI's character
    counts, so a wider PID at the next refresh cannot re-lay the table out.
    Task 7 built `pluginColWidths` precisely so this can be observed; nothing
    before this test asserts that a colgroup is rendered at all.
    """
    payload = _run_render_probe("processlist-wide")
    assert payload["pluginColWidths"]["processlist"] == [
        f"calc({n} * var(--gl-col))" for n in (5, 5, 5, 5, 7, 10, 3, 3, 1, 8, 5, 5)
    ]
    assert "gl-process-table" in payload["pluginTableClasses"]["processlist"]


def test_a_long_user_name_is_cropped_not_wrapped():
    payload = _render("processlist-wide")
    cells = _cells(payload, plugin="processlist", column="USER")
    assert all(len(text) <= 10 for text in cells)
    assert any(text.endswith("+") for text in cells)


def test_the_command_column_carries_no_character_cap():
    """Defect P2: Command takes whatever is left. Its floor is reserved by the
    table's min-width, not by a cap on the cell."""
    payload = _render("processlist-wide")
    classes = payload["pluginValueClasses"]["processlist"]
    assert classes, "the scenario must actually render process rows"
    assert not any("gl-command" in c for c in classes), (
        "the cap belongs to containers, which keeps the measure-driven cascade; "
        "here the column width truncates instead"
    )
```

Add a `budget-tall-with-config-cap` scenario reusing `budget-tall`'s height
fixture with `CONFIG_FIXTURES`' `max_processes_display` set to 5.

- [ ] **Step 2: Run them and watch them fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`

- [ ] **Step 3: Add the colgroup and the table class**

In the template, as the `#cols` slot:

```html
		<template #cols>
			<colgroup>
				<col v-for="key in visibleFixedColumns" :key="key" :style="colStyle(key)" />
				<!-- Command: no width. Under `table-layout: fixed` an `auto`
				column takes whatever the fixed ones leave, which is exactly the
				TUI's elastic last column. -->
				<col />
			</colgroup>
		</template>
```

Bind the shell: `<CollectionBlock ... table-class="gl-process-table" :style="fixedColsStyle">`.

- [ ] **Step 4: Add the computed values**

```js
		// The fixed columns still on screen, in display order. Command is not
		// one of them -- it is the elastic tail.
		visibleFixedColumns() {
			return FIXED_COL_KEYS.filter((key) => this.shows(key));
		},
		// The integer the stylesheet turns into a width. CSS does the
		// character->pixel conversion, so no JS ever measures `--gl-col`
		// (design D7): the sum is the visible fixed widths, plus one separator
		// column between cells, plus Command's floor. The table's min-width is
		// built from it, so the table overflows its container exactly when
		// Command would fall below the floor -- which is what keeps the
		// existing measure-driven cascade firing at the TUI's own threshold.
		fixedColsStyle() {
			const keys = this.visibleFixedColumns;
			const fixed = keys.reduce((total, key) => total + PROCESS_COL_WIDTHS[key], 0);
			const separators = keys.length; // one after each fixed column, before Command
			return { "--gl-fixed-cols": String(fixed + separators + MIN_COMMAND_WIDTH) };
		},
```

```js
		colStyle(key) {
			return { width: `calc(${PROCESS_COL_WIDTHS[key]} * var(--gl-col))` };
		},
```

- [ ] **Step 5: Apply the row budget and the formatters**

Replace the `rows()` computed:

```js
		// Two ceilings, composed: the height-driven budget and the config key.
		// `min()` because `[outputs] max_processes_display` is a hard cap that
		// available height may never raise (design 4.7) -- the browser's
		// counterpart of the TUI's row_budget(view, "processlist", _MAX_ROWS)
		// fallback chain (processlist/render_curses_v5.py:414).
		rows() {
			const caps = [this.maxProcessesDisplay, this.rowBudget?.processlist].filter(
				(cap) => Number.isInteger(cap) && cap >= 0,
			);
			if (!caps.length) return this.allRows;
			return this.allRows.slice(0, Math.min(...caps));
		},
```

Declare the prop:

```js
		// The row quota AppShell's vertical pass allots this block. `{}` means
		// no budget -- an environment without measurement must never hide stats
		// (design 4.8).
		rowBudget: { type: Object, default: () => ({}) },
```

In the template, swap the formatters. This plan originally left the IO columns
open, saying to verify which formatter the terminal uses for them. That is now
settled, against what the note implied: `_io_cell`
(`processlist/render_curses_v5.py:294-297`) renders through the **same local
`_format_bytes`** as VIRT and RES. So **all four** byte columns move to
`formatProcessBytes`, not two:

- `formatBytes(memField(item, 'vms'))` → `formatProcessBytes(...)`
- `formatBytes(memField(item, 'rss'))` → `formatProcessBytes(...)`
- `formatBytes(ioRate(item, true))` → `formatProcessBytes(...)`
- `formatBytes(ioRate(item, false))` → `formatProcessBytes(...)`
- `fmt(item.username)` → `formatUsername(item.username)`

One more parity detail visible at the same lines: `_io_cell` renders `?` when
the rate is *unknown* — a distinct state from zero, produced by `_io_rate`'s
second return value. Check what the browser currently renders for that case and
report it; do not change it in this task unless it is already wrong.

Remove `gl-command` from the Command cell's class list, keeping `gl-truncate`
and the `title`.

- [ ] **Step 6: Add the stylesheet rules**

```css
/* Fixed-layout collection tables (processlist, programlist, alert). Their
 * columns come from a <colgroup> in TUI character widths, so they no longer
 * depend on their content: a wider PID at the next refresh cannot re-lay the
 * table out. `min-width` is what keeps the existing width cascade working --
 * under fixed layout a table never overflows, so `scrollWidth > clientWidth`
 * would stop being true and the cascade would never fire. The component sets
 * `--gl-fixed-cols` to the sum of the visible fixed widths plus separators
 * plus the elastic column's floor, so the table overflows its container
 * exactly at the terminal's own threshold (design 5.1). */
.gl-table.gl-process-table {
  table-layout: fixed;
  min-width: calc(var(--gl-fixed-cols) * var(--gl-col));
}
/* Cells stop wrapping and crop instead -- defects P4 and A1. The crop the
 * DATA needs (USER's `+` marker) is done by the formatter; this is the
 * layout's own floor for everything else. */
.gl-table.gl-process-table th,
.gl-table.gl-process-table td {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0;
}
/* One character BETWEEN cells, like the terminal's separator -- so the table is
 * `sum(widths) + (n - 1)` columns wide, exactly the TUI's formula and exactly
 * what `--gl-fixed-cols` computes. `:not(:last-child)` is load-bearing: padding
 * every cell would add one column the arithmetic does not account for, and the
 * cascade would fire one column early on every process table (design 5.3). */
.gl-table.gl-process-table th:not(:last-child),
.gl-table.gl-process-table td:not(:last-child) {
  padding-right: var(--gl-col);
}
/* The right column's slack goes to the last cell -- but not here: under fixed
 * layout that rule would claim the whole width. The `auto` <col> already does
 * the job the rule was written for. */
[data-slot="right"] .gl-table.gl-process-table td:last-child,
[data-slot="right"] .gl-table.gl-process-table th:last-child {
  width: auto;
}
```

- [ ] **Step 7: Update the existing last-cell test**

`tests/test_webui_v5_tokens.py::test_the_right_column_gives_its_slack_to_the_last_cell`
pins the rule this exclusion narrows. **Do not weaken its assertions**: it must
still prove the rule applies to the automatic-layout blocks (`amps`,
`containers`). Add a second assertion for the exclusion and say in the report
exactly which lines you changed and why.

- [ ] **Step 8: Run the tests**

Run: `python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py tests/test_webui_v5_processlist_drop_order_drift.py -v`
Expected: PASS.

- [ ] **Step 9: Rebuild, stage, report**

```bash
git add glances/outputs/static/js/v5/PluginProcesslist.vue glances/outputs/static/css/v5.css glances/outputs/static/public/glances5.js tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py tests/fixtures/
git status --short | grep -v '^[AM] ' || true
```

---

## Task 9: `PluginProgramlist` — same treatment, no cascade

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginProgramlist.vue`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: everything Task 8 consumes.
- Produces: nothing.

- [ ] **Step 1: Verify the divergence before building**

`glances/plugins/programlist/render_curses_v5.py` contains **no** drop order and
no `_MIN_COMMAND_WIDTH` — grep it and confirm. Its WebUI component correspondingly
has no `fitBlockMixin`. So this block gets static widths and the row budget but
**no width cascade**: when it is too narrow the block scrolls, which is the
browser's floor. That is the faithful port, not an oversight. If the grep
contradicts this, stop and report.

- [ ] **Step 2: Write the failing tests**

```python
def test_the_program_block_uses_nprocs_where_processes_use_pid():
    payload = _render("programlist-wide")
    widths = payload["pluginColWidths"]["programlist"]
    assert widths == [f"calc({n} * var(--gl-col))" for n in (5, 5, 5, 5, 7, 10, 3, 3, 1, 8, 5, 5)]


def test_the_program_block_takes_the_same_row_budget_as_the_process_block():
    payload = _render("budget-short-programs")
    assert payload["rowBudget"]["programlist"] == payload["rowBudget"]["processlist"]
    assert len(_rows(payload, plugin="programlist")) == payload["rowBudget"]["programlist"]
```

Add `budget-short-programs`: `budget-short`'s heights with `ARGS_FIXTURES`'
`programs` set true, so `slots()` shows `programlist` instead of `processlist`.

- [ ] **Step 3: Run them and watch them fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`

- [ ] **Step 4: Implement**

Apply exactly Task 8's steps 3–5 to this component, with one substitution: the
fifth column is `NPROCS` at `NPROCS_WIDTH` (7), not `PID`. Because there is no
cascade here, `visibleFixedColumns` is the full list — no `shows()` filter —
and `--gl-fixed-cols` is a constant per render.

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_width_drift.py -v`
Expected: PASS.

- [ ] **Step 6: Rebuild, stage, report**

```bash
git add glances/outputs/static/js/v5/PluginProgramlist.vue glances/outputs/static/public/glances5.js tests/test_webui_v5_render.py tests/fixtures/
git status --short | grep -v '^[AM] ' || true
```

---

## Task 10: `PluginAlert` — fixed grid, width cascade, row budget

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginAlert.vue`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `ALERT_*` from Task 5; `fitBlockMixin`; `rowBudget` from Task 4.
- Produces: nothing.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_alert_grid_drops_top_processes_first():
    """The TUI sacrifices TOP to keep TARGET readable
    (curses_renderer_v5.py:538-540). The browser must not do the opposite."""
    payload = _render("alert-narrow-one-notch")
    headers = _headers(payload, plugin="alert")
    assert "TOP PROCESSES" not in headers
    assert "TARGET" in headers
    assert "LEVEL" in headers


def test_the_alert_grid_drops_level_then_duration():
    headers = _headers(_render("alert-narrow-two-notches"), plugin="alert")
    assert "LEVEL" not in headers and "DURATION" in headers
    headers = _headers(_render("alert-narrowest"), plugin="alert")
    assert "DURATION" not in headers and "TARGET" in headers


def test_the_alert_block_honours_its_row_budget():
    payload = _render("budget-short-with-alerts")
    assert len(_rows(payload, plugin="alert")) == payload["rowBudget"]["alert"]
```

Add the three width scenarios to `BLOCK_WIDTH_FIXTURES` keyed on `alert`, and
`budget-short-with-alerts` combining `budget-short`'s heights with
`ALERT_INCIDENTS_FIXTURE`.

- [ ] **Step 2: Run them and watch them fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`

- [ ] **Step 3: Add the colgroup**

Inside the existing `<table class="gl-table">`, before `<thead>`:

```html
			<colgroup>
				<col :style="colStyle('GLYPH')" />
				<col :style="colStyle('TIME')" />
				<col v-if="shows('DURATION')" :style="colStyle('DURATION')" />
				<!-- TARGET and TOP are elastic: the terminal gives TARGET its
				natural width and lets TOP absorb the slack
				(curses_renderer_v5.py:534-536). `auto` columns under fixed
				layout do exactly that; their floors live in the table's
				min-width, not here. -->
				<col />
				<col v-if="shows('TOP')" />
				<col v-if="shows('LEVEL')" :style="colStyle('LEVEL')" />
			</colgroup>
```

Add `class="gl-process-table"` to the table (the shared fixed-layout class) and
bind `:style="fixedColsStyle"` on the `<article>` root.

- [ ] **Step 4: Add the cascade**

```js
import { fitBlockMixin } from "./fit_block.js";
import {
	ALERT_COL_WIDTHS,
	ALERT_MIN_TARGET,
	ALERT_MIN_TOP,
	ALERT_W_WITH_TOP,
	ALERT_W_WITH_LEVEL,
	ALERT_W_WITH_DURATION,
} from "./process_widths.js";
```

```js
	mixins: [fitBlockMixin],
```

```js
		// The TUI's own order: TOP first, then LEVEL, then DURATION
		// (curses_renderer_v5.py:538-540). TARGET is never dropped -- it says
		// WHAT the alert is about, and the terminal sacrifices TOP to keep it.
		dropCascadeSteps: () => [
			{ key: "drop_TOP", value: true },
			{ key: "drop_LEVEL", value: true },
			{ key: "drop_DURATION", value: true },
		],
		// `hiddenColumns`/`shows()` do not exist on this component yet -- it has
		// never had a cascade. Same shape as processlist_columns.js's
		// `hiddenColumns`: the mixin's cumulative `drop_<column>` flags.
		hiddenColumns() {
			const hidden = new Set();
			for (const [key, value] of Object.entries(this.dropFlags || {})) {
				if (value && key.startsWith("drop_")) hidden.add(key.slice("drop_".length));
			}
			return hidden;
		},
		// The <col> elements actually rendered: GLYPH, TIME and TARGET always,
		// plus whichever of DURATION/TOP/LEVEL survive the cascade.
		columnCount() {
			return 3 + ["DURATION", "TOP", "LEVEL"].filter((key) => this.shows(key)).length;
		},
		fixedColsStyle() {
			let total = ALERT_COL_WIDTHS.GLYPH + ALERT_COL_WIDTHS.TIME + ALERT_MIN_TARGET;
			if (this.shows("DURATION")) total += ALERT_COL_WIDTHS.DURATION;
			if (this.shows("LEVEL")) total += ALERT_COL_WIDTHS.LEVEL;
			if (this.shows("TOP")) total += ALERT_MIN_TOP;
			// One separator between cells, never after the last.
			return { "--gl-fixed-cols": String(total + this.columnCount - 1) };
		},
```

In `methods`:

```js
		shows(column) {
			return !this.hiddenColumns.has(column);
		},
```

And the mixin's documented host contract, which this component does not have
yet — `fit_block.js`'s header lists it: a `payload` watcher that re-runs the
pass, because a new incident changes the natural width and the ResizeObserver
does not fire when only the CONTENT changes.

```js
	watch: {
		payload() {
			this.fitBlock().catch(() => {});
		},
	},
```

The three thresholds (66 / 43 / 34) are what `fixedColsStyle` reconstructs:
verify that the sums it produces equal them for the four cascade states, and
**say so in the report with the four numbers**. If they do not match, the
constants or this arithmetic are wrong — report rather than adjusting a
constant to fit.

Add the `rowBudget` prop and cap `rows()` on `rowBudget.alert`, exactly as
Task 8 does — but with no config key to compose with.

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_width_drift.py tests/test_alerts_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Rebuild, stage, report**

```bash
git add glances/outputs/static/js/v5/PluginAlert.vue glances/outputs/static/public/glances5.js tests/test_webui_v5_render.py tests/fixtures/
git status --short | grep -v '^[AM] ' || true
```

---

## Task 11: `PluginAmps` — ladder step j

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginAmps.vue`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: the `rowBudget` prop (Task 4). `rowBudget.amps` is present **only**
  when the ladder truncated the block.
- Produces: nothing.

- [ ] **Step 0: Fix `ampsHeight()` in `AppShell.vue` — it over-counts twice**

Task 4 shipped `ampsHeight()` as:

```js
return 1 + rows.reduce((total, item) => total + Math.max(1, String(item.result || "").split("\n").length), 0);
```

Both halves are wrong against the terminal, and both make the solver believe the
block is taller than it is — so it shrinks the process list for rows that do not
exist.

1. **The `1 +` is a phantom header row.** `amps/render_curses_v5.py:65-95` builds
   `rows` purely from result lines: there is no header row, which is exactly why
   `row_budget`'s docstring singles `amps` out as the one plugin whose budget
   counts *all* its rows. `CollectionBlock` renders `<thead>` only when a `#head`
   slot is passed, and `PluginAmps.vue` passes none — so the browser has no
   header row either. Drop the `1 +`.
2. **It counts items the renderer skips.** `amps/render_curses_v5.py:67-71`
   skips an AMP whose `result` is `None` entirely, and `PluginAmps.vue`'s own
   `rows()` filters `result !== null && result !== undefined` to match. But
   `ampsHeight()` reduces over the raw `payload.data`, so every configured AMP
   that has not produced output yet costs a phantom row.

Use the same filter the component uses. The two must agree by construction, not
by coincidence: if you can express that without duplicating the predicate, do so
and say how; if not, say why and make both sides point at each other in a
comment.

Write a test that fails on the old behaviour before you fix it — a payload with
one null-result AMP and one two-line AMP should yield a height of 2, not 4.

- [ ] **Step 1: Write the failing test**

```python
def test_a_truncated_amps_block_keeps_a_marker_line():
    """Ladder step j truncates amps to what is left and keeps at least the
    `+N lines` marker (curses_renderer_v5.py:1074-1076). The browser renders a
    multi-line result in ONE `pre-line` cell (G9-9A D6), so it clamps lines
    rather than dropping rows.
    """
    payload = _render("budget-amps-truncated")
    text = _cells(payload, plugin="amps", column="result")[-1]
    assert text.rstrip().endswith("lines")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_webui_v5_render.py -v`

- [ ] **Step 3: Implement**

Add the `rowBudget` prop. When `rowBudget.amps` is an integer, clamp the
rendered lines across the block — the budget counts **all** its rows, marker
included (`curses_renderer_v5.py:1008-1010`) — and append a `+N lines` marker as
the last line. Read `render_curses_v5.py` for the amps plugin and reproduce its
marker text exactly; **quote the line you copied it from in the report**.

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_webui_v5_render.py -v`
Expected: PASS.

- [ ] **Step 5: Rebuild, stage, report**

```bash
git add glances/outputs/static/js/v5/PluginAmps.vue glances/outputs/static/public/glances5.js tests/test_webui_v5_render.py tests/fixtures/
git status --short | grep -v '^[AM] ' || true
```

---

## Task 12: The blocks the solver budgets but nobody told

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginVms.vue`
- Modify: `glances/outputs/static/js/v5/PluginContainers.vue`
- Modify: `glances/outputs/static/js/v5/PluginProcesslist.vue`
- Modify: `glances/outputs/static/js/v5/PluginProgramlist.vue`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: the `rowBudget` injection (Task 4), `CollectionBlock`'s existing `hidden` prop.
- Produces: nothing later tasks read.

This task exists because the plan had a hole. `planRightColumn` returns a quota for
`vms` and `containers` as well as the process blocks — `_split_workloads`
divides a shared pool between them and the max-min fairness rule is a third of
the solver's logic — but **no task wired either one**, so the solver reserves
rows for five containers while the browser renders thirty. On a host running
containers the right column overflows the viewport by exactly the amount the
solver thought it had saved, which is defect P1 surviving in the place the
solver works hardest.

The second half is the same defect one level down. `cost()` charges **zero**
rows for a block whose quota is zero — `if n_processes and candidate["processes"]`
(`curses_renderer_v5.py:1044`) — and the terminal's ladder steps g and l exist
precisely to make a block vanish, header included. The browser currently renders
an empty table with its header row still visible, so every zeroed block costs one
row the solver did not budget.

- [ ] **Step 1: Verify the claim before building**

Confirm each, and stop and report on a mismatch:

- `row_budget.js`'s returned object contains `vms` and `containers` keys.
- `grep -rln rowBudget glances/outputs/static/js/v5/` lists only `AppShell.vue`,
  `PluginProcesslist.vue` and `PluginProgramlist.vue` — neither workload block.
- `curses_renderer_v5.py:1044` charges no rows for a zero process quota, and
  `:1035-1038` does the same for a zero workload quota.
- `CollectionBlock.vue` already has a `hidden` prop that hides the whole block.

- [ ] **Step 2: Write the failing tests**

```python
def test_a_workload_block_honours_its_row_quota():
    """The solver splits a shared pool between vms and containers
    (`_split_workloads`, curses_renderer_v5.py:923-942). Nothing consumed that
    split before this task, so the solver reserved rows the browser then
    overspent."""
    payload = _run_render_probe("budget-workloads-capped")
    assert len(payload["pluginRowGroups"]["containers"][0]) == payload["rowBudget"]["containers"]


def test_a_zero_quota_hides_the_block_header_included():
    """Ladder steps g and l make a block VANISH, and `cost()` charges it zero
    rows (curses_renderer_v5.py:1035-1044). A header row left on screen is one
    row the solver did not budget."""
    payload = _run_render_probe("budget-processlist-zeroed")
    assert payload["rowBudget"]["processlist"] == 0
    assert payload["pluginHidden"]["processlist"] is True
```

Add the two scenarios, aliasing existing height fixtures by object reference
rather than copying numbers, as `HEIGHT_FIXTURES` was built to allow.

- [ ] **Step 3: Run them and watch them fail**

Run: `.venv-uv/bin/uv run pytest tests/test_webui_v5_render.py -v`

- [ ] **Step 4: Wire the two workload blocks**

Give `PluginVms.vue` and `PluginContainers.vue` the same `inject` and the same
slicing `PluginProcesslist.vue` already uses, keyed by their own names. Neither
has a config cap to compose with, so the budget is their only ceiling. Do not
copy the `> 0` / `>= 0` split blindly — read the comment explaining why the two
predicates differ before deciding what each block needs.

- [ ] **Step 5: Hide a zeroed block**

Pass `CollectionBlock`'s existing `hidden` prop when the effective quota is 0,
in all four components. Assert on `pluginHidden`, never on the absence of
slots: `CollectionBlock` hides with `v-show`, so a hidden block is still in the
DOM.

- [ ] **Step 6: Run the tests, rebuild, stage**

Run: `.venv-uv/bin/uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -v`
Then `cd glances/outputs/static && npm run build`.

```bash
git add glances/outputs/static/js/v5/PluginVms.vue glances/outputs/static/js/v5/PluginContainers.vue glances/outputs/static/js/v5/PluginProcesslist.vue glances/outputs/static/js/v5/PluginProgramlist.vue glances/outputs/static/public/glances5.js tests/test_webui_v5_render.py tests/fixtures/
git status --short | grep -v '^[AM] ' || true
```

---

## Task 13: Verification

**Files:** none changed unless a defect is found.

- [ ] **Step 1: Run every affected test file, whole**

```bash
python -m pytest \
  tests/test_webui_v5_render.py \
  tests/test_webui_v5_tokens.py \
  tests/test_webui_v5_width_drift.py \
  tests/test_webui_v5_row_budget_drift.py \
  tests/test_webui_v5_processlist_drop_order_drift.py \
  tests/test_webui_v5_degrade_drift.py \
  tests/test_alerts_v5.py \
  tests/test_curses_renderer_v5.py \
  tests/test_curses_v5.py \
  tests/test_routes_v5.py \
  -v
node --test tests/js/
```

Record the counts. No `-k` slices.

- [ ] **Step 2: Run the full suite and ESTABLISH the attribution of any failure**

```bash
ss -lptn 'sport = :61234' 'sport = :61235' || true
python -m pytest tests/ -q
```

`tests/test_mcp*` and `tests/test_restful*` are known to fail together when a
stray server holds 61234/61235 — check **before** the run, and reproduce any
failure per-file in isolation before attributing it to this batch.
`tests/test_perf.py` is known to be flaky under load: re-run it alone before
diagnosing. Do not inherit an attribution; establish it.

- [ ] **Step 3: Lint and hooks**

```bash
ruff check glances/ tests/
make pre-commit
```

`tests/test_web_list_ssl_verify.py`'s missing executable bit is a pre-existing
failure outside this batch and the maintainer's call. Any other failure is
ours. `gitleaks` scans the **index**, so re-stage before re-running.

- [ ] **Step 4: Live smoke**

```bash
python -m glances.main_v5 -s
```

(The v5 server is `python -m glances.main_v5 -s`, not `python -m glances`.)

Then check, in a real browser, at a normal window size and at a short one:

1. The alert block is visible without scrolling.
2. Column widths do not move between refreshes.
3. `S` is one character wide; `USER` crops with `+` rather than wrapping.
4. `Command` fills the remaining width.
5. No alert row wraps.
6. Narrowing the window drops `TOP PROCESSES` before `TARGET` crops.

- [ ] **Step 5: Write the final report**

State the test counts, the pre-commit outcome, every divergence §9 of the spec
predicted, and — separately — anything found that the spec did **not** predict.
Do not commit; the maintainer does that.

---

## Self-Review

**Spec coverage.** §4.2 → T2. §4.4/§4.5 → T3, T4. §4.6 → T4 (`ampsHeight`), T11
(step j). §4.7 → T8. §4.8 → T4. §4.9 → T4. §5.1 → T8's `min-width`. §5.2 → T5.
§5.3 → T8's padding rule. §5.4 → T8 step 7. §5.5 → T6. §5.6 → T8 step 5
(`gl-command` removed from this component only). §5.7 → T10. §7.4 → T1. §7.1 →
T2, T5. §7.2 → T2. §7.3 → T6.

**Two gaps found and closed while reviewing:**

1. `programlist` has no drop cascade in the terminal, so Task 9 cannot be "Task
   8 again" — its `visibleFixedColumns` is unconditional. Called out explicitly
   in Task 9 step 1, with a grep the implementer must run first.
2. Three tasks change the probe fixtures, so Task 1 must export `HEIGHT_FIXTURES`
   in a shape the later scenarios can compose with `CONFIG_FIXTURES` and
   `ARGS_FIXTURES`, not only stand alone. Tasks 8, 9 and 10 each name the
   scenario they add.

**One item deliberately left to the implementer**, because guessing would be
worse than asking: Task 8 step 5 says to *verify* which byte formatter the
terminal uses for the `R/s` / `W/s` columns before changing or keeping them.
This plan does not assert it, because it was not checked.

**Type consistency.** `planRightColumn` / `splitWorkloads` / `alertBlockHeight`
(T2) are used under those names in T4 and the drift test. `PROCESS_COL_WIDTHS`,
`NPROCS_WIDTH`, `MIN_COMMAND_WIDTH`, `ALERT_*` (T5) are used under those names
in T6, T8, T9, T10. `rowBudget` is the prop name in T4, T8, T9, T10, T11.
`--gl-fixed-cols` and `.gl-process-table` are written identically in T8's CSS
and T8/T9/T10's components.

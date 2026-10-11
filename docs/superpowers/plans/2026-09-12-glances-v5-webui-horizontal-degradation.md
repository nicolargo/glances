# Horizontal degradation in the v5 WebUI: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the v5 WebUI's header and top row behave like the TUI when the window narrows — hide stats in the TUI's own priority order, then crop, then scroll horizontally — instead of wrapping plugins onto extra lines.

**Architecture:** A pure module owns the two cascades and the fit test (Task 1, guarded against drift from the Python tuples). The CSS stops wrapping and starts cropping (Task 2). `AppShell` measures each zone and applies cascade notches until the zone stops overflowing, hiding whole blocks itself (Task 3). The four components that shrink rather than disappear read a `degrade` prop (Task 4). Task 5 verifies the whole thing against a real server.

**Tech Stack:** Vue 3.5 SFC (options API), webpack 5, `node --test`, pytest, headless Chrome, Python 3 (`uv run`).

**Spec:** `docs/superpowers/specs/2026-09-12-glances-v5-webui-horizontal-degradation-design.md`

**Depends on:** G9-6, staged on develop-v5 (HEAD `84c14da0` plus the staged G9-6 work).

**SDD workspace:** `.superpowers/sdd/2026-09-12-glances-v5-webui-horizontal-degradation/` (git-ignored; it already holds `spikes/measure.html`).

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer. Never `git clean`, never `git checkout`/`restore` over working files, never `git stash`, **never unstage anything** (`git reset`, `git restore --staged`, `git rm --cached`). After staging, run `git status --short | grep -v '^[AM] '` and report any line it prints — a large amount of G9-6 work is already staged and must stay staged.
- **Never touch `NEWS.rst`.**
- **No TUI Python file may change.** Nothing under `glances/plugins/*/render_curses_v5.py`, `glances/plugins/*/model_v5.py`, `glances/outputs/curses_renderer_v5.py`, `glances/outputs/glances_curses_v5.py`, `glances/outputs/curses_formatters_v5.py`, and no `tests/test_*render_curses_v5.py`. This group reads the TUI, it does not change it. If a task seems to need one, STOP and report.
- **v4 is read-only.** `glances/outputs/glances_restful_api.py`, `js/app.js`, `js/browser.js`, `js/services.js`, `js/components/**`, `js/App.vue`, `js/Browser.vue`, `js/store.js`, `js/filters.js`, `js/uiconfig.json`, `css/*.scss`, `templates/index.html`, `webpack.config.js`. `css/v5.css` IS in scope.
- **After every `npm run build`, the v4 bundles must be byte-identical:**
  ```bash
  for f in glances.js browser.js; do
    W=$(git hash-object glances/outputs/static/public/$f)
    C=$(git rev-parse HEAD:glances/outputs/static/public/$f)
    [ "$W" = "$C" ] && echo "$f IDENTICAL" || echo "$f DIFFERS"
  done
  ```
  Both must print IDENTICAL. If either DIFFERS, STOP and report — do not rebuild, do not `git checkout`, do not stage them.
- **Build with `npm run build` only**, from `glances/outputs/static`. Never `npm install`; `npm ci` is acceptable if `node_modules` is missing. Every task that changes a file under `js/v5/` or `css/v5.css` rebuilds `public/glances5.js` and stages it: the render probe runs against the bundle.
- **No new npm dependency. No new Python dependency.** `ResizeObserver` is a browser built-in.
- **No colour literal under `js/v5/`** — enforced by `tests/test_webui_v5_tokens.py`.
- **The cascades are the TUI's, in the TUI's order.** `TOP_CASCADE` and `HEADER_CASCADE` mirror `_DEGRADE_STEPS` and `_HEADER_DEGRADE_STEPS` (`glances/outputs/glances_curses_v5.py:62` and `:87`) entry by entry, including the two `quicklook` steps that do nothing in the WebUI today. Never reorder, drop or edit one side alone.
- **Never degrade on an unusable measurement.** `0`, `NaN` or a missing API means "cannot measure": no flag is applied and everything renders.
- **`ruff format --check` failing on a file the task wrote:** run `uv run ruff format <that file>` and re-run the task's tests. Never reformat a file the task did not touch.
- **Lint the JS you touch**, from the repository root:
  ```bash
  glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
  ```
  It must print nothing. `tests/fixtures/` is not linted (it never was).
- **Vue template traps:** a template comment placed before a component's root element makes a second root node and `data-plugin` stops landing on it — keep comments inside the root. Never put a comment between a `v-if`/`v-else-if` element and its `v-else` sibling.
- **Reports must not invent mechanisms.** If you observe something you cannot explain, write "I cannot explain this" rather than a plausible cause.
- `tests/test_restful.py::test_050/051` are flaky by construction — re-run that file alone before believing a failure. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `glances/outputs/static/js/v5/degrade.js` | **New.** `TOP_CASCADE`, `HEADER_CASCADE`, `fits`, `resolveDegrade` — pure | 1 |
| `tests/js/degrade.test.mjs` | **New.** Unit tests for the module | 1 |
| `tests/test_webui_v5_degrade_drift.py` | **New.** The JS cascades vs the Python tuples | 1 |
| `glances/outputs/static/js/v5/AppShell.vue` | Zone styles (Task 2), then observers, loop, block hiding, `degrade` prop (Task 3) | 2, 3 |
| `glances/outputs/static/css/v5.css` | `.gl-plugin` blocks keep their natural width | 2 |
| `tests/test_webui_v5_tokens.py` | The zones no longer wrap and crop instead | 2 |
| `tests/fixtures/webui_render_probe.js` | `scrollWidth`/`clientWidth` from fixtures, `ResizeObserver` stub, resolved flags in the output | 3 |
| `tests/fixtures/webui_render_fixtures.js` | Per-scenario zone widths | 3 |
| `tests/test_webui_v5_render.py` | Cascade behaviour end to end | 3, 4 |
| `glances/outputs/static/js/v5/PluginMem.vue`, `PluginCpu.vue`, `PluginIp.vue`, `PluginSystem.vue` | The four shrink flags | 4 |
| every other `Plugin*.vue` | `degrade` prop declaration | 4 |
| `glances/outputs/static/public/glances5.js` | Rebuilt | 2, 3, 4 |

---

### Task 1: The cascade module

**Files:**
- Create: `glances/outputs/static/js/v5/degrade.js`, `tests/js/degrade.test.mjs`, `tests/test_webui_v5_degrade_drift.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `TOP_CASCADE` and `HEADER_CASCADE`: arrays of `{key: string, value: number|boolean, notApplicable?: true}`, in the TUI's order.
  - `fits({content, available}) -> boolean` — `true` when the zone does not overflow, and `true` for any unusable reading.
  - `resolveDegrade(cascade, measure) -> Promise<object>` — `measure(flags)` returns (or resolves to) `{content, available}`; the result is the flat flag object to apply.

- [ ] **Step 1: Write the failing unit tests**

Create `tests/js/degrade.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { TOP_CASCADE, HEADER_CASCADE, fits, resolveDegrade } from "../../glances/outputs/static/js/v5/degrade.js";

test("fits compares the zone's content with its available width", () => {
	assert.equal(fits({ content: 300, available: 400 }), true);
	assert.equal(fits({ content: 400, available: 400 }), true); // exactly full still fits
	assert.equal(fits({ content: 401, available: 400 }), false);
});

test("fits never degrades on an unusable measurement", () => {
	// A detached node, a hidden tab, a DOM without layout (the render probe):
	// reading 0 or NaN must not hide the user's stats.
	for (const available of [0, NaN, undefined, null]) {
		assert.equal(fits({ content: 5000, available }), true, `available=${available}`);
	}
	assert.equal(fits({ content: NaN, available: 400 }), true);
});

test("resolveDegrade applies nothing when the zone already fits", async () => {
	const seen = [];
	const flags = await resolveDegrade(TOP_CASCADE, (f) => {
		seen.push(f);
		return { content: 100, available: 400 };
	});
	assert.deepEqual(flags, {});
	assert.equal(seen.length, 1, "measures once, applies no notch");
});

test("resolveDegrade stops at the first notch that fits", async () => {
	// Fits only from the second measurement on: one notch applied.
	let call = 0;
	const flags = await resolveDegrade(TOP_CASCADE, () => ({ content: call++ === 0 ? 500 : 300, available: 400 }));
	assert.deepEqual(flags, { mem_cols: 1 });
});

test("resolveDegrade walks the cascade in the TUI's order", async () => {
	const applied = [];
	await resolveDegrade(TOP_CASCADE, (f) => {
		applied.push({ ...f });
		return { content: 5000, available: 400 }; // never fits: the whole cascade runs
	});
	// applied[0] is the measurement before any notch.
	assert.deepEqual(applied[1], { mem_cols: 1 });
	assert.deepEqual(applied[2], { mem_cols: 1, cpu_cols: 2 });
	assert.deepEqual(applied[3], { mem_cols: 1, cpu_cols: 1 });
	assert.deepEqual(applied[7], {
		mem_cols: 1,
		cpu_cols: 1,
		quicklook_freq_only: true,
		hide_quicklook: true,
		hide_memswap: true,
		hide_gpu: true,
	});
});

test("resolveDegrade returns every flag when the cascade is exhausted", async () => {
	const flags = await resolveDegrade(HEADER_CASCADE, () => ({ content: 5000, available: 100 }));
	assert.deepEqual(flags, {
		hide_cloud: true,
		hide_ip_location: true,
		hide_os_info: true,
		hide_now: true,
		hide_ip: true,
		hide_uptime: true,
	});
});

test("resolveDegrade starts from no flag every time, so widening restores stats", async () => {
	const measure = (widths) => (f) => ({ content: Object.keys(f).length ? 300 : 500, available: widths });
	const narrow = await resolveDegrade(TOP_CASCADE, measure(400));
	assert.deepEqual(narrow, { mem_cols: 1 });
	const wide = await resolveDegrade(TOP_CASCADE, () => ({ content: 300, available: 4000 }));
	assert.deepEqual(wide, {}, "a second run does not inherit the first run's flags");
});

test("resolveDegrade awaits an async measure", async () => {
	const flags = await resolveDegrade(TOP_CASCADE, async () => ({ content: 300, available: 400 }));
	assert.deepEqual(flags, {});
});

test("the cascades carry the TUI's steps, quicklook included", () => {
	assert.deepEqual(
		TOP_CASCADE.map((s) => [s.key, s.value]),
		[
			["mem_cols", 1],
			["cpu_cols", 2],
			["cpu_cols", 1],
			["quicklook_freq_only", true],
			["hide_quicklook", true],
			["hide_memswap", true],
			["hide_gpu", true],
		],
	);
	// Declared, not omitted: quicklook is not ported, so these two change
	// nothing today -- but the order and the count must match the TUI.
	assert.deepEqual(
		TOP_CASCADE.filter((s) => s.notApplicable).map((s) => s.key),
		["quicklook_freq_only", "hide_quicklook"],
	);
	assert.deepEqual(
		HEADER_CASCADE.map((s) => [s.key, s.value]),
		[
			["hide_cloud", true],
			["hide_ip_location", true],
			["hide_os_info", true],
			["hide_now", true],
			["hide_ip", true],
			["hide_uptime", true],
		],
	);
});
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `degrade.js` does not exist.

- [ ] **Step 3: Implement the module**

Create `glances/outputs/static/js/v5/degrade.js`:

```js
// Glances v5 WebUI -- horizontal degradation: the TUI's cascades, in the TUI's
// order.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it. The caller
// owns measurement; this module owns the ORDER and the fit test. That split is
// what makes the behaviour testable at all -- the render probe has no layout
// engine, and a browser is not available under `node --test`.
//
// The two cascades mirror glances/outputs/glances_curses_v5.py
// (_DEGRADE_STEPS:62, _HEADER_DEGRADE_STEPS:87) entry by entry;
// tests/test_webui_v5_degrade_drift.py compares them. Never reorder, drop or
// edit one side alone.

// TOP row (a->g). Least useful detail first, whole blocks last.
export const TOP_CASCADE = [
	{ key: "mem_cols", value: 1 }, // (a) hide MEM's 2nd column
	{ key: "cpu_cols", value: 2 }, // (b) hide CPU's 3rd column
	{ key: "cpu_cols", value: 1 }, // (c) hide CPU's 2nd column
	// (d) and (e) act on `quicklook`, which the v5 WebUI does not render yet.
	// They are declared so the order and the count stay identical to the TUI's
	// and applying them is a no-op today; the drift test fails if quicklook is
	// ported without revisiting this file.
	{ key: "quicklook_freq_only", value: true, notApplicable: true },
	{ key: "hide_quicklook", value: true, notApplicable: true },
	{ key: "hide_memswap", value: true }, // (f) hide the swap block
	{ key: "hide_gpu", value: true }, // (g) hide the gpu block (last resort)
];

// Header line (0->5). `cloud` is opt-in, so it goes first: enabling it must
// never cost information that was on screen before it was turned on.
export const HEADER_CASCADE = [
	{ key: "hide_cloud", value: true },
	{ key: "hide_ip_location", value: true },
	{ key: "hide_os_info", value: true },
	{ key: "hide_now", value: true },
	{ key: "hide_ip", value: true },
	{ key: "hide_uptime", value: true },
];

// The TUI computes `sum(widths) + (n - 1) * gap <= max_x` because curses has no
// layout engine. The browser has one: `content` is the zone's scrollWidth and
// `available` its clientWidth, so the rule is measured rather than recomputed
// and no gap constant can drift from the CSS.
//
// An unusable reading means "cannot measure", and the answer is always `true`:
// a DOM without layout (the render probe), a hidden tab or a detached node must
// never hide the user's stats.
export function fits({ content, available }) {
	if (!Number.isFinite(content) || !Number.isFinite(available) || available <= 0) return true;
	return content <= available;
}

// Mirrors _build_fitted_frame / _fit_header: start with NO flag, apply one
// cascade entry at a time, re-measure, stop as soon as it fits. Starting from
// zero on every call is what makes a widening window give the stats back.
//
// `measure(flags)` may be async: applying a flag re-renders the view, and the
// caller awaits that before reading the DOM.
export async function resolveDegrade(cascade, measure) {
	let flags = {};
	if (fits(await measure(flags))) return flags;
	for (const step of cascade) {
		flags = { ...flags, [step.key]: step.value };
		if (fits(await measure(flags))) break;
	}
	return flags;
}
```

Run `uv run pytest tests/test_webui_v5_js.py -q` → PASS.

- [ ] **Step 4: Write the failing drift test**

Create `tests/test_webui_v5_degrade_drift.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's degradation cascades are the TUI's.

The WebUI keeps its own copy of `_DEGRADE_STEPS` / `_HEADER_DEGRADE_STEPS`
(js/v5/degrade.js): the browser cannot import Python. Nothing prevents the two
copies from drifting apart, so this test makes drift a failure — including the
two `quicklook` steps the WebUI declares but cannot act on yet, which is what
turns "quicklook was ported and nobody revisited the cascade" into a red test.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS, _HEADER_DEGRADE_STEPS

_DEGRADE_JS = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "degrade.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _cascades() -> dict:
    """Import degrade.js under node and return its two cascades as data."""
    script = (
        f"import({json.dumps(_DEGRADE_JS.as_uri())})"
        ".then((m) => process.stdout.write(JSON.stringify({top: m.TOP_CASCADE, header: m.HEADER_CASCADE})))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_top_cascade_matches_the_tui():
    top = [[step["key"], step["value"]] for step in _cascades()["top"]]
    assert top == [list(step) for step in _DEGRADE_STEPS]


def test_the_header_cascade_matches_the_tui():
    header = [[step["key"], step["value"]] for step in _cascades()["header"]]
    assert header == [list(step) for step in _HEADER_DEGRADE_STEPS]


def test_only_the_unported_steps_are_marked_not_applicable():
    """`quicklook` is the only TOP plugin the v5 WebUI does not render yet."""
    top = _cascades()["top"]
    assert [s["key"] for s in top if s.get("notApplicable")] == ["quicklook_freq_only", "hide_quicklook"]
    assert not [s for s in _cascades()["header"] if s.get("notApplicable")]
```

- [ ] **Step 5: Run the drift test**

```bash
uv run pytest tests/test_webui_v5_degrade_drift.py -q
```
Expected: PASS (the module was written in Step 3). If a comparison fails, the module is wrong — fix `degrade.js`, never the Python tuples.

- [ ] **Step 6: Lint and stage**

```bash
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run ruff check tests/test_webui_v5_degrade_drift.py && uv run ruff format --check tests/test_webui_v5_degrade_drift.py
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_degrade_drift.py -q
git add glances/outputs/static/js/v5/degrade.js tests/js/degrade.test.mjs tests/test_webui_v5_degrade_drift.py
git status --short | grep -v '^[AM] '
```
No bundle rebuild: nothing imports `degrade.js` yet (Task 3 does).

---

### Task 2: The zones crop instead of wrapping

**Files:**
- Modify: `glances/outputs/static/js/v5/AppShell.vue` (the `.gl-zone-header`, `.gl-slot-header-left`, `.gl-slot-header-right`, `.gl-slot-top` rules), `glances/outputs/static/css/v5.css` (`.gl-plugin`), `tests/test_webui_v5_tokens.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: nothing.
- Produces: the header zone and the top slot are `flex-wrap: nowrap` with `overflow-x: auto`; a `.gl-plugin` block is `flex: 0 0 auto`, so it keeps its natural width and the zone overflows instead of squeezing. Task 3's measurement premise (`scrollWidth > clientWidth` when a zone overflows) rests on this.

- [ ] **Step 1: Write the failing CSS tests**

Append to `tests/test_webui_v5_tokens.py`:

```python
def test_a_block_keeps_its_natural_width():
    """Spec section 8: a block must not be squeezed by its neighbours, or the
    zone would never report an overflow and the cascade would never run. CSS is
    not observable through the render probe, so this reads the token file.
    """
    body = _rule_body(_strip_comments(_TOKENS.read_text()), ".gl-plugin")
    assert re.search(r"\bflex:\s*0\s+0\s+auto\s*;", body), f".gl-plugin keeps its natural width: {body!r}"


def test_the_header_and_top_zones_never_wrap():
    """Spec goal 1: a plugin never moves to another line. The zones stop
    wrapping and scroll horizontally once the cascade is exhausted (D4).
    """
    shell = _strip_comments((_V5_JS / "AppShell.vue").read_text())
    for selector in (".gl-zone-header", ".gl-slot-top"):
        body = _rule_body(shell, selector)
        assert re.search(r"\bflex-wrap:\s*nowrap\s*;", body), f"{selector} does not wrap: {body!r}"
        assert re.search(r"\boverflow-x:\s*auto\s*;", body), f"{selector} scrolls instead: {body!r}"
    for selector in (".gl-slot-header-left", ".gl-slot-header-right"):
        body = _rule_body(shell, selector)
        assert re.search(r"\bflex-wrap:\s*nowrap\s*;", body), f"{selector} does not wrap: {body!r}"
```

`_rule_body` matches a selector followed by `{`, so `.gl-slot-header-left` must
keep its own rule block rather than share one with `.gl-slot-header-right`.

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_tokens.py -q -k "natural_width or never_wrap"
```
Expected: FAIL — the rules still say `wrap`, and `.gl-plugin` has no `flex`.

- [ ] **Step 3: Change the zone styles**

In `glances/outputs/static/js/v5/AppShell.vue`, replace the `.gl-zone-header` rule:

```css
.gl-zone-header {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	column-gap: 3ch;
}
```

with:

```css
/* The header never wraps: when it no longer fits, the cascade in this
 * component hides blocks in the TUI's order (degrade.js), then the blocks
 * crop, then this zone scrolls -- the browser's floor, where a terminal user
 * would have resized the window (spec D4). */
.gl-zone-header {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: 3ch;
	overflow-x: auto;
}
```

Replace the two slot rules:

```css
.gl-slot-header-left,
.gl-slot-header-right {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	column-gap: 3ch;
	/* Lets the header's long strings shrink into their ellipsis. */
	min-width: 0;
}
```

with:

```css
.gl-slot-header-left {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: 3ch;
	/* Lets the header's long strings shrink into their ellipsis. */
	min-width: 0;
}
.gl-slot-header-right {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: 3ch;
	min-width: 0;
}
```

and add `overflow-x: auto;` plus `flex-wrap: nowrap;` to `.gl-slot-top`, whose
rule becomes:

```css
/* Top row: first block flush left, last flush right, gaps distributed --
 * _paint_top_row()'s rule. Never wraps (spec goal 1): the cascade hides
 * blocks, then they crop, then this zone scrolls. */
.gl-slot-top {
	display: flex;
	flex-wrap: nowrap;
	justify-content: space-between;
	gap: calc(var(--gl-gap) * 2);
	flex: 1;
	overflow-x: auto;
}
```

The `.gl-slot-header-right { margin-left: auto; }` rule that follows stays as it is.

- [ ] **Step 4: Give a block its natural width**

Append to `glances/outputs/static/css/v5.css`:

```css

/* A block keeps its natural width inside a zone that no longer wraps: without
 * this, flex would squeeze the blocks and the zone would never report an
 * overflow, so the degradation cascade (js/v5/degrade.js) would never run. The
 * zone scrolls instead, once the cascade is exhausted. */
.gl-plugin {
  flex: 0 0 auto;
}
```

Run `uv run pytest tests/test_webui_v5_tokens.py -q` → PASS.

- [ ] **Step 5: Check the measurement premise in a real browser**

Task 3 measures `zone.scrollWidth` against `zone.clientWidth`. Prove the DOM
reports what the cascade will rely on, with the real stylesheet. Create
`.superpowers/sdd/2026-09-12-glances-v5-webui-horizontal-degradation/task2/overflow.html`:

```html
<!doctype html>
<meta charset="utf-8">
<link rel="stylesheet" href="../../../../glances/outputs/static/css/v5.css">
<body>
<div class="gl-zone gl-zone-top" style="width: 400px">
  <section class="gl-slot gl-slot-top" data-slot="top">
    <article class="gl-plugin" data-plugin="cpu">CPU 4.5% user 3.8% system 0.7% iowait 0.0%</article>
    <article class="gl-plugin" data-plugin="mem">MEM 53.2% total 16.0G avail 8.0G free 2.0G</article>
    <article class="gl-plugin" data-plugin="memswap">SWAP 25.0% total 16.0G sin 0B/s sout 0B/s</article>
  </section>
</div>
<div id="out"></div>
<script>
const zone = document.querySelector(".gl-slot-top");
const line = (label) => `${label}: scrollWidth=${zone.scrollWidth} clientWidth=${zone.clientWidth} overflows=${zone.scrollWidth > zone.clientWidth}`;
const out = [line("three blocks")];
zone.children[2].remove();
out.push(line("two blocks"));
zone.children[1].remove();
out.push(line("one block"));
out.push(`block heights equal (no wrap): ${new Set([...document.querySelectorAll(".gl-plugin")].map((b) => b.offsetTop)).size === 1}`);
document.getElementById("out").textContent = "RESULT\n" + out.join("\n") + "\nEND";
</script>
</body>
```

```bash
T=$PWD/.superpowers/sdd/2026-09-12-glances-v5-webui-horizontal-degradation/task2
timeout 60 google-chrome --headless=new --disable-gpu --no-first-run --dump-dom file://$T/overflow.html 2>/dev/null | sed -n '/RESULT/,/END/p'
```

Expected: `overflows=true` with three blocks, a smaller `scrollWidth` with two,
and `overflows=false` with one. **If `scrollWidth` does not shrink as blocks are
removed, or never exceeds `clientWidth`, STOP and report** — Task 3's whole
measurement rests on it, and the spec names the fallback (measure the blocks
individually).

- [ ] **Step 6: Rebuild, run, lint, stage**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check from the Global Constraints -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
git add glances/outputs/static/js/v5/AppShell.vue glances/outputs/static/css/v5.css tests/test_webui_v5_tokens.py glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```
Every existing render test must still pass: the probe's DOM has no layout, so
nothing degrades there yet.

---

### Task 3: `AppShell` measures, resolves and hides

**Files:**
- Modify: `glances/outputs/static/js/v5/AppShell.vue`, `tests/fixtures/webui_render_probe.js`, `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `resolveDegrade`, `TOP_CASCADE`, `HEADER_CASCADE` (Task 1); the non-wrapping zones (Task 2).
- Produces:
  - Every plugin component receives a fifth prop, `degrade` (a flat object; `{}` when nothing is degraded).
  - `AppShell` hides whole blocks itself: `hide_cloud`, `hide_now`, `hide_ip`, `hide_uptime`, `hide_memswap`, `hide_gpu` remove the block from its slot.
  - Probe: `FakeElement` reports `scrollWidth`/`clientWidth` from `WIDTH_FIXTURES`; the sandbox has a `ResizeObserver` stub; `collect()` emits `degrade: {header, top}`.
  - Fixture scenarios `degrade-wide`, `degrade-medium`, `degrade-narrow`.

- [ ] **Step 1: Teach the probe to measure**

In `tests/fixtures/webui_render_probe.js`, add to `FakeElement`'s constructor,
right after `this.dataset = {};`:

```js
		// Layout, faked. A real DOM computes these; this harness reads them from
		// WIDTH_FIXTURES so a scenario can drive the degradation cascade
		// (js/v5/degrade.js). Unset -> 0, which degrade.js reads as "cannot
		// measure" and never degrades on.
		this._width = 0;
		this._content = 0;
```

and, after the `className` accessors, add:

```js
	get clientWidth() {
		return this._width;
	}

	get scrollWidth() {
		return this._content;
	}
```

In the module's fixture destructuring add `WIDTH_FIXTURES`, and in the sandbox
object (beside `setInterval`) add:

```js
	// AppShell observes zone widths with this; the harness never fires it, so
	// the cascade runs exactly once, on the shell's own post-payload pass.
	ResizeObserver: class {
		observe() {}
		disconnect() {}
	},
```

After `vm.runInContext(...)` — the shell has rendered, so the zones exist —
apply the scenario's widths before `collect()` runs, by adding this function and
calling it from the `setImmediate` callback before `collect()`:

```js
// Give the zones their scenario widths, then let AppShell re-measure. Without
// this every width is 0 and degrade.js refuses to degrade, which is exactly
// what the pre-cascade tests assert.
function applyWidths() {
	const widths = WIDTH_FIXTURES[scenario];
	if (!widths) return false;
	for (const [slot, { available, content }] of Object.entries(widths)) {
		for (const zone of findAllByAttr(appDiv, "data-slot")) {
			if (zone.getAttribute("data-slot") !== slot) continue;
			zone._width = available;
			zone._content = content;
		}
	}
	return true;
}
```

The shell exposes a re-measure entry point for the harness (Step 3), so the
`setImmediate` callback becomes:

```js
setImmediate(async () => {
	if (applyWidths() && sandbox.__glancesRefit) await sandbox.__glancesRefit();
	process.stdout.write(JSON.stringify(collect()));
});
```

and `collect()` gains, beside the other outputs:

```js
		// The flags AppShell resolved for each zone -- the cascade's decision,
		// which the DOM alone cannot show (a hidden block looks like a disabled
		// one).
		degrade: sandbox.__glancesDegrade ? { ...sandbox.__glancesDegrade } : {},
```

- [ ] **Step 2: Add the width fixtures**

In `tests/fixtures/webui_render_fixtures.js`, add beside the other fixture
tables, and to the `module.exports` list:

```js
// Zone widths per scenario, keyed by the `data-slot` the shell renders. The
// numbers are what a browser would report: `available` is clientWidth,
// `content` scrollWidth. `content` is what the cascade shrinks -- the harness
// re-reads it after each notch through CONTENT_STEPS below.
const WIDTH_FIXTURES = {
	// Fits as it is: no notch.
	"degrade-wide": { top: { available: 1400, content: 900 }, "header-left": { available: 1400, content: 300 } },
	// 850 - 150 = 700: exactly one notch (mem_cols=1). The header fits.
	"degrade-medium": { top: { available: 700, content: 850 }, "header-left": { available: 1400, content: 300 } },
	// 1500 - 7*150 = 450 > 200, and 1500 - 6*150 = 600 > 200: neither cascade
	// ever fits, so both run to their last step.
	"degrade-narrow": { top: { available: 200, content: 1500 }, "header-left": { available: 200, content: 1500 } },
};
```

`degrade-medium` shrinks by one notch; `degrade-narrow` never fits, so both
cascades run to the end. The shell's own measurement re-reads `scrollWidth`
after every notch, and the harness models that by dropping `content` by 150 per
applied notch — add, next to the table:

```js
// One notch removes roughly one column or one block. The exact figure does not
// matter: what the tests assert is WHICH notches land, not the pixels.
const CONTENT_PER_NOTCH = 150;
```

and export both.

In the probe, the measurement the shell calls must consume them: `applyWidths`
sets the initial `content`, and the shell's re-measure reads
`zone._content - CONTENT_PER_NOTCH * appliedNotches`, which the probe models by
overriding `scrollWidth` as a function of the flags — implement it by giving
`FakeElement` a `_notches` counter the shell increments through the harness
hook:

```js
	get scrollWidth() {
		return Math.max(0, this._content - CONTENT_PER_NOTCH * this._notches);
	}
```

with `this._notches = 0;` beside `this._content = 0;`, and the harness hook in
Step 3 bumping `_notches` on each measure pass.

- [ ] **Step 3: Wire the shell**

In `glances/outputs/static/js/v5/AppShell.vue`:

(a) imports — add beside the others:

```js
import { resolveDegrade, TOP_CASCADE, HEADER_CASCADE } from "./degrade.js";
```

(b) `data()` — add:

```js
			// The flags each zone resolved. {} = nothing degraded, which is also
			// what an environment without measurement keeps (spec section 9).
			degrade: { header: {}, top: {} },
			observers: [],
```

(c) the blocks a flag hides, as a module constant beside `ZONES`:

```js
// Which flag removes which block. The TUI does the same in
// _build_fitted_frame, by filtering frame.top -- a block that disappears is
// the shell's business; a block that merely shrinks is the component's
// (spec D7).
const HIDDEN_BY = {
	hide_cloud: "cloud",
	hide_now: "now",
	hide_ip: "ip",
	hide_uptime: "uptime",
	hide_memswap: "memswap",
	hide_gpu: "gpu",
};
```

(d) `slots` computed — filter the hidden blocks out:

```js
		slots() {
			const hidden = new Set(
				Object.entries({ ...this.degrade.header, ...this.degrade.top })
					.filter(([key, value]) => value && HIDDEN_BY[key])
					.map(([key]) => HIDDEN_BY[key]),
			);
			return groupBySlot(this.plugins.filter((plugin) => !hidden.has(plugin.name)));
		},
```

(e) the template — pass the prop on the `<component :is>`:

```html
					:degrade="zone.name === 'header' ? degrade.header : degrade.top"
```

(f) the loop, as methods:

```js
		// Measure one zone, apply a candidate flag set, let Vue re-render, and
		// report what the browser says. `resolveDegrade` calls this once per
		// notch (spec section 6).
		async measureZone(slotName, zoneKey, flags) {
			this.degrade = { ...this.degrade, [zoneKey]: flags };
			await this.$nextTick();
			const zone = this.$el?.querySelector?.(`[data-slot="${slotName}"]`);
			if (!zone) return { content: 0, available: 0 };
			return { content: zone.scrollWidth, available: zone.clientWidth };
		},
		// Re-run both cascades from scratch. Starting from no flag is what gives
		// the stats back when the window widens (spec section 6).
		async refit() {
			const header = await resolveDegrade(HEADER_CASCADE, (flags) =>
				this.measureZone("header-left", "header", flags),
			);
			const top = await resolveDegrade(TOP_CASCADE, (flags) => this.measureZone("top", "top", flags));
			this.degrade = { header, top };
		},
```

(g) `mounted()` — after the first `tick()`, observe and fit:

```js
			await this.refit();
			if (typeof ResizeObserver === "function") {
				for (const slotName of ["header-left", "top"]) {
					const zone = this.$el?.querySelector?.(`[data-slot="${slotName}"]`);
					if (!zone) continue;
					const observer = new ResizeObserver(() => this.refit());
					observer.observe(zone);
					this.observers.push(observer);
				}
			}
			// The render probe drives the cascade through this hook: its fake DOM
			// has no ResizeObserver and no layout until the harness sets widths.
			if (typeof window !== "undefined") {
				window.__glancesRefit = () => this.refit();
				window.__glancesDegrade = this.degrade;
			}
```

and in `tick()`, after `this.results = results;`, re-fit because the values'
widths changed:

```js
					await this.refit();
					if (typeof window !== "undefined") window.__glancesDegrade = this.degrade;
```

(h) `unmounted()` — disconnect:

```js
			for (const observer of this.observers) observer.disconnect();
```

- [ ] **Step 4: Write the failing probe tests**

Append to `tests/test_webui_v5_render.py`:

```python
# ------------------------------------------- horizontal degradation (2026-09-12)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_wide_window_degrades_nothing():
    """The cascade only runs when a zone overflows."""
    payload = _run_render_probe("degrade-wide")
    assert payload["degrade"] == {"header": {}, "top": {}}
    for name in ("cpu", "mem", "memswap", "gpu"):
        assert name in payload["pluginNames"], f"{name} must still render: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_narrow_top_row_degrades_in_the_tui_order():
    """glances_curses_v5.py:62 -- MEM's 2nd column goes first, whole blocks last."""
    payload = _run_render_probe("degrade-medium")
    assert payload["degrade"]["top"] == {"mem_cols": 1}
    assert "memswap" in payload["pluginNames"], "a block is hidden only after the column notches"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_exhausted_cascade_hides_the_last_resort_blocks():
    """Both cascades run to the end: swap and gpu go from the top row, and the
    header keeps only the hostname (spec section 4.1).
    """
    payload = _run_render_probe("degrade-narrow")
    assert payload["degrade"]["top"]["hide_memswap"] is True
    assert payload["degrade"]["top"]["hide_gpu"] is True
    assert payload["degrade"]["header"]["hide_uptime"] is True
    for name in ("memswap", "gpu", "cloud", "now", "ip", "uptime"):
        assert name not in payload["pluginNames"], f"{name} must be hidden: {payload['pluginNames']!r}"
    assert "system" in payload["pluginNames"], "the hostname block always survives"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_dom_without_layout_degrades_nothing():
    """Spec section 9: an unusable measurement (0) must never hide a stat. Every
    pre-existing scenario runs with no widths at all, which is this case.
    """
    payload = _run_render_probe("default")
    assert payload["degrade"] == {"header": {}, "top": {}}
```

- [ ] **Step 5: Run them**

```bash
(cd glances/outputs/static && npm run build)
uv run pytest tests/test_webui_v5_render.py -q -k "degrade or exhausted or without_layout"
```
Expected: PASS. If a scenario resolves a different flag set, report the resolved
set and the widths — do not edit the expectation to match the code.

- [ ] **Step 6: Full WebUI run, lint, stage**

```bash
# v4 identity check -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py tests/test_webui_v5_degrade_drift.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run ruff check tests/test_webui_v5_render.py && uv run ruff format --check tests/test_webui_v5_render.py
git add glances/outputs/static/js/v5/AppShell.vue tests/fixtures/webui_render_probe.js tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```
Every pre-existing render test must still pass: without widths, nothing degrades.

---

### Task 4: The four components that shrink

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginMem.vue`, `PluginCpu.vue`, `PluginIp.vue`, `PluginSystem.vue`, and the prop declaration in `PluginNetwork.vue`, `PluginDiskio.vue`, `PluginFs.vue`, `PluginWifi.vue`, `PluginSensors.vue`, `PluginGpu.vue`, `PluginLoad.vue`, `PluginMemswap.vue`, `PluginCloud.vue`, `PluginNow.vue`, `PluginUptime.vue`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: the `degrade` prop (Task 3).
- Produces: `mem_cols`, `cpu_cols`, `hide_ip_location`, `hide_os_info` change what their component renders; every other component declares the prop and ignores it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webui_v5_render.py`:

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_mem_drops_its_second_column_first():
    """mem/render_curses_v5.py:92 -- at mem_cols=1 the 2nd column goes, which in
    the WebUI is where `active` lives (G9-5 A1).
    """
    payload = _run_render_probe("degrade-medium")
    columns = payload["pluginGrid"]["mem"]
    assert len(columns) == 1, f"only column 1 survives: {columns!r}"
    assert [pair[0] for pair in columns[0]] == ["MEM", "total", "avail", "free"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_drops_its_third_then_its_second_column():
    """cpu/render_curses_v5.py:127 -- cpu_cols 3 -> 2 -> 1."""
    narrow = _run_render_probe("degrade-narrow")
    assert len(narrow["pluginGrid"]["cpu"]) == 1, narrow["pluginGrid"]["cpu"]
    assert [pair[0] for pair in narrow["pluginGrid"]["cpu"][0]] == ["CPU", "user", "system", "iowait"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_header_drops_the_geolocation_before_the_addresses():
    """glances_curses_v5.py:87 -- step (1) drops ip's geolocation string; the
    addresses themselves survive until step (4).
    """
    payload = _run_render_probe("degrade-header-location")
    text = payload["pluginText"]["ip"]
    assert "192.168.1.10" in text, f"the private address stays: {text!r}"
    assert "Paris" not in text, f"the geolocation goes: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_header_drops_the_os_string_but_keeps_the_hostname():
    """glances_curses_v5.py:87 -- step (2)."""
    payload = _run_render_probe("degrade-header-os")
    text = payload["pluginText"]["system"]
    assert "test-host" in text, f"the hostname stays: {text!r}"
    assert "Ubuntu" not in text, f"the OS string goes: {text!r}"
```

In `tests/fixtures/webui_render_fixtures.js`, add the two scenarios to
`WIDTH_FIXTURES`:

```js
	// 1250 - 2*150 = 950 <= 1000, and one notch alone leaves 1100 > 1000: the
	// cascade stops at step (1), hide_ip_location.
	"degrade-header-location": { "header-left": { available: 1000, content: 1250 } },
	// 1400 - 3*150 = 950 <= 1000, and two notches leave 1100 > 1000: it stops at
	// step (2), hide_os_info.
	"degrade-header-os": { "header-left": { available: 1000, content: 1400 } },
```

and give both scenarios the header payloads. An object literal cannot reference
itself, so these are assignments placed AFTER the `ALL_FIXTURES` literal — the
pattern `"scalar-grids"` already uses:

```js
ALL_FIXTURES["degrade-header-location"] = ALL_FIXTURES.header;
ALL_FIXTURES["degrade-header-os"] = ALL_FIXTURES.header;
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_render.py -q -k "drops"
```
Expected: FAIL — the components ignore `degrade`.

- [ ] **Step 3: `PluginMem` honours `mem_cols`**

Declare the prop (beside `serverArgs`):

```js
		// `mem_cols` (1 or 2) -- the TUI's first degradation notch
		// (glances_curses_v5.py:62). Anything else means "no degradation".
		degrade: { type: Object, default: () => ({}) },
```

and make the second column conditional by replacing the `col2` computed:

```js
		col2() {
			return COL2_FIELDS.map((field) => this.statFor(field));
		},
```

with:

```js
		// mem_cols=1 (TUI step a) drops the whole 2nd column. In the TUI that
		// also drops the line-1 `active` pair; in the WebUI `active` IS the
		// first pair of this column (G9-5 A1), so one rule covers both.
		col2() {
			if (this.degrade.mem_cols === 1) return [];
			return COL2_FIELDS.map((field) => this.statFor(field));
		},
```

and make the template skip an empty column — replace:

```html
			<dl>
				<template v-for="(stat, i) in col2" :key="i">
```

with:

```html
			<dl v-if="col2.length">
				<template v-for="(stat, i) in col2" :key="i">
```

- [ ] **Step 4: `PluginCpu` honours `cpu_cols`**

Declare the same prop (with the comment naming `cpu_cols`, 1..3), and in the
`columns` computed replace the final line:

```js
			return [col1, col2, col3].map((fields) => fields.map((f) => this.statFor(f)));
```

with:

```js
			// cpu_cols (TUI steps b and c, glances_curses_v5.py:62) keeps the
			// first N of the three columns; the selection rules above are
			// untouched. Clamped like cpu/render_curses_v5.py:137.
			const nCols = Math.max(1, Math.min(3, Number(this.degrade.cpu_cols) || 3));
			return [col1, col2, col3].slice(0, nCols).map((fields) => fields.map((f) => this.statFor(f)));
```

- [ ] **Step 5: `PluginIp` and `PluginSystem` honour their flags**

In `PluginIp.vue`, declare the prop and replace the `publicInfo` computed and
its comment:

```js
		// The TUI's `hide_ip_location` is terminal-width degradation and is not
		// reproduced (G9-5 D3): the string truncates with an ellipsis instead.
		publicInfo() {
			return this.payload?.public_info_human || "";
		},
```

with:

```js
		// `hide_ip_location` is the TUI's header step (1)
		// (glances_curses_v5.py:87): the widest, least essential segment of the
		// banner goes first, and both addresses survive it. G9-5 D3 said the
		// browser would not reproduce this; the 2026-09-12 spec reverses that.
		publicInfo() {
			if (this.degrade.hide_ip_location) return "";
			return this.payload?.public_info_human || "";
		},
```

In `PluginSystem.vue`, declare the prop and replace `hrName`'s comment tail and
body the same way:

```js
		// `hide_os_info` is the TUI's header step (2)
		// (glances_curses_v5.py:87): static host metadata is worth less under
		// width pressure than any live metric. G9-5 D3 said the browser would
		// not reproduce this; the 2026-09-12 spec reverses that.
		hrName() {
			if (this.degrade.hide_os_info) return "";
			return this.payload?.hr_name || "";
		},
```

- [ ] **Step 6: Declare the prop everywhere else**

In each of `PluginNetwork.vue`, `PluginDiskio.vue`, `PluginFs.vue`,
`PluginWifi.vue`, `PluginSensors.vue`, `PluginGpu.vue`, `PluginLoad.vue`,
`PluginMemswap.vue`, `PluginCloud.vue`, `PluginNow.vue`, `PluginUptime.vue`,
add beside `serverArgs`:

```js
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
```

- [ ] **Step 7: Run, rebuild, lint, stage**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py tests/test_webui_v5_degrade_drift.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run ruff check tests/test_webui_v5_render.py && uv run ruff format --check tests/test_webui_v5_render.py
git add glances/outputs/static/js/v5 tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```
`test_server_args_does_not_leak_into_the_dom_as_an_attribute` must still pass:
it fails for any component that forgot the declaration.

---

### Task 5: Verify against a real server and close

**Files:** everything the group touched. No new code unless a hook rewrites something.

- [ ] **Step 1: No TUI or v4 file moved**

```bash
git diff --stat HEAD -- glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py \
  glances/outputs/curses_formatters_v5.py 'glances/plugins/*/render_curses_v5.py' \
  'glances/plugins/*/model_v5.py' 'tests/test_*render_curses_v5.py' tests/test_curses_renderer_v5.py
```
Expected: empty — this group reads the TUI, it never changes it. (G9-6's own
staged TUI changes are already in `HEAD`'s index; if this command prints those,
compare against the G9-6 file list in
`.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/progress.md`
and report anything beyond it.) Then the v4 file list and the bundle identity
check from the Global Constraints.

- [ ] **Step 2: Full suite**

```bash
uv run pytest -q
```
No NEW failures. `test_050/051`: re-run `tests/test_restful.py` alone.

- [ ] **Step 3: Screenshots at four widths, both themes**

Save as `.superpowers/sdd/2026-09-12-glances-v5-webui-horizontal-degradation/shots/shoot.py` and run it with `uv run python`:

```python
"""Horizontal degradation: a real v5 server at four widths, both themes."""

import os
import subprocess
import sys
import time
import urllib.request

OUT = os.path.abspath(".superpowers/sdd/2026-09-12-glances-v5-webui-horizontal-degradation/shots")
PORT = 61297
BODY = """[diskio]
hide=loop.*,/dev/loop.*
[fs]
hide=/boot.*,.*/snap.*
"""


def shoot(theme: str, width: int) -> None:
    conf = os.path.join(OUT, f"deg-{theme}.conf")
    with open(conf, "w") as handle:
        handle.write(BODY + f"[outputs]\ntheme={theme}\n")
    server = subprocess.Popen(
        [sys.executable, "-m", "glances.main_v5", "-s", "--bind", "127.0.0.1", "--port", str(PORT), "-C", conf],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/status", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise SystemExit("the v5 server did not come up")
        time.sleep(12)
        png = os.path.join(OUT, f"deg-{theme}-{width}.png")
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
             f"--screenshot={png}", f"--window-size={width},900", "--virtual-time-budget=8000",
             f"http://127.0.0.1:{PORT}/"],
            check=True, timeout=120, capture_output=True,
        )
        print(png)
    finally:
        server.terminate()
        server.wait(timeout=15)


os.makedirs(OUT, exist_ok=True)
for theme in ("dark", "light"):
    for width in (1500, 1000, 720, 400):
        shoot(theme, width)
```

Check `ss -ltn 'sport = :61297'` is empty first. Open each PNG and report, per
width: whether any block wrapped onto a second line (a failure), which blocks
are present, how many columns `mem` and `cpu` show, and whether the header still
shows the geolocation and the OS string. At 400px, report whether the zones
scroll rather than clip content out of reach.

- [ ] **Step 4: Hooks and final stage**

```bash
git add -A
make pre-commit
git add -A
git status --short
```
`check-shebang-scripts-are-executable` fails on 5 pre-existing files from the
develop backports — report any OTHER failing hook and its files. Do NOT commit.

- [ ] **Step 5: Report, do not write**

In the task report only, never in the repository:

- **Owed to the maintainer:** the manual smoke test — resizing the window live,
  checking that no block wraps, that stats come back when it widens, and
  whether any intermediate state flickers while the loop runs (spec section 11,
  his call).
- **Release-notes items:** the spec's section 12 list, verbatim.
- **Pressure report:** the probe's and the render test file's line counts after
  this group.

---

## Self-review notes

Checked against the spec, section by section:

- §1 goals → Task 2 (no wrap, crop, scroll), Tasks 3-4 (progressive hiding in the TUI's order).
- §2 out of scope → no task touches the body columns, the vertical fit, `quicklook`, or `--gl-font`.
- §3 D1 → Tasks 2-3 (header + top only). D2 → Task 1 `fits`/`resolveDegrade`, Task 3 `measureZone`. D3 → Task 1's drift test. D4 → Task 2's `overflow-x: auto`. D5 → Task 1's cascade entries and their test. D6 → Task 3 (e), Task 4 Step 6. D7 → Task 3 (c)(d) for hiding, Task 4 for shrinking.
- §4.1 → Task 1's cascades, values checked against the Python tuples by the drift test. §4.3 → Task 2 Step 5 re-checks the premise against the real stylesheet.
- §5 → Task 1. §6 → Task 3 (f)(g), including the re-fit on every payload and the restart from zero. §7 → Task 3 `HIDDEN_BY` + Task 4. §8 → Task 2.
- §9 failure modes → Task 1's "unusable measurement" test, Task 3's `test_a_dom_without_layout_degrades_nothing`, the `ResizeObserver` guard in Task 3 (g).
- §10 → Tasks 1, 2, 3, 4 tests; §11 flicker → Task 5 Step 5 (the maintainer's smoke test); §12 → the File Structure table.

Two places this plan decides what the spec left open:

1. **The probe models re-measurement with `CONTENT_PER_NOTCH`** (Task 3 Step 2). The spec says the shell re-measures after each notch; a fake DOM has to model that shrink somehow, and a flat per-notch figure keeps the fixtures readable. The tests assert which notches land, never the pixel figures.
2. **The shell exposes `window.__glancesRefit` / `window.__glancesDegrade`** for the harness (Task 3 Step 3). The probe cannot observe a decision that leaves no DOM trace (a hidden block looks like a disabled one), and `ResizeObserver` never fires in the fake DOM. The hook is inert in a real browser beyond the assignment.

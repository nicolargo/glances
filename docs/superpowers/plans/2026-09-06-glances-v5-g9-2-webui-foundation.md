# G9-2 — v5 WebUI foundation: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn G9-1's diagnostic page into the foundation the remaining 32 plugin ports build on: a service layer, a design-token contract, an app shell, and the two reference components `mem` and `network`.

**Architecture:** Bottom-up, each layer testable before the one above exists. Tokens and their enforcement first (they bind everything). Then the two pure modules — formatting and level mapping. Then the service layer. Then the shell that composes them. Then the two components. Nothing depends on a later task.

**Tech Stack:** Vue 3 (Options API, SFC), modern CSS custom properties, webpack 5, `node --test` (built in, no npm dependency), pytest.

**Spec:** `docs/superpowers/specs/2026-09-06-glances-v5-g9-2-webui-foundation-design.md`

**Depends on:** G9-1, committed as `dd53508e`.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.**
- **v4 is read-only.** `js/app.js`, `js/browser.js`, `js/services.js`, `js/components/**`, `js/App.vue`, `js/Browser.vue`, `js/store.js`, `js/filters.js`, `css/*.scss`, `templates/index.html`, and the v4 bundles `public/glances.js` / `public/browser.js`. `webpack.config.js` is shared: **only its `v5Config` object may be edited**, never `v4Config`.
- **After every `npm run build`, the v4 bundles must be byte-identical:**
  ```bash
  for f in glances.js browser.js; do
    W=$(git hash-object glances/outputs/static/public/$f)
    C=$(git rev-parse HEAD:glances/outputs/static/public/$f)
    [ "$W" = "$C" ] && echo "$f IDENTICAL" || echo "$f DIFFERS"
  done
  ```
  Both must print IDENTICAL. If either DIFFERS, STOP and report — do not revert by hand.
- **Build with `npm run build` only.** Never `npm install`: `package-lock.json` is tracked and must not move.
- **No new npm dependency.** Node's built-in test runner and ESM auto-detection cover the JS tests — verified: `node -e "import('./glances/outputs/static/js/v5/x.js')"` resolves ESM from that directory with no `type` field and no config.
- **R1 — no colour literal in any component or module.** Every colour comes from a token in `css/v5.css`. Task 1 makes this a test; do not weaken it later to make a component easier.
- **No dead code may be merged.**
- `tests/test_mcp.py` has pre-existing failures unrelated to this work when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`); `tests/test_perf.py` is load-sensitive — re-run it alone before believing a failure.

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/outputs/static/css/v5.css` | Token blocks for `dark` (default) and `light`; typographic scale. |
| `glances/outputs/static/js/v5/format.js` | Bytes, rates, percentages. Pure. |
| `glances/outputs/static/js/v5/levels.js` | `_levels` → CSS class. The only place tier semantics live. Pure. |
| `glances/outputs/static/js/v5/api.js` | `getJson()`, shape validation, refresh resolution, poll loop. |
| `glances/outputs/static/js/v5/AppShell.vue` | Header, plugin area, footer alert list. |
| `glances/outputs/static/js/v5/PluginMem.vue` | Reference: scalar shape. |
| `glances/outputs/static/js/v5/PluginNetwork.vue` | Reference: collection shape. |
| `glances/outputs/static/js/app_v5.js` | Entry; mounts the shell. Replaces G9-1's diagnostic body. |
| `glances/outputs/static/webpack.config.js` | `v5Config` only: `vue-loader` restored, `devServer` added. |
| `tests/js/format.test.mjs` | `node --test` unit tests. |
| `tests/js/levels.test.mjs` | `node --test` unit tests. |
| `tests/js/api.test.mjs` | `node --test` unit tests. |
| `tests/test_webui_v5_tokens.py` | Enforces R1 (no colour literals). |
| `tests/test_webserver_v5.py` | Reworked render probe (append/modify). |
| `tests/fixtures/webui_render_probe.js` | Extended DOM stub. |

---

### Task 1: Design tokens and the rule that protects them

**Files:**
- Create: `glances/outputs/static/css/v5.css`
- Create: `tests/test_webui_v5_tokens.py`

**Interfaces:**
- Produces: the token names every later task and every future theme uses. Treat this list as an interface: later tasks may ADD a token, never rename one.

- [ ] **Step 1: Write the enforcement test first**

Create `tests/test_webui_v5_tokens.py` with the repo's 8-line SPDX header (copy from `glances/exports/export_base_v5.py`), then:

```python
"""Glances v5 — the WebUI design-token contract is enforced, not documented.

Spec section 5.1, R1: a component carrying a colour literal cannot be themed.
A user theme sets custom properties; it cannot reach `color: #d33` inside a
component. Unenforced, that promise degrades one plugin at a time across 32
ports and nobody notices until a user's theme half-works.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_STATIC = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static"
_V5_JS = _STATIC / "js" / "v5"
_TOKENS = _STATIC / "css" / "v5.css"

# Hex colours, rgb()/rgba()/hsl()/hsla(), and the CSS named colours a
# component is realistically tempted to reach for.
#
# Named colours are only matched after a `:` -- i.e. in CSS property-value
# position. Without that anchor the word "green" in a prose comment trips the
# test, which across 32 plugin ports becomes a permanent source of friction
# and, eventually, of someone disabling the check.
_COLOUR = re.compile(
    r"#[0-9a-fA-F]{3,8}\b"
    r"|\brgba?\s*\("
    r"|\bhsla?\s*\("
    r"|:\s*(?:red|green|blue|yellow|orange|purple|magenta|cyan|white|black|grey|gray)\b",
)


def _v5_sources() -> list[Path]:
    return sorted(p for p in _V5_JS.rglob("*") if p.suffix in {".vue", ".js"})


def test_v5_sources_exist():
    """Guard: an empty glob would make every assertion below vacuous."""
    assert _v5_sources(), f"no v5 sources found under {_V5_JS}"


@pytest.mark.parametrize("path", _v5_sources(), ids=lambda p: p.name)
def test_no_colour_literal_outside_the_token_file(path: Path):
    hits = [
        f"{path.name}:{i}: {line.strip()}"
        for i, line in enumerate(path.read_text().splitlines(), 1)
        if _COLOUR.search(line)
    ]
    assert not hits, (
        "Colour literals must live in css/v5.css so a user theme can override "
        "them (spec 5.1 R1):\n" + "\n".join(hits)
    )


def test_token_file_defines_both_shipped_themes():
    css = _TOKENS.read_text()
    assert ':root[data-theme="light"]' in css
    # `dark` is the default block on bare :root, matching [outputs] theme=dark.
    assert re.search(r"^:root\s*\{", css, re.M)


def test_every_tier_has_a_token_in_both_themes():
    css = _TOKENS.read_text()
    for tier in ("ok", "careful", "warning", "critical"):
        assert css.count(f"--gl-level-{tier}:") >= 2, (
            f"--gl-level-{tier} must be defined in both the default and the light block"
        )
```

- [ ] **Step 2: Run it to verify it fails**

```bash
uv run pytest tests/test_webui_v5_tokens.py -q
```
Expected: FAIL — `css/v5.css` and `js/v5/` do not exist yet.

- [ ] **Step 3: Write the token file**

Create `glances/outputs/static/css/v5.css`:

```css
/* Glances v5 WebUI — design tokens.
 *
 * A theme is ONE block of custom-property values. `dark` is the default
 * (bare :root, matching `[outputs] theme=dark`); `light` overrides it.
 * Adding a third theme means adding a block here — never editing a
 * component. See the design spec, section 5.
 *
 * Tier hues are web-native, not the TUI's ANSI ones: blue-for-careful and
 * magenta-for-warning come from the terminal's 8-colour palette. Only ONE
 * hue actually changes — warning goes magenta -> amber; ok/careful/critical
 * keep their meaning and roughly their look.
 */

:root {
  --gl-bg: #15181c;
  --gl-surface: #1d2126;
  --gl-fg: #e8eaed;
  --gl-muted: #99a1ab;
  --gl-border: #2c3239;

  --gl-level-ok: #57c08a;
  --gl-level-careful: #5aa9e6;
  --gl-level-warning: #e0a63c;
  --gl-level-critical: #e8695c;
  --gl-prominent-bg: #2a313a;

  --gl-font: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  --gl-size-sm: 0.78rem;
  --gl-size-base: 0.88rem;
  --gl-size-lg: 1.05rem;
  --gl-weight-normal: 400;
  --gl-weight-bold: 600;
  --gl-gap: 0.5rem;
}

:root[data-theme="light"] {
  --gl-bg: #ffffff;
  --gl-surface: #f4f6f8;
  --gl-fg: #1b1f23;
  --gl-muted: #5a636d;
  --gl-border: #d5dae0;

  --gl-level-ok: #1a7f4b;
  --gl-level-careful: #1667a8;
  --gl-level-warning: #97650a;
  --gl-level-critical: #b3261e;
  --gl-prominent-bg: #e6eaef;
}

body {
  margin: 0;
  background: var(--gl-bg);
  color: var(--gl-fg);
  font-family: var(--gl-font);
  font-size: var(--gl-size-base);
}

/* Tier classes. `prominent` adds a BACKGROUND, never a different hue --
 * spec 5.1 R3: colour is never the only signal, because contrast cannot be
 * guaranteed for a user-written theme. */
.gl-level-ok { color: var(--gl-level-ok); }
.gl-level-careful { color: var(--gl-level-careful); }
.gl-level-warning { color: var(--gl-level-warning); }
.gl-level-critical { color: var(--gl-level-critical); }
.gl-prominent { background: var(--gl-prominent-bg); }

/* Titles and column headers are NEVER given a tier colour -- ported verbatim
 * from the TUI contract (glances/outputs/curses_renderer_v5.py:126-129): an
 * alert is signalled on the VALUE only. */
.gl-header {
  color: var(--gl-muted);
  font-weight: var(--gl-weight-bold);
}
```

- [ ] **Step 4: Verify the contrast ratios**

The two shipped themes are the only ones whose contrast can be guaranteed
(spec §5.1 R3). Measure, do not eyeball:

```bash
uv run python - <<'PY'
def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
dark_bg, light_bg = "#15181c", "#ffffff"
dark = {"ok": "#57c08a", "careful": "#5aa9e6", "warning": "#e0a63c", "critical": "#e8695c", "fg": "#e8eaed", "muted": "#99a1ab"}
light = {"ok": "#1a7f4b", "careful": "#1667a8", "warning": "#97650a", "critical": "#b3261e", "fg": "#1b1f23", "muted": "#5a636d"}
for name, bg, pal in (("dark", dark_bg, dark), ("light", light_bg, light)):
    for k, v in pal.items():
        r = ratio(v, bg)
        print(f"{name:5s} {k:9s} {v} -> {r:.2f} {'OK' if r >= 4.5 else 'FAIL'}")
PY
```

Every line must print OK (≥ 4.5:1, WCAG AA for body text). If any FAILs,
adjust that token until it passes and report the value you changed it to.
**Paste the full table into your task report** — this is the evidence that
R3's premise ("contrast can be verified for the shipped themes") holds.

- [ ] **Step 5: Run the enforcement test**

```bash
uv run pytest tests/test_webui_v5_tokens.py -q
```
Expected: `test_v5_sources_exist` still FAILS (no `js/v5/` yet — Task 2 creates it); the three token-file tests PASS. Confirm that is the only failure.

- [ ] **Step 6: Stage**

```bash
git add glances/outputs/static/css/v5.css tests/test_webui_v5_tokens.py
```

---

### Task 2: `format.js` and `levels.js`

**Files:**
- Create: `glances/outputs/static/js/v5/format.js`
- Create: `glances/outputs/static/js/v5/levels.js`
- Test: `tests/js/format.test.mjs`, `tests/js/levels.test.mjs`
- Test: `tests/test_webui_v5_js.py` (the pytest bridge that runs them)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `formatBytes(n) -> string`, `formatRate(n) -> string`, `formatPercent(n) -> string` from `format.js`
  - `levelClass(entry) -> string`, `scalarLevel(payload, field) -> entry|null`, `itemLevel(payload, key, field) -> entry|null` from `levels.js`

`levels.js` deliberately exposes NO function for colouring a header. The TUI rule (an alert is signalled on the value only) is enforced by there being no API to violate it.

- [ ] **Step 1: Write the failing tests**

Create `tests/js/format.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { formatBytes, formatRate, formatPercent } from "../../glances/outputs/static/js/v5/format.js";

test("formatBytes uses binary units", () => {
	assert.equal(formatBytes(0), "0B");
	assert.equal(formatBytes(1023), "1023B");
	assert.equal(formatBytes(1024), "1.0K");
	assert.equal(formatBytes(16417853440), "15.3G");
});

test("formatBytes survives what the API can actually send", () => {
	// A rate field is null until its second cycle -- see the v5 base plugin.
	assert.equal(formatBytes(null), "-");
	assert.equal(formatBytes(undefined), "-");
});

test("formatRate marks per-second values", () => {
	assert.equal(formatRate(1024), "1.0K/s");
	assert.equal(formatRate(null), "-");
});

test("formatPercent keeps one decimal", () => {
	assert.equal(formatPercent(52.5), "52.5%");
	assert.equal(formatPercent(0), "0.0%");
	assert.equal(formatPercent(null), "-");
});
```

Create `tests/js/levels.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { levelClass, scalarLevel, itemLevel } from "../../glances/outputs/static/js/v5/levels.js";

const SCALAR = { percent: 52.5, _levels: { percent: { level: "careful", prominent: true } } };
const COLLECTION = {
	data: [{ interface_name: "eth0", errors_in: 0 }],
	_levels: { eth0: { errors_in: { level: "ok", prominent: false } } },
};

test("each tier maps to its class", () => {
	for (const tier of ["ok", "careful", "warning", "critical"]) {
		assert.equal(levelClass({ level: tier }), `gl-level-${tier}`);
	}
});

test("prominent adds a background class, not a different colour", () => {
	assert.equal(levelClass({ level: "critical", prominent: true }), "gl-level-critical gl-prominent");
});

test("an unknown or missing tier yields no class", () => {
	assert.equal(levelClass(null), "");
	assert.equal(levelClass(undefined), "");
	assert.equal(levelClass({ level: "bogus" }), "");
	assert.equal(levelClass({}), "");
});

test("scalarLevel reads _levels[field]", () => {
	assert.deepEqual(scalarLevel(SCALAR, "percent"), { level: "careful", prominent: true });
	assert.equal(scalarLevel(SCALAR, "total"), null);
	assert.equal(scalarLevel({}, "percent"), null);
});

test("itemLevel reads _levels[primaryKeyValue][field]", () => {
	assert.deepEqual(itemLevel(COLLECTION, "eth0", "errors_in"), { level: "ok", prominent: false });
	assert.equal(itemLevel(COLLECTION, "eth0", "bytes_recv"), null);
	assert.equal(itemLevel(COLLECTION, "lo", "errors_in"), null);
});

test("the module exposes no way to colour a header", () => {
	// The TUI signals an alert on the VALUE only
	// (glances/outputs/curses_renderer_v5.py:126-129). The rule is enforced
	// by there being no API to break it, not by a comment.
	// eslint-disable-next-line no-undef
	assert.equal(typeof globalThis.headerClass, "undefined");
});
```

Create `tests/test_webui_v5_js.py` (SPDX header, then):

```python
"""Glances v5 — run the WebUI's pure JS modules under node's built-in runner.

No npm test dependency: node ships a runner (`node --test`, 18+) and
auto-detects ESM syntax in a `.js` file when the nearest package.json has no
`type` field (22+) -- which is exactly the case for
`glances/outputs/static/`. Verified before this plan was written.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_JS_TESTS = Path(__file__).resolve().parent / "js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _run(*paths: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "--no-warnings", "--test", *paths],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_js_test_files_exist():
    """Guard: an empty file list would make node exit 0 and prove nothing."""
    assert sorted(p.name for p in _JS_TESTS.glob("*.test.mjs"))


def test_pure_modules_pass_their_unit_tests():
    result = _run("tests/js/format.test.mjs", "tests/js/levels.test.mjs")
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `js/v5/format.js` and `js/v5/levels.js` do not exist.

- [ ] **Step 3: Write `format.js`**

```js
// Glances v5 WebUI — value formatting.
//
// Shared by every plugin component, so the same number reads the same way
// everywhere. Pure: no DOM, no fetch, no imports.
//
// Every function accepts null/undefined and returns "-". This is not
// defensive padding: a v5 `rate` field is genuinely null until its second
// cycle (the plugin base keeps the field present rather than dropping it),
// so null IS a value the API sends.

const UNITS = ["B", "K", "M", "G", "T", "P"];
const MISSING = "-";

function isNumber(value) {
	return typeof value === "number" && Number.isFinite(value);
}

export function formatBytes(value) {
	if (!isNumber(value)) return MISSING;
	let n = value;
	let i = 0;
	while (n >= 1024 && i < UNITS.length - 1) {
		n /= 1024;
		i += 1;
	}
	return i === 0 ? `${Math.round(n)}${UNITS[0]}` : `${n.toFixed(1)}${UNITS[i]}`;
}

export function formatRate(value) {
	if (!isNumber(value)) return MISSING;
	return `${formatBytes(value)}/s`;
}

export function formatPercent(value) {
	if (!isNumber(value)) return MISSING;
	return `${value.toFixed(1)}%`;
}
```

- [ ] **Step 4: Write `levels.js`**

```js
// Glances v5 WebUI — the `_levels` payload field to a CSS class.
//
// The ONLY place tier semantics live. Components ask this module; they never
// test `level === "critical"` themselves, or the redesign drifts from the TUI
// one component at a time across 32 ports.
//
// Ported from the TUI contract (glances/outputs/curses_renderer_v5.py):
//   - four tiers: ok, careful, warning, critical
//   - `prominent` means a BACKGROUND highlight, not a different hue
//   - an alert is signalled on the VALUE only; titles and column headers are
//     never given a tier colour. This module therefore exposes no function
//     that could colour a header -- the rule is enforced by omission.

const TIERS = new Set(["ok", "careful", "warning", "critical"]);

export function levelClass(entry) {
	if (!entry || !TIERS.has(entry.level)) return "";
	return entry.prominent ? `gl-level-${entry.level} gl-prominent` : `gl-level-${entry.level}`;
}

export function scalarLevel(payload, field) {
	const levels = payload && payload._levels;
	return (levels && levels[field]) || null;
}

export function itemLevel(payload, key, field) {
	const levels = payload && payload._levels;
	const item = levels && levels[key];
	return (item && item[field]) || null;
}
```

- [ ] **Step 5: Run the tests**

```bash
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
```
Expected: PASS. `js/v5/` now exists, so Task 1's `test_v5_sources_exist` is satisfied and the colour-literal check runs against these two modules.

- [ ] **Step 6: Prove the colour check bites**

Temporarily add `const RED = "#ff0000";` to `levels.js`, re-run
`uv run pytest tests/test_webui_v5_tokens.py -q`, confirm it FAILS naming that
line, then remove it and confirm it PASSES. **A rule nobody has seen fail is a
rule nobody knows works.** Report both outcomes.

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/format.js glances/outputs/static/js/v5/levels.js \
        tests/js/format.test.mjs tests/js/levels.test.mjs tests/test_webui_v5_js.py
```

---

### Task 3: The service layer

**Files:**
- Create: `glances/outputs/static/js/v5/api.js`
- Test: `tests/js/api.test.mjs`
- Modify: `tests/test_webui_v5_js.py` (add the new file to the runner call)

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces:
  - `getJson(path) -> Promise<object>` — throws `Error("<path>: HTTP <status>")` on a non-OK status
  - `validate(payload, spec) -> object` — throws on shape mismatch; `spec` is `{shape: "scalar"|"collection", required: string[]}`
  - `resolveRefreshSeconds() -> Promise<number>`
  - `fetchPlugins(specs) -> Promise<{results, errors}>` — independent per-endpoint outcomes
  - `DEFAULT_REFRESH_SECONDS` (2)

- [ ] **Step 1: Write the failing tests**

Create `tests/js/api.test.mjs`:

```js
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
	getJson,
	validate,
	resolveRefreshSeconds,
	fetchPlugins,
	DEFAULT_REFRESH_SECONDS,
} from "../../glances/outputs/static/js/v5/api.js";

function stubFetch(routes) {
	globalThis.fetch = async (path) => {
		const r = routes[path];
		if (!r) throw new TypeError("network error");
		return {
			ok: r.status === undefined || (r.status >= 200 && r.status < 300),
			status: r.status ?? 200,
			json: async () => r.body,
		};
	};
}

beforeEach(() => {
	delete globalThis.fetch;
});

test("getJson returns the parsed body on 200", async () => {
	stubFetch({ "api/5/mem": { body: { percent: 1 } } });
	assert.deepEqual(await getJson("api/5/mem"), { percent: 1 });
});

test("getJson throws with the path and status on a non-OK response", async () => {
	stubFetch({ "api/5/mem": { status: 500, body: { detail: "boom" } } });
	await assert.rejects(() => getJson("api/5/mem"), /api\/5\/mem: HTTP 500/);
});

test("validate rejects a 200 carrying the wrong shape", () => {
	// The failure that started this: fetch does not reject on 4xx/5xx, and a
	// FastAPI error body is valid JSON. Without a shape check it renders as
	// data -- G9-1's page reported a plausible, wrong plugin count.
	const spec = { shape: "scalar", required: ["percent", "total"] };
	assert.throws(() => validate({ detail: "boom" }, spec), /missing|shape/i);
});

test("validate accepts a well-formed scalar payload", () => {
	const spec = { shape: "scalar", required: ["percent"] };
	const payload = { percent: 52.5, _levels: {} };
	assert.equal(validate(payload, spec), payload);
});

test("validate requires a data array for a collection", () => {
	const spec = { shape: "collection", required: ["interface_name"] };
	assert.throws(() => validate({ detail: "boom" }, spec), /shape/i);
	assert.throws(() => validate({ data: {} }, spec), /shape/i);
	const ok = { data: [{ interface_name: "eth0" }] };
	assert.equal(validate(ok, spec), ok);
});

test("validate accepts an empty collection", () => {
	// A plugin with nothing to show (no container running) is not an error.
	const spec = { shape: "collection", required: ["interface_name"] };
	const ok = { data: [] };
	assert.equal(validate(ok, spec), ok);
});

test("validate passes a cycle-0 null through untouched", () => {
	// /api/5/<plugin> answers `200 null` before the first cycle (G9-1
	// contract). That is a loading state, not a shape error.
	const spec = { shape: "scalar", required: ["percent"] };
	assert.equal(validate(null, spec), null);
});

test("resolveRefreshSeconds reads [global] refresh", async () => {
	stubFetch({ "api/5/config": { body: { global: { refresh: 5 } } } });
	assert.equal(await resolveRefreshSeconds(), 5);
});

test("resolveRefreshSeconds falls back when config is unreachable", async () => {
	stubFetch({});
	assert.equal(await resolveRefreshSeconds(), DEFAULT_REFRESH_SECONDS);
});

test("resolveRefreshSeconds falls back on a config without the key", async () => {
	stubFetch({ "api/5/config": { body: {} } });
	assert.equal(await resolveRefreshSeconds(), DEFAULT_REFRESH_SECONDS);
});

test("one failing endpoint does not discard the others", async () => {
	stubFetch({
		"api/5/mem": { body: { percent: 52.5 } },
		"api/5/network": { status: 503, body: {} },
	});
	const { results, errors } = await fetchPlugins([
		{ name: "mem", path: "api/5/mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", path: "api/5/network", spec: { shape: "collection", required: [] } },
	]);
	assert.deepEqual(results.mem, { percent: 52.5 });
	assert.equal(results.network, undefined);
	assert.match(errors.network, /HTTP 503/);
	assert.equal(errors.mem, undefined);
});
```

Then add the file to the runner call in `tests/test_webui_v5_js.py`:

```python
def test_pure_modules_pass_their_unit_tests():
    result = _run(
        "tests/js/format.test.mjs",
        "tests/js/levels.test.mjs",
        "tests/js/api.test.mjs",
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `js/v5/api.js` does not exist.

- [ ] **Step 3: Write `api.js`**

```js
// Glances v5 WebUI — the only module that talks to /api/5.
//
// Three things components must not each reinvent:
//
// 1. `fetch` does NOT reject on 4xx/5xx. Only a network failure rejects, so a
//    500 carrying a JSON error body parses cleanly and looks like data.
// 2. Nor does a status check catch a 200 whose BODY is the wrong shape
//    (FastAPI's `{"detail": ...}`). G9-1's diagnostic page reported a
//    plausible, wrong plugin count for exactly this reason. Hence `validate`.
// 3. Endpoint outcomes must be independent: one plugin's failure must not
//    blank the page.

export const DEFAULT_REFRESH_SECONDS = 2;

export async function getJson(path) {
	const response = await fetch(path);
	if (!response.ok) {
		throw new Error(`${path}: HTTP ${response.status}`);
	}
	return response.json();
}

export function validate(payload, spec) {
	// `200 null` means the plugin has registered but has not published yet
	// (scheduler cycle 0) -- the G9-1 route contract. A loading state, not a
	// shape error; the caller renders it as such.
	if (payload === null || payload === undefined) return payload;

	if (spec.shape === "collection") {
		if (typeof payload !== "object" || !Array.isArray(payload.data)) {
			throw new Error("unexpected shape: expected a collection envelope with a data array");
		}
		// An empty collection is legitimate (no container running, no folder
		// configured). Only a NON-empty one can be checked for fields.
		const first = payload.data[0];
		if (first) requireFields(first, spec.required);
		return payload;
	}

	if (typeof payload !== "object" || Array.isArray(payload)) {
		throw new Error("unexpected shape: expected a scalar payload object");
	}
	requireFields(payload, spec.required);
	return payload;
}

function requireFields(obj, required) {
	const missing = (required || []).filter((field) => !(field in obj));
	if (missing.length) {
		throw new Error(`unexpected shape: missing ${missing.join(", ")}`);
	}
}

export async function resolveRefreshSeconds() {
	// [global] refresh, via /api/5/config. NOT /api/5/args: measured in G9-1,
	// the v5 argument namespace carries no refresh key at all.
	try {
		const config = await getJson("api/5/config");
		const refresh = config && config.global && config.global.refresh;
		const seconds = Number(refresh);
		if (Number.isFinite(seconds) && seconds > 0) return seconds;
	} catch {
		// Fall through: a UI that cannot read the cadence still polls at the
		// default rather than not polling at all.
	}
	return DEFAULT_REFRESH_SECONDS;
}

export async function fetchPlugins(specs) {
	const settled = await Promise.allSettled(
		specs.map(async (s) => ({ name: s.name, payload: validate(await getJson(s.path), s.spec) })),
	);
	const results = {};
	const errors = {};
	settled.forEach((outcome, i) => {
		const name = specs[i].name;
		if (outcome.status === "fulfilled") {
			results[name] = outcome.value.payload;
		} else {
			errors[name] = outcome.reason.message;
		}
	});
	return { results, errors };
}
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
```
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add glances/outputs/static/js/v5/api.js tests/js/api.test.mjs tests/test_webui_v5_js.py
```

---

### Task 4: The shell, the two reference components, and a render test that survives them

**Files:**
- Create: `glances/outputs/static/js/v5/AppShell.vue`
- Create: `glances/outputs/static/js/v5/PluginMem.vue`, `glances/outputs/static/js/v5/PluginNetwork.vue`
- Modify: `glances/outputs/static/js/app_v5.js` (replace G9-1's diagnostic body)
- Modify: `glances/outputs/static/webpack.config.js` (**`v5Config` only**)
- Modify: `glances/outputs/static/templates/index_v5.html` (link the stylesheet)
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`

**Interfaces:**
- Consumes: `api.js` (`fetchPlugins`, `resolveRefreshSeconds`), `css/v5.css`.
- Produces: `AppShell.vue` rendering `<main class="gl-app">` with a `<header>`, a plugin area and a `<footer>` alert list; plus the two components it composes.

**Why one task and not two.** `AppShell.vue` imports both components, so the
build cannot succeed without them and neither renders without the shell. A
reviewer cannot meaningfully approve one and reject the other, which is the
test for whether work belongs in the same task.

Both components handle three states, in this order: `error` (a string),
`payload === null` (cycle 0, loading), then data. Scalar and collection are the
only two payload shapes v5 has, so between them these two establish the pattern
G9-3…N follow for the remaining 32 plugins.

- [ ] **Step 1: Restore `vue-loader`, add the CSS rule and `devServer` to the v5 config**

In `glances/outputs/static/webpack.config.js`, inside **`v5Config` only** — do
not touch `v4Config`. Add a `module` key and a `devServer` key, and extend
`plugins`. The `v5Config` object currently ends:

```js
		plugins: [vueDefines],
	};
```

Replace that with:

```js
		module: {
			rules: [
				{
					test: /\.vue$/i,
					loader: "vue-loader",
				},
				{
					test: /\.css$/i,
					use: [{ loader: "style-loader" }, { loader: "css-loader" }],
				},
			],
		},
		// vue-loader and its plugin come back with this group: G9-1 removed
		// them as dead config because no .vue file existed yet.
		plugins: [vueDefines, new VueLoaderPlugin()],
		// G9-1 left `npm start` serving v4 only: webpack-dev-server picks the
		// config carrying `devServer`, which was v4Config's. Without this,
		// G9-3..N develop 32 components with no hot reload -- a tax paid 32
		// times. A distinct port lets both dev servers run side by side.
		devServer: {
			client: { overlay: false },
			host: "0.0.0.0",
			port: PORT + 1,
			hot: true,
		},
	};
```

`VueLoaderPlugin` and `PORT` are already imported/defined at the top of the
file for `v4Config`; do not re-declare them. Leave the `resolve.alias` that is
already there — single-file components are compiled at build time, so the
runtime build would now suffice, but removing the alias is a separate change
with its own risk and is not this task's business.

- [ ] **Step 2: Write `PluginMem.vue` (scalar)**

```vue
<template>
	<article class="gl-plugin">
		<h2 class="gl-header">MEM</h2>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<dl v-else>
			<div v-for="row in rows" :key="row.field">
				<dt class="gl-header">{{ row.label }}</dt>
				<dd :class="levelClass(scalarLevel(payload, row.field))">{{ row.value }}</dd>
			</div>
		</dl>
	</article>
</template>

<script>
import { formatBytes, formatPercent } from "./format.js";
import { levelClass, scalarLevel } from "./levels.js";

export default {
	name: "PluginMem",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
	},
	computed: {
		rows() {
			const p = this.payload;
			return [
				{ field: "percent", label: "percent", value: formatPercent(p.percent) },
				{ field: "total", label: "total", value: formatBytes(p.total) },
				{ field: "used", label: "used", value: formatBytes(p.used) },
				{ field: "free", label: "free", value: formatBytes(p.free) },
			];
		},
	},
	methods: { levelClass, scalarLevel },
};
</script>

<style scoped>
.gl-plugin dl {
	margin: 0;
}
.gl-plugin dt {
	display: inline-block;
	width: 6rem;
}
.gl-plugin dd {
	display: inline;
	margin: 0;
}
</style>
```

Note `<h2 class="gl-header">` and `<dt class="gl-header">`: titles and column
labels take the header class, **never a tier class**. Only the `<dd>` value
gets `levelClass(...)`. That is the TUI rule (spec §4), and it is why
`levels.js` offers no header helper.

- [ ] **Step 3: Write `PluginNetwork.vue` (collection)**

```vue
<template>
	<article class="gl-plugin">
		<h2 class="gl-header">NETWORK</h2>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<p v-else-if="!payload.data.length" class="gl-muted">no interface</p>
		<table v-else>
			<thead>
				<tr>
					<th class="gl-header">interface</th>
					<th class="gl-header">Rx/s</th>
					<th class="gl-header">Tx/s</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in payload.data" :key="item.interface_name">
					<td>{{ item.interface_name }}</td>
					<td :class="cellClass(item, 'bytes_recv')">{{ rate(item.bytes_recv) }}</td>
					<td :class="cellClass(item, 'bytes_sent')">{{ rate(item.bytes_sent) }}</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatRate } from "./format.js";
import { levelClass, itemLevel } from "./levels.js";

export default {
	name: "PluginNetwork",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
	},
	methods: {
		rate: formatRate,
		cellClass(item, field) {
			// _levels for a collection is keyed by the item's PRIMARY KEY value,
			// not by its index -- see the design spec, section 4.
			return levelClass(itemLevel(this.payload, item.interface_name, field));
		},
	},
};
</script>

<style scoped>
.gl-plugin table {
	border-collapse: collapse;
}
.gl-plugin th,
.gl-plugin td {
	padding: 0 var(--gl-gap) 0 0;
	text-align: left;
}
</style>
```

`bytes_recv` and `bytes_sent` ARE the per-second rates in v5 — converted in
place by the plugin base. The v4 component's `bytes_recv_rate_per_sec` and
`bytes_all` do not exist here (spec §4).

- [ ] **Step 4: Write the shell**

Create `glances/outputs/static/js/v5/AppShell.vue`:

```vue
<template>
	<main class="gl-app">
		<header class="gl-topbar">
			<span class="gl-header">Glances</span>
			<span class="gl-muted">{{ refreshLabel }}</span>
		</header>

		<section class="gl-plugins">
			<PluginMem :payload="results.mem" :error="errors.mem" />
			<PluginNetwork :payload="results.network" :error="errors.network" />
		</section>

		<footer class="gl-alerts">
			<span v-if="!alerts.length" class="gl-muted">No alert</span>
			<ul v-else>
				<li v-for="(alert, i) in alerts" :key="i" :class="levelClass(alert)">
					{{ alert.description || alert.level }}
				</li>
			</ul>
		</footer>
	</main>
</template>

<script>
import { fetchPlugins, resolveRefreshSeconds, getJson } from "./api.js";
import { levelClass } from "./levels.js";
import PluginMem from "./PluginMem.vue";
import PluginNetwork from "./PluginNetwork.vue";

// Each plugin declares the shape it expects. The service layer rejects a 200
// whose body does not match, so a FastAPI error body can never render as data.
const PLUGINS = [
	{ name: "mem", path: "api/5/mem", spec: { shape: "scalar", required: ["percent", "total"] } },
	{
		name: "network",
		path: "api/5/network",
		spec: { shape: "collection", required: ["interface_name"] },
	},
];

export default {
	name: "AppShell",
	components: { PluginMem, PluginNetwork },
	data() {
		return { results: {}, errors: {}, alerts: [], refresh: null, timer: null };
	},
	computed: {
		refreshLabel() {
			return this.refresh === null ? "…" : `refresh ${this.refresh}s`;
		},
	},
	async mounted() {
		this.refresh = await resolveRefreshSeconds();
		await this.tick();
		this.timer = setInterval(() => this.tick(), this.refresh * 1000);
	},
	unmounted() {
		// The poll must stop with the component, or a hot reload during G9-3..N
		// leaves timers stacking up against the API.
		if (this.timer) clearInterval(this.timer);
	},
	methods: {
		levelClass,
		async tick() {
			const { results, errors } = await fetchPlugins(PLUGINS);
			this.results = results;
			this.errors = errors;
			// The footer alert list is its own endpoint; its failure must not
			// disturb the plugins above it.
			try {
				const history = await getJson("api/5/alert");
				this.alerts = Array.isArray(history) ? history.slice(0, 10) : [];
			} catch {
				this.alerts = [];
			}
		},
	},
};
</script>

<style scoped>
.gl-app {
	display: flex;
	flex-direction: column;
	gap: var(--gl-gap);
	padding: var(--gl-gap);
}
.gl-topbar {
	display: flex;
	justify-content: space-between;
	border-bottom: 1px solid var(--gl-border);
	padding-bottom: var(--gl-gap);
}
.gl-plugins {
	display: flex;
	flex-wrap: wrap;
	gap: calc(var(--gl-gap) * 2);
}
.gl-alerts ul {
	margin: 0;
	padding-left: 1rem;
}
.gl-muted {
	color: var(--gl-muted);
}
</style>
```

The footer is a **vertical list capped at 10**, matching the project's WebUI
principle (a vertical alert list, not one horizontal row).

- [ ] **Step 5: Rewrite the entry point**

Replace the body of `glances/outputs/static/js/app_v5.js`:

```js
// Glances v5 WebUI entry point.
//
// The `template:` option G9-1 used needs Vue's template compiler, which the
// runtime-only build does not carry -- that shipped a silently blank page.
// Single-file components are compiled by vue-loader at build time, so the
// runtime build is enough and the alias stays a belt-and-braces measure.

import { createApp } from "vue";
import "../css/v5.css";
import AppShell from "./v5/AppShell.vue";

createApp(AppShell).mount("#app");
```

- [ ] **Step 6: Link nothing new in the HTML**

`css/v5.css` is imported by `app_v5.js` and injected by `style-loader`, so
`templates/index_v5.html` needs no `<link>`. Set the initial theme instead —
replace the `<html ...>` opening tag's `data-bs-theme="dark"` (a Bootstrap
attribute that does nothing now that D3 dropped the framework) with
`data-theme="dark"`, matching the token file's selector and `[outputs] theme`'s
default.

- [ ] **Step 7: Build**

```bash
cd glances/outputs/static && npm run build && cd -
git status --short glances/outputs/static/public/
```

Then run the v4-bundle identity check from Global Constraints. Both must print
IDENTICAL. Report the output verbatim.

- [ ] **Step 8: Rework the render probe**

`tests/test_webserver_v5.py::test_the_v5_bundle_actually_renders_an_element`
currently asserts `tagName == "MAIN"` against G9-1's stub. The shell also
renders `<main>`, so update the probe to assert something this group actually
guarantees, and that a blank page cannot satisfy:

- the root element is `MAIN` **and** carries the class `gl-app`;
- it contains a `HEADER` and a `FOOTER` child.

Extend `tests/fixtures/webui_render_probe.js` only as far as the new markup
needs (class attributes, nested element lookup). Keep the stub reflecting what
Vue actually appended — it must still return `childCount: 0` for an empty
script, or it proves nothing.

- [ ] **Step 9: Prove the probe still bites**

Temporarily change `app_v5.js` to `createApp({ template: "<p>x</p>" })`
(the runtime-only failure mode), rebuild, confirm the probe test FAILS, then
restore, rebuild, confirm it PASSES. **This is the regression that shipped a
blank page in G9-1; the guard must be shown to work, not assumed.** Report both
outcomes.

- [ ] **Step 10: Run the affected tests**

```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py -q
```
Expected: PASS. The token check now covers both new components.

- [ ] **Step 11: End-to-end smoke against a real server**

```bash
timeout 25 uv run python -m glances.main_v5 -s --port 61820 --quiet &
until curl -s --max-time 1 -o /dev/null http://127.0.0.1:61820/api/5/mem; do sleep 0.5; done
sleep 3
echo "index:  $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:61820/)"
echo "bundle: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:61820/static/glances5.js)"
curl -s http://127.0.0.1:61820/api/5/mem | head -c 200; echo
curl -s http://127.0.0.1:61820/api/5/network | head -c 200; echo
wait
```

Paste the ACTUAL output. Both endpoints must return the shapes the components
expect — if `network` has no `interface_name` in its items, the component's
`spec.required` is wrong and must be corrected, not the validation loosened.

- [ ] **Step 12: Stage**

```bash
git add glances/outputs/static/js/v5/AppShell.vue \
        glances/outputs/static/js/v5/PluginMem.vue \
        glances/outputs/static/js/v5/PluginNetwork.vue \
        glances/outputs/static/js/app_v5.js \
        glances/outputs/static/webpack.config.js \
        glances/outputs/static/templates/index_v5.html \
        glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_probe.js tests/test_webserver_v5.py
```

Do NOT stage `public/glances.js` or `public/browser.js` — they must be
unchanged. Do NOT commit. Mention in your report that `public/glances5.js` is a
generated artifact, so the maintainer can split it into its own
"Rebuild WebUI" commit if he prefers.

---

### Task 5: Full verification and hooks

**Files:** all files touched by Tasks 1-4.

- [ ] **Step 1: Full suite**

```bash
uv run pytest -q
```
Expected: no new failures. If `tests/test_mcp.py` fails, check
`ss -lptn 'sport = :61235'` for a leaked server before diagnosing. If
`tests/test_perf.py::test_perf_update` fails, re-run it alone — it exercises
the v4 stack and is load-sensitive, so no v5-only change can cause it.

- [ ] **Step 2: Confirm v4 is untouched**

```bash
git diff --stat HEAD -- \
  glances/outputs/static/js/app.js glances/outputs/static/js/browser.js \
  glances/outputs/static/js/services.js glances/outputs/static/js/components/ \
  glances/outputs/static/js/App.vue glances/outputs/static/js/Browser.vue \
  glances/outputs/static/js/store.js glances/outputs/static/js/filters.js \
  glances/outputs/static/css/custom.scss glances/outputs/static/css/style.scss \
  glances/outputs/static/templates/index.html
```
Expected: empty. Then the v4-bundle identity check one last time.

- [ ] **Step 3: Confirm the v5 CI job would still pass**

The job added in `.github/workflows/test.yml` runs `tests/test_*_v5*.py`. The
new test files are `test_webui_v5_tokens.py` and `test_webui_v5_js.py`, which
match that glob — confirm they are collected:

```bash
uv run pytest tests/test_*_v5*.py -q --collect-only 2>&1 | tail -3
uv run pytest tests/test_*_v5*.py -q 2>&1 | tail -3
```
Expected: both new files collected, all green.

- [ ] **Step 4: Hooks**

```bash
git add -A
make pre-commit
```
Expected: all hooks pass. Restage and re-run if a hook reformats. `.mjs` and
`.vue` files may be new to some hooks — fix what they report rather than
excluding the files.

- [ ] **Step 5: Stage the final state**

```bash
git add -A
git status --short
```
Do NOT commit.

- [ ] **Step 6: Report, do not write**

Record in the task report only, never in the repo:

- Release-notes item: the v5 WebUI now renders `mem` and `network`; the v4 UI is unchanged.
- The measured contrast table from Task 1 Step 4.
- Whether `node --test` proved sufficient, or whether the G9-3 decision point on a JS test runner (spec §9.2) should now be resolved in favour of adding one.

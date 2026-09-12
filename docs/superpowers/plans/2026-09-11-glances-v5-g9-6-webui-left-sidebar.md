# G9-6 — v5 WebUI left sidebar, batch 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `diskio`, `fs`, `sensors` and `wifi` in the v5 WebUI's left column at strict TUI parity, bring `network` to the same parity, and split the WebUI render tests out of `tests/test_webserver_v5.py` first.

**Architecture:** A pure move of tests and fixtures (Task 0), then the pure JS pieces every component needs — Python-exact formatting (Task 1), row helpers and the shared table/name CSS (Task 2) — then the schema labels on the TUI side (Task 3). The five components follow: `network` retrofitted, which also extends the probe (Task 4), `diskio` + `fs` (Task 5), `wifi` + `sensors` (Task 6). Task 7 verifies against a real server and closes.

**Tech Stack:** Vue 3.5 SFC (options API), webpack 5, `node --test`, pytest, headless Chrome, Python 3 (`uv run`).

**Spec:** `docs/superpowers/specs/2026-09-11-glances-v5-g9-6-webui-left-sidebar-design.md` (including its §6 amendment made while planning).

**Depends on:** G9-5, committed as `e3b28bfa`; HEAD `84c14da0`.

**SDD workspace:** `.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/` (git-ignored). Scratch files, captures and screenshots go there, never in the repository.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer. Never `git clean`, never `git checkout`/`restore` over working files, never `git stash`, **never unstage anything** (`git reset`, `git restore --staged`, `git rm --cached`). After staging, run `git status --short | grep -v '^[AM] '` and report any line it prints.
- **Never touch `NEWS.rst`.**
- **TUI Python files: only these may change, and only in the task named.**
  - Task 3: `glances/plugins/diskio/render_curses_v5.py`, `glances/plugins/fs/render_curses_v5.py`, `glances/plugins/wifi/render_curses_v5.py`, `glances/plugins/diskio/model_v5.py`, `glances/plugins/fs/model_v5.py`, `glances/plugins/wifi/model_v5.py`; and in `tests/test_plugin_diskio_render_curses_v5.py`, `tests/test_plugin_fs_render_curses_v5.py`, `tests/test_plugin_wifi_render_curses_v5.py` **only the schema source** — not one `assert` line may change.
  - Task 4: `glances/plugins/network/model_v5.py` (the `interface_name` `short_name` and its comment).
  - Nothing else under `glances/plugins/*/render_curses_v5.py`, `glances/plugins/*/model_v5.py`, `glances/outputs/curses_renderer_v5.py`, `glances/outputs/glances_curses_v5.py`, `glances/outputs/curses_formatters_v5.py`, `tests/test_*render_curses_v5.py`, `tests/test_curses_renderer_v5.py`. If a task seems to need one, STOP and report.
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
- **Build with `npm run build` only**, from `glances/outputs/static`. Never `npm install` (`package-lock.json` is tracked); `npm ci` is acceptable if `node_modules` is missing. Every task that changes a file under `js/v5/` or `css/v5.css` rebuilds `public/glances5.js` and stages it: the render probe runs against the bundle.
- **No new npm dependency. No new Python dependency.**
- **No colour literal under `js/v5/`** — enforced by `tests/test_webui_v5_tokens.py`.
- **`levels.js`, `columns.js`, `layout.js`, `api.js`, `labels.js`, `AppShell.vue` are not touched.**
- **No dead code at the end of Task 7.** Exports added before their first caller are listed in each task's Interfaces block; nothing may be left uncalled at the end.
- **Every expected string in a test comes from the TUI, not from this plan.** Where a step gives a Python check, run it before implementing; if Python disagrees with the plan, the plan is wrong: report it and match Python.
- **A test whose name claims something must actually observe it.** Prefer the render probe over source text.
- **Lint the JS you touch**, from the repository root:
  ```bash
  glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
  ```
  It must print nothing. If the binary fails through the harness, say so in the report — do not skip silently. `tests/fixtures/` is not linted (it never was).
- **`ruff format --check` failing on a file the task wrote or edited:** run `uv run ruff format <that file>` and re-run the task's tests. Never reformat a file the task did not touch.
- **Reports must not invent mechanisms.** If you observe something you cannot explain (a byte delta, a flaky pass), write "I cannot explain this" rather than a plausible cause.
- `tests/test_restful.py::test_050/051` are flaky by construction (hard-coded `time.sleep(5)` on a subprocess server) — re-run alone before believing a failure. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`).
- **Vue template traps** (both hit in earlier groups): a template comment placed before a component's root element makes a second root node and `data-plugin` stops landing on it — keep comments inside the root. Do not put a comment between a `v-if`/`v-else-if` element and its `v-else` sibling.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `tests/test_webui_v5_render.py` | **New.** Every render-probe test, moved from `test_webserver_v5.py`; grows in Tasks 3–6 | 0, 3–6 |
| `tests/fixtures/webui_render_fixtures.js` | **New.** The probe's fixture constants (`module.exports`) | 0, 4–6 |
| `tests/fixtures/webui_render_probe.js` | Fake DOM + collection; `require`s the fixtures; new `pluginNameCells` output and a `text` on `pluginTableCells` | 0, 4 |
| `tests/test_webserver_v5.py` | Loses the moved block and the imports only it used | 0 |
| `glances/outputs/static/js/v5/format.js` | `toFixedHalfEven`, `formatNetworkRate`, `formatFixed0`; `formatBytes` truncates below 1K and breaks ties to even | 1 |
| `glances/outputs/static/js/v5/rows.js` | **New.** `displayName`, `byText` | 2 |
| `glances/outputs/static/css/v5.css` | `.gl-name`, `.gl-truncate-start`, `.gl-table`; `.gl-truncate` comment amended | 2 |
| `glances/plugins/{diskio,fs,wifi}/model_v5.py` | `short_name`s | 3 |
| `glances/plugins/{diskio,fs,wifi}/render_curses_v5.py` | Column labels through `field_label()` | 3 |
| `tests/test_plugin_{diskio,fs,wifi}_render_curses_v5.py` | Schema source = `PluginModel.fields_description` | 3 |
| `glances/plugins/network/model_v5.py` | `interface_name` loses its `short_name` | 4 |
| `glances/outputs/static/js/v5/PluginNetwork.vue` | Retrofit | 4 |
| `glances/outputs/static/js/v5/PluginDiskio.vue`, `PluginFs.vue` | **New** | 5 |
| `glances/outputs/static/js/v5/PluginWifi.vue`, `PluginSensors.vue` | **New** | 6 |
| `glances/outputs/static/js/v5/plugins/index.js` | Four entries, `left` order `network, wifi, diskio, fs, sensors` | 5, 6 |
| `tests/js/format.test.mjs`, `tests/js/rows.test.mjs` (**new**), `tests/test_webui_v5_tokens.py` | Unit and CSS tests | 1, 2 |
| `glances/outputs/static/public/glances5.js` | Rebuilt | 1, 2, 4, 5, 6 |

---

### Task 0: Move the render tests and the probe fixtures, unchanged

**Files:**
- Create: `tests/test_webui_v5_render.py`, `tests/fixtures/webui_render_fixtures.js`
- Modify: `tests/test_webserver_v5.py`, `tests/fixtures/webui_render_probe.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `tests/test_webui_v5_render.py` holding `_BUNDLE_PATH`, `_RENDER_PROBE_PATH`, `_run_render_probe(scenario) -> dict`, `_TUI_SLOTS`, `_tier_classes(class_name) -> set`, and every probe test. `tests/fixtures/webui_render_fixtures.js` exporting `ALERT_FIXTURES`, `INFO_FIXTURES`, `SERVER_PLUGINS`, `PLUGINSLIST_FIXTURES`, `ALL_UNREACHABLE_SCENARIOS`, `ARGS_FIXTURES`, `ALL_FIXTURES`. Later tasks add fixtures to that file and tests to that test file.

No bundle rebuild in this task: nothing under `js/v5/` changes.

- [ ] **Step 1: Capture the baseline — collected test ids and every probe scenario's output**

```bash
D=.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/task0
mkdir -p $D/before $D/before2 $D/after
uv run pytest --collect-only -q tests/test_webserver_v5.py 2>/dev/null | grep '::' | sed 's/^[^:]*:://' | sort > $D/ids-before.txt
wc -l < $D/ids-before.txt
SCEN="default gpu-disabled pluginslist-unreachable mem-with-available mem-no-available network network-prominent gpu-multi-levels load memswap memswap-no-rates cpu cpu-idle-tag cpu-guest-null cpu-no-third-row cpu-ctx-switches-null gpu-one-card gpu-three-cards gpu-no-memory gpu-three-cards-mean gpu-one-card-fahrenheit gpu-first-card-colour gpu-mixed-memory gpu-zero-cards header header-hide-public ip-no-cidr ip-no-address cloud-no-name cloud-no-region cloud-disabled system-no-hostname scalar-grids all-unreachable"
B=glances/outputs/static/public/glances5.js
P=tests/fixtures/webui_render_probe.js
for s in $SCEN; do node $P $B "$s" > $D/before/$s.json 2>&1; node $P $B "$s" > $D/before2/$s.json 2>&1; done
node $P $B > $D/before/NOARG.json 2>&1; node $P $B > $D/before2/NOARG.json 2>&1
diff -r $D/before $D/before2 && echo "PROBE DETERMINISTIC"
```
Expected: a count of 91 ids, then `PROBE DETERMINISTIC`. If the probe is not deterministic, STOP and report: the byte-identity evidence below would be meaningless.

- [ ] **Step 2: Split `tests/test_webserver_v5.py`**

Save as `$D/split_tests.py` and run `uv run python $D/split_tests.py`:

```python
"""G9-6 Task 0: move the render-probe block out of test_webserver_v5.py, unchanged."""

import pathlib
import re

src_path = pathlib.Path("tests/test_webserver_v5.py")
dst_path = pathlib.Path("tests/test_webui_v5_render.py")
assert not dst_path.exists(), "tests/test_webui_v5_render.py already exists"

lines = src_path.read_text().splitlines(keepends=True)
start = next(i for i, line in enumerate(lines) if line.startswith("_BUNDLE_PATH = "))
assert lines[start + 1].startswith("_RENDER_PROBE_PATH = "), lines[start + 1]
kept, moved = lines[:start], lines[start:]
while kept[-1].strip() == "":
    kept.pop()
kept_text = "".join(kept)

ORPHANS = [
    "import shutil\n",
    "import subprocess\n",
    "from pathlib import Path\n",
    "from glances.outputs.curses_renderer_v5 import HEADER_SLOT_LEFT, HEADER_SLOT_RIGHT, LEFT_SLOT, RIGHT_SLOT, TOP_SLOT\n",
]
for imp in ORPHANS:
    assert kept_text.count(imp) == 1, f"import not found exactly once: {imp!r}"
    kept_text = kept_text.replace(imp, "", 1)
for name in ("shutil", "subprocess", "Path", "HEADER_SLOT_LEFT", "TOP_SLOT"):
    assert not re.search(rf"\b{name}\b", kept_text), f"{name} is still used in test_webserver_v5.py"
src_path.write_text(kept_text)

HEADER = '''#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI bundle rendered against a fake DOM.

These tests run tests/fixtures/webui_render_probe.js under node against the
built bundle; they never start the FastAPI app. Moved out of
test_webserver_v5.py unchanged (G9-6 Task 0).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.outputs.curses_renderer_v5 import HEADER_SLOT_LEFT, HEADER_SLOT_RIGHT, LEFT_SLOT, RIGHT_SLOT, TOP_SLOT


'''
dst_path.write_text(HEADER + "".join(moved))
print("kept", len(kept_text.splitlines()), "lines; moved", len(moved), "lines")
```

The moved block uses none of `build_app`, `config_factory`, `store`, `_args`, `TestClient` (measured while planning). `json` stays imported in `test_webserver_v5.py`: the kept tests still use it.

- [ ] **Step 3: Split the probe**

Save as `$D/split_probe.py` and run `uv run python $D/split_probe.py`:

```python
"""G9-6 Task 0: move the probe's fixture constants into their own module, unchanged."""

import pathlib

probe = pathlib.Path("tests/fixtures/webui_render_probe.js")
fixtures = pathlib.Path("tests/fixtures/webui_render_fixtures.js")
assert not fixtures.exists(), "webui_render_fixtures.js already exists"

src = probe.read_text().splitlines(keepends=True)
a = next(i for i, line in enumerate(src) if line.startswith("// Real event shape from `_build_event()`"))
b = next(i for i, line in enumerate(src) if line.startswith("const scenario = process.argv[3]"))
block = "".join(src[a:b])

EXPORTS = [
    "ALERT_FIXTURES",
    "INFO_FIXTURES",
    "SERVER_PLUGINS",
    "PLUGINSLIST_FIXTURES",
    "ALL_UNREACHABLE_SCENARIOS",
    "ARGS_FIXTURES",
    "ALL_FIXTURES",
]
for name in EXPORTS:
    assert f"const {name} = " in block, f"{name} is not defined in the moved block"

HEADER = """// Fixtures for webui_render_probe.js: the answers its fake `fetch` gives,
// per scenario (argv[3]). Moved out of the probe unchanged (G9-6 Task 0), so
// the harness and the data it serves can be read -- and grown -- separately.

"use strict";

"""
fixtures.write_text(HEADER + block + "\nmodule.exports = {\n" + "".join(f"\t{n},\n" for n in EXPORTS) + "};\n")

require = "const {\n" + "".join(f"\t{n},\n" for n in EXPORTS) + '} = require("./webui_render_fixtures.js");\n\n'
probe_text = "".join(src[:a]) + require + "".join(src[b:])
for name in ("MEM_FIXTURE_WITH_AVAILABLE", "NETWORK_FIXTURE", "GPU_ONE_CARD", "SYSTEM_FIXTURE"):
    assert name not in probe_text, f"{name} is still referenced by the probe"
probe.write_text(probe_text)

for path in (probe, fixtures):
    text = path.read_text()
    count = text.count("test_webserver_v5.py")
    path.write_text(text.replace("test_webserver_v5.py", "test_webui_v5_render.py"))
    print(path.name, "file-name references updated:", count)
```

The only content change the move allows is that file name in comments.

- [ ] **Step 4: Prove the move changed nothing**

```bash
D=.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/task0
node --check tests/fixtures/webui_render_probe.js && node --check tests/fixtures/webui_render_fixtures.js
uv run pytest --collect-only -q tests/test_webserver_v5.py tests/test_webui_v5_render.py 2>/dev/null | grep '::' | sed 's/^[^:]*:://' | sort > $D/ids-after.txt
diff $D/ids-before.txt $D/ids-after.txt && echo "IDS IDENTICAL"
SCEN="default gpu-disabled pluginslist-unreachable mem-with-available mem-no-available network network-prominent gpu-multi-levels load memswap memswap-no-rates cpu cpu-idle-tag cpu-guest-null cpu-no-third-row cpu-ctx-switches-null gpu-one-card gpu-three-cards gpu-no-memory gpu-three-cards-mean gpu-one-card-fahrenheit gpu-first-card-colour gpu-mixed-memory gpu-zero-cards header header-hide-public ip-no-cidr ip-no-address cloud-no-name cloud-no-region cloud-disabled system-no-hostname scalar-grids all-unreachable"
B=glances/outputs/static/public/glances5.js
P=tests/fixtures/webui_render_probe.js
for s in $SCEN; do node $P $B "$s" > $D/after/$s.json 2>&1; done
node $P $B > $D/after/NOARG.json 2>&1
diff -r $D/before $D/after && echo "PROBE OUTPUT IDENTICAL"
```
Expected: `IDS IDENTICAL` and `PROBE OUTPUT IDENTICAL`. Anything else is a STOP.

- [ ] **Step 5: Lint, run, stage**

```bash
uv run ruff check tests/test_webserver_v5.py tests/test_webui_v5_render.py
uv run ruff format --check tests/test_webserver_v5.py tests/test_webui_v5_render.py
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_render.py -q
git add tests/test_webserver_v5.py tests/test_webui_v5_render.py tests/fixtures/webui_render_probe.js tests/fixtures/webui_render_fixtures.js
git status --short | grep -v '^[AM] '
```
Expected: ruff clean, eslint prints nothing, 91 tests pass (40 + 51). If `ruff format --check` flags only the blank lines between the new file's imports and `_BUNDLE_PATH`, run `uv run ruff format tests/test_webui_v5_render.py` and repeat Step 4's id comparison; any other ruff finding on moved code is a STOP (the move is byte-for-byte).

---

### Task 1: Python-exact formatting in `format.js`

**Files:**
- Modify: `glances/outputs/static/js/v5/format.js`
- Test: `tests/js/format.test.mjs`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: nothing.
- Produces (all from `format.js`):
  - `toFixedHalfEven(value: number, digits: number) -> string` — CPython's `f"{value:.{digits}f}"`. Called inside `format.js` by `formatBytes` and `formatFixed0`.
  - `formatBytes(value) -> string` — unchanged signature; now `"855B"` for 855.6 and `"1.2K"` for 1280.
  - `formatNetworkRate(value, byte: boolean) -> string` — first caller `PluginNetwork.vue` (Task 4).
  - `formatFixed0(value) -> string` — `"-"` for a non-number; first callers `PluginWifi.vue`, `PluginSensors.vue` (Task 6).

- [ ] **Step 1: Check every expected value against Python first**

```bash
uv run python - <<'EOF'
from glances.plugins.network.render_curses_v5 import _format_rate
from glances.plugins.diskio.render_curses_v5 import _format_byte_rate
from glances.outputs.curses_formatters_v5 import format_bytes, format_bytespers
cases = [(0.15, 1), (1.25, 1), (1.35, 1), (0.75, 1), (42.5, 0), (43.5, 0), (0.5, 0), (-54.5, 0), (-54.4, 0), (108.5, 0)]
print("fixed:", [f"{v:.{d}f}" for v, d in cases])
print("bytes:", [format_bytes(v) for v in (855.6, 1023.9, 1280, 1792, 16417853440)], _format_byte_rate(855.6))
print("rate:", format_bytespers(855.6))
print("net bits:", [_format_rate(v) for v in (100, 1048576, 524288)])
print("net byte:", [_format_rate(v, True) for v in (100, 1048576, 524288)])
print("fixed0:", [f"{v:.0f}" for v in (42.5, -71.2, 1200)])
EOF
```
Expected (measured while planning):
```
fixed: ['0.1', '1.2', '1.4', '0.8', '42', '44', '0', '-54', '-54', '108']
bytes: ['855B', '1023B', '1.2K', '1.8K', '15.3G'] 855B
rate: 855B/s
net bits: ['800b', '8.0Mb', '4.0Mb']
net byte: ['100', '1.0M', '512.0K']
fixed0: ['42', '-71', '1200']
```

- [ ] **Step 2: Write the failing tests**

In `tests/js/format.test.mjs`, replace the import line with:

```js
import { formatBytes, formatRate, formatPercent, formatCount, toFahrenheit, formatSeconds, toFixedHalfEven, formatNetworkRate, formatFixed0 } from "../../glances/outputs/static/js/v5/format.js";
```

Append:

```js
test("toFixedHalfEven matches CPython's float formatting, exact ties included", () => {
	// Expected strings are CPython's f"{value:.{digits}f}". JS toFixed agrees
	// everywhere except on an EXACT tie, which it rounds away from zero.
	const cases = [
		[0.15, 1, "0.1"], // stored as 0.1499999..., no tie -- a detector using value * 10 would call it one
		[1.25, 1, "1.2"],
		[1.35, 1, "1.4"], // stored above 1.35, no tie
		[0.75, 1, "0.8"],
		[42.5, 0, "42"],
		[43.5, 0, "44"],
		[0.5, 0, "0"],
		[-54.5, 0, "-54"],
		[-54.4, 0, "-54"],
		[108.5, 0, "108"], // 42.5 C in Fahrenheit: 42.5 * 1.8 + 32 is exactly 108.5
	];
	for (const [value, digits, expected] of cases) {
		assert.equal(toFixedHalfEven(value, digits), expected, `${value} at ${digits} digit(s)`);
	}
});

test("formatBytes truncates below 1K like the TUI's int()", () => {
	// _auto_unit() in curses_formatters_v5.py prints int(value) below 1024.
	assert.equal(formatBytes(855.6), "855B");
	assert.equal(formatBytes(1023.9), "1023B");
});

test("formatBytes breaks an exact one-decimal tie to even, like the TUI", () => {
	assert.equal(formatBytes(1280), "1.2K"); // 1.25K exactly
	assert.equal(formatBytes(1792), "1.8K"); // 1.75K exactly
});

test("formatRate inherits the TUI's sub-K truncation", () => {
	assert.equal(formatRate(855.6), "855B/s"); // format_bytespers(855.6)
});

test("formatNetworkRate mirrors network's _format_rate: bits, or bytes under --byte", () => {
	assert.equal(formatNetworkRate(100, false), "800b");
	assert.equal(formatNetworkRate(1048576, false), "8.0Mb");
	assert.equal(formatNetworkRate(524288, false), "4.0Mb");
	assert.equal(formatNetworkRate(100, true), "100");
	assert.equal(formatNetworkRate(1048576, true), "1.0M");
	assert.equal(formatNetworkRate(524288, true), "512.0K");
	assert.equal(formatNetworkRate(null, false), "-");
	assert.equal(formatNetworkRate(null, true), "-");
});

test("formatFixed0 is Python's :.0f, and the usual missing marker", () => {
	assert.equal(formatFixed0(42.5), "42");
	assert.equal(formatFixed0(-71.2), "-71");
	assert.equal(formatFixed0(1200), "1200");
	assert.equal(formatFixed0(null), "-");
	assert.equal(formatFixed0("ERR"), "-");
});
```

- [ ] **Step 3: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `toFixedHalfEven` is not exported.

- [ ] **Step 4: Implement**

In `glances/outputs/static/js/v5/format.js`, replace the whole `formatBytes` function:

```js
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
```

with:

```js
// Mirrors _auto_unit() (glances/outputs/curses_formatters_v5.py) and the
// renderers' copies of it: one decimal from 1K up, and below 1K the TUI's
// int(value) -- a truncation, not a rounding: 855.6 bytes is "855B".
// Dividing by 1024 is exact, so the tie rule below sees the true value.
function autoUnit(value, subKiloUnit, suffix) {
	let n = value;
	let i = 0;
	while (n >= 1024 && i < UNITS.length - 1) {
		n /= 1024;
		i += 1;
	}
	return i === 0 ? `${Math.trunc(n)}${subKiloUnit}${suffix}` : `${toFixedHalfEven(n, 1)}${UNITS[i]}${suffix}`;
}

export function formatBytes(value) {
	if (!isNumber(value)) return MISSING;
	return autoUnit(value, UNITS[0], "");
}

// Mirrors network/render_curses_v5.py::_format_rate(). Bits by default --
// bytes x 8, with a `b` on every magnitude ("800b", "8.0Mb") -- and the
// plain byte count with no unit letter at all under --byte ("100", "1.0M").
// No "/s": the column header carries the per-second meaning, as in the TUI.
export function formatNetworkRate(value, byte) {
	if (!isNumber(value)) return MISSING;
	return byte ? autoUnit(value, "", "") : autoUnit(value * 8, "", "b");
}

// Python's float formatting, which JS does not have. f"{x:.1f}" and
// f"{x:.0f}" round the exact binary value and break an EXACT tie to the even
// digit; toFixed() rounds the same exact value but breaks a tie away from
// zero. The two differ on exact ties only: 1.25 is "1.2" in Python, "1.3" in
// JS; 42.5 is "42" and "43".
//
// A value is a tie at `digits` exactly when value * 2 ** (digits + 1) is an
// odd integer. That product is exact (a power-of-two multiply), unlike
// value * 10 ** digits: 0.15 * 10 === 1.5 in floating point, although 0.15 is
// stored below 0.15 and is no tie at all.
export function toFixedHalfEven(value, digits) {
	const scaled = value * 2 ** (digits + 1);
	if (!Number.isInteger(scaled) || Math.abs(scaled) % 2 !== 1) return value.toFixed(digits);
	// A tie: |value| * 10 ** digits is exactly k + 0.5 (a small multiple of
	// one half is representable), so floor() yields k exactly.
	let k = Math.floor(Math.abs(value) * 10 ** digits);
	if (k % 2 === 1) k += 1;
	return `${value < 0 ? "-" : ""}${(k / 10 ** digits).toFixed(digits)}`;
}

// f"{value:.0f}" -- the sensors and wifi values. Half-even on an exact tie,
// like every Python float format.
export function formatFixed0(value) {
	if (!isNumber(value)) return MISSING;
	return toFixedHalfEven(value, 0);
}
```

`toFixedHalfEven` is a function declaration, so `autoUnit` may call it although it is defined further down the module.

- [ ] **Step 5: Run the unit tests**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: PASS, the existing `formatBytes`/`formatRate` tests included.

- [ ] **Step 6: Rebuild, run the render tests, lint, stage**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check from Global Constraints -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
git add glances/outputs/static/js/v5/format.js tests/js/format.test.mjs glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```
Expected: every render test still passes — no existing fixture lands on a sub-K float or an exact tie. If one fails, report which value moved; do not edit the test.

---

### Task 2: Row helpers and the shared table/name CSS

**Files:**
- Create: `glances/outputs/static/js/v5/rows.js`, `tests/js/rows.test.mjs`
- Modify: `glances/outputs/static/css/v5.css`, `tests/test_webui_v5_tokens.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `displayName(item: object, keyField: string) -> string` from `rows.js` — first callers `PluginNetwork.vue` (Task 4), `PluginDiskio.vue`, `PluginFs.vue` (Task 5).
  - `byText(field: string) -> (a, b) => -1 | 0 | 1` from `rows.js` — first callers `PluginDiskio.vue`, `PluginFs.vue` (Task 5), `PluginWifi.vue` (Task 6).
  - Global CSS classes, first used in Task 4: `.gl-table` (collection `<table>`), `.gl-name` (name `<span>`, capped at `var(--gl-name-width)`), `.gl-truncate-start` (ellipsis at the start; its text must sit in a `<bdi>`).

- [ ] **Step 1: Write the failing unit tests**

Create `tests/js/rows.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { displayName, byText } from "../../glances/outputs/static/js/v5/rows.js";

test("displayName shows the configured alias", () => {
	assert.equal(displayName({ interface_name: "lo", alias: "Loopback" }, "interface_name"), "Loopback");
});

test("displayName falls back to the raw key when there is no usable alias", () => {
	assert.equal(displayName({ disk_name: "sda" }, "disk_name"), "sda");
	assert.equal(displayName({ disk_name: "sda", alias: "" }, "disk_name"), "sda");
	assert.equal(displayName({ disk_name: "sda", alias: null }, "disk_name"), "sda");
});

test("displayName never renders undefined", () => {
	assert.equal(displayName({}, "disk_name"), "");
	assert.equal(displayName({ disk_name: null }, "disk_name"), "");
});

test("byText sorts like Python's sorted(key=str): code units, not locale", () => {
	// Python: sorted(["a", "B"]) == ["B", "a"]; localeCompare would give ["a", "B"].
	const rows = [{ ssid: "a" }, { ssid: "B" }, { ssid: "wlp0s20f3" }, { ssid: "wlan0" }];
	assert.deepEqual(rows.slice().sort(byText("ssid")).map((r) => r.ssid), ["B", "a", "wlan0", "wlp0s20f3"]);
});

test("byText keeps equal keys in their original order, like sorted()", () => {
	const rows = [
		{ mnt_point: "/", n: 1 },
		{ mnt_point: "/", n: 2 },
	];
	assert.deepEqual(rows.slice().sort(byText("mnt_point")).map((r) => r.n), [1, 2]);
});
```

Check the ordering claim against Python: `uv run python -c 'print(sorted(["a", "B", "wlp0s20f3", "wlan0"]))'` → `['B', 'a', 'wlan0', 'wlp0s20f3']`.

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `rows.js` does not exist.

- [ ] **Step 3: Implement `rows.js`**

Create `glances/outputs/static/js/v5/rows.js`:

```js
// Glances v5 WebUI -- row helpers shared by the collection components.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it; logic in
// a .vue file cannot be unit-tested. Only what at least two components use
// lives here -- a skip rule used by one component stays in that component.

// The name a row displays: the configured alias when there is one, otherwise
// the raw primary key. Display only: `_levels` and the row key stay on the
// RAW key (base_v5.py `_apply_alias()`), exactly as in the TUI renderers.
export function displayName(item, keyField) {
	const alias = item && item.alias;
	if (typeof alias === "string" && alias !== "") return alias;
	const key = item ? item[keyField] : undefined;
	return key === undefined || key === null ? "" : String(key);
}

// Comparator for the TUI renderers' `sorted(items, key=lambda it:
// str(it.get(field, "")))`: plain code-unit order ("B" before "a"), never
// localeCompare(), whose collation would order rows differently from the
// terminal. Array.prototype.sort is stable, like sorted().
export function byText(field) {
	return (a, b) => {
		const x = String(a[field] ?? "");
		const y = String(b[field] ?? "");
		return x < y ? -1 : x > y ? 1 : 0;
	};
}
```

Run `uv run pytest tests/test_webui_v5_js.py -q` → PASS.

- [ ] **Step 4: Write the failing CSS tests**

Append to `tests/test_webui_v5_tokens.py`:

```python
def test_a_name_cell_is_capped_and_can_keep_its_tail():
    """G9-6 D3: a left-sidebar name is capped at the TUI's name width, which
    each component sets as --gl-name-width, on a BLOCK span (max-width on a
    table cell is not reliably honoured). `.gl-truncate-start` puts the
    ellipsis at the start, keeping the tail like the TUI's "_" + name[-17:].
    CSS is not observable through the render probe, so this reads the file.
    """
    css = _strip_comments(_TOKENS.read_text())
    name = _rule_body(css, ".gl-name")
    assert re.search(r"\bdisplay:\s*block\s*;", name), f".gl-name is a block: {name!r}"
    assert re.search(r"\bmax-width:\s*var\(--gl-name-width\)\s*;", name), f".gl-name is capped: {name!r}"
    start = _rule_body(css, ".gl-truncate-start")
    assert re.search(r"\bdirection:\s*rtl\s*;", start), f"the ellipsis moves to the start: {start!r}"
    assert re.search(r"\btext-align:\s*left\s*;", start), f"a short name stays left-aligned: {start!r}"


def test_a_collection_table_left_aligns_only_its_non_numeric_cells():
    """The browser centres a <th>; the TUI left-aligns names and titles and
    right-aligns values. `:not(.gl-num)` is load-bearing: `.gl-table th`
    outranks the global `.gl-num`, so a plain rule would stop numeric columns
    right-aligning.
    """
    css = _strip_comments(_TOKENS.read_text())
    assert re.search(r"\.gl-table\s+th:not\(\.gl-num\)\s*,", css), "the <th> rule excludes numeric columns"
    body = _rule_body(css, ".gl-table td:not(.gl-num)")
    assert re.search(r"\btext-align:\s*left\s*;", body), f"non-numeric cells left-align: {body!r}"
```

Run `uv run pytest tests/test_webui_v5_tokens.py -q` → the two new tests FAIL (`no .gl-name rule found`).

- [ ] **Step 5: Add the CSS**

In `glances/outputs/static/css/v5.css`, replace the comment above `.gl-truncate`:

```css
/* Ellipsis for a string too long for its line (system's OS name, ip's
 * geolocation). Pair it with a `title` attribute carrying the full text.
 * `min-width: 0` is load-bearing: a flex item otherwise refuses to shrink
 * below its content, and the ellipsis never triggers. A browser truncates
 * with the layout; never copy a terminal character count instead. */
```

with:

```css
/* Ellipsis for a string too long for its line (system's OS name, ip's
 * geolocation). Pair it with a `title` attribute carrying the full text.
 * `min-width: 0` is load-bearing: a flex item otherwise refuses to shrink
 * below its content, and the ellipsis never triggers. A browser truncates
 * with the layout; never copy a terminal character count instead -- except
 * the left-sidebar name cells, by the maintainer's choice (.gl-name, G9-6 D3). */
```

Then append at the end of the file:

```css

/* Left-sidebar name (G9-6 D3): capped at the TUI's name width, which each
 * component sets as --gl-name-width (18ch, 19ch or 26ch). Put it on a block
 * <span> inside the cell, never on the <td>: max-width on a table cell in
 * automatic table layout is not reliably honoured. Pair with .gl-truncate
 * and a `title` carrying the full name. */
.gl-name {
  display: block;
  max-width: var(--gl-name-width);
}

/* Ellipsis at the START, keeping the tail -- the TUI's "_" + name[-17:] for
 * interfaces, disks and mount points. The text MUST sit in a <bdi>: without
 * it the bidi algorithm moves a leading "/" to the end, and "/boot/efi"
 * renders "boot/efi/" (checked in headless Chrome). `text-align: left` keeps
 * a short name aligned with its neighbours. */
.gl-truncate-start {
  direction: rtl;
  text-align: left;
}

/* Collection table. Global, like .gl-stat-grid: five components share it.
 * `:not(.gl-num)` is load-bearing: `.gl-table th` (0,1,1) outranks the global
 * `.gl-num` (0,1,0), so a plain `text-align: left` would silently stop the
 * numeric columns right-aligning. It also overrides the browser's centred
 * <th>. */
.gl-table {
  border-collapse: collapse;
}
.gl-table th,
.gl-table td {
  padding: 0 var(--gl-gap) 0 0;
}
.gl-table th:not(.gl-num),
.gl-table td:not(.gl-num) {
  text-align: left;
}
```

Run `uv run pytest tests/test_webui_v5_tokens.py -q` → PASS.

- [ ] **Step 6: Check the real CSS in headless Chrome**

Create `.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/task2/ellipsis.html`:

```html
<!doctype html>
<meta charset="utf-8">
<link rel="stylesheet" href="../../../../glances/outputs/static/css/v5.css">
<body style="padding: 8px">
<p>leading, 18ch</p>
<table class="gl-table" style="--gl-name-width: 18ch">
<tr><th class="gl-header">FILE SYS</th><th class="gl-header gl-num">Used</th><th class="gl-header gl-num">Total</th></tr>
<tr><td><span class="gl-name gl-truncate gl-truncate-start" title="/var/snap/firefox/common/host-hunspell"><bdi>/var/snap/firefox/common/host-hunspell</bdi></span></td><td class="gl-num"><span>1.2K</span></td><td class="gl-num"><span>1.2K</span></td></tr>
<tr><td><span class="gl-name gl-truncate gl-truncate-start" title="/"><bdi>/</bdi></span></td><td class="gl-num"><span>125.0G</span></td><td class="gl-num"><span>500.0G</span></td></tr>
<tr><td><span class="gl-name gl-truncate gl-truncate-start" title="/boot/efi"><bdi>/boot/efi</bdi></span></td><td class="gl-num"><span>6.2M</span></td><td class="gl-num"><span>1.0G</span></td></tr>
</table>
<p>trailing, 19ch</p>
<table class="gl-table" style="--gl-name-width: 19ch">
<tr><th class="gl-header">SENSORS</th><th class="gl-header gl-num"></th></tr>
<tr><td><span class="gl-name gl-truncate" title="Composite temperature of the NVMe controller">Composite temperature of the NVMe controller</span></td><td class="gl-num"><span>42C</span></td></tr>
<tr><td><span class="gl-name gl-truncate" title="Core 0">Core 0</span></td><td class="gl-num"><span>45C</span></td></tr>
</table>
</body>
```

`css/v5.css` already styles `body` (dark theme tokens, monospace font) — which is the point: the spike ran with a proportional font, this check runs with the real one.

```bash
T=$PWD/.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/task2
timeout 60 google-chrome --headless=new --disable-gpu --no-first-run --hide-scrollbars \
  --screenshot=$T/ellipsis.png --window-size=520,420 file://$T/ellipsis.html
```

Open `ellipsis.png` (the Read tool displays images) and check all four: the long mount point reads `…` + its tail; `/` and `/boot/efi` start with their slash and are left-aligned; `FILE SYS` and `SENSORS` are left-aligned, `Used`/`Total` right-aligned; the long sensor label ends with `…`. The same markup passed in a spike while planning. **If any check fails, STOP and ask the maintainer** — do not change the approach.

- [ ] **Step 7: Rebuild, lint, stage**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check -- both IDENTICAL
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py tests/test_webui_v5_render.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
git add glances/outputs/static/js/v5/rows.js tests/js/rows.test.mjs glances/outputs/static/css/v5.css tests/test_webui_v5_tokens.py glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```

---

### Task 3: Schema labels for `diskio`, `fs`, `wifi` (TUI side)

**Files:**
- Modify: `glances/plugins/diskio/model_v5.py`, `glances/plugins/fs/model_v5.py`, `glances/plugins/wifi/model_v5.py`
- Modify: `glances/plugins/diskio/render_curses_v5.py`, `glances/plugins/fs/render_curses_v5.py`, `glances/plugins/wifi/render_curses_v5.py`
- Modify (schema source only): `tests/test_plugin_diskio_render_curses_v5.py`, `tests/test_plugin_fs_render_curses_v5.py`, `tests/test_plugin_wifi_render_curses_v5.py`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `/api/5/all/info` carries `diskio.read_bytes.short_name == "R/s"`, `diskio.write_bytes.short_name == "W/s"`, `fs.used.short_name == "Used"`, `fs.free.short_name == "Free"`, `fs.size.short_name == "Total"`, `wifi.quality_level.short_name == "dBm"` — the WebUI headers of Tasks 5 and 6 resolve from these.

- [ ] **Step 1: Switch the three TUI test files to the real schema — assertions untouched**

Production passes `PluginModel.fields_description` (`glances/outputs/curses_renderer_v5.py:1459`); the G9-4 precedent is `tests/test_plugin_gpu_render_curses_v5.py:16-24`.

In `tests/test_plugin_diskio_render_curses_v5.py`, add **before** `from glances.plugins.diskio.render_curses_v5 import render` (ruff's import order puts `model_v5` before `render_curses_v5`):

```python
from glances.plugins.diskio.model_v5 import PluginModel
```

and replace the whole `diskio_fields` fixture body (the hand-written dict, from `return {` to its closing `}`) so the fixture reads:

```python
@pytest.fixture
def diskio_fields():
    """The REAL schema, as production passes it (curses_renderer_v5.py:1459).

    The column labels come from it (field_label), so a hand-written subset
    without `short_name` would test a header no user ever sees.
    """
    return PluginModel.fields_description
```

In `tests/test_plugin_fs_render_curses_v5.py`, the same with `from glances.plugins.fs.model_v5 import PluginModel` and the `fs_fields` fixture.

In `tests/test_plugin_wifi_render_curses_v5.py`, add `from glances.plugins.wifi.model_v5 import PluginModel` **before** the renderer import block, then after the imports:

```python
# The REAL schema, as production passes it (curses_renderer_v5.py:1459): the
# `dBm` column label comes from it. These tests used to call render() with no
# schema at all.
FIELDS = PluginModel.fields_description
```

and pass it to every `render(...)` call with this script (`$D/wifi_fields.py`, run with `uv run python`):

```python
import pathlib
import re

path = pathlib.Path("tests/test_plugin_wifi_render_curses_v5.py")
text = path.read_text()
new, count = re.subn(r"render\((_payload\(.*\))\)$", r"render(\1, FIELDS)", text, flags=re.M)
assert count == 11, f"expected 11 render() calls, rewrote {count}"
path.write_text(new)
```

Then:

```bash
uv run pytest tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py -q
git diff -U0 -- tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py | grep -E '^[-+]\s*assert' || echo "NO ASSERT LINE CHANGED"
```
Expected: all pass (renderers still use literals), and `NO ASSERT LINE CHANGED`.

- [ ] **Step 2: Write the failing schema pins**

Append to `tests/test_webui_v5_render.py`, right after `test_network_schema_declares_the_tui_short_names`:

```python
@pytest.mark.parametrize(
    ("plugin", "expected"),
    [
        pytest.param("diskio", {"read_bytes": "R/s", "write_bytes": "W/s"}, id="diskio"),
        pytest.param("fs", {"used": "Used", "free": "Free", "size": "Total"}, id="fs"),
        pytest.param("wifi", {"quality_level": "dBm"}, id="wifi"),
    ],
)
def test_left_sidebar_schemas_declare_the_tui_short_names(plugin, expected):
    """Pin the schema the WebUI's column headers AND the TUI's resolve from
    (G9-6 D5). The probe's /all/info stub is a hand copy, so only this test
    notices a `short_name` dropped from the real plugin.
    """
    import importlib

    fields = importlib.import_module(f"glances.plugins.{plugin}.model_v5").PluginModel.fields_description
    assert {field: fields[field].get("short_name") for field in expected} == expected
```

Run `uv run pytest tests/test_webui_v5_render.py -q -k left_sidebar_schemas` → 3 FAIL.

- [ ] **Step 3: Add the `short_name`s**

`glances/plugins/diskio/model_v5.py` — in `read_bytes`, after `"description": "Bytes read per second (rate of psutil read_bytes counter).",` insert:

```python
            # Column label, TUI header and WebUI alike (field_label, prefer_short).
            "short_name": "R/s",
```

and in `write_bytes`, after its `"description"` line:

```python
            "short_name": "W/s",
```

`glances/plugins/fs/model_v5.py` — `size`, `used`, `free` become:

```python
        "size": {
            "description": "Total size of the filesystem in bytes.",
            # Column labels, TUI header and WebUI alike (field_label, prefer_short).
            "short_name": "Total",
            "unit": "bytes",
        },
        "used": {
            "description": "Used size in bytes.",
            "short_name": "Used",
            "unit": "bytes",
        },
        "free": {
            "description": "Free size in bytes.",
            "short_name": "Free",
            "unit": "bytes",
        },
```

`glances/plugins/wifi/model_v5.py` — `quality_level` becomes:

```python
        "quality_level": {
            "description": "Signal strength level.",
            # Column label, TUI header and WebUI alike (field_label, prefer_short).
            "short_name": "dBm",
            "unit": "dBm",
            "watched": True,
            "watch_direction": "low",
            "prominent": False,
        },
```

Run `uv run pytest tests/test_webui_v5_render.py -q -k left_sidebar_schemas` → PASS.

- [ ] **Step 4: Renderers read the labels from the schema**

`glances/plugins/diskio/render_curses_v5.py` — change the import to:

```python
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label
```

and replace:

```python
    header_row = Row(
        cells=[
            Cell(text="DISK I/O".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="R/s".rjust(_RATE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="W/s".rjust(_RATE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )
```

with:

```python
    # The first header cell is the TUI block title, not a field label -- it
    # stays a literal. The rate columns read their labels from the schema
    # (single source of truth, shared with the WebUI), as network's do.
    header_row = Row(
        cells=[
            Cell(text="DISK I/O".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            *(
                Cell(
                    text=field_label(fields_desc.get(key, {}), key, prefer_short=True).rjust(_RATE_COL_WIDTH),
                    color=ColorRole.HEADER,
                    bold=True,
                )
                for key in ("read_bytes", "write_bytes")
            ),
        ]
    )
```

`glances/plugins/fs/render_curses_v5.py` — change the import to:

```python
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label
```

replace:

```python
    value_field = "free" if free_space else "used"
    value_label = "Free" if free_space else "Used"
```

with:

```python
    value_field = "free" if free_space else "used"
    # The block title stays a literal; the column labels come from the schema
    # (single source of truth, shared with the WebUI), as network's do.
    value_label = field_label(fields_desc.get(value_field, {}), value_field, prefer_short=True)
    total_label = field_label(fields_desc.get("size", {}), "size", prefer_short=True)
```

and replace `Cell(text="Total".rjust(_TOTAL_COL_WIDTH), color=ColorRole.HEADER, bold=True),` with `Cell(text=total_label.rjust(_TOTAL_COL_WIDTH), color=ColorRole.HEADER, bold=True),`.

`glances/plugins/wifi/render_curses_v5.py` — change the import to:

```python
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label
```

and replace:

```python
    header = Row(
        cells=[
            Cell(text="WIFI".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="dBm".rjust(_VALUE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )
```

with:

```python
    # The block title stays a literal; the signal column's label comes from
    # the schema (single source of truth, shared with the WebUI).
    fields = fields_desc or {}
    header = Row(
        cells=[
            Cell(text="WIFI".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(
                text=field_label(fields.get("quality_level", {}), "quality_level", prefer_short=True).rjust(
                    _VALUE_COL_WIDTH
                ),
                color=ColorRole.HEADER,
                bold=True,
            ),
        ]
    )
```

- [ ] **Step 5: Verify the TUI is unchanged**

```bash
uv run pytest tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py tests/test_curses_renderer_v5.py -q
uv run pytest tests/ -q -k "diskio or fs or wifi"
git diff -U0 -- tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py | grep -E '^[-+]\s*assert' || echo "NO ASSERT LINE CHANGED"
uv run ruff check glances/plugins/diskio glances/plugins/fs glances/plugins/wifi tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py tests/test_webui_v5_render.py
uv run ruff format --check glances/plugins/diskio glances/plugins/fs glances/plugins/wifi tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py tests/test_webui_v5_render.py
```
Expected: all green; `NO ASSERT LINE CHANGED`. As a negative check, temporarily delete `"short_name": "dBm",` and confirm `test_header_and_one_row` fails on `"dBm" in flat`, then restore it — this proves the TUI test now depends on the schema. Report that you did it.

- [ ] **Step 6: Stage**

```bash
git add glances/plugins/diskio/model_v5.py glances/plugins/fs/model_v5.py glances/plugins/wifi/model_v5.py \
  glances/plugins/diskio/render_curses_v5.py glances/plugins/fs/render_curses_v5.py glances/plugins/wifi/render_curses_v5.py \
  tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py \
  tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] '
```

---

### Task 4: Retrofit `network` (D2 + D6) and extend the probe

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginNetwork.vue` (whole file)
- Modify: `glances/plugins/network/model_v5.py` (`interface_name`)
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `formatNetworkRate` (Task 1); `displayName` (Task 2); `.gl-table`, `.gl-name`, `.gl-truncate`, `.gl-truncate-start` (Task 2).
- Produces:
  - **The collection component shape Tasks 5 and 6 repeat:** root `<article class="gl-plugin" aria-label="TITLE">`; `<h2>` only under `v-if="error || !payload"`; `<table v-else class="gl-table">` whose first `<th class="gl-header">` is the title and whose value `<th>`s carry `gl-header gl-num`; a name cell `<td><span class="gl-name gl-truncate[ gl-truncate-start]" :title="name">` (`<bdi>` inside for `gl-truncate-start`); value cells `<td class="gl-num"><span :class="...">`; scoped `.gl-plugin { --gl-name-width: Nch; }`.
  - Probe output `pluginNameCells: { [plugin]: [{ text, className, title, hasBdi }] }`, and a `text` key on every `pluginTableCells` entry.
  - Test helper `_table_rows(payload, name, width) -> list[list[str]]` in `tests/test_webui_v5_render.py`.
  - Fixture scenarios `network-rows`, `network-byte`, `network-empty`.

- [ ] **Step 1: Extend the probe**

In `tests/fixtures/webui_render_probe.js`, `collect()`'s `result` object, add after the `pluginTableCells` comment block and key:

```js
		// The name <span class~="gl-name"> of each row of a collection plugin,
		// keyed by data-plugin: its text, classes, `title` and whether the text
		// sits in a <bdi>. Lets a test observe the displayed name (alias or raw
		// key), which truncation side it uses, and that the full name is on
		// hover -- none of which textContent or the <td> classes show.
		pluginNameCells: {},
```

Replace the `pluginTableCells` collection:

```js
				const tds = findAllByTag(article, "TD");
				if (tds.length) {
					result.pluginTableCells[name] = tds.map((td) => {
						const span = findDescendantTag(td, "SPAN");
						return { cell: td.className, value: span ? span.className : null };
					});
				}
```

with:

```js
				const tds = findAllByTag(article, "TD");
				if (tds.length) {
					result.pluginTableCells[name] = tds.map((td) => {
						const span = findDescendantTag(td, "SPAN");
						return { cell: td.className, value: span ? span.className : null, text: td.textContent.trim() };
					});
				}
				const nameCells = findAllByTag(article, "SPAN").filter((span) => span.classList.contains("gl-name"));
				if (nameCells.length) {
					result.pluginNameCells[name] = nameCells.map((span) => ({
						text: span.textContent,
						className: span.className,
						title: span.getAttribute("title"),
						hasBdi: !!findDescendantTag(span, "BDI"),
					}));
				}
```

- [ ] **Step 2: Add the fixtures**

In `tests/fixtures/webui_render_fixtures.js`:

(a) In `INFO_FIXTURES.network`, replace `interface_name: { short_name: "interface" },` with `interface_name: {},` and replace the two-line comment above `network: {` with:

```js
	// short_names copied from glances/plugins/network/model_v5.py. The name
	// column declares none: its header cell is the block title (G9-6 D6).
```

(b) After the `NETWORK_FIXTURE` constant, add:

```js
// The network rows the TUI renderer skips, next to two it shows
// (network/render_curses_v5.py:129-142): a down interface, one hide_zero still
// hides, one with no rate yet. `lo` comes FIRST with an alias: the TUI keeps
// payload order, so "Loopback" must render before "eth0" -- a component
// sorting by raw key or by display name would put "eth0" first.
const NETWORK_ROWS = {
	_key: "interface_name",
	data: [
		{ interface_name: "lo", alias: "Loopback", bytes_recv: 100, bytes_sent: 100, is_up: true, hidden: false },
		{ interface_name: "virbr0", bytes_recv: 0, bytes_sent: 0, is_up: false, hidden: false },
		{ interface_name: "docker0", bytes_recv: 0, bytes_sent: 0, is_up: true, hidden: true },
		{ interface_name: "wlan0", bytes_recv: null, bytes_sent: null, is_up: true, hidden: false },
		{ interface_name: "eth0", bytes_recv: 1048576, bytes_sent: 524288, is_up: true, hidden: false },
	],
	_levels: {},
};
```

(c) In `ARGS_FIXTURES`, add `"network-byte": { byte: true },`.

(d) In `ALL_FIXTURES`, after the `"network-prominent"` entry, add:

```js
	"network-rows": { network: NETWORK_ROWS },
	// Same rows as `network-rows`; only ARGS_FIXTURES differs (--byte).
	"network-byte": { network: NETWORK_ROWS },
	"network-empty": { network: { _key: "interface_name", data: [], _levels: {} } },
```

- [ ] **Step 3: Write the failing tests**

In `tests/test_webui_v5_render.py`:

(a) `test_network_column_headers_are_the_tui_strings` — replace its assertion with:

```python
    assert headers == ["NETWORK", "Rx/s", "Tx/s"], f"expected the TUI's network header row, got {headers!r}"
```

and in its docstring replace the paragraph starting "`PluginNetwork.vue` resolves every header" through "move AWAY from TUI parity." with:

```
    The TUI header row is the block title then the two rate labels
    (`glances/plugins/network/render_curses_v5.py`: `NETWORK` / `Rx/s` /
    `Tx/s`). Since G9-6 D6 the WebUI's first <th> is that title; the rate
    headers resolve through `labelFor()` from the schema, and degrade to
    `bytes_recv` / `bytes_sent` without a `short_name`.
```

(b) `test_network_schema_declares_the_tui_short_names` — replace `assert fields["interface_name"]["short_name"] == "interface"` with:

```python
    # G9-6 D6: the name column's header cell is the block title, so the key
    # field declares no label of its own.
    assert "short_name" not in fields["interface_name"]
```

(c) `test_network_rate_columns_are_marked_numeric` — in the docstring replace "the interface one must not" with "the title column must not", and replace the assertion message `f"the interface column must not be numeric, got {classes[0]!r}"` with `f"the title column must not be numeric, got {classes[0]!r}"`.

(d) In `test_a_table_value_carries_its_tier_on_the_text_not_the_cell`'s parameters, replace the comment `# Columns: interface, Rx/s, Tx/s -> cell 1 is eth0's Rx.` with `# Columns: name, Rx/s, Tx/s -> cell 1 is eth0's Rx.`

(e) After `test_a_table_value_carries_its_tier_on_the_text_not_the_cell`, add:

```python
# ------------------------------------------- left-sidebar collections (G9-6)


def _table_rows(payload, name, width):
    """The rendered <td> texts of a collection plugin, grouped into rows."""
    cells = [cell["text"] for cell in payload["pluginTableCells"].get(name, [])]
    return [cells[i : i + width] for i in range(0, len(cells), width)]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_renders_only_the_rows_the_tui_renders_in_payload_order():
    """network/render_curses_v5.py:129-142 skips a down interface, one
    hide_zero still hides, and one without a rate yet; it keeps payload order
    and shows the alias. Rates are bits, as `_format_rate()` prints them.
    """
    payload = _run_render_probe("network-rows")
    assert _table_rows(payload, "network", 3) == [["Loopback", "800b", "800b"], ["eth0", "8.0Mb", "4.0Mb"]]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_network_shows_bytes_under_the_byte_flag():
    """`--byte` reaches the WebUI through /api/5/args (`serverArgs.byte`)."""
    payload = _run_render_probe("network-byte")
    assert _table_rows(payload, "network", 3) == [["Loopback", "100", "100"], ["eth0", "1.0M", "512.0K"]]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_network_keeps_its_header_row_and_shows_no_line():
    """The TUI paints the header row of an empty block; so does the WebUI now,
    instead of G9-3's "no interface" text.
    """
    payload = _run_render_probe("network-empty")
    assert payload["pluginColumnHeaders"].get("network") == ["NETWORK", "Rx/s", "Tx/s"]
    assert "network" not in payload["pluginTableCells"], "no row may render"
    assert "no interface" not in payload["pluginText"].get("network", "")


@pytest.mark.parametrize(
    ("scenario", "name", "title"),
    [
        pytest.param("network-rows", "network", "NETWORK", id="network"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_loaded_collection_puts_its_title_in_the_header_row(scenario, name, title):
    """G9-6 D6: once loaded, the title is the first <th> and there is no <h2>;
    the <article> keeps naming itself through aria-label.
    """
    payload = _run_render_probe(scenario)
    index = payload["pluginNames"].index(name)
    assert payload["pluginHeaders"][index] is None, f"{name}: no <h2> once loaded"
    assert payload["pluginColumnHeaders"][name][0] == title
    assert "aria-label" in payload["pluginAttrs"][name]


@pytest.mark.parametrize(
    ("name", "title"),
    [
        pytest.param("network", "NETWORK", id="network"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_collection_keeps_its_title_heading_while_loading(name, title):
    """Before its first payload a collection still says what it is."""
    payload = _run_render_probe("default")
    index = payload["pluginNames"].index(name)
    assert payload["pluginHeaders"][index] == title
    assert "loading" in payload["pluginText"][name]


@pytest.mark.parametrize(
    ("scenario", "name"),
    [
        pytest.param("network-rows", "network", id="network"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_path_like_name_keeps_its_tail_and_its_full_text_on_hover(scenario, name):
    """G9-6 D3: interfaces, disks and mount points lose their START, like the
    TUI's "_" + name[-17:]. That needs `.gl-truncate-start` AND a <bdi>, which
    stops the bidi algorithm from moving a leading "/" to the end.
    """
    cells = _run_render_probe(scenario)["pluginNameCells"].get(name)
    assert cells, f"{name}: vacuous, no name cell rendered"
    for cell in cells:
        classes = cell["className"].split()
        assert {"gl-name", "gl-truncate", "gl-truncate-start"} <= set(classes), cell
        assert cell["hasBdi"], f"{name}: the name must sit in a <bdi>: {cell!r}"
        assert cell["title"] == cell["text"], f"{name}: the full name is on hover: {cell!r}"
```

Run the network tests before implementing:

```bash
(cd glances/outputs/static && npm run build)
uv run pytest tests/test_webui_v5_render.py -q -k "network or collection or path_like"
```
Expected: FAIL — headers still `interface`, no `pluginNameCells`, "no interface" rendered, rates in bytes.

- [ ] **Step 4: Remove the `interface` label from the network schema**

In `glances/plugins/network/model_v5.py`, replace the comment block and the `interface_name` entry:

```python
        # `short_name` is the compact UI label (short_name → label → field
        # name, cf. `field_label()` in curses_renderer_v5.py). The strings
        # feed the TUI block rendered by `render_curses_v5.render()` and the
        # WebUI alike: both resolve their column headers from this schema.
        # The interface column is `interface` rather than the TUI's
        # `NETWORK`: in the TUI that first header cell doubles as the block
        # title (a literal in the renderer), which the WebUI already renders
        # separately as <h2>NETWORK.
        "interface_name": {
            "description": "Network interface name.",
            "short_name": "interface",
            "unit": "string",
            "primary_key": True,
        },
```

with:

```python
        # `short_name` is the compact UI label (short_name → label → field
        # name, cf. `field_label()` in curses_renderer_v5.py). The strings
        # feed the TUI block rendered by `render_curses_v5.render()` and the
        # WebUI alike: both resolve their column headers from this schema.
        # The interface column declares none: its header cell is the block
        # title, a literal in both outputs (G9-6 D6).
        "interface_name": {
            "description": "Network interface name.",
            "unit": "string",
            "primary_key": True,
        },
```

- [ ] **Step 5: Rewrite `PluginNetwork.vue`**

Replace the whole file with:

```vue
<template>
	<article class="gl-plugin" aria-label="NETWORK">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">NETWORK</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- G9-6 D6: the TUI's header row -- the block title, then the rate
				labels from the schema. An empty collection keeps this row and
				shows no line, as the TUI paints its header. -->
				<tr>
					<th class="gl-header">NETWORK</th>
					<th v-for="field in RATE_FIELDS" :key="field" class="gl-header gl-num">
						{{ labelFor(labels, field) }}
					</th>
				</tr>
			</thead>
			<tbody>
				<!-- The row key hardcodes `interface_name` on purpose: deriving it
				from `payload._key` yields `item[undefined]` against a server that
				does not publish `_key`, i.e. one duplicate key per row. -->
				<tr v-for="item in rows" :key="item.interface_name">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="nameOf(item)"><bdi>{{ nameOf(item) }}</bdi></span>
					</td>
					<!-- The tier goes on the <span>, not the <td>: a prominent badge's
					background would otherwise fill the whole cell. -->
					<td v-for="field in RATE_FIELDS" :key="field" class="gl-num">
						<span :class="cellClassFor(payload, item, field)">{{
							formatNetworkRate(item[field], !!serverArgs.byte)
						}}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatNetworkRate } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { displayName } from "./rows.js";

const RATE_FIELDS = ["bytes_recv", "bytes_sent"];

export default {
	name: "PluginNetwork",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// `byte` (--byte) switches the rates from bits to bytes, as in the TUI.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		RATE_FIELDS: () => RATE_FIELDS,
		// Mirrors network/render_curses_v5.py:129-142: skip a down interface
		// (v4 #765), one hide_zero still hides, and one with no rate yet (cycle
		// 1). Payload order -- the TUI does not sort this block.
		rows() {
			return (this.payload?.data || []).filter(
				(item) =>
					item.is_up !== false && item.hidden !== true && item.bytes_recv != null && item.bytes_sent != null,
			);
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatNetworkRate,
		nameOf(item) {
			return displayName(item, "interface_name");
		},
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (network/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 18ch;
}
</style>
```

- [ ] **Step 6: Rebuild and run**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
uv run pytest tests/ -q -k network
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run ruff check glances/plugins/network tests/test_webui_v5_render.py
uv run ruff format --check glances/plugins/network tests/test_webui_v5_render.py
```
Expected: all green, including `test_server_args_does_not_leak_into_the_dom_as_an_attribute` (still 11 plugins) and the `network` case of `test_a_table_value_carries_its_tier_on_the_text_not_the_cell`.

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/PluginNetwork.vue glances/plugins/network/model_v5.py \
  tests/fixtures/webui_render_probe.js tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py \
  glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```

---

### Task 5: `diskio` and `fs`

**Files:**
- Create: `glances/outputs/static/js/v5/PluginDiskio.vue`, `glances/outputs/static/js/v5/PluginFs.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `formatBytes` (Task 1); `displayName`, `byText`, the CSS classes (Task 2); the `diskio`/`fs` `short_name`s (Task 3); the collection shape, `pluginNameCells`, `_table_rows` and the three parametrized G9-6 tests (Task 4).
- Produces: registry entries `diskio` and `fs` after `network`; fixture scenarios `diskio`, `fs`, `fs-free-space`.

- [ ] **Step 1: Check the expected values against the TUI**

```bash
uv run python - <<'EOF'
from glances.plugins.diskio.render_curses_v5 import render as diskio
from glances.plugins.diskio.model_v5 import PluginModel as D
from glances.plugins.fs.render_curses_v5 import render as fs
from glances.plugins.fs.model_v5 import PluginModel as F
DISKIO = {"data": [
    {"disk_name": "sdb", "alias": "Backup", "read_bytes": 1536, "write_bytes": 0, "hidden": False},
    {"disk_name": "loop0", "read_bytes": 0, "write_bytes": 0, "hidden": True},
    {"disk_name": "sda", "read_bytes": None, "write_bytes": None, "hidden": False},
    {"disk_name": "nvme0n1", "read_bytes": 855.6, "write_bytes": 1280, "hidden": False}], "_levels": {}}
FS = {"free_space": False, "data": [
    {"mnt_point": "/var/snap/firefox/common/host-hunspell", "size": 1280, "used": 1280, "free": 0, "percent": 100.0},
    {"mnt_point": "/home", "size": 1099511627776, "used": 549755813888, "free": 549755813888, "percent": 50.0},
    {"mnt_point": "", "size": 1024, "used": 0, "free": 1024, "percent": 0.0},
    {"mnt_point": "/", "alias": "root", "size": 536870912000, "used": 134217728000, "free": 402653184000, "percent": 25.0}], "_levels": {}}
for rows in (diskio(DISKIO, D.fields_description), fs(FS, F.fields_description), fs({**FS, "free_space": True}, F.fields_description)):
    print([[c.text.strip() for c in r.cells] for r in rows])
EOF
```
Expected (the TUI truncates long names in characters; the WebUI keeps the whole name and truncates with CSS):
```
[['DISK I/O', 'R/s', 'W/s'], ['nvme0n1', '855B', '1.2K'], ['Backup', '1.5K', '0B']]
[['FILE SYS', 'Used', 'Total'], ['root', '125.0G', '500.0G'], ['/home', '512.0G', '1.0T'], ['_irefox/common/host-hunspell', '1.2K', '1.2K']]
[['FILE SYS', 'Free', 'Total'], ['root', '375.0G', '500.0G'], ['/home', '512.0G', '1.0T'], ['_irefox/common/host-hunspell', '0B', '1.2K']]
```
If the printed `_…` name differs in length, that is the TUI's 18-character slice and is fine; every other string must match.

- [ ] **Step 2: Add the fixtures**

In `tests/fixtures/webui_render_fixtures.js`:

(a) In `INFO_FIXTURES`, after `network: { … },` add:

```js
	// short_names copied from glances/plugins/diskio/model_v5.py and
	// glances/plugins/fs/model_v5.py (G9-6 Task 3).
	diskio: { disk_name: {}, read_bytes: { short_name: "R/s" }, write_bytes: { short_name: "W/s" } },
	fs: { mnt_point: {}, size: { short_name: "Total" }, used: { short_name: "Used" }, free: { short_name: "Free" }, percent: {} },
```

(b) After `NETWORK_ROWS`, add:

```js
// diskio (render_curses_v5.py:100-131): sorted by RAW disk_name, a hide_zero
// row and a rate-less row skipped, the alias displayed. `sdb`'s alias
// "Backup" sorts before "nvme0n1" but its raw key sorts after it, so a sort on
// the display name cannot pass. 855.6 B/s truncates ("855B"); 1280 is an
// exact 1.25K tie ("1.2K"). `sdb`'s read rate carries a warning.
const DISKIO_FIXTURE = {
	_key: "disk_name",
	data: [
		{ disk_name: "sdb", alias: "Backup", read_bytes: 1536, write_bytes: 0, hidden: false },
		{ disk_name: "loop0", read_bytes: 0, write_bytes: 0, hidden: true },
		{ disk_name: "sda", read_bytes: null, write_bytes: null, hidden: false },
		{ disk_name: "nvme0n1", read_bytes: 855.6, write_bytes: 1280, hidden: false },
	],
	_levels: { sdb: { read_bytes: { level: "warning", prominent: false } } },
};

// fs (render_curses_v5.py:96-121): sorted by RAW mount point, an empty mount
// point skipped, the alias "root" displayed for "/" (it would sort LAST by
// display name). The tier comes from `percent` and lands on the used/free
// cell only, never on Total.
const FS_FIXTURE = {
	_key: "mnt_point",
	free_space: false,
	data: [
		{ mnt_point: "/var/snap/firefox/common/host-hunspell", size: 1280, used: 1280, free: 0, percent: 100.0 },
		{ mnt_point: "/home", size: 1099511627776, used: 549755813888, free: 549755813888, percent: 50.0 },
		{ mnt_point: "", size: 1024, used: 0, free: 1024, percent: 0.0 },
		{ mnt_point: "/", alias: "root", size: 536870912000, used: 134217728000, free: 402653184000, percent: 25.0 },
	],
	_levels: {
		"/home": { percent: { level: "careful", prominent: false } },
		"/var/snap/firefox/common/host-hunspell": { percent: { level: "critical", prominent: false } },
	},
};
```

(c) In `ALL_FIXTURES`, after `"network-empty"`, add:

```js
	diskio: { diskio: DISKIO_FIXTURE },
	fs: { fs: FS_FIXTURE },
	// `free_space` is envelope metadata (fs/model_v5.py:113-115): the config
	// key merged with --fs-free-space, which is why the component reads it
	// from the payload and not from /api/5/args.
	"fs-free-space": { fs: { ...FS_FIXTURE, free_space: true } },
```

- [ ] **Step 3: Write the failing tests**

In `tests/test_webui_v5_render.py`:

(a) In `test_the_registry_renders_every_registered_plugin` and `test_an_unreadable_pluginslist_renders_the_whole_registry`, replace in both expected lists the final `"network",` line with:

```python
        "network",
        "diskio",
        "fs",
```

(b) In `test_server_args_does_not_leak_into_the_dom_as_an_attribute`, replace `== 11` with `== 13` and "Eleven is the registry size" with "Thirteen is the registry size", and `f"expected all eleven plugins' attributes` with `f"expected all thirteen plugins' attributes`.

(c) In `test_a_table_value_carries_its_tier_on_the_text_not_the_cell`'s parameters, add after the `gpu` param:

```python
        # Columns: name, R/s, W/s -> row 1 (sdb) cell 4 is its read rate.
        pytest.param("diskio", "diskio", 4, {"gl-level-warning"}, id="diskio"),
        # Columns: name, Used, Total -> row 1 (/home) cell 4 is its used space.
        pytest.param("fs", "fs", 4, {"gl-level-careful"}, id="fs"),
```

(d) Extend the parameters of the three parametrized G9-6 tests of Task 4:

`test_a_loaded_collection_puts_its_title_in_the_header_row`:

```python
        pytest.param("diskio", "diskio", "DISK I/O", id="diskio"),
        pytest.param("fs", "fs", "FILE SYS", id="fs"),
```

`test_a_collection_keeps_its_title_heading_while_loading`:

```python
        pytest.param("diskio", "DISK I/O", id="diskio"),
        pytest.param("fs", "FILE SYS", id="fs"),
```

`test_a_path_like_name_keeps_its_tail_and_its_full_text_on_hover`:

```python
        pytest.param("diskio", "diskio", id="diskio"),
        pytest.param("fs", "fs", id="fs"),
```

(e) Append after `test_a_path_like_name_keeps_its_tail_and_its_full_text_on_hover`:

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_diskio_renders_the_tui_rows_sorted_by_raw_name():
    """diskio/render_curses_v5.py:100-131: sorted by raw disk_name, hide_zero
    and rate-less rows skipped, the alias displayed, byte rates without "/s".
    """
    payload = _run_render_probe("diskio")
    assert payload["pluginColumnHeaders"]["diskio"] == ["DISK I/O", "R/s", "W/s"]
    assert _table_rows(payload, "diskio", 3) == [["nvme0n1", "855B", "1.2K"], ["Backup", "1.5K", "0B"]]


@pytest.mark.parametrize(
    ("scenario", "label", "rows"),
    [
        pytest.param(
            "fs",
            "Used",
            [["root", "125.0G", "500.0G"], ["/home", "512.0G", "1.0T"], ["/var/snap/firefox/common/host-hunspell", "1.2K", "1.2K"]],
            id="used",
        ),
        pytest.param(
            "fs-free-space",
            "Free",
            [["root", "375.0G", "500.0G"], ["/home", "512.0G", "1.0T"], ["/var/snap/firefox/common/host-hunspell", "0B", "1.2K"]],
            id="free",
        ),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_fs_renders_the_tui_rows_and_switches_used_for_free(scenario, label, rows):
    """fs/render_curses_v5.py:73-121: the payload's `free_space` picks both
    the second column and its label; rows sorted by raw mount point.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginColumnHeaders"]["fs"] == ["FILE SYS", label, "Total"]
    assert _table_rows(payload, "fs", 3) == rows


@pytest.mark.parametrize("scenario", ["fs", "fs-free-space"])
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_fs_colours_the_used_or_free_cell_from_percent_never_the_total(scenario):
    """v4 decorates the used/free cell from `percent` (fs/render_curses_v5.py
    docstring); Total is never coloured. Cells: root 0-2, /home 3-5, snap 6-8.
    """
    cells = _run_render_probe(scenario)["pluginTableCells"]["fs"]
    assert _tier_classes(cells[4]["value"]) == {"gl-level-careful"}, cells[4]
    assert _tier_classes(cells[5]["value"]) == set(), cells[5]
    assert _tier_classes(cells[7]["value"]) == {"gl-level-critical"}, cells[7]
    assert _tier_classes(cells[8]["value"]) == set(), cells[8]
```

Run: `uv run pytest tests/test_webui_v5_render.py -q` → the new and extended cases FAIL (no `diskio`/`fs` component).

- [ ] **Step 4: Create `PluginDiskio.vue`**

```vue
<template>
	<article class="gl-plugin" aria-label="DISK I/O">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">DISK I/O</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- The TUI's header row: block title, then the schema's labels. -->
				<tr>
					<th class="gl-header">DISK I/O</th>
					<th v-for="field in RATE_FIELDS" :key="field" class="gl-header gl-num">
						{{ labelFor(labels, field) }}
					</th>
				</tr>
			</thead>
			<tbody>
				<!-- Keyed and coloured by the RAW disk_name: the alias is display only. -->
				<tr v-for="item in rows" :key="item.disk_name">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="nameOf(item)"><bdi>{{ nameOf(item) }}</bdi></span>
					</td>
					<td v-for="field in RATE_FIELDS" :key="field" class="gl-num">
						<span :class="cellClassFor(payload, item, field)">{{ formatBytes(item[field]) }}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatBytes } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { byText, displayName } from "./rows.js";

const RATE_FIELDS = ["read_bytes", "write_bytes"];

export default {
	name: "PluginDiskio",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		RATE_FIELDS: () => RATE_FIELDS,
		// Mirrors diskio/render_curses_v5.py:100-113: sorted by raw disk_name;
		// skip a row hide_zero still hides, a disk with no rate yet (cycle 1),
		// and a nameless one. Byte rates without "/s", the header carries it.
		rows() {
			return (this.payload?.data || [])
				.filter((item) => item.hidden !== true && item.read_bytes != null && item.write_bytes != null && item.disk_name)
				.sort(byText("disk_name"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatBytes,
		nameOf(item) {
			return displayName(item, "disk_name");
		},
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (diskio/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 18ch;
}
</style>
```

- [ ] **Step 5: Create `PluginFs.vue`**

```vue
<template>
	<article class="gl-plugin" aria-label="FILE SYS">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">FILE SYS</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- The TUI's header row: block title, then the schema's labels. -->
				<tr>
					<th class="gl-header">FILE SYS</th>
					<th class="gl-header gl-num">{{ labelFor(labels, valueField) }}</th>
					<th class="gl-header gl-num">{{ labelFor(labels, "size") }}</th>
				</tr>
			</thead>
			<tbody>
				<!-- Keyed and coloured by the RAW mnt_point: the alias is display only. -->
				<tr v-for="item in rows" :key="item.mnt_point">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="nameOf(item)"><bdi>{{ nameOf(item) }}</bdi></span>
					</td>
					<!-- v4 parity: the used/free cell takes the `percent` tier, whatever
					free_space selects; Total is never coloured. -->
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'percent')">{{ formatBytes(item[valueField]) }}</span>
					</td>
					<td class="gl-num">
						<span>{{ formatBytes(item.size) }}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatBytes } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { byText, displayName } from "./rows.js";

export default {
	name: "PluginFs",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: `free_space` is read from the payload, not from
		// here -- /api/5/args misses a `[fs] free_space` set in the
		// configuration, which the model has already merged (fs/model_v5.py).
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// fs/render_curses_v5.py:75-77.
		valueField() {
			return this.payload?.free_space ? "free" : "used";
		},
		// fs/render_curses_v5.py:98-103: sorted by raw mount point, a row with
		// no mount point skipped.
		rows() {
			return (this.payload?.data || []).filter((item) => item.mnt_point).sort(byText("mnt_point"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatBytes,
		nameOf(item) {
			return displayName(item, "mnt_point");
		},
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (fs/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 18ch;
}
</style>
```

- [ ] **Step 6: Register them**

In `glances/outputs/static/js/v5/plugins/index.js`, add the imports after `import PluginCloud from "../PluginCloud.vue";`:

```js
import PluginDiskio from "../PluginDiskio.vue";
import PluginFs from "../PluginFs.vue";
```

and after the `network` entry:

```js
	{
		name: "diskio",
		component: PluginDiskio,
		slot: "left",
		spec: { shape: "collection", required: ["disk_name"] },
	},
	{
		name: "fs",
		component: PluginFs,
		slot: "left",
		spec: { shape: "collection", required: ["mnt_point"] },
	},
```

- [ ] **Step 7: Rebuild, run, lint, stage**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run ruff check tests/test_webui_v5_render.py && uv run ruff format --check tests/test_webui_v5_render.py
git add glances/outputs/static/js/v5/PluginDiskio.vue glances/outputs/static/js/v5/PluginFs.vue glances/outputs/static/js/v5/plugins/index.js \
  tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```
Expected: all green; `test_every_slot_orders_its_plugins_like_the_tui` passes unchanged. If `ruff format --check` wants to rewrap the long `pytest.param` rows, run `uv run ruff format tests/test_webui_v5_render.py` and re-run the tests.

---

### Task 6: `wifi` and `sensors`

**Files:**
- Create: `glances/outputs/static/js/v5/PluginWifi.vue`, `glances/outputs/static/js/v5/PluginSensors.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `formatFixed0`, `toFahrenheit` (`format.js`); `byText` (Task 2); the `wifi` `short_name` (Task 3); the collection shape, `pluginNameCells`, `_table_rows`, the parametrized tests (Tasks 4–5).
- Produces: registry `left` order `network, wifi, diskio, fs, sensors`; fixture scenarios `wifi`, `sensors`, `sensors-fahrenheit`.

- [ ] **Step 1: Check the expected values against the TUI**

```bash
uv run python - <<'EOF'
from glances.plugins.wifi.render_curses_v5 import render as wifi
from glances.plugins.wifi.model_v5 import PluginModel as W
from glances.plugins.sensors.render_curses_v5 import render as sensors
WIFI = {"data": [
    {"ssid": "wlp0s20f3", "quality_link": 56.0, "quality_level": -54.5},
    {"ssid": "", "quality_link": 50.0, "quality_level": -50.0},
    {"ssid": "wlx-no-signal", "quality_link": 0.0, "quality_level": None},
    {"ssid": "wlx-bad-reading", "quality_link": 0.0, "quality_level": "N/A"},
    {"ssid": "wlan0", "quality_link": 40.0, "quality_level": -71.2}], "_levels": {}}
S = [
    {"label": "Composite", "type": "temperature_core", "unit": "C", "value": 42.5},
    {"label": "fan1", "type": "fan_speed", "unit": "R", "value": 1200},
    {"label": "Core 0", "type": "temperature_core", "unit": "C", "value": 43.5},
    {"label": "BAT BAT0", "type": "battery", "unit": "%", "value": 80, "status": "Discharging"},
    {"label": "BAT BAT1", "type": "battery", "unit": "%", "value": [], "status": "Unknown"},
    {"label": "BAT BAT2", "type": "battery", "unit": "%", "value": 100, "status": "Full"},
    {"label": "BAT BAT3", "type": "battery", "unit": "%", "value": 55, "status": "Charging"},
    {"label": "odd", "type": "temperature_core", "unit": "C", "value": "n/a"},
    {"label": "sda", "type": "temperature_hdd", "unit": "C", "value": "ERR"},
    {"label": "Composite temperature of the NVMe controller", "type": "temperature_core", "unit": "C", "value": 36}]
print([[c.text.strip() for c in r.cells] for r in wifi(WIFI, W.fields_description)])
for f in (False, True):
    print([[c.text.strip() for c in r.cells] for r in sensors({"data": S, "_levels": {}}, {}, {"fahrenheit": f})])
EOF
```
Expected (the TUI cuts sensor labels at 19 characters; the WebUI keeps them whole):
```
[['WIFI', 'dBm'], ['wlan0', '-71'], ['wlp0s20f3', '-54']]
[['SENSORS'], ['Composite', '42C'], ['fan1', '1200R'], ['Core 0', '44C'], ['BAT BAT0', '80%↓'], ['BAT BAT2', '100%✓'], ['BAT BAT3', '55%↑'], ['sda', 'ERR'], ['Composite temperatu', '36C']]
[['SENSORS'], ['Composite', '108F'], ['fan1', '1200R'], ['Core 0', '110F'], ['BAT BAT0', '80%↓'], ['BAT BAT2', '100%✓'], ['BAT BAT3', '55%↑'], ['sda', 'ERR'], ['Composite temperatu', '97F']]
```

- [ ] **Step 2: Add the fixtures**

In `tests/fixtures/webui_render_fixtures.js`:

(a) In `INFO_FIXTURES`, after the `fs` entry:

```js
	// short_name copied from glances/plugins/wifi/model_v5.py (G9-6 Task 3);
	// sensors declares none -- its value column has no header in the TUI.
	wifi: { ssid: {}, quality_link: {}, quality_level: { short_name: "dBm" } },
	sensors: { label: {}, type: {}, unit: {}, value: {}, warning: {}, critical: {}, status: {} },
```

(b) After `FS_FIXTURE`:

```js
// wifi (render_curses_v5.py:73-95): sorted by ssid, an empty ssid and a
// non-numeric signal skipped. -54.5 is an exact tie: Python's :.0f gives -54.
const WIFI_FIXTURE = {
	_key: "ssid",
	data: [
		{ ssid: "wlp0s20f3", quality_link: 56.0, quality_level: -54.5 },
		{ ssid: "", quality_link: 50.0, quality_level: -50.0 },
		{ ssid: "wlx-no-signal", quality_link: 0.0, quality_level: null },
		{ ssid: "wlx-bad-reading", quality_link: 0.0, quality_level: "N/A" },
		{ ssid: "wlan0", quality_link: 40.0, quality_level: -71.2 },
	],
	_levels: { wlan0: { quality_level: { level: "warning", prominent: false } } },
};

// sensors (render_curses_v5.py:77-128), in PAYLOAD order: the server sorts
// with natural keys, the renderer does not, so "fan1" before "Core 0" must
// survive. An empty battery and a non-numeric value are skipped; "ERR" is an
// hddtemp sentinel shown verbatim. 42.5 C is a tie ("42C"), and so is its
// Fahrenheit value, exactly 108.5 ("108F"). `Core 0` is prominent critical.
const SENSORS_FIXTURE = {
	_key: "label",
	data: [
		{ label: "Composite", type: "temperature_core", unit: "C", value: 42.5, warning: null, critical: null },
		{ label: "fan1", type: "fan_speed", unit: "R", value: 1200, warning: null, critical: null },
		{ label: "Core 0", type: "temperature_core", unit: "C", value: 43.5, warning: null, critical: null },
		{ label: "BAT BAT0", type: "battery", unit: "%", value: 80, warning: null, critical: null, status: "Discharging" },
		{ label: "BAT BAT1", type: "battery", unit: "%", value: [], warning: null, critical: null, status: "Unknown" },
		{ label: "BAT BAT2", type: "battery", unit: "%", value: 100, warning: null, critical: null, status: "Full" },
		{ label: "BAT BAT3", type: "battery", unit: "%", value: 55, warning: null, critical: null, status: "Charging" },
		{ label: "odd", type: "temperature_core", unit: "C", value: "n/a", warning: null, critical: null },
		{ label: "sda", type: "temperature_hdd", unit: "C", value: "ERR", warning: null, critical: null },
		{ label: "Composite temperature of the NVMe controller", type: "temperature_core", unit: "C", value: 36, warning: null, critical: null },
	],
	_levels: { "Core 0": { value: { level: "critical", prominent: true } } },
};
```

(c) In `ARGS_FIXTURES`, add `"sensors-fahrenheit": { fahrenheit: true },`.

(d) In `ALL_FIXTURES`, after `"fs-free-space"`:

```js
	wifi: { wifi: WIFI_FIXTURE },
	sensors: { sensors: SENSORS_FIXTURE },
	// Same payload as `sensors`; only ARGS_FIXTURES differs (--fahrenheit).
	"sensors-fahrenheit": { sensors: SENSORS_FIXTURE },
```

- [ ] **Step 3: Write the failing tests**

In `tests/test_webui_v5_render.py`:

(a) In both registry name lists (see Task 5 (a)), replace:

```python
        "network",
        "diskio",
        "fs",
```

with:

```python
        "network",
        "wifi",
        "diskio",
        "fs",
        "sensors",
```

(b) `test_server_args_does_not_leak_into_the_dom_as_an_attribute`: `== 13` → `== 15`, "Thirteen" → "Fifteen", "thirteen" → "fifteen".

(c) `test_a_table_value_carries_its_tier_on_the_text_not_the_cell` parameters, add:

```python
        # Columns: name, dBm -> row 0 (wlan0) cell 1 is its signal.
        pytest.param("wifi", "wifi", 1, {"gl-level-warning"}, id="wifi"),
        # Columns: name, value -> row 2 (Core 0) cell 5 is its value.
        pytest.param("sensors", "sensors", 5, {"gl-level-critical", "gl-prominent"}, id="sensors"),
```

(d) `test_a_loaded_collection_puts_its_title_in_the_header_row` parameters, add:

```python
        pytest.param("wifi", "wifi", "WIFI", id="wifi"),
        pytest.param("sensors", "sensors", "SENSORS", id="sensors"),
```

`test_a_collection_keeps_its_title_heading_while_loading` parameters, add:

```python
        pytest.param("wifi", "WIFI", id="wifi"),
        pytest.param("sensors", "SENSORS", id="sensors"),
```

(e) Append at the end of the G9-6 section:

```python
@pytest.mark.parametrize(("scenario", "name"), [("wifi", "wifi"), ("sensors", "sensors")])
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_label_like_name_keeps_its_head_and_its_full_text_on_hover(scenario, name):
    """G9-6 D3: ssids and sensor labels lose their END, like the TUI's
    label[:N] -- plain `.gl-truncate`, no <bdi> needed.
    """
    cells = _run_render_probe(scenario)["pluginNameCells"].get(name)
    assert cells, f"{name}: vacuous, no name cell rendered"
    for cell in cells:
        classes = set(cell["className"].split())
        assert {"gl-name", "gl-truncate"} <= classes and "gl-truncate-start" not in classes, cell
        assert cell["title"] == cell["text"], f"{name}: the full name is on hover: {cell!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_wifi_renders_the_tui_rows_sorted_by_ssid():
    payload = _run_render_probe("wifi")
    assert payload["pluginColumnHeaders"]["wifi"] == ["WIFI", "dBm"]
    assert _table_rows(payload, "wifi", 2) == [["wlan0", "-71"], ["wlp0s20f3", "-54"]]


@pytest.mark.parametrize(
    ("scenario", "values"),
    [
        pytest.param("sensors", ["42C", "1200R", "44C", "80%↓", "100%✓", "55%↑", "ERR", "36C"], id="celsius"),
        pytest.param("sensors-fahrenheit", ["108F", "1200R", "110F", "80%↓", "100%✓", "55%↑", "ERR", "97F"], id="fahrenheit"),
    ],
)
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_sensors_renders_the_tui_values_in_payload_order(scenario, values):
    """sensors/render_curses_v5.py:77-128: payload order; `--fahrenheit`
    converts temperatures but never a battery or a fan; battery trend arrows;
    a sentinel verbatim; an empty battery and a non-numeric value skipped.
    The TUI's header row is one cell, so the value column's <th> is empty.
    """
    payload = _run_render_probe(scenario)
    assert payload["pluginColumnHeaders"]["sensors"] == ["SENSORS", ""]
    labels = ["Composite", "fan1", "Core 0", "BAT BAT0", "BAT BAT2", "BAT BAT3", "sda", "Composite temperature of the NVMe controller"]
    assert _table_rows(payload, "sensors", 2) == [list(pair) for pair in zip(labels, values)]
```

Run: `uv run pytest tests/test_webui_v5_render.py -q` → the new and extended cases FAIL.

- [ ] **Step 4: Create `PluginWifi.vue`**

```vue
<template>
	<article class="gl-plugin" aria-label="WIFI">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">WIFI</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- The TUI's header row: block title, then the schema's label. -->
				<tr>
					<th class="gl-header">WIFI</th>
					<th class="gl-header gl-num">{{ labelFor(labels, "quality_level") }}</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in rows" :key="item.ssid">
					<td>
						<span class="gl-name gl-truncate" :title="item.ssid">{{ item.ssid }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'quality_level')">{{ formatFixed0(item.quality_level) }}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatFixed0 } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { byText } from "./rows.js";

export default {
	name: "PluginWifi",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// Mirrors wifi/render_curses_v5.py:73-85: sorted by ssid; skip an empty
		// ssid (v4 #1151) and a signal that is not a number (#1973).
		rows() {
			return (this.payload?.data || [])
				.filter((item) => item.ssid != null && item.ssid !== "" && Number.isFinite(item.quality_level))
				.sort(byText("ssid"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatFixed0,
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (wifi/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 26ch;
}
</style>
```

`Number.isFinite` is false for a string, `null` and `undefined`, and never coerces.

- [ ] **Step 5: Create `PluginSensors.vue`**

```vue
<template>
	<article class="gl-plugin" aria-label="SENSORS">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">SENSORS</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- The TUI's header row is ONE cell, the title. The empty <th> keeps
				the header aligned column by column with the body. -->
				<tr>
					<th class="gl-header">SENSORS</th>
					<th class="gl-header gl-num"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="row in rows" :key="row.item.label">
					<td>
						<span class="gl-name gl-truncate" :title="row.item.label">{{ row.item.label }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, row.item, 'value')">{{ row.text }}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatFixed0, toFahrenheit } from "./format.js";
import { cellClassFor } from "./columns.js";

// sensors/render_curses_v5.py:48-49.
const SENTINELS = new Set(["ERR", "SLP", "UNK", "NOS"]);
const NO_FAHRENHEIT_TYPES = new Set(["battery", "fan_speed"]);

// _battery_trend(). Always the unicode glyphs: v4 and the TUI both call
// unicode_message() without args, so --disable-unicode never reaches them.
function batteryTrend(item) {
	const status = String(item.status ?? "");
	if (status.startsWith("Charg")) return "↑";
	if (status.startsWith("Discharg")) return "↓";
	if (status.startsWith("Full")) return "✓";
	return "";
}

// _value_text(). "" means the TUI skips the row. That also covers the
// renderer's separate empty-battery guard (value [], None or ""): none of
// those is a number or a sentinel, so both rules skip the same rows.
function valueText(item, fahrenheit) {
	const value = item.value;
	if (typeof value === "string" && SENTINELS.has(value)) return value;
	if (!Number.isFinite(value)) return "";
	const type = String(item.type ?? "");
	if (fahrenheit && !NO_FAHRENHEIT_TYPES.has(type)) return `${formatFixed0(toFahrenheit(value))}F`;
	const trend = type === "battery" ? batteryTrend(item) : "";
	return `${formatFixed0(value)}${item.unit ?? ""}${trend}`;
}

export default {
	name: "PluginSensors",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: the TUI's value column has no label.
		labels: { type: Object, default: () => ({}) },
		// `fahrenheit` (--fahrenheit) converts temperatures, as in the TUI.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// Payload order: the server already sorts with natural keys
		// (sensors/model_v5.py:198) and the renderer does not re-sort.
		rows() {
			const fahrenheit = !!this.serverArgs.fahrenheit;
			return (this.payload?.data || [])
				.map((item) => ({ item, text: valueText(item, fahrenheit) }))
				.filter((row) => row.text !== "");
		},
	},
	methods: {
		cellClassFor,
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (sensors/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 19ch;
}
</style>
```

- [ ] **Step 6: Register them in TUI order**

In `glances/outputs/static/js/v5/plugins/index.js`, add after `import PluginFs from "../PluginFs.vue";`:

```js
import PluginWifi from "../PluginWifi.vue";
import PluginSensors from "../PluginSensors.vue";
```

Insert the `wifi` entry **between** `network` and `diskio`:

```js
	{
		name: "wifi",
		component: PluginWifi,
		slot: "left",
		spec: { shape: "collection", required: ["ssid"] },
	},
```

and append the `sensors` entry **after** `fs`:

```js
	{
		name: "sensors",
		component: PluginSensors,
		slot: "left",
		spec: { shape: "collection", required: ["label"] },
	},
```

The resulting `left` order is `network, wifi, diskio, fs, sensors` — `LEFT_SLOT` filtered to the registry.

- [ ] **Step 7: Rebuild, run, lint, stage**

```bash
(cd glances/outputs/static && npm run build)
# v4 identity check -- both IDENTICAL
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
uv run ruff check tests/test_webui_v5_render.py && uv run ruff format --check tests/test_webui_v5_render.py
git add glances/outputs/static/js/v5/PluginWifi.vue glances/outputs/static/js/v5/PluginSensors.vue glances/outputs/static/js/v5/plugins/index.js \
  tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py glances/outputs/static/public/glances5.js
git status --short | grep -v '^[AM] '
```
Expected: all green, `test_every_slot_orders_its_plugins_like_the_tui` included.

---

### Task 7: Verify against a real server and close

**Files:** everything the group touched. No new code unless a hook rewrites something.

- [ ] **Step 1: Only the allowed TUI files moved**

```bash
git diff --stat HEAD -- glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py \
  glances/outputs/curses_formatters_v5.py 'glances/plugins/*/render_curses_v5.py' \
  'glances/plugins/*/model_v5.py' 'tests/test_*render_curses_v5.py' tests/test_curses_renderer_v5.py
```
Expected: exactly `glances/plugins/{diskio,fs,wifi}/render_curses_v5.py`, `glances/plugins/{diskio,fs,wifi,network}/model_v5.py`, `tests/test_plugin_{diskio,fs,wifi}_render_curses_v5.py`. Then:

```bash
git diff -U0 HEAD -- tests/test_plugin_diskio_render_curses_v5.py tests/test_plugin_fs_render_curses_v5.py tests/test_plugin_wifi_render_curses_v5.py | grep -E '^[-+]\s*assert' || echo "NO ASSERT LINE CHANGED"
```

- [ ] **Step 2: v4 untouched**

```bash
git diff --stat HEAD -- glances/outputs/glances_restful_api.py \
  glances/outputs/static/js/app.js glances/outputs/static/js/browser.js \
  glances/outputs/static/js/services.js glances/outputs/static/js/components/ \
  glances/outputs/static/js/App.vue glances/outputs/static/js/Browser.vue \
  glances/outputs/static/js/store.js glances/outputs/static/js/filters.js \
  glances/outputs/static/js/uiconfig.json glances/outputs/static/webpack.config.js \
  glances/outputs/static/css/custom.scss glances/outputs/static/css/style.scss \
  glances/outputs/static/templates/index.html \
  glances/outputs/static/js/v5/levels.js glances/outputs/static/js/v5/columns.js \
  glances/outputs/static/js/v5/layout.js glances/outputs/static/js/v5/api.js \
  glances/outputs/static/js/v5/labels.js glances/outputs/static/js/v5/AppShell.vue
```
Expected: empty. Then the v4 bundle identity check one final time.

- [ ] **Step 3: No dead code**

```bash
grep -rn '"interface"\|no interface' glances/outputs/static/js/v5 glances/plugins/network tests/fixtures tests/test_webui_v5_render.py
grep -rn "toFixedHalfEven\|formatNetworkRate\|formatFixed0\|displayName\|byText" glances/outputs/static/js/v5 --include=*.vue --include=*.js
grep -rn "gl-table\|gl-name\|gl-truncate-start" glances/outputs/static/js/v5
```
Expected: the first prints nothing. The second shows a caller outside `format.js`/`rows.js` for `formatNetworkRate` (PluginNetwork), `formatFixed0` (PluginWifi, PluginSensors), `displayName` (PluginNetwork, PluginDiskio, PluginFs), `byText` (PluginDiskio, PluginFs, PluginWifi), and `toFixedHalfEven` called inside `format.js`. The third shows every class used by a component.

- [ ] **Step 4: Full suite**

```bash
uv run pytest -q
```
No NEW failures versus the pre-existing state. `test_050/051`: re-run `tests/test_restful.py` alone. `test_mcp.py`: check `ss -lptn 'sport = :61235'` first.

- [ ] **Step 5: Screenshots from a real server**

Save as `.superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/shots/shoot.py` and run `uv run python .superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/shots/shoot.py`:

```python
"""G9-6 Task 7: the left column of a real v5 server, both themes, two widths."""

import os
import subprocess
import sys
import time
import urllib.request

OUT = os.path.abspath(".superpowers/sdd/2026-09-11-glances-v5-g9-6-webui-left-sidebar/shots")
PORT = 61296
CONF_BODY = """[diskio]
hide=loop.*,/dev/loop.*
[fs]
hide=/boot.*,.*/snap.*
alias=/:/a/very/long/alias/standing/in/for/the/root/mount/point
[network]
alias=lo:A-very-long-loopback-interface-alias
[sensors]
alias=Composite:A very long sensor label to show the trailing ellipsis
"""


def shoot(theme: str, width: int) -> None:
    conf = os.path.join(OUT, f"g96-{theme}.conf")
    with open(conf, "w") as f:
        f.write(CONF_BODY + f"[outputs]\ntheme={theme}\n")
    cmd = [sys.executable, "-m", "glances.main_v5", "-s", "--bind", "127.0.0.1", "--port", str(PORT), "-C", conf]
    server = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/status", timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise SystemExit("the v5 server did not come up")
        time.sleep(12)  # two rate cycles, and the first fs/sensors publication
        png = os.path.join(OUT, f"left-{theme}-{width}.png")
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
             f"--screenshot={png}", f"--window-size={width},1600", "--virtual-time-budget=8000",
             f"http://127.0.0.1:{PORT}/"],
            check=True, timeout=120, capture_output=True,
        )
        print(png)
    finally:
        server.terminate()
        server.wait(timeout=15)


os.makedirs(OUT, exist_ok=True)
for theme in ("dark", "light"):
    for width in (720, 1500):
        shoot(theme, width)
```

Check `ss -ltn 'sport = :61296'` is empty first. Open each PNG and check: `NETWORK`, `WIFI` (if this host has one), `DISK I/O`, `FILE SYS`, `SENSORS` in that order in the left column; titles in the header row; the network alias and the `/` alias truncated at the start with their tail visible; the long sensor alias truncated at the end; network rates in bits (`…b`); numeric columns right-aligned. Report what each screenshot shows. If a check fails, report it with the screenshot path — do not fix it in this step.

- [ ] **Step 6: Hooks and final stage**

```bash
git add -A
make pre-commit
git add -A
git status --short
```
`make pre-commit` runs ~23 hooks and some rewrite files; gitleaks scans the INDEX, which is why it is `add`, `run`, `add`. `check-shebang-scripts-are-executable` failed on 5 test files from develop backports before this group: for any failing hook, list its files and say whether each is part of this group's diff. **If a hook rewrites a v4 file or a TUI file outside the allowed list, STOP and report** — do not stage it and do not revert it. Do NOT commit.

- [ ] **Step 7: Report, do not write**

In the task report only, never in the repository:

- **Manual UI smoke test owed to the maintainer** (`python -m glances.main_v5 -s`, open the page): long mount point and disk alias (leading ellipsis, tail kept), long sensor label (trailing), `--byte`, `--fahrenheit`, `--fs-free-space`, a laptop battery (arrows), both themes, a narrow viewport. **Firefox was never checked** — the leading ellipsis was verified in Chrome only.
- **Reported, not fixed** (spec §2): the other WebUI formatters still round an exact tie away from zero where the TUI rounds to even — `formatPercent` and `formatCount` (`toFixed(1)`, e.g. `52.25` → `52.3%` vs the TUI's `52.2%`), `PluginLoad.vue`'s `toFixed(2)`, and `gpuValue()`'s `Math.round`. Each can adopt `toFixedHalfEven` in a later group.
- **Release-notes items:** spec §12 list, verbatim.
- **Pressure report for G9-7** (`ports`, `connections`, `irq`, `folders`, `raid`, `smart`): the size of `tests/test_webui_v5_render.py` and `tests/fixtures/webui_render_fixtures.js` after this group.

---

## Self-review notes

Checked against the spec, section by section:

- §1 goals → Tasks 4–6 (plugins, retrofit), Task 4 (D6), Task 0 (split).
- §3 D1 → Tasks 5–6 registry + drift guard unchanged. D2 → Task 4 `rows` + `formatNetworkRate`. D3 → Task 2 CSS + Chrome check, `--gl-name-width` per component, `pluginNameCells` tests in Tasks 4–6. D4 → Task 0 with ids and per-scenario byte identity. D5 → Task 3. D6 → Task 4 (network, schema, empty collection) and the parametrized title tests extended in Tasks 5–6.
- §4.1 row rules → each component's `rows` computed, with its renderer line range in a comment; §4.2 `free_space` from the payload → `PluginFs` + `fs-free-space` fixture.
- §5 `rows.js` → Task 2. §6 labels + amendment → Task 3 (fixture switch first, `NO ASSERT LINE CHANGED` twice, negative check). §7.1–§7.3 → Task 1, every value checked against Python in Step 1.
- §8.1 shape → Task 4 Interfaces, repeated literally in Tasks 5–6. §8.2 CSS → Task 2. §8.3–§8.5 → Tasks 4, 5, 6.
- §9.1 → Task 0 Steps 1–4. §9.2 → Tasks 1–2. §9.3 → Tasks 2–3. §9.4 table → Tasks 4–6 tests. §9.5 → Global Constraints + Task 7 Steps 1–2, 4, 6. §9.6 → Task 7 Step 7.
- §10 tasks → same numbering. §11 risks → Task 2 Step 6 (STOP rule), Task 1 (`0.15`), Task 0 (evidence), Task 7 Step 6 (pre-commit), `git status` after every stage.

Decisions this plan takes that the spec left open:

1. **`.gl-table` is a global class**, and `PluginNetwork.vue`'s scoped table block goes with the rewrite. Five components would otherwise carry five copies of the same scoped rules, including the load-bearing `:not(.gl-num)`. `PluginGpu.vue`'s table is not touched.
2. **The sensors empty-battery guard is not a separate rule** in `PluginSensors.vue`: the renderer's `value in ([], None, "")` check skips rows that `_value_text()` would skip anyway, so one filter reproduces both (commented in the component).
3. **`pluginTableCells` gains a `text` key** instead of a new per-cell output: existing tests read only `cell` and `value`, so the addition is inert for them.
4. **The unused `pluginHeaders` probe output (a G9-5 carry-over) gets its first reader**: the D6 tests use it to observe that the `<h2>` is gone once loaded.
5. **The fixture TUI tests switch to the real schema before the renderers change** (Task 3 Step 1), so a failure in Step 5 can only come from the renderer change.

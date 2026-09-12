# G9-7 — v5 WebUI left sidebar, batch 2: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `ports`, `connections`, `irq`, `folders`, `raid` and `smart` in the v5 WebUI's left column at strict TUI parity — closing the eleven-plugin left column — on top of a shared collection shell extracted from the five components G9-6 left behind.

**Architecture:** A pure refactor first (Task 0: `CollectionBlock.vue`, the five existing collection components migrated with not one assertion changed), then the pure pieces the new components consume — `formatAutoUnit` and the mirrored `LARGE_VALUE_KEYS` (Task 1) — then the two Python-side tasks the components depend on: schema labels (Task 2) and the empty-collection parity fix (Task 3). The six components follow in family order: flat (Task 4: `ports`, `folders`), scalar + ranked (Task 5: `connections`, `irq`), hierarchical plus the probe extension they need (Task 6: `raid`, `smart`). Task 7 verifies against a real server and closes.

**Tech Stack:** Vue 3.5 SFC (options API), webpack 5, `node --test` (via `tests/test_webui_v5_js.py`), pytest (`uv run`), a fake-DOM node probe (`tests/fixtures/webui_render_probe.js`).

**Spec:** `docs/superpowers/specs/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2-design.md`

**Depends on:** G9-6 and the horizontal degradation group, committed as `98e25644`; HEAD `42a60cd9`.

**SDD workspace:** `.superpowers/sdd/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2/` (git-ignored). Scratch files, captures and screenshots go there, never in the repository.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer. Never `git clean`, never `git checkout`/`restore` over working files, never `git stash`, **never unstage anything** (`git reset`, `git restore --staged`, `git rm --cached`). After staging, run `git status --short | grep -v '^[AM] '` and report any line it prints.
- **Never touch `NEWS.rst`.**
- **TUI Python files: only these may change, and only in the task named.**
  - Task 2: `glances/plugins/{irq,raid,connections}/model_v5.py` (new `short_name`s) and `glances/plugins/{irq,raid,connections}/render_curses_v5.py` (labels through `field_label()`); in `tests/test_plugin_irq_render_curses_v5.py`, `tests/test_plugin_raid_render_curses_v5.py`, `tests/test_plugin_connections_render_curses_v5.py` **only the schema source** — not one `assert` line may change.
  - Task 3: `glances/plugins/raid/render_curses_v5.py`, `glances/plugins/smart/render_curses_v5.py`, and in their two test files the single `test_empty_returns_header_only` case (this is the one place an assertion changes on purpose).
  - Nothing else under `glances/plugins/*/render_curses_v5.py`, `glances/plugins/*/model_v5.py`, `glances/outputs/curses_renderer_v5.py`, `glances/outputs/glances_curses_v5.py`, `glances/outputs/curses_formatters_v5.py`, `tests/test_*render_curses_v5.py`, `tests/test_curses_renderer_v5.py`. If a task seems to need one, STOP and report.
- **v4 is read-only.** `glances/outputs/glances_restful_api.py`, `js/app.js`, `js/browser.js`, `js/services.js`, `js/components/**`, `js/App.vue`, `js/Browser.vue`, `js/store.js`, `js/filters.js`, `js/uiconfig.json`, `css/*.scss`, `templates/index.html`, `webpack.config.js`. `css/v5.css` IS in scope. `glances/plugins/smart/__init__.py` and `glances/globals.py` are read-only — they are the reference the JS mirrors, never the thing that changes.
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
- **No colour literal under `js/v5/` or in a new `css/v5.css` rule** — enforced by `tests/test_webui_v5_tokens.py`. Use the existing `--gl-*` tokens.
- **`levels.js`, `columns.js`, `rows.js`, `layout.js`, `api.js`, `labels.js`, `degrade.js` and `AppShell.vue` are not touched** by any task in this group.
- **The `ch` caps are approximate and stay that way** (spec D2): `1ch` ≈ 0.83 rendered characters under the shipped font stack. No task changes `--gl-font`.
- **Every new component declares the two deliberately-unused props** `serverArgs` and `degrade`, with the existing comment: an undeclared object prop falls through onto the DOM as `server-args="[object Object]"`. `tests/test_webui_v5_render.py` observes this through `pluginAttrs`.
- Test-suite footguns: `tests/test_restful.py::test_050/051` are flaky by construction (hard-coded `time.sleep(5)` on a subprocess server) — re-run alone before believing a failure. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `glances/outputs/static/js/v5/CollectionBlock.vue` | **New.** The collection shell: root `<article>`, `aria-label`, loading/error states, `<table>`, optional `<thead>` | 0 |
| `glances/outputs/static/js/v5/PluginNetwork.vue`, `PluginDiskio.vue`, `PluginFs.vue`, `PluginWifi.vue`, `PluginSensors.vue` | Migrated onto the shell, iso-behaviour | 0 |
| `glances/outputs/static/js/v5/format.js` | `formatAutoUnit` — v4 `glances.globals.auto_unit`, NOT `formatBytes` | 1 |
| `glances/outputs/static/js/v5/smart_keys.js` | **New.** The JS mirror of `LARGE_VALUE_KEYS` | 1 |
| `tests/js/format.test.mjs` | `formatAutoUnit` unit tests | 1 |
| `tests/test_webui_v5_smart_keys_drift.py` | **New.** JS copy vs the Python frozenset | 1 |
| `glances/plugins/{irq,raid,connections}/model_v5.py` | New `short_name`s | 2 |
| `glances/plugins/{irq,raid,connections}/render_curses_v5.py` | Labels through `field_label()` | 2 |
| `tests/test_plugin_{irq,raid,connections}_render_curses_v5.py` | Schema source = `PluginModel.fields_description` | 2 |
| `glances/plugins/{raid,smart}/render_curses_v5.py` | `[]` on an empty collection (v4 parity) | 3 |
| `tests/test_plugin_{raid,smart}_render_curses_v5.py` | `test_empty_returns_header_only` inverted | 3 |
| `glances/outputs/static/js/v5/PluginPorts.vue`, `PluginFolders.vue` | **New** | 4 |
| `glances/outputs/static/css/v5.css` | `.gl-strong` (bold, no tier colour), `.gl-subline` (`white-space: pre`) | 4, 6 |
| `glances/outputs/static/js/v5/PluginConnections.vue`, `PluginIrq.vue` | **New** | 5 |
| `glances/outputs/static/js/v5/PluginRaid.vue`, `PluginSmart.vue` | **New** | 6 |
| `tests/fixtures/webui_render_probe.js` | New `pluginRowGroups` output | 6 |
| `glances/outputs/static/js/v5/plugins/index.js` | Six new entries in `LEFT_SLOT` order | 4, 5, 6 |
| `tests/fixtures/webui_render_fixtures.js` | New payload fixtures and scenarios | 4, 5, 6 |
| `tests/test_webui_v5_render.py` | New render assertions; the hardcoded registry list grows to 21 names | 0, 4, 5, 6 |
| `glances/outputs/static/public/glances5.js` | Rebuilt | 0, 1, 4, 5, 6 |

---

### Task 0: `CollectionBlock.vue`, and the five existing collections migrated onto it

**Files:**
- Create: `glances/outputs/static/js/v5/CollectionBlock.vue`
- Modify: `glances/outputs/static/js/v5/PluginNetwork.vue`, `PluginDiskio.vue`, `PluginFs.vue`, `PluginWifi.vue`, `PluginSensors.vue`
- Modify: `tests/test_webui_v5_render.py` (one new test, no existing assertion touched)
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `CollectionBlock.vue`, default-exported as `name: "CollectionBlock"`, with props
  `payload: Object|null`, `error: String|undefined`, `title: String` (required),
  `ariaLabel: String` (defaults to `title`), `hidden: Boolean` (default `false`;
  `v-show`s the whole block away — see **Planning decision P1** below), and two
  slots — `head` (the full `<tr>` of `<th>`s; when absent, **no `<thead>` is
  rendered**) and `body` (one or more `<tbody>` elements). Tasks 4, 5 and 6 build
  every new collection on it.

This is a refactor: the existing render tests must pass **before and after**, with
no assertion edited. If an assertion has to change, the migration is wrong — STOP
and report.

**Planning decision P1 — the `hidden` prop.** The spec's §10 matrix requires
"an empty collection renders nothing" for the six new blocks, because each of
their TUI renderers returns `[]` on an empty collection. The five migrated
components must NOT change: G9-6 D6 gave them the opposite behaviour (an empty
collection keeps its header row, pinned by the `network-empty` scenario). The
shell therefore takes a `hidden` prop, defaulting to `false`; the five migrated
components do not pass it, and each new component passes
`:hidden="!!payload && rows.length === 0"` — hide once a payload exists and
yields no row, keep "loading…" before the first payload. `v-show`, not `v-if`:
the article stays in the DOM and the probe observes it through `pluginHidden`,
the same contract `cloud` uses. Its first user is Task 4.

- [ ] **Step 1: Capture the baseline**

```bash
D=.superpowers/sdd/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2
mkdir -p $D
uv run pytest tests/test_webui_v5_render.py -q | tail -3 | tee $D/render-before.txt
uv run pytest tests/test_webui_v5_render.py --collect-only -q | sed 's/^.*:://' | sort > $D/ids-before.txt
wc -l $D/ids-before.txt
```

Expected: all tests pass. Keep both files; Step 9 compares against them.

- [ ] **Step 2: Write the pin that guards the new nested root**

The hazard this refactor introduces: `AppShell` passes `data-plugin` as a
fallthrough attribute. With the root moved into a child component, the attribute
has to cascade through **two** component roots, and it is dropped silently the
moment a plugin component's template has more than one root node — a
root-level comment is enough. Add to `tests/test_webui_v5_render.py`, after
`test_every_slot_orders_its_plugins_like_the_tui`:

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_collection_block_keeps_its_root_attributes():
    """G9-7 Task 0 moved the root <article> into CollectionBlock.vue, so
    `data-plugin` and `aria-label` now reach it through TWO component roots.
    Vue drops a fallthrough attribute without error when a template has more
    than one root node -- a root-level comment is enough -- and the symptom is
    a plugin that silently vanishes from the page.
    """
    payload = _run_render_probe("default")
    attrs = payload["pluginAttrs"]
    for name in ("network", "wifi", "diskio", "fs", "sensors"):
        assert name in attrs, f"{name} did not render at all: {sorted(attrs)!r}"
        assert "data-plugin" in attrs[name], f"{name} lost data-plugin: {attrs[name]!r}"
        assert "aria-label" in attrs[name], f"{name} lost aria-label: {attrs[name]!r}"
        assert "server-args" not in attrs[name], f"{name} leaked a prop as an attribute: {attrs[name]!r}"
```

- [ ] **Step 3: Run the pin against the unmigrated code**

Run: `uv run pytest tests/test_webui_v5_render.py::test_every_collection_block_keeps_its_root_attributes -q`
Expected: PASS. It pins behaviour that already holds; it must still pass at Step 9.

- [ ] **Step 4: Create the shell**

`glances/outputs/static/js/v5/CollectionBlock.vue`:

```vue
<template>
	<article v-show="!hidden" class="gl-plugin" :aria-label="ariaLabel || title">
		<!-- Keep every comment INSIDE this root: the build keeps template
		comments, and one before <article> would make a second root node, which
		drops the `data-plugin` and `aria-label` attributes AppShell passes down
		(they now cascade through two component roots -- this one and the
		plugin's). Pinned by test_every_collection_block_keeps_its_root_attributes. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">{{ title }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<!-- G9-6 D6: a loaded collection's title is its first <th>, so the
			<h2> above renders only while loading or erroring. G9-7 D4: a block
			with no header row in the TUI (`ports`) passes no #head slot and gets
			no <thead> at all. -->
			<thead v-if="$slots.head">
				<slot name="head"></slot>
			</thead>
			<slot name="body"></slot>
		</table>
	</article>
</template>

<script>
export default {
	name: "CollectionBlock",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		title: { type: String, required: true },
		// The accessible name. Defaults to the title; `ports` passes one while
		// rendering no visible title (G9-7 D4).
		ariaLabel: { type: String, default: "" },
		// Hide the whole block. The six G9-7 blocks pass `!!payload &&
		// rows.length === 0`, because their TUI renderers return [] on an empty
		// collection; the five G9-6 blocks keep D6's behaviour (an empty
		// collection still paints its header row) by not passing it at all.
		hidden: { type: Boolean, default: false },
	},
};
</script>
```

No `<style scoped>`: the shell owns no width and no colour. A plugin's own
`<style scoped>` still reaches this `<article>` — Vue stamps a child component's
root element with the parent's scope id as well — which is what keeps each
component's `--gl-name-width` rule working.

- [ ] **Step 5: Migrate `PluginDiskio.vue`**

Replace the whole `<template>` block, and add the `components` option plus the
`TITLE` constant to the `<script>`. The title string was written three times
(aria-label, `<h2>`, `<th>`); it becomes one constant:

```vue
<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th v-for="field in RATE_FIELDS" :key="field" class="gl-header gl-num">
					{{ labelFor(labels, field) }}
				</th>
			</tr>
		</template>
		<template #body>
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
		</template>
	</CollectionBlock>
</template>
```

In the `<script>`, add the import and the two options, changing nothing else:

```js
import CollectionBlock from "./CollectionBlock.vue";

const TITLE = "DISK I/O";

export default {
	name: "PluginDiskio",
	components: { CollectionBlock },
	// ... props unchanged ...
	computed: {
		TITLE: () => TITLE,
		RATE_FIELDS: () => RATE_FIELDS,
		// ... rows() unchanged ...
	},
	// ... methods unchanged ...
};
```

- [ ] **Step 6: Migrate the four other components the same way**

Mechanical, one file at a time. For each: the `<template>` becomes
`<CollectionBlock :title="TITLE" :payload="payload" :error="error">` wrapping a
`#head` slot holding the existing `<tr>` of `<th>`s and a `#body` slot holding the
existing `<tbody>`; the `<script>` gains the import, `components: { CollectionBlock }`
and `TITLE: () => TITLE`. Every cell, class, `:key`, `:title`, comment and
`<style scoped>` block is carried over verbatim.

| File | `TITLE` | Carry over unchanged |
|---|---|---|
| `PluginNetwork.vue` | `"NETWORK"` | the `RATE_FIELDS` header loop and its D6 comment, the "row key hardcodes `interface_name`" comment, the "tier goes on the `<span>`" comment, `formatNetworkRate(item[field], !!serverArgs.byte)` |
| `PluginFs.vue` | `"FILE SYS"` | the three `<th>`s (`valueField` then `size`), the "used/free cell takes the `percent` tier" comment |
| `PluginWifi.vue` | `"WIFI"` | the single `quality_level` `<th>`, `formatFixed0` |
| `PluginSensors.vue` | `"SENSORS"` | the empty second `<th>` **and its comment**, the index-keying comment and `:key="index"` |

- [ ] **Step 7: Rebuild the bundle**

```bash
cd glances/outputs/static && npm run build
```

Expected: webpack succeeds with no error. Then, from the repository root, run the
v4 bundle identity check from the Global Constraints. Both files must print
IDENTICAL.

- [ ] **Step 8: Run the JS lint**

```bash
cd glances/outputs/static && npx eslint js/v5 --ext .js,.vue
```

Expected: no output.

- [ ] **Step 9: Prove the refactor is iso-behaviour**

```bash
D=.superpowers/sdd/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2
uv run pytest tests/test_webui_v5_render.py -q | tail -3 | tee $D/render-after.txt
uv run pytest tests/test_webui_v5_render.py --collect-only -q | sed 's/^.*:://' | sort > $D/ids-after.txt
diff $D/ids-before.txt $D/ids-after.txt
git diff -- tests/test_webui_v5_render.py | grep -E '^-\s*assert' && echo "AN ASSERTION WAS REMOVED -- STOP" || echo "no assertion removed"
```

Expected: every test passes; the only `ids` difference is the one test added in
Step 2; no removed assertion. Also run the token and JS suites:
`uv run pytest tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py -q` → green.

- [ ] **Step 10: Stage**

```bash
git add glances/outputs/static/js/v5/CollectionBlock.vue \
        glances/outputs/static/js/v5/PluginNetwork.vue \
        glances/outputs/static/js/v5/PluginDiskio.vue \
        glances/outputs/static/js/v5/PluginFs.vue \
        glances/outputs/static/js/v5/PluginWifi.vue \
        glances/outputs/static/js/v5/PluginSensors.vue \
        glances/outputs/static/public/glances5.js \
        tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

---

### Task 1: `formatAutoUnit` and the mirrored `LARGE_VALUE_KEYS`

**Files:**
- Modify: `glances/outputs/static/js/v5/format.js`
- Create: `glances/outputs/static/js/v5/smart_keys.js`
- Modify: `tests/js/format.test.mjs`
- Create: `tests/test_webui_v5_smart_keys_drift.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `formatAutoUnit(value) -> string` exported from `format.js`, and
  `LARGE_VALUE_KEYS` (a `Set` of six strings) exported from `smart_keys.js`.
  Task 6's `PluginSmart.vue` is their only consumer.

`smart` is the first WebUI consumer of v4's `glances.globals.auto_unit`, which is
**not** the algorithm `formatBytes` mirrors. Reusing `formatBytes` here would
print wrong numbers, not a wrong layout — hence a dedicated function, its own
tests, and the comment that says why both exist.

- [ ] **Step 1: Write the failing unit tests**

Append to `tests/js/format.test.mjs`, and add `formatAutoUnit` to the existing
`import { ... } from "../../glances/outputs/static/js/v5/format.js";` line:

```js
// The cases are auto_unit()'s own docstring (glances/globals.py:431-447) --
// the one place the v4 algorithm is specified by example.
test("formatAutoUnit mirrors v4 auto_unit", () => {
	assert.equal(formatAutoUnit(613421788), "585M");
	assert.equal(formatAutoUnit(5307033647), "4.94G");
	assert.equal(formatAutoUnit(44968414685), "41.9G");
	assert.equal(formatAutoUnit(838471403472), "781G");
	assert.equal(formatAutoUnit(9683209690677), "8.81T");
	// A quotient of exactly 1024 stays in the smaller unit: the loop takes the
	// largest prefix whose quotient is > 1, so 1G is "1024M", not "1.0G".
	assert.equal(formatAutoUnit(1073741824), "1024M");
	// The trailing zero is part of the contract: a fixed-decimal string, never
	// a Number round-trip that would print "1.1G".
	assert.equal(formatAutoUnit(1181116006), "1.10G");
});

test("formatAutoUnit below 1K, at zero and on a missing value", () => {
	// Python: `if number == 0: return '0'` -- before any division.
	assert.equal(formatAutoUnit(0), "0");
	// No prefix quotient is > 1, so the fallthrough formats the number itself:
	// 0 decimals for an integer, 2 for a float (Python's isinstance check).
	assert.equal(formatAutoUnit(500), "500");
	assert.equal(formatAutoUnit(500.5), "500.50");
	assert.equal(formatAutoUnit(1024), "1024");
	assert.equal(formatAutoUnit(null), "-");
	assert.equal(formatAutoUnit(undefined), "-");
});
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd glances/outputs/static 2>/dev/null; cd - >/dev/null; uv run pytest tests/test_webui_v5_js.py -q`
Expected: FAIL — node reports `formatAutoUnit is not a function` (the import
resolves to `undefined`).

- [ ] **Step 3: Implement `formatAutoUnit`**

In `glances/outputs/static/js/v5/format.js`, after `formatBytes`:

```js
// The prefixes of v4's auto_unit(), largest first -- its
// `for symbol in reversed(symbols)` (glances/globals.py:450-471).
const AUTO_UNIT_PREFIXES = [
	["Y", 1208925819614629174706176],
	["Z", 1180591620717411303424],
	["E", 1152921504606846976],
	["P", 1125899906842624],
	["T", 1099511627776],
	["G", 1073741824],
	["M", 1048576],
	["K", 1024],
];

// Mirrors glances.globals.auto_unit() -- v4's OTHER auto-unit, the one `smart`
// uses for its LARGE_VALUE_KEYS raw values. Deliberately NOT formatBytes():
// that function mirrors _auto_unit() in curses_formatters_v5.py, and the two
// algorithms disagree on almost everything. auto_unit() takes the largest
// prefix whose quotient is > 1 (so 1G prints "1024M"), varies its precision
// with the quotient (2 decimals up to 9.995, 1 below 99.95, 0 above, and
// always 0 for K), returns "0" for zero, and below 1K formats the number
// itself with 0 decimals for an integer and 2 for a float.
// `low_precision` and the non-default min_symbol/none_symbol arguments are not
// ported: `smart` passes none of them.
export function formatAutoUnit(value) {
	if (!isNumber(value)) return MISSING;
	if (value === 0) return "0";
	// Python picks 2 decimals for a float and 0 for an int; JS has one number
	// type, so an integral value takes the int branch.
	const fallbackDecimals = Number.isInteger(value) ? 0 : 2;
	for (const [symbol, prefix] of AUTO_UNIT_PREFIXES) {
		const quotient = value / prefix;
		if (quotient > 1) {
			let decimals = 0;
			if (quotient <= 9.995) decimals = 2;
			else if (quotient < 99.95) decimals = 1;
			if (symbol === "K") decimals = 0;
			return `${toFixedHalfEven(quotient, decimals)}${symbol}`;
		}
	}
	return toFixedHalfEven(value, fallbackDecimals);
}
```

`toFixedHalfEven` rather than `toFixed`: Python's float formatting breaks an
exact tie to even, and `toFixedHalfEven` ends with `.toFixed(digits)`, so it
keeps the trailing zero `1.10G` needs. This refines the spec's §7 parenthetical,
which named `toFixed` — the tie rule is the project's standing rule
(`toFixedHalfEven` exists for exactly this), and the trailing zero survives
either way.

- [ ] **Step 4: Run the unit tests**

Run: `uv run pytest tests/test_webui_v5_js.py -q`
Expected: PASS, including the pre-existing `formatBytes` cases — if one of those
changed, `formatAutoUnit` was written over shared code instead of beside it.

- [ ] **Step 5: Write the failing drift test**

Create `tests/test_webui_v5_smart_keys_drift.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's LARGE_VALUE_KEYS is the plugin's.

`smart` formats six attribute keys with auto_unit() and prints every other one
raw (glances/plugins/smart/__init__.py:70-79, :257-259). The browser cannot
import Python, so js/v5/smart_keys.js keeps a copy — and a silent divergence
there changes displayed NUMBERS, not layout. This test makes drift a failure,
like tests/test_webui_v5_degrade_drift.py does for the degradation cascades.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.plugins.smart import LARGE_VALUE_KEYS

_MODULE = Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "smart_keys.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js_keys() -> list[str]:
    script = (
        f"import('{_MODULE.as_posix()}')"
        ".then((m) => process.stdout.write(JSON.stringify([...m.LARGE_VALUE_KEYS].sort())))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_js_copy_matches_the_plugin_constant():
    assert _js_keys() == sorted(LARGE_VALUE_KEYS)


def test_the_copy_is_not_empty():
    """Guard: an empty Set on both sides would satisfy the comparison above."""
    assert len(LARGE_VALUE_KEYS) == 6
```

- [ ] **Step 6: Run it to verify it fails**

Run: `uv run pytest tests/test_webui_v5_smart_keys_drift.py -q`
Expected: FAIL — node cannot resolve `smart_keys.js` (the module does not exist).

- [ ] **Step 7: Create `smart_keys.js`**

```js
// Glances v5 WebUI -- the SMART attribute keys whose raw value is formatted
// with auto_unit() instead of printed as-is.
//
// A mirror of LARGE_VALUE_KEYS (glances/plugins/smart/__init__.py:70-79): the
// browser cannot import Python. tests/test_webui_v5_smart_keys_drift.py fails
// on drift -- this copy decides displayed NUMBERS, not layout, which is why it
// gets a test of its own (the degrade.js precedent).
export const LARGE_VALUE_KEYS = new Set([
	"bytesWritten",
	"bytesRead",
	"dataUnitsRead",
	"dataUnitsWritten",
	"hostReadCommands",
	"hostWriteCommands",
]);
```

- [ ] **Step 8: Run the drift test**

Run: `uv run pytest tests/test_webui_v5_smart_keys_drift.py -q`
Expected: PASS (2 tests).

- [ ] **Step 9: Rebuild, lint, stage**

```bash
cd glances/outputs/static && npm run build && npx eslint js/v5 --ext .js,.vue; cd -
```
Then the v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_smart_keys_drift.py tests/test_webui_v5_render.py -q
git add glances/outputs/static/js/v5/format.js \
        glances/outputs/static/js/v5/smart_keys.js \
        glances/outputs/static/public/glances5.js \
        tests/js/format.test.mjs \
        tests/test_webui_v5_smart_keys_drift.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

Expected: all green. `smart_keys.js` is not imported by anything yet, so the
bundle is unchanged in content — rebuild and stage it anyway; webpack is
deterministic and a no-op diff is the proof.

---

### Task 2: Schema labels for `irq`, `raid` and `connections`

**Files:**
- Modify: `glances/plugins/irq/model_v5.py`, `glances/plugins/raid/model_v5.py`, `glances/plugins/connections/model_v5.py`
- Modify: `glances/plugins/irq/render_curses_v5.py`, `glances/plugins/raid/render_curses_v5.py`, `glances/plugins/connections/render_curses_v5.py`
- Modify: `tests/test_plugin_irq_render_curses_v5.py`, `tests/test_plugin_raid_render_curses_v5.py`, `tests/test_plugin_connections_render_curses_v5.py` (schema plumbing only)

**Interfaces:**
- Consumes: nothing.
- Produces: `short_name` on `irq.irq_rate` (`Rate/s`), `raid.used` (`Used`),
  `raid.available` (`Avail`), `connections.LISTEN` (`Listen`),
  `connections.initiated` (`Initiated`), `connections.ESTABLISHED`
  (`Established`), `connections.terminated` (`Terminated`),
  `connections.nf_conntrack_count` (`Tracked`). Tasks 5 and 6 read them in the
  browser through `labelFor(labels, field)`, which resolves from
  `/api/5/all/info`.

Spec D5: a displayed label lives in the schema, and both surfaces read it from
there. `ports`, `folders` and `smart` display no field label and get no
`short_name`.

- [ ] **Step 1: Write the failing test for the schema**

First add, to each of the three test files, the `PluginModel` import and the
`_SCHEMA` constant described in Step 5 — the new tests below use both. Then add
to `tests/test_plugin_irq_render_curses_v5.py`:

```python
def test_the_rate_header_comes_from_the_schema():
    """G9-7 D5: the column label lives in the schema, so the TUI and the WebUI
    (labelFor -> /api/5/all/info) cannot drift. A hardcoded "Rate/s" in the
    renderer would pass the header assertions and still leave the WebUI
    labelling the column `irq_rate`.
    """
    assert PluginModel.fields_description["irq_rate"]["short_name"] == "Rate/s"
    rows = render(_payload([_irq("0", 12.0)]), _SCHEMA)
    assert "Rate/s" in " ".join(c.text for c in rows[0].cells)
```

Add the equivalent to the `raid` test file (`used` → `Used`, `available` →
`Avail`, asserted on `rows[0]`) and to the `connections` test file (the four
state fields and `nf_conntrack_count`, asserted on the rendered row labels).

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_plugin_irq_render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py -q`
Expected: FAIL with `KeyError: 'short_name'` in each file.

- [ ] **Step 3: Add the `short_name`s**

`glances/plugins/irq/model_v5.py` — in `fields_description["irq_rate"]`, add
`"short_name": "Rate/s",`. Same shape for `raid.used` (`"Used"`),
`raid.available` (`"Avail"`), and the five `connections` fields (`"Listen"`,
`"Initiated"`, `"Established"`, `"Terminated"`, `"Tracked"`). Add nothing else:
no `label`, no `unit` change.

- [ ] **Step 4: Read the labels from the schema in the three renderers**

`irq/render_curses_v5.py` — import `field_label` from
`glances.outputs.curses_renderer_v5` and replace the literal in the header row:

```python
Cell(
    text="{:>{w}}".format(
        field_label(fields_desc.get("irq_rate", {}), "irq_rate", prefer_short=True), w=_RATE_WIDTH
    ),
    color=ColorRole.HEADER,
    bold=True,
),
```

`raid/render_curses_v5.py` — `fields_desc` is optional there, so resolve once at
the top of `render()`:

```python
schema = fields_desc or {}
header = Row(
    cells=[
        Cell(text="RAID disks".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
        Cell(
            text=field_label(schema.get("used", {}), "used", prefer_short=True).rjust(_USED_COL_WIDTH),
            color=ColorRole.HEADER,
            bold=True,
        ),
        Cell(
            text=field_label(schema.get("available", {}), "available", prefer_short=True).rjust(_AVAIL_COL_WIDTH),
            color=ColorRole.HEADER,
            bold=True,
        ),
    ]
)
```

`connections/render_curses_v5.py` — `_ROW_ORDER` keeps the field order and loses
the labels:

```python
# Fixed v4 display order (glances/plugins/connections/__init__.py:205). The
# labels come from the schema (G9-7 D5), so the WebUI cannot drift from them.
_ROW_ORDER: tuple[str, ...] = ("LISTEN", "initiated", "ESTABLISHED", "terminated")
```

and in `render()`:

```python
schema = fields_desc or {}
...
    for key in _ROW_ORDER:
        if key not in payload:
            continue
        rows.append(_stat_row(field_label(schema.get(key, {}), key, prefer_short=True), payload[key]))
...
    tracked_label = field_label(schema.get("nf_conntrack_count", {}), "nf_conntrack_count", prefer_short=True)
    rows.append(_stat_row(tracked_label, value_text, color=role, prominent=prominent))
```

`_stat_row` derives the value width from `len(label)`, so the rendered shape is
unchanged as long as the `short_name`s are exactly the previous literals — which
is why Step 1 asserts the strings.

- [ ] **Step 5: Give the three test files the real schema**

Each file calls `render(payload)` or `render(payload, {})` at every site, which
now resolves labels to the field names. Add, next to the imports:

```python
# one per file, from that plugin's own module:
#   tests/test_plugin_irq_render_curses_v5.py         -> glances.plugins.irq.model_v5
#   tests/test_plugin_raid_render_curses_v5.py        -> glances.plugins.raid.model_v5
#   tests/test_plugin_connections_render_curses_v5.py -> glances.plugins.connections.model_v5
from glances.plugins.irq.model_v5 import PluginModel

# The REAL schema, as production passes it (curses_renderer_v5.py:1459). The
# column labels come from it (field_label), so a hand-written subset without
# `short_name` would test a header no user ever sees.
_SCHEMA = PluginModel.fields_description
```

then pass `_SCHEMA` at every `render(...)` call site in the file. **Not one
`assert` line may change** — if one does, the `short_name` does not match the
literal it replaced.

- [ ] **Step 6: Run the three TUI suites**

Run: `uv run pytest tests/test_plugin_irq_render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py -q`
Expected: PASS, with the three new tests included.

- [ ] **Step 7: Check no assertion moved, then stage**

```bash
git diff -- tests/test_plugin_irq_render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py | grep -E '^-\s*assert' && echo "AN ASSERTION CHANGED -- STOP" || echo "no assertion changed"
uv run pytest tests/test_curses_renderer_v5.py -q
git add glances/plugins/irq/model_v5.py glances/plugins/raid/model_v5.py glances/plugins/connections/model_v5.py \
        glances/plugins/irq/render_curses_v5.py glances/plugins/raid/render_curses_v5.py glances/plugins/connections/render_curses_v5.py \
        tests/test_plugin_irq_render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_connections_render_curses_v5.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

---

### Task 3: An empty `raid` / `smart` collection renders nothing (v4 parity)

**Files:**
- Modify: `glances/plugins/raid/render_curses_v5.py`, `glances/plugins/smart/render_curses_v5.py`
- Modify: `tests/test_plugin_raid_render_curses_v5.py`, `tests/test_plugin_smart_render_curses_v5.py`

**Interfaces:**
- Consumes: Task 2's `schema = fields_desc or {}` line in `raid`.
- Produces: `render()` returning `[]` for an empty collection in both plugins —
  the behaviour Tasks 6's components mirror.

v4 opens both `msg_curse()` with `if not self.stats or self.is_disabled(): return ret`
(`glances/plugins/raid/__init__.py:73-75`). The v5 renderers build their header
before looking at the payload, and the painter drops only a **zero-row** block,
so `[raid] disable=False` on a box with no array paints a bare
`RAID disks  Used  Avail`. Both plugins ship `disable=True`, which is why no
smoke test caught it. This is the one task in the group where an existing
assertion changes on purpose.

- [ ] **Step 1: Invert the two pinned tests**

In `tests/test_plugin_raid_render_curses_v5.py`, replace
`test_empty_returns_header_only` with:

```python
def test_an_empty_collection_renders_nothing():
    """v4 parity (glances/plugins/raid/__init__.py:73-75): no stats, no block.

    Before G9-7 this renderer returned its header row, and the painter drops
    only a zero-row block -- so a box with `[raid] disable=False` and no array
    painted a bare "RAID disks  Used  Avail" line. v4 paints nothing.
    """
    assert render(_payload([]), _SCHEMA) == []
    assert render({}, _SCHEMA) == []
    assert render(None, _SCHEMA) == []
```

and the same in `tests/test_plugin_smart_render_curses_v5.py` (without
`_SCHEMA`, which `smart` does not use — it has no field label).

- [ ] **Step 2: Fix `test_header_labels`, which derives the header from an empty payload**

`tests/test_plugin_raid_render_curses_v5.py::test_header_labels` calls
`render(_payload([]), _SCHEMA)`. Give it one array so there is a header to read;
**the three assertions stay exactly as they are**:

```python
def test_header_labels():
    flat = _flat(render(_payload([_array("md0", "raid1", "active", used=2, available=2)]), _SCHEMA))
    assert "RAID disks" in flat
    assert "Used" in flat
    assert "Avail" in flat
```

Then grep both files for any other empty-payload call site:

```bash
grep -n '_payload(\[\])' tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_smart_render_curses_v5.py
```

Every hit must be inside the new "renders nothing" test.

- [ ] **Step 3: Run the two suites to verify they fail**

Run: `uv run pytest tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_smart_render_curses_v5.py -q`
Expected: FAIL — both new tests report a one-row list instead of `[]`.

- [ ] **Step 4: Hoist the guard above the header in `raid`**

In `glances/plugins/raid/render_curses_v5.py::render`, replace the opening
(header first, guards after) with guards first:

```python
def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    # v4 parity (glances/plugins/raid/__init__.py:73-75): no stats -> no block.
    # The header row is built only once there is an array to put under it;
    # returning it unconditionally painted a bare "RAID disks  Used  Avail" on
    # any box with the plugin enabled and no array (G9-7 spec §8).
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        return []

    schema = fields_desc or {}
    header = Row(...)  # unchanged, Task 2's version
    rows: list[Row] = [header]
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    for item in sorted(items, key=lambda it: str(it.get("name", ""))):
        ...
```

The two old guards (`if not isinstance(payload, dict): return rows` and the
`items` check returning `rows`) disappear — they are what the new opening
replaces.

- [ ] **Step 5: Same in `smart`**

```python
def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    # v4 parity (glances/plugins/smart/__init__.py, msg_curse's `if not
    # self.stats`): no device -> no block, not a bare "SMART disks" line.
    devices = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(devices, list) or not devices:
        return []

    rows: list[Row] = [Row(cells=[Cell(text="SMART disks".ljust(_NAME_COL_WIDTH), color=ColorRole.HEADER, bold=True)])]
    for device in devices:
        ...
```

A `data` list holding only non-dict entries still yields a header with no row —
v4 does the same (its `self.stats` is non-empty), so that case is left alone.

- [ ] **Step 6: Run the two suites**

Run: `uv run pytest tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_smart_render_curses_v5.py -q`
Expected: PASS.

- [ ] **Step 7: Prove the painter is happy and stage**

```bash
uv run pytest tests/test_curses_renderer_v5.py tests/test_curses_v5.py -q
git add glances/plugins/raid/render_curses_v5.py glances/plugins/smart/render_curses_v5.py \
        tests/test_plugin_raid_render_curses_v5.py tests/test_plugin_smart_render_curses_v5.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

Expected: green. A painter test that asserted a `raid`/`smart` header on an
empty payload would fail here — if one does, report it rather than editing it.

---

### Task 4: `ports` and `folders` — the flat family

**Files:**
- Create: `glances/outputs/static/js/v5/PluginPorts.vue`, `glances/outputs/static/js/v5/PluginFolders.vue`
- Modify: `glances/outputs/static/css/v5.css` (add `.gl-strong`)
- Modify: `glances/outputs/static/js/v5/plugins/index.js` (two entries)
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `CollectionBlock` (Task 0), including its `hidden` prop.
- Produces: the registry entries `{ name: "ports", component: PluginPorts, slot: "left", spec: { shape: "collection", required: ["indice"] } }` and `{ name: "folders", component: PluginFolders, slot: "left", spec: { shape: "collection", required: ["path"] } }`, and the `.gl-strong` CSS class (Task 6 does not reuse it; `.gl-subline` comes later).

Registry order after this task — `network, ports, wifi, diskio, fs, folders, sensors`
(the `LEFT_SLOT` order with the not-yet-ported names removed).

- [ ] **Step 1: Write the fixtures**

In `tests/fixtures/webui_render_fixtures.js`, before `ALL_FIXTURES`:

```js
// `ports` — one item per branch of _status_if_host / _status_if_url
// (ports/render_curses_v5.py:57-78). `_levels` is keyed by `indice` and the
// model publishes an entry for every SCANNABLE item, healthy ones included
// (the "ok" tier is v4's green OK). The last item has neither `url` nor
// `host`: it cannot be scanned and the renderer skips it.
const PORTS_FIXTURE = {
	_key: "indice",
	data: [
		{ indice: "port_0", description: "Home Box", host: "192.168.1.1", port: 0, status: 0.0123 },
		{ indice: "port_1", description: "Internet ICMP", host: "8.8.8.8", port: 0, status: 0 },
		{ indice: "port_2", description: "Mail relay", host: "mail", port: 25, status: false },
		{ indice: "port_3", description: "SSH", host: "srv", port: 22, status: true },
		{ indice: "port_4", description: "Still scanning", host: "srv", port: 80, status: null },
		{ indice: "port_5", description: "No gateway", host: null, port: 0, status: null },
		{ indice: "web_1", description: "My Blog", url: "https://blog.example", status: 200 },
		{ indice: "web_2", description: "Broken site", url: "https://down.example", status: "Error" },
		{ indice: "web_3", description: "Web scanning", url: "https://slow.example", status: null },
		{ indice: "nope", description: "Neither url nor host" },
	],
	_levels: {
		port_0: { status: { level: "ok", prominent: false } },
		port_1: { status: { level: "critical", prominent: false } },
		port_2: { status: { level: "critical", prominent: false } },
		port_3: { status: { level: "ok", prominent: false } },
		port_4: { status: { level: "careful", prominent: false } },
		port_5: { status: { level: "careful", prominent: false } },
		web_1: { status: { level: "ok", prominent: false } },
		web_2: { status: { level: "critical", prominent: false } },
		web_3: { status: { level: "careful", prominent: false } },
	},
};

// `folders` — a healthy folder, one whose name is longer than the 24ch cap
// (its ellipsis falls at the START: the TUI keeps the tail), and one the
// plugin could not read. The unreadable one has NO `_levels` entry: the model
// short-circuits its size ladder (folders/model_v5.py::_folder_level), v4
// parity -- no alert, no history, no action.
const FOLDERS_FIXTURE = {
	_key: "path",
	data: [
		{ path: "/tmp", size: 131072000, errno: 0 },
		{ path: "/home/nicolargo/media/library/Videos", size: 18253611008, errno: 0 },
		{ path: "/nonexisting", size: null, errno: 13 },
	],
	_levels: {
		"/tmp": { size: { level: "ok", prominent: false } },
		"/home/nicolargo/media/library/Videos": { size: { level: "warning", prominent: false } },
	},
};
```

and in `ALL_FIXTURES`:

```js
	ports: { ports: PORTS_FIXTURE },
	"ports-empty": { ports: { _key: "indice", data: [], _levels: {} } },
	folders: { folders: FOLDERS_FIXTURE },
	"folders-empty": { folders: { _key: "path", data: [], _levels: {} } },
```

Add both constants to the `module.exports` list at the end of the file only if
the file exports the individual fixtures — it exports the aggregates
(`ALL_FIXTURES` et al.), so nothing else changes there.

Neither plugin gets an `INFO_FIXTURES` entry: neither component reads a schema
label (spec D4 — they have no column header to label).

- [ ] **Step 2: Write the failing render tests**

Append to `tests/test_webui_v5_render.py`, after the G9-6 block:

```python
# ------------------------------------------------------ ports (G9-7 Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_renders_every_status_branch():
    """ports/render_curses_v5.py:57-78 -- the eight status strings, in payload
    order (the TUI does not sort), each next to its description.
    """
    payload = _run_render_probe("ports")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["ports"]]
    assert texts == [
        "Home Box", "12ms",
        "Internet ICMP", "Timeout",
        "Mail relay", "Timeout",
        "SSH", "Open",
        "Still scanning", "Scanning",
        "No gateway", "None",
        "My Blog", "Code 200",
        "Broken site", "Error",
        "Web scanning", "Scanning",
    ], f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_skips_an_item_it_cannot_scan():
    """An item with neither `url` nor `host` is skipped, not rendered with a
    blank status (ports/render_curses_v5.py:100-106)."""
    payload = _run_render_probe("ports")
    assert "Neither url nor host" not in payload["pluginText"]["ports"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_has_no_header_row():
    """G9-7 D4, and ports/render_curses_v5.py's own
    `test_no_title_row_deliberate_do_not_fix`: `ports` reads as one block with
    `network` above it, so it paints no title and no column header. The block
    is still named for assistive technology.
    """
    payload = _run_render_probe("ports")
    assert "ports" not in payload["pluginColumnHeaders"], f"ports must render no <th>: {payload['pluginColumnHeaders']!r}"
    assert "PORTS" not in payload["pluginText"]["ports"], "the title must not be visible"
    assert "aria-label" in payload["pluginAttrs"]["ports"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ports_colours_the_status_from_its_levels_entry():
    """The tier reaches the DOM as a class on the value <span> and nowhere
    else; a healthy port is green ("ok"), v4's OK decoration."""
    payload = _run_render_probe("ports")
    status_classes = [cell["value"] for cell in payload["pluginTableCells"]["ports"]][1::2]
    assert status_classes[0] == "gl-level-ok", f"Home Box is healthy: {status_classes!r}"
    assert status_classes[1] == "gl-level-critical", f"a timeout is critical: {status_classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_ports_collection_is_hidden():
    """The TUI returns [] for an empty list, so the block is not painted."""
    payload = _run_render_probe("ports-empty")
    assert payload["pluginHidden"].get("ports") is True, f"got {payload['pluginHidden']!r}"


# ---------------------------------------------------- folders (G9-7 Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_renders_its_title_and_an_empty_size_header():
    """G9-7 D4: the TUI's FOLDERS line has no size label, and the empty <th>
    keeps the header aligned column by column with the body (the sensors
    precedent)."""
    payload = _run_render_probe("folders")
    assert payload["pluginColumnHeaders"]["folders"] == ["FOLDERS", ""], f"got {payload['pluginColumnHeaders']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_renders_its_sizes():
    payload = _run_render_probe("folders")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["folders"]]
    assert texts[1] == "125.0M", f"got {texts!r}"
    assert texts[3] == "17.0G", f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_marks_an_unreadable_folder_bold_and_untiered():
    """errno != 0 -> a "?" prefix and curses.A_BOLD with NO colour pair. The
    model emits no _levels entry for it, so a tier class here would mean the
    component invented one."""
    payload = _run_render_probe("folders")
    cells = payload["pluginTableCells"]["folders"]
    assert cells[5]["text"].startswith("?"), f"got {cells[5]!r}"
    assert cells[5]["value"] == "gl-strong", f"bold, no tier: {cells[5]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_folders_truncates_a_long_path_from_the_start():
    """The TUI keeps the tail ("_" + path[-23:]), so the ellipsis falls at the
    start; the <bdi> is load-bearing (without it the bidi algorithm moves the
    leading "/" to the end)."""
    payload = _run_render_probe("folders")
    cells = payload["pluginNameCells"]["folders"]
    assert all(cell["hasBdi"] for cell in cells), f"got {cells!r}"
    assert all("gl-truncate-start" in cell["className"] for cell in cells), f"got {cells!r}"
    assert cells[1]["title"] == "/home/nicolargo/media/library/Videos"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_folders_collection_is_hidden():
    payload = _run_render_probe("folders-empty")
    assert payload["pluginHidden"].get("folders") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_webui_v5_render.py -q -k "ports or folders"`
Expected: FAIL — `KeyError: 'ports'` / `'folders'`: neither component is
registered, so neither renders.

- [ ] **Step 4: Write `PluginPorts.vue`**

```vue
<template>
	<CollectionBlock title="PORTS" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<!-- No #head slot: `ports` has NO title and NO column header in the TUI
		(ports/render_curses_v5.py, test_no_title_row_deliberate_do_not_fix). It
		sits under `network` and the two read as one block; the missing header is
		that continuity, not an oversight. CollectionBlock renders no <thead>
		when the slot is absent, and the title reaches the page as the
		aria-label only (G9-7 D4). -->
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.indice">
					<td>
						<span class="gl-name gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'status')">{{ statusText(item) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { formatFixed0 } from "./format.js";

export default {
	name: "PluginPorts",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: `ports` shows no schema label (no column header).
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Payload order -- the TUI does not sort. An item with neither `url`
		// nor `host` cannot be scanned and is skipped, never rendered with a
		// blank status (ports/render_curses_v5.py:100-106).
		rows() {
			return (this.payload?.data || []).filter((item) => "url" in item || "host" in item);
		},
	},
	methods: {
		cellClassFor,
		nameOf(item) {
			return String(item.description || "");
		},
		statusText(item) {
			return "url" in item ? this.webStatus(item) : this.hostStatus(item);
		},
		// v4 `set_status_if_url` (ports/render_curses_v5.py:70-78).
		webStatus(item) {
			const status = item.status;
			if (typeof status === "number") return `Code ${status}`;
			if (status === null || status === undefined) return "Scanning";
			// The scanner writes the literal string "Error" when requests raises.
			return String(status);
		},
		// v4 `set_status_if_host` (ports/render_curses_v5.py:57-67). The order
		// matters: `true` is checked before the number branch, and `status === 0
		// || status === false` reproduces Python's `status == 0`, which is true
		// for both.
		hostStatus(item) {
			if (item.host === null || item.host === undefined) return "None";
			const status = item.status;
			if (status === null || status === undefined) return "Scanning";
			if (status === true) return "Open";
			if (status === 0 || status === false) return "Timeout";
			// The RTT is stored in seconds and displayed in milliseconds.
			return `${formatFixed0(status * 1000)}ms`;
		},
	},
};
</script>

<style scoped>
/* The TUI's description width (ports/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 25ch;
}
</style>
```

- [ ] **Step 5: Add `.gl-strong` to `css/v5.css`**

Next to `.gl-header`:

```css
/* Bold with NO tier colour -- the TUI's curses.A_BOLD without a colour pair
 * (glances/outputs/glances_colors.py:167). `folders` paints a folder it could
 * not read this way: the model emits no `_levels` entry for it, so a tier
 * class here would be one the payload never carried. */
.gl-strong {
  font-weight: var(--gl-weight-bold);
}
```

- [ ] **Step 6: Write `PluginFolders.vue`**

```vue
<template>
	<CollectionBlock title="FOLDERS" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's FOLDERS line carries no size label; the empty <th>
			keeps the header aligned column by column with the body (the sensors
			precedent). G9-7 D4. -->
			<tr>
				<th class="gl-header">FOLDERS</th>
				<th class="gl-header gl-num"></th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.path">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="item.path"><bdi>{{ item.path }}</bdi></span>
					</td>
					<td class="gl-num">
						<span :class="sizeClass(item)">{{ sizeText(item) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { formatBytes } from "./format.js";

export default {
	name: "PluginFolders",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: the size column has no header to label.
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Payload order -- the TUI does not sort, and it drops no row: it keeps
		// every dict item (folders/render_curses_v5.py:93-94) and coalesces a
		// missing path to "" inside the loop. Filtering on `path` here would
		// invent a rule the TUI does not have.
		rows() {
			return (this.payload?.data || []).filter((item) => item && typeof item === "object");
		},
	},
	methods: {
		// The "?" is a rendering decision, not a formatting one: it marks a
		// folder the plugin could not read (errno != 0), and the formatter
		// must stay the plain byte formatter.
		sizeText(item) {
			return `${item.errno ? "?" : ""}${formatBytes(item.size)}`;
		},
		// v4 parity: a broken folder short-circuits the size ladder and gets no
		// `_levels` entry, so it is bold with no colour -- never alert-coloured.
		sizeClass(item) {
			return item.errno ? "gl-strong" : cellClassFor(this.payload, item, "size");
		},
	},
};
</script>

<style scoped>
/* The TUI's path width (folders/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 24ch;
}
</style>
```

- [ ] **Step 7: Register both plugins**

In `glances/outputs/static/js/v5/plugins/index.js`: import both components and
insert their entries **in `LEFT_SLOT` order** — `ports` right after `network`,
`folders` right after `fs`:

```js
	{
		name: "ports",
		component: PluginPorts,
		slot: "left",
		spec: { shape: "collection", required: ["indice"] },
	},
```
```js
	{
		name: "folders",
		component: PluginFolders,
		slot: "left",
		spec: { shape: "collection", required: ["path"] },
	},
```

- [ ] **Step 8: Update the hardcoded registry list**

`tests/test_webui_v5_render.py::test_an_unreadable_pluginslist_renders_the_whole_registry`
asserts the exact ordered list of rendered names. It becomes:

```python
    assert payload["pluginNames"] == [
        "system", "ip", "uptime", "cloud", "now",
        "cpu", "gpu", "mem", "memswap", "load",
        "network", "ports", "wifi", "diskio", "fs", "folders", "sensors",
    ], f"expected the whole registry, got {payload['pluginNames']!r}"
```

Keep the file's existing one-name-per-line formatting if `ruff format` asks for
it; run `uv run ruff format tests/test_webui_v5_render.py` at the end.

- [ ] **Step 9: Rebuild and run**

```bash
cd glances/outputs/static && npm run build && npx eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -q
```
Expected: all green, including the drift guard
`test_every_slot_orders_its_plugins_like_the_tui` (it reads the real
`LEFT_SLOT`, so a misplaced entry fails it) and
`test_every_collection_block_keeps_its_root_attributes`. Then the v4 bundle
identity check — both IDENTICAL.

- [ ] **Step 10: Stage**

```bash
git add glances/outputs/static/js/v5/PluginPorts.vue glances/outputs/static/js/v5/PluginFolders.vue \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/css/v5.css \
        glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

---

### Task 5: `connections` and `irq` — the scalar and the ranked

**Files:**
- Create: `glances/outputs/static/js/v5/PluginConnections.vue`, `glances/outputs/static/js/v5/PluginIrq.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js` (two entries)
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `CollectionBlock` (Task 0) for `irq`; Task 2's `short_name`s for both.
- Produces: the registry entries `{ name: "connections", component: PluginConnections, slot: "left", spec: { shape: "scalar", required: [] } }` and `{ name: "irq", component: PluginIrq, slot: "left", spec: { shape: "collection", required: ["irq_line"] } }`.

`connections` is the group's only **scalar**: it renders with the existing
`.gl-stat-grid` + `<dl>` pattern, like `PluginLoad.vue`, not with
`CollectionBlock`.

- [ ] **Step 1: Write the fixtures**

In `INFO_FIXTURES` (the `short_name`s Task 2 added — copied here, which is what
makes a component reading the wrong field visible):

```js
	connections: {
		LISTEN: { short_name: "Listen" },
		initiated: { short_name: "Initiated" },
		ESTABLISHED: { short_name: "Established" },
		terminated: { short_name: "Terminated" },
		nf_conntrack_count: { short_name: "Tracked" },
		nf_conntrack_max: {},
		nf_conntrack_percent: {},
	},
	irq: { irq_line: {}, irq_rate: { short_name: "Rate/s" } },
```

Then, before `ALL_FIXTURES`:

```js
// `connections` is a SCALAR payload: the four state counters, the conntrack
// pair, and the two flags that decide which half renders
// (connections/render_curses_v5.py:80-100). Only the Tracked row is coloured,
// from nf_conntrack_percent.
const CONNECTIONS_FIXTURE = {
	net_connections_enabled: true,
	nf_conntrack_enabled: true,
	LISTEN: 3,
	initiated: 0,
	ESTABLISHED: 12,
	terminated: 204,
	nf_conntrack_count: 512,
	nf_conntrack_max: 1024,
	nf_conntrack_percent: 50.0,
	_levels: { nf_conntrack_percent: { level: "careful", prominent: false } },
};

// Seven IRQ lines, one of them on its first cycle (a null rate). The model
// publishes every line -- a documented v4 divergence, so exporters get the
// whole series -- and the TUI ranks and cuts to five
// (irq/render_curses_v5.py:38-58), which the component must reproduce.
const IRQ_FIXTURE = {
	_key: "irq_line",
	data: [
		{ irq_line: "0", irq_rate: 12.0 },
		{ irq_line: "LOC", irq_rate: 340.0 },
		{ irq_line: "NMI", irq_rate: 0.0 },
		{ irq_line: "1_i8042", irq_rate: 95.0 },
		{ irq_line: "RES", irq_rate: 501.0 },
		{ irq_line: "CAL", irq_rate: 7.0 },
		{ irq_line: "TLB", irq_rate: null },
	],
	_levels: {},
};
```

and in `ALL_FIXTURES`:

```js
	connections: { connections: CONNECTIONS_FIXTURE },
	// Netfilter conntrack off: the four state rows, no Tracked row.
	"connections-no-conntrack": {
		connections: { ...CONNECTIONS_FIXTURE, nf_conntrack_enabled: false },
	},
	// psutil's net_connections() unavailable (the disabled-probe latch): only
	// the Tracked row survives.
	"connections-no-net": {
		connections: { ...CONNECTIONS_FIXTURE, net_connections_enabled: false },
	},
	"connections-off": {
		connections: { net_connections_enabled: false, nf_conntrack_enabled: false, _levels: {} },
	},
	irq: { irq: IRQ_FIXTURE },
	"irq-empty": { irq: { _key: "irq_line", data: [], _levels: {} } },
```

- [ ] **Step 2: Write the failing render tests**

```python
# ------------------------------------------------ connections (G9-7 Task 5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_renders_the_tui_rows_in_order():
    """connections/render_curses_v5.py:80-100 -- the title, then the four state
    counters in the TUI's fixed order, then Tracked as `count/max`. The labels
    come from the schema (G9-7 D5), so this also proves the component reads
    /api/5/all/info rather than hardcoding them.
    """
    payload = _run_render_probe("connections")
    grid = payload["pluginGrid"]["connections"]
    assert grid == [[
        ["TCP CONNECTIONS", ""],
        ["Listen", "3"],
        ["Initiated", "0"],
        ["Established", "12"],
        ["Terminated", "204"],
        ["Tracked", "512/1024"],
    ]], f"got {grid!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_colours_only_the_tracked_row():
    """The Tracked row is the only coloured one, from nf_conntrack_percent."""
    payload = _run_render_probe("connections")
    classes = payload["pluginValueClasses"]["connections"]
    assert classes[-1] == "gl-level-careful", f"got {classes!r}"
    assert set(classes[:-1]) == {""}, f"no other row may be coloured: {classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_without_conntrack_drops_the_tracked_row():
    payload = _run_render_probe("connections-no-conntrack")
    labels = [pair[0] for pair in payload["pluginGrid"]["connections"][0]]
    assert labels == ["TCP CONNECTIONS", "Listen", "Initiated", "Established", "Terminated"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_without_net_connections_keeps_only_tracked():
    payload = _run_render_probe("connections-no-net")
    labels = [pair[0] for pair in payload["pluginGrid"]["connections"][0]]
    assert labels == ["TCP CONNECTIONS", "Tracked"], f"got {labels!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_connections_with_both_probes_off_is_hidden():
    """The TUI returns [] when neither probe is enabled."""
    payload = _run_render_probe("connections-off")
    assert payload["pluginHidden"].get("connections") is True, f"got {payload['pluginHidden']!r}"


# -------------------------------------------------------- irq (G9-7 Task 5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_irq_keeps_the_five_busiest_lines_ranked():
    """Ranking lives in the renderer, not the model: model_v5 publishes every
    line (a v4 divergence made for exporters), and the TUI sorts by rate
    descending and keeps five (irq/render_curses_v5.py:48-58). A null rate
    sorts last instead of throwing.
    """
    payload = _run_render_probe("irq")
    texts = [cell["text"] for cell in payload["pluginTableCells"]["irq"]]
    assert texts == [
        "RES", "501",
        "LOC", "340",
        "1_i8042", "95",
        "0", "12",
        "CAL", "7",
    ], f"got {texts!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_irq_labels_its_rate_column_from_the_schema():
    payload = _run_render_probe("irq")
    assert payload["pluginColumnHeaders"]["irq"] == ["IRQ", "Rate/s"], f"got {payload['pluginColumnHeaders']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_irq_collection_is_hidden():
    payload = _run_render_probe("irq-empty")
    assert payload["pluginHidden"].get("irq") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run pytest tests/test_webui_v5_render.py -q -k "connections or irq"`
Expected: FAIL — neither plugin is registered.

- [ ] **Step 4: Write `PluginConnections.vue`**

```vue
<template>
	<article v-show="!hidden" class="gl-plugin" aria-label="TCP CONNECTIONS">
		<!-- aria-label: once loaded the title is a <dt>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">TCP CONNECTIONS</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<!-- The TUI's title line carries no value, so the pair that opens
				the grid has an empty <dd> -- the shape PluginLoad.vue established,
				where the core count fills that slot. -->
				<dt class="gl-header">TCP CONNECTIONS</dt>
				<dd></dd>
				<template v-for="row in rows" :key="row.field">
					<dt class="gl-header">{{ labelFor(labels, row.field) }}</dt>
					<dd :class="row.className">{{ row.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";
import { formatFixed0 } from "./format.js";

// The TUI's fixed display order (connections/render_curses_v5.py:48-53). Each
// row is skipped when its key is ABSENT from the payload -- absent, not null.
const STATE_FIELDS = ["LISTEN", "initiated", "ESTABLISHED", "terminated"];

export default {
	name: "PluginConnections",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Neither probe enabled -> the TUI returns [] and the block is not
		// painted. Before the first payload the block still says "loading…",
		// like every other left-column block.
		hidden() {
			if (!this.payload || this.error) return false;
			return !this.payload.net_connections_enabled && !this.payload.nf_conntrack_enabled;
		},
		rows() {
			const payload = this.payload || {};
			const rows = [];
			if (payload.net_connections_enabled) {
				for (const field of STATE_FIELDS) {
					if (field in payload) rows.push({ field, value: String(payload[field]), className: "" });
				}
			}
			// Both values must be present: conntrack can be enabled and still
			// have nothing to report (connections/render_curses_v5.py:95).
			if (
				payload.nf_conntrack_enabled &&
				payload.nf_conntrack_count !== null && payload.nf_conntrack_count !== undefined &&
				payload.nf_conntrack_max !== null && payload.nf_conntrack_max !== undefined
			) {
				rows.push({
					field: "nf_conntrack_count",
					value: `${formatFixed0(payload.nf_conntrack_count)}/${formatFixed0(payload.nf_conntrack_max)}`,
					className: levelClass(scalarLevel(payload, "nf_conntrack_percent")),
				});
			}
			return rows;
		},
	},
	methods: { labelFor },
};
</script>
```

- [ ] **Step 5: Write `PluginIrq.vue`**

```vue
<template>
	<CollectionBlock title="IRQ" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's label. -->
			<tr>
				<th class="gl-header">IRQ</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "irq_rate") }}</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.irq_line">
					<td>
						<span class="gl-name gl-truncate" :title="item.irq_line">{{ item.irq_line }}</span>
					</td>
					<td class="gl-num">
						<span>{{ formatFixed0(item.irq_rate) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { labelFor } from "./labels.js";
import { formatFixed0 } from "./format.js";

// The TUI keeps the five busiest lines (irq/render_curses_v5.py _TOP_N).
const TOP_N = 5;

export default {
	name: "PluginIrq",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Ranking lives HERE, as it does in the TUI renderer: model_v5
		// publishes every IRQ line so exporters get the complete series, and
		// the display keeps the busiest five. A null rate (an item's first
		// cycle) sorts last rather than throwing. Copy the array first --
		// sort() mutates, and the payload is shared with every other consumer.
		rows() {
			return [...(this.payload?.data || [])]
				.sort((a, b) => (b.irq_rate || 0) - (a.irq_rate || 0))
				.slice(0, TOP_N);
		},
	},
	methods: { labelFor, formatFixed0 },
};
</script>

<style scoped>
/* The TUI's IRQ-line width (irq/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 24ch;
}
</style>
```

- [ ] **Step 6: Register both, and grow the registry list**

Insert in `LEFT_SLOT` order: `connections` right after `wifi`, `irq` right after
`fs`. The hardcoded list in
`test_an_unreadable_pluginslist_renders_the_whole_registry` becomes:

```python
        "network", "ports", "wifi", "connections", "diskio", "fs", "irq", "folders", "sensors",
```
(the header and top rows above it are unchanged).

- [ ] **Step 7: Rebuild, run, stage**

```bash
cd glances/outputs/static && npm run build && npx eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py -q
```
Expected: green, `test_every_slot_orders_its_plugins_like_the_tui` included.
Then the v4 bundle identity check, then:
```bash
git add glances/outputs/static/js/v5/PluginConnections.vue glances/outputs/static/js/v5/PluginIrq.vue \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

---

### Task 6: `raid` and `smart` — the hierarchical family, and the probe extension they need

**Files:**
- Create: `glances/outputs/static/js/v5/PluginRaid.vue`, `glances/outputs/static/js/v5/PluginSmart.vue`
- Modify: `glances/outputs/static/css/v5.css` (add `.gl-subline`)
- Modify: `tests/fixtures/webui_render_probe.js` (new `pluginRowGroups` output)
- Modify: `glances/outputs/static/js/v5/plugins/index.js` (two entries)
- Modify: `tests/fixtures/webui_render_fixtures.js`, `tests/test_webui_v5_render.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `CollectionBlock` (Task 0), `formatAutoUnit` and `LARGE_VALUE_KEYS` (Task 1), the `raid` `short_name`s (Task 2), the empty-collection behaviour (Task 3).
- Produces: the registry entries `{ name: "raid", component: PluginRaid, slot: "left", spec: { shape: "collection", required: ["name"] } }` and `{ name: "smart", component: PluginSmart, slot: "left", spec: { shape: "collection", required: ["name"] } }`, and the probe's `pluginRowGroups` output (nothing later in this group consumes it).

Spec D3: one `<tbody>` per array/device, and the TUI's `└─` / `├─` glyphs kept
verbatim.

- [ ] **Step 1: Extend the probe with `pluginRowGroups`**

In `tests/fixtures/webui_render_probe.js`, add the field to the `collect()`
result object, next to `pluginTableCells`:

```js
		// Each <tbody> of a plugin as its rows' raw cell texts:
		// [[[cell, cell], ...], ...], one inner list per row group. `raid` and
		// `smart` emit one group per array/device (G9-7 D3), and this is the
		// only way a test can see that grouping rather than a flat table. NOT
		// trimmed, unlike pluginTableCells: `smart`'s attribute names carry the
		// TUI's leading-space indent, and trimming would hide it.
		pluginRowGroups: {},
```

and, in the per-article block:

```js
				const groups = findAllByTag(article, "TBODY");
				if (groups.length) {
					result.pluginRowGroups[name] = groups.map((tbody) =>
						findAllByTag(tbody, "TR").map((tr) => findAllByTag(tr, "TD").map((td) => td.textContent)),
					);
				}
```

- [ ] **Step 2: Write the fixtures**

```js
// `raid` -- one array per branch of the renderer, plus md12, which is BOTH
// inactive and degraded: the two sub-line groups are not exclusive, and the
// TUI emits them in this order (raid/render_curses_v5.py:126-140).
const RAID_FIXTURE = {
	_key: "name",
	data: [
		{ name: "md0", type: "raid1", status: "active", used: 2, available: 2, components: { sda1: "0", sdb1: "1" }, config: "UU" },
		{ name: "md9", type: "raid0", status: "active", used: null, available: null, components: { sdc1: "0", sdd1: "1" }, config: "UU" },
		{ name: "md12", type: "raid1", status: "inactive", used: 1, available: 2, components: { sde1: "0", sdf1: "1" }, config: "U_" },
		{ name: "md4", type: "raid5", status: "active", used: 2, available: 3, components: {}, config: "UU_" },
	],
	_levels: {
		md0: { status: { level: "ok", prominent: false } },
		md9: { status: { level: "ok", prominent: false } },
		md12: { status: { level: "critical", prominent: false } },
		md4: { status: { level: "warning", prominent: false } },
	},
};

// `smart` -- one device, one attribute per branch of _attr_value_text:
// a plain integer, a zero, a LARGE_VALUE_KEYS raw formatted with auto_unit(),
// and a null raw (rendered as an empty cell).
const SMART_FIXTURE = {
	_key: "name",
	data: [
		{
			name: "/dev/sda Samsung SSD 850",
			attributes: [
				{ name: "Power_On_Hours", key: "powerOnHours", raw: 12345 },
				{ name: "Reallocated_Sector_Ct", key: "reallocatedSectorCt", raw: 0 },
				{ name: "Data_Units_Written", key: "dataUnitsWritten", raw: 5307033647 },
				{ name: "Unknown_Attribute", key: "unknown", raw: null },
			],
		},
	],
	_levels: {},
};
```

and in `ALL_FIXTURES`:

```js
	raid: { raid: RAID_FIXTURE },
	"raid-empty": { raid: { _key: "name", data: [], _levels: {} } },
	smart: { smart: SMART_FIXTURE },
	"smart-empty": { smart: { _key: "name", data: [], _levels: {} } },
```

- [ ] **Step 3: Write the failing render tests**

```python
# ------------------------------------------------------- raid (G9-7 Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_groups_each_array_with_its_sub_lines():
    """G9-7 D3: one <tbody> per array, sub-lines inside it, the TUI's glyphs
    kept. Arrays are sorted by name as strings (raid/render_curses_v5.py:96),
    which puts md12 before md4.

    md12 is inactive AND degraded: both sub-line groups are emitted, in that
    order -- they are not exclusive, and a component that treated them as an
    if/else would drop the second.
    """
    payload = _run_render_probe("raid")
    groups = payload["pluginRowGroups"]["raid"]
    assert groups == [
        [["RAID1 md0", "2", "2"]],
        [
            ["RAID1 md12", "", ""],
            ["└─ Status inactive"],
            ["   ├─ disk 0: sde1"],
            ["   └─ disk 1: sdf1"],
            ["└─ Degraded mode"],
            ["   └─ UA"],
        ],
        [["RAID5 md4", "2", "3"], ["└─ Degraded mode"], ["   └─ UUA"]],
        [["RAID0 md9", "2", "-"]],
    ], f"got {groups!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_labels_its_columns_from_the_schema():
    payload = _run_render_probe("raid")
    assert payload["pluginColumnHeaders"]["raid"] == ["RAID disks", "Used", "Avail"], (
        f"got {payload['pluginColumnHeaders']!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_raid_colours_the_values_and_the_status_lines_from_levels():
    """The tier reaches the DOM as a class on the value <span>, never on the
    <td> -- a prominent badge's background would otherwise fill the whole cell.
    `pluginTableCells[i]["value"]` is that span's class list;
    `pluginValueClasses` would give the cell's ("gl-num") and prove nothing.
    """
    payload = _run_render_probe("raid")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["raid"]]
    assert any("gl-level-critical" in (span or "") for span in spans), f"md12 must be critical: {spans!r}"
    assert any("gl-level-warning" in (span or "") for span in spans), f"md4 must be warning: {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_raid_collection_is_hidden():
    """v4 parity, and Task 3's TUI fix: no array, no block -- not a bare
    "RAID disks  Used  Avail" header."""
    payload = _run_render_probe("raid-empty")
    assert payload["pluginHidden"].get("raid") is True, f"got {payload['pluginHidden']!r}"


# ------------------------------------------------------ smart (G9-7 Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_smart_groups_each_device_with_its_attributes():
    """G9-7 D3 and smart/render_curses_v5.py: a device row, then one row per
    attribute -- the name indented by the TUI's leading space, underscores
    rendered as spaces, the raw value right-aligned. A LARGE_VALUE_KEYS raw
    goes through auto_unit() (5307033647 -> "4.94G"); everything else is
    printed as-is; a null raw renders an empty cell.
    """
    payload = _run_render_probe("smart")
    groups = payload["pluginRowGroups"]["smart"]
    assert groups == [
        [
            ["/dev/sda Samsung SSD 850"],
            [" Power On Hours", "12345"],
            [" Reallocated Sector Ct", "0"],
            [" Data Units Written", "4.94G"],
            [" Unknown Attribute", ""],
        ],
    ], f"got {groups!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_smart_never_colours_a_cell():
    """v4 `smart` is display-only: EMITS_ALERTS is False and no field is
    watched, so no cell may carry a tier class."""
    payload = _run_render_probe("smart")
    spans = [cell["value"] for cell in payload["pluginTableCells"]["smart"]]
    assert not any("gl-level-" in (span or "") for span in spans), f"smart must not colour anything: {spans!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_smart_collection_is_hidden():
    payload = _run_render_probe("smart-empty")
    assert payload["pluginHidden"].get("smart") is True, f"got {payload['pluginHidden']!r}"
```

- [ ] **Step 4: Run them to verify they fail**

Run: `uv run pytest tests/test_webui_v5_render.py -q -k "raid or smart"`
Expected: FAIL — neither plugin is registered.

- [ ] **Step 5: Add `.gl-subline` to `css/v5.css`**

```css
/* A sub-line of a hierarchical block: `raid`'s tree lines and `smart`'s
 * attribute names. `white-space: pre` keeps the TUI's leading spaces, which
 * HTML would otherwise collapse into one -- the indent is what makes the tree
 * readable, and the glyphs are the TUI's own (G9-7 D3). */
.gl-subline {
  white-space: pre;
}
```

- [ ] **Step 6: Write `PluginRaid.vue`**

```vue
<template>
	<CollectionBlock title="RAID disks" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">RAID disks</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "used") }}</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "available") }}</th>
			</tr>
		</template>
		<template #body>
			<!-- One <tbody> per array (G9-7 D3): the sub-lines belong to their
			array, and grouping is what lets a test - and a stylesheet - tell
			them apart from a flat table. -->
			<tbody v-for="array in rows" :key="array.name">
				<tr>
					<td>
						<span class="gl-name gl-truncate" :title="array.title">{{ array.title }}</span>
					</td>
					<!-- An array that is neither raid0-active nor active renders a
					name-only row in the TUI. Here it keeps two EMPTY cells rather
					than a colspan: both look the same, but empty cells keep the
					three-column grid a colspan would let the name spread under. -->
					<td class="gl-num"><span :class="array.className">{{ array.used }}</span></td>
					<td class="gl-num"><span :class="array.className">{{ array.avail }}</span></td>
				</tr>
				<tr v-for="(line, index) in array.subLines" :key="index">
					<td colspan="3"><span class="gl-subline" :class="line.className">{{ line.text }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { labelFor } from "./labels.js";
import { byText } from "./rows.js";

export default {
	name: "PluginRaid",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// sorted(items, key=lambda it: str(it.get("name", ""))) -- code-unit
		// order, so "md12" comes before "md4". A nameless array is skipped.
		rows() {
			return [...(this.payload?.data || [])].filter((item) => item.name).sort(byText("name")).map((item) => this.describe(item));
		},
	},
	methods: {
		labelFor,
		describe(item) {
			// `type` null renders UNKNOWN -- v4 parity.
			const type = item.type === null || item.type === undefined ? "UNKNOWN" : String(item.type).toUpperCase();
			const className = cellClassFor(this.payload, item, "status");
			const components = item.components || {};
			let used = "";
			let avail = "";
			if (item.type === "raid0" && item.status === "active") {
				// raid0 has no redundancy: the TUI shows the component count and
				// a dash.
				used = String(Object.keys(components).length);
				avail = "-";
			} else if (item.status === "active") {
				used = String(item.used);
				avail = String(item.available);
			}
			return { name: item.name, title: `${type} ${item.name}`, used, avail, className, subLines: this.subLines(item, className) };
		},
		subLines(item, className) {
			const lines = [];
			const components = item.components || {};
			if (item.status === "inactive") {
				lines.push({ text: `└─ Status ${item.status}`, className });
				const names = Object.keys(components).sort();
				names.forEach((component, index) => {
					const tree = index === names.length - 1 ? "└─" : "├─";
					lines.push({ text: `   ${tree} disk ${components[component]}: ${component}`, className: "" });
				});
			}
			// NOT an else: an inactive array can also be degraded, and the TUI
			// emits both groups, in this order.
			if (
				item.type !== "raid0" &&
				item.used !== null && item.used !== undefined &&
				item.available !== null && item.available !== undefined &&
				item.used < item.available
			) {
				lines.push({ text: "└─ Degraded mode", className });
				const config = String(item.config || "");
				// The layout line is dropped when it is too wide for the block --
				// v4's `len(config) < 17`. "_" marks a missing disk and is shown
				// as "A", as v4 does.
				if (config.length < 17) lines.push({ text: `   └─ ${config.replace(/_/g, "A")}`, className: "" });
			}
			return lines;
		},
	},
};
</script>

<style scoped>
/* The TUI's array-name width (raid/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 18ch;
}
</style>
```

- [ ] **Step 7: Write `PluginSmart.vue`**

```vue
<template>
	<CollectionBlock title="SMART disks" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header row is ONE cell, the title; the empty <th> keeps
			the header aligned column by column with the body (the sensors and
			folders precedent). -->
			<tr>
				<th class="gl-header">SMART disks</th>
				<th class="gl-header gl-num"></th>
			</tr>
		</template>
		<template #body>
			<!-- One <tbody> per device (G9-7 D3). -->
			<tbody v-for="device in rows" :key="device.name">
				<tr>
					<!-- The device line spans both columns: it has no value. Its
					own cap is the block's full width, so it is set inline rather
					than through the component's --gl-name-width. -->
					<td colspan="2">
						<span class="gl-name gl-truncate" style="--gl-name-width: 34ch" :title="device.name">{{ device.name }}</span>
					</td>
				</tr>
				<!-- Keyed by position: an attribute name is not guaranteed unique
				across a device's list, and these rows are plain text with no
				component state. -->
				<tr v-for="(attr, index) in device.attributes" :key="index">
					<td>
						<span class="gl-name gl-truncate gl-subline" :title="attr.name">{{ attr.name }}</span>
					</td>
					<td class="gl-num"><span>{{ attr.value }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { formatAutoUnit } from "./format.js";
import { LARGE_VALUE_KEYS } from "./smart_keys.js";

export default {
	name: "PluginSmart",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: `smart` has no column label (no value header).
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Payload order -- the plugin sorts the attributes itself (v4's own
		// order) and the TUI renderer does not re-sort.
		rows() {
			return (this.payload?.data || []).map((device) => ({
				name: String(device.name || ""),
				attributes: (device.attributes || []).map((attr) => ({
					// The leading space is the TUI's indent; .gl-subline keeps it.
					name: ` ${String(attr.name ?? "").replace(/_/g, " ")}`,
					value: this.attrValue(attr),
				})),
			}));
		},
	},
	methods: {
		// v4 `_attr_value_text`: auto_unit() for the six large-value keys, the
		// raw value otherwise, and an empty cell when there is none. NOT
		// formatBytes: auto_unit() is a different algorithm (see format.js).
		attrValue(attr) {
			if (attr.raw === null || attr.raw === undefined) return "";
			return LARGE_VALUE_KEYS.has(attr.key) ? formatAutoUnit(attr.raw) : String(attr.raw);
		},
	},
};
</script>

<style scoped>
/* The TUI's attribute-name width (smart/render_curses_v5.py _NAME_COL_WIDTH).
 * The device line overrides it inline: its own cap is the block's width. */
.gl-plugin {
	--gl-name-width: 25ch;
}
</style>
```

- [ ] **Step 8: Register both, and close the registry list**

`raid` and `smart` go right after `folders`, in `LEFT_SLOT` order. The hardcoded
list in `test_an_unreadable_pluginslist_renders_the_whole_registry` reaches its
final, 21-name form:

```python
    assert payload["pluginNames"] == [
        "system", "ip", "uptime", "cloud", "now",
        "cpu", "gpu", "mem", "memswap", "load",
        "network", "ports", "wifi", "connections", "diskio", "fs",
        "irq", "folders", "raid", "smart", "sensors",
    ], f"expected the whole registry, got {payload['pluginNames']!r}"
```

- [ ] **Step 9: Rebuild, run, stage**

```bash
cd glances/outputs/static && npm run build && npx eslint js/v5 --ext .js,.vue; cd -
uv run pytest tests/test_webui_v5_render.py tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py -q
```
Expected: green. Then the v4 bundle identity check, then:
```bash
git add glances/outputs/static/js/v5/PluginRaid.vue glances/outputs/static/js/v5/PluginSmart.vue \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/css/v5.css \
        glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_probe.js tests/fixtures/webui_render_fixtures.js tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' && echo "REPORT THE LINES ABOVE" || echo "clean"
```

---

### Task 7: Verify against a real server, and close

**Files:** none changed unless a defect is found (then: the file that holds it,
and the test that should have caught it).

**Interfaces:**
- Consumes: everything.
- Produces: the evidence the group is done, in the SDD workspace.

- [ ] **Step 1: Run the whole suite**

```bash
uv run pytest -q 2>&1 | tail -15
```

Expected: no failure. `tests/test_restful.py::test_050/051` are flaky by
construction — re-run them alone before believing a failure, and never bisect
them. `tests/test_mcp.py` fails when a stale server squats port 61235
(`ss -lptn 'sport = :61235'`).

- [ ] **Step 2: Serve the six blocks from a real server**

The three plugins that ship `disable=True` need a scratch config; the other
three need something to show. Write
`.superpowers/sdd/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2/g9-7.conf`:

```ini
[irq]
disable=False
[raid]
disable=False
[smart]
disable=False
[folders]
disable=False
folder_1_path=/tmp
folder_1_careful=2500
folder_2_path=/nonexisting
[ports]
disable=False
port_1_host=127.0.0.1
port_1_port=22
port_1_description=Local SSH
web_1_url=https://example.com
web_1_description=Example
[connections]
disable=False
```

then:

```bash
uv run python -m glances.main_v5 -s -C .superpowers/sdd/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2/g9-7.conf
```

The v5 server is `python -m glances.main_v5 -s`, never `python -m glances`, and
`-s` is the flag that binds the socket and serves the Web UI — there is no `-w`
in v5. Open
`http://localhost:61208/` and, in a second terminal, the TUI on the same config
(`uv run python -m glances.main_v5 -C <same file>`) for a side-by-side read.

- [ ] **Step 3: Compare each block against the terminal**

For each of the six, check the page against the TUI beside it:

| Block | What must match |
|---|---|
| `ports` | no title, no column header; each row's status string and its colour, healthy ones green |
| `connections` | the row order, `Tracked` as `count/max` and the only coloured row |
| `irq` | five rows, the busiest first, `Rate/s` as the column label |
| `folders` | `/nonexisting` bold with a `?` and no tier colour; a long path's ellipsis at the START |
| `raid` | absent if the box has no array — **not** a bare header (Task 3); otherwise the sub-lines with their glyphs and indent |
| `smart` | absent unless the server can read SMART data; otherwise a device line then its attributes, indented |

Capture the page for the record:

```bash
D=.superpowers/sdd/2026-09-12-glances-v5-g9-7-webui-left-sidebar-2
google-chrome --headless --disable-gpu --screenshot=$D/g9-7-left-column.png --window-size=1600,1200 http://localhost:61208/
```

- [ ] **Step 4: Check the page at a phone width and in both themes**

Resize to ~400px: the left column's blocks must all take the same width (G9-6
§13 — `.gl-table { width: 100% }` and the body grid), no horizontal scrollbar on
the page body, and the sub-line indents intact. Toggle `[outputs] theme=light`
and reload: no colour may disappear (the tiers are tokens, not literals).

- [ ] **Step 5: Run the hooks**

```bash
git add -A -- glances tests docs
make pre-commit
```

`make pre-commit` supersedes `make lint && make format` (~23 hooks). gitleaks
scans the **index**, so stage before running, and restage anything a formatter
rewrites. The shebang hook fails on a pre-existing file — that failure is not
this group's.

- [ ] **Step 6: Report, and hand back**

Report to the maintainer:

1. Suite count and result, and `make pre-commit` output.
2. The screenshot path.
3. The three v4 divergences this group deliberately keeps (spec D2 `ch`, D4
   `ports` with no visible title, G9-6 D6 empty collections keeping their header
   for the five older blocks) and the one it removes (the `raid`/`smart` bare
   header, Task 3) — the release changelog will want them.
4. Anything found and NOT fixed, with the file and line.
5. `git status --short` — everything staged, nothing committed.

**Owed by the maintainer afterwards** (not this group's to close): the browser
smoke of the six blocks above, plus the two smokes still owed from G9-6 and the
horizontal degradation group.

---

## Self-Review

Checked after writing:

- **Spec coverage.** §4 shell → Task 0. §5.1 `ports` → Task 4. §5.2
  `connections` → Task 5. §5.3 `irq` → Task 5. §5.4 `folders` → Task 4. §5.5
  `raid` → Task 6. §5.6 `smart` → Task 6. §6 labels → Task 2. §7
  `formatAutoUnit` → Task 1. §8 empty-collection fix → Task 3. §9 registry,
  widths, degradation → Tasks 4–6 (widths in each component's scoped style; no
  `degrade.js` change, as specified). §10 tests → the test steps of Tasks 1, 4,
  5, 6 plus the drift test in Task 1. §11 risks → the iso-behaviour gate in Task
  0 Step 9, the two-formatter comment in Task 1 Step 3, the eight `ports`
  branches in Task 4 Step 2, the inactive+degraded array in Task 6 Step 2, and
  "no style is added for a `<tbody>`" — `.gl-subline` styles the sub-line
  `<span>`, never the group.
- **One addition the spec does not name:** the shell's `hidden` prop
  (**P1**, Task 0). The spec requires "an empty collection renders nothing" for
  the six new blocks while G9-6 D6 requires the opposite for the five old ones;
  a per-component flag is the only way to hold both.
- **Type consistency.** `CollectionBlock` props (`payload`, `error`, `title`,
  `ariaLabel`, `hidden`) and slots (`head`, `body`) are used with those exact
  names in Tasks 0, 4, 5 and 6. `formatAutoUnit` and `LARGE_VALUE_KEYS` are
  defined in Task 1 and consumed only in Task 6. `cellClassFor(payload, item,
  field)`, `levelClass`, `scalarLevel`, `labelFor(labels, field)`, `byText` and
  `formatFixed0`/`formatBytes` are the existing helpers, used with their current
  signatures. The probe field `pluginRowGroups` is produced in Task 6 Step 1 and
  consumed in Task 6 Step 3.

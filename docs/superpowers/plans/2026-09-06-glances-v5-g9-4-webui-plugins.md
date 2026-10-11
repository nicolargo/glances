# G9-4 — `cpu`, `load`, `memswap` and `gpu` in the v5 WebUI: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render `cpu`, `load`, `memswap` and `gpu` in the v5 WebUI at strict TUI parity, add the server-argument channel `gpu` needs, and make the plugin schema the single source of every label.

**Architecture:** Infrastructure first — the formatters, then DOM identity (`data-plugin`), then the `serverArgs` channel — because every component depends on all three. Then the components in rising order of difficulty: `load`, `memswap`, `cpu`, `gpu`. Then the `network` retrofit that closes D2, and full verification. Each plugin that needs a schema change carries it in its own task, so "the schema is the single source" is verifiable end to end in one review.

**Tech Stack:** Vue 3 SFC (options API), webpack 5, `node --test`, pytest, Python 3.

**Spec:** `docs/superpowers/specs/2026-09-06-glances-v5-g9-4-webui-plugins-design.md`

**Depends on:** G9-3, committed as `4986c901`.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer. Never `git clean`, never `git checkout`/`restore` over working files, never `git stash`.
- **Never touch `NEWS.rst`.**
- **v4 is read-only.** `glances/outputs/glances_restful_api.py`, `js/app.js`, `js/browser.js`, `js/services.js`, `js/components/**`, `js/App.vue`, `js/Browser.vue`, `js/store.js`, `js/filters.js`, `css/*.scss`, `templates/index.html`. In `webpack.config.js`, **only `v5Config`** may be edited. Note `css/v5.css` IS in scope — the v4 stylesheets are the `.scss` files.
- **After every `npm run build`, the v4 bundles must be byte-identical:**
  ```bash
  for f in glances.js browser.js; do
    W=$(git hash-object glances/outputs/static/public/$f)
    C=$(git rev-parse HEAD:glances/outputs/static/public/$f)
    [ "$W" = "$C" ] && echo "$f IDENTICAL" || echo "$f DIFFERS"
  done
  ```
  Both must print IDENTICAL. If either DIFFERS, STOP and report — do not rebuild, do not `git checkout`, do not stage them.
- **Build with `npm run build` only.** Never `npm install` (`package-lock.json` is tracked); `npm ci` is acceptable if `node_modules` is missing.
- **No new npm dependency.**
- **No colour literal under `js/v5/`** — enforced by `tests/test_webui_v5_tokens.py`, which strips comments before matching and knows all 148 CSS colour names. Use the tokens in `css/v5.css`.
- **`levels.js` exports exactly `levelClass`, `scalarLevel`, `itemLevel`** — a test asserts that surface. Do not extend it.
- **No dead code may be merged.** G9-3's final review removed the group's one permitted exception (`priority`); G9-4 has none at all.
- **A test whose name claims something structural must actually observe it.** G9-2 shipped two that did not (`typeof globalThis.X`, and a probe reading the DOM before any fetch resolved). Prefer asserting real rendered behaviour.
- **The five TUI renderer test files touched by D2 must pass UNMODIFIED** (`tests/test_plugin_load_render_curses_v5.py`, `..._gpu_...`, `..._network_...`, and any other that the refactor touches). If one needs editing, the refactor changed the TUI's output — that is a stop signal, not a test to adjust.
- **A `rate` field in v5 is `null` but present.** `"x" in payload` and `payload.x != null` are NOT interchangeable. Port each check exactly as the TUI writes it.
- `tests/test_restful.py::test_051` is flaky by construction (hard-coded `time.sleep(5)` on a subprocess server) — re-run it alone before believing a failure. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/outputs/static/js/v5/format.js` | `formatCount`, `toFahrenheit` (append). |
| `glances/outputs/static/js/v5/api.js` | `resolveArgs()` (new export). |
| `glances/outputs/static/js/v5/AppShell.vue` | Fetches args, binds `data-plugin`, passes `serverArgs`. |
| `glances/outputs/static/js/v5/PluginLoad.vue` | New — scalar, 1 column. |
| `glances/outputs/static/js/v5/PluginMemswap.vue` | New — scalar, 1 column. |
| `glances/outputs/static/js/v5/PluginCpu.vue` | New — scalar, 3 columns, presence-driven field sets. |
| `glances/outputs/static/js/v5/PluginGpu.vue` | New — collection, two layouts. |
| `glances/outputs/static/js/v5/PluginMem.vue`, `PluginNetwork.vue` | Declare the `serverArgs` prop. |
| `glances/outputs/static/js/v5/plugins/index.js` | Four new registry entries. |
| `glances/plugins/load/model_v5.py` | `short_name` for `min1`/`min5`/`min15`. |
| `glances/plugins/load/render_curses_v5.py` | Read `field_label()`. |
| `glances/plugins/gpu/model_v5.py` | `short_name` for `proc`/`mem`/`temperature`. |
| `glances/plugins/gpu/render_curses_v5.py` | Read `field_label()`, keep composing `:` and `mean`. |
| `glances/plugins/network/render_curses_v5.py` | Retrofit: read `field_label()`. |
| `tests/js/format.test.mjs` | Units for the two new formatters. |
| `tests/fixtures/webui_render_probe.js` | `data-plugin` keying; `/info` and `/all` fixtures per plugin. |
| `tests/test_webserver_v5.py` | Render assertions per component. |

---

### Task 1: The two formatters

**Files:**
- Modify: `glances/outputs/static/js/v5/format.js`
- Test: `tests/js/format.test.mjs` (append)

**Interfaces:**
- Produces: `formatCount(value) -> string` and `toFahrenheit(celsius) -> number`, both exported from `format.js`.

No build is needed for this task: `tests/js/*.test.mjs` import the source module directly, not the bundle.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/format.test.mjs`, and add `formatCount, toFahrenheit` to the existing import at the top of the file:

```js
test("formatCount is a plain integer below 1024 and K-scaled at or above it", () => {
	// The TUI is the authority here: _ctx_sw_value_cell()
	// (glances/plugins/cpu/render_curses_v5.py:52-70) scales at >= 1024, not
	// >= 1000, matching v4's auto_unit. Counting in powers of two is odd, but
	// the two outputs agreeing matters more than either being tidy.
	assert.equal(formatCount(0), "0");
	assert.equal(formatCount(42), "42");
	assert.equal(formatCount(1023), "1023");
	assert.equal(formatCount(1024), "1.0K");
	assert.equal(formatCount(6860), "6.7K");
	assert.equal(formatCount(1048576), "1.0M");
});

test("formatCount returns the missing marker for a non-number", () => {
	// `rate` fields are null until their second cycle -- null IS a value the
	// API sends, so this is a live path, not defensive padding.
	assert.equal(formatCount(null), "-");
	assert.equal(formatCount(undefined), "-");
	assert.equal(formatCount("12"), "-");
});

test("toFahrenheit mirrors glances.globals.to_fahrenheit", () => {
	// celsius * 1.8 + 32, and nothing else -- no rounding, no unit. The
	// caller decides how to render, because gpu's missing marker is "N/A"
	// while every other v5 formatter uses "-".
	assert.equal(toFahrenheit(0), 32);
	assert.equal(toFahrenheit(100), 212);
	assert.equal(toFahrenheit(55), 131);
});
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `formatCount` is not exported.

- [ ] **Step 3: Write the implementation**

Append to `format.js`:

```js
// Counter units. Base 1024, deliberately: the TUI's _ctx_sw_value_cell()
// scales these at >= 1024 to match v4's auto_unit, and D1 makes the TUI the
// authority. Changing this to base 1000 is a TUI change first.
const COUNT_UNITS = ["", "K", "M", "G", "T", "P"];

export function formatCount(value) {
	if (!isNumber(value)) return MISSING;
	let n = value;
	let i = 0;
	while (n >= 1024 && i < COUNT_UNITS.length - 1) {
		n /= 1024;
		i += 1;
	}
	return i === 0 ? `${Math.round(n)}` : `${n.toFixed(1)}${COUNT_UNITS[i]}`;
}

export function toFahrenheit(celsius) {
	// glances/globals.py:203 -- the conversion only. Rendering (rounding,
	// unit letter, missing marker) belongs to the caller.
	return celsius * 1.8 + 32;
}
```

- [ ] **Step 4: Run to verify they pass**

```bash
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
```
Expected: PASS.

- [ ] **Step 5: Stage**

```bash
git add glances/outputs/static/js/v5/format.js tests/js/format.test.mjs
```

---

### Task 2: `data-plugin` — stable DOM identity

**Files:**
- Modify: `glances/outputs/static/js/v5/AppShell.vue` (template only)
- Modify: `tests/fixtures/webui_render_probe.js`
- Modify: `tests/test_webserver_v5.py` (re-key the existing render assertions)

**Interfaces:**
- Produces: every `<article class="gl-plugin">` carries `data-plugin="<registry name>"`. The probe's `pluginText`, `pluginColumnHeaders` and `pluginColumnClasses` are keyed by that name (`"mem"`, `"network"`), no longer by the `<h2>` text (`"MEM"`, `"NETWORK"`). `pluginHeaders` stays the ordered list of `<h2>` texts. A new `pluginNames` is the ordered list of `data-plugin` values.

This is a pure refactor: no rendered output changes, and the existing render tests are its guard.

- [ ] **Step 1: Bind the attribute**

In `AppShell.vue`, add one line to the `<component>` tag:

```html
			<component
				:is="plugin.component"
				v-for="plugin in plugins"
				:key="plugin.name"
				:data-plugin="plugin.name"
				:payload="results[plugin.name]"
				:error="errors[plugin.name]"
				:labels="labels[plugin.name] || {}"
			/>
```

`data-plugin` is not a declared prop on any component, so Vue treats it as a fallthrough attribute and puts it on each component's single root element — the `<article>`. No plugin component changes.

- [ ] **Step 2: Re-key the probe**

In `tests/fixtures/webui_render_probe.js`, replace the block that fills `pluginText` / `pluginColumnHeaders` / `pluginColumnClasses` with:

```js
			articles.forEach((article, i) => {
				// Keyed by data-plugin (the registry name), NOT by the <h2>
				// text: gpu's title is built from the hardware it finds
				// ("GeForce RTX 3080" / "3 GPUs"), so a title key would make
				// these assertions depend on the machine running the test.
				const name = article.getAttribute("data-plugin");
				if (!name) return;
				result.pluginNames.push(name);
				result.pluginText[name] = article.textContent;
				const ths = findAllByTag(article, "TH");
				if (ths.length) {
					result.pluginColumnHeaders[name] = ths.map((th) => th.textContent);
					result.pluginColumnClasses[name] = ths.map((th) => th.className);
				}
			});
```

Add `pluginNames: [],` to the `result` object literal beside `pluginHeaders`, with this comment:

```js
		// The ordered `data-plugin` values -- stable identity, unlike
		// pluginHeaders below, which is the ordered <h2> TEXT and is only
		// meaningful for components whose title is a constant.
		pluginNames: [],
```

`FakeElement` already stores attributes in `_attrs` via `setAttribute`. If it has no `getAttribute`, add the two-line accessor beside `setAttribute`:

```js
	getAttribute(name) {
		return this._attrs.has(name) ? this._attrs.get(name) : null;
	}
```

- [ ] **Step 3: Re-key the existing assertions**

In `tests/test_webserver_v5.py`, change every `payload["pluginText"].get("MEM", "")` to `.get("mem", "")`, and `payload["pluginColumnHeaders"].get("NETWORK")` / `payload["pluginColumnClasses"].get("NETWORK")` to `.get("network")`. In `test_the_registry_renders_every_registered_plugin`, assert on the new stable list instead of the titles:

```python
    assert payload["pluginNames"] == ["mem", "network"], (
        f"expected both registered plugins to render, got {payload['pluginNames']!r}"
    )
```

- [ ] **Step 4: Build and verify nothing changed**

```bash
cd glances/outputs/static && npm run build && cd -
```
Then the v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
```
Expected: PASS. Every previously-passing render assertion still passes — that is the proof this refactor changed no output.

- [ ] **Step 5: Stage**

```bash
git add glances/outputs/static/js/v5/AppShell.vue glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_probe.js tests/test_webserver_v5.py
```

---

### Task 3: The `serverArgs` channel

**Files:**
- Modify: `glances/outputs/static/js/v5/api.js`
- Modify: `glances/outputs/static/js/v5/AppShell.vue`
- Modify: `glances/outputs/static/js/v5/PluginMem.vue`, `glances/outputs/static/js/v5/PluginNetwork.vue`
- Test: `tests/js/api.test.mjs` (append)

**Interfaces:**
- Consumes: `getJson` from `api.js`.
- Produces: `resolveArgs() -> Promise<Object>` from `api.js`, cached for the page's life. Every plugin component declares a `serverArgs` prop: `serverArgs: { type: Object, default: () => ({}) }`. `AppShell` binds `:server-args="serverArgs"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/api.test.mjs`, adding `resolveArgs` to the import at the top:

```js
test("resolveArgs returns the args object and fetches once", async () => {
	let calls = 0;
	globalThis.fetch = async () => {
		calls += 1;
		return { ok: true, status: 200, json: async () => ({ meangpu: true, fahrenheit: false }) };
	};
	assert.deepEqual(await resolveArgs(), { meangpu: true, fahrenheit: false });
	// CLI arguments cannot change while the server runs, so a second call
	// must not hit the network.
	await resolveArgs();
	assert.equal(calls, 1);
});
```

`resolveArgs` caches at module scope, so this test must be the only one in the file that calls it — a second test would read the first one's cached value instead of exercising the fetch. (This is the trap G9-3's `labels.test.mjs` fell into: two tests sharing a cache key, where the second silently asserted the first one's result.)

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `resolveArgs` is not exported.

- [ ] **Step 3: Write the implementation**

Add to `api.js`:

```js
let argsCache = null;

export async function resolveArgs() {
	// The server's CLI arguments -- `--meangpu` and `--fahrenheit` today.
	// They cannot change while the server runs, so this is fetched once per
	// page load and cached, exactly like the schema in labels.js.
	//
	// NOT merged into resolveConfig(): that reads /api/5/config, and the two
	// namespaces are genuinely different (the argument namespace carries no
	// `refresh` key at all -- measured in G9-1).
	if (argsCache) return argsCache;
	try {
		argsCache = await getJson("api/5/args");
	} catch {
		// A UI that cannot read the arguments renders in Celsius and lets the
		// card count decide gpu's layout. That is a degraded view, not a
		// broken one -- never a reason to blank the page.
		argsCache = {};
	}
	return argsCache;
}
```

- [ ] **Step 4: Wire it into the shell**

In `AppShell.vue`: import `resolveArgs` alongside `fetchAll, resolveConfig, getJson`; add `serverArgs: {},` to `data()`; resolve it in `mounted()` in the same parallel burst as the labels, replacing the labels block with:

```js
		// The schema and the server's CLI arguments both never change at
		// runtime, so both are resolved once here rather than on every tick.
		const [labelEntries, serverArgs] = await Promise.all([
			Promise.all(PLUGINS.map(async (p) => [p.name, await resolveLabels(p.name)])),
			resolveArgs(),
		]);
		this.labels = Object.fromEntries(labelEntries);
		this.serverArgs = serverArgs;
```

and add the binding to the `<component>` tag, below `:labels`:

```html
				:server-args="serverArgs"
```

- [ ] **Step 5: Declare the prop everywhere**

In `PluginMem.vue` and `PluginNetwork.vue`, add to `props`:

```js
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// serverargs="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
```

- [ ] **Step 6: Prove the fallthrough claim, then verify**

Add to `tests/test_webserver_v5.py`:

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_server_args_does_not_leak_into_the_dom_as_an_attribute():
    """Every component must DECLARE `serverArgs`, even when it ignores it.

    Vue turns an undeclared prop into a fallthrough attribute, so a component
    missing the declaration renders serverargs="[object Object]" onto its
    root <article>. This observes the rendered attribute rather than the
    source, so it fails for a component added later that forgets the line.
    """
    payload = _run_render_probe("mem-with-available")
    for name, attrs in payload["pluginAttrs"].items():
        assert "serverargs" not in attrs, f"{name} leaked serverArgs as an attribute: {attrs!r}"
```

For that to work, collect the attribute names in the probe, inside the same `articles.forEach` as Task 2:

```js
				result.pluginAttrs[name] = Array.from(article._attrs.keys());
```

and add `pluginAttrs: {},` to the `result` literal.

Then:
```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
```

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/api.js glances/outputs/static/js/v5/AppShell.vue \
        glances/outputs/static/js/v5/PluginMem.vue glances/outputs/static/js/v5/PluginNetwork.vue \
        glances/outputs/static/public/glances5.js tests/js/api.test.mjs \
        tests/fixtures/webui_render_probe.js tests/test_webserver_v5.py
```

---

### Task 4: `load` — component, schema, and the TUI refactor

**Files:**
- Create: `glances/outputs/static/js/v5/PluginLoad.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `glances/plugins/load/model_v5.py`, `glances/plugins/load/render_curses_v5.py`
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`

**Interfaces:**
- Consumes: `labelFor` from `labels.js`; `levelClass`, `scalarLevel` from `levels.js`.
- Produces: registry entry `{ name: "load", component: PluginLoad, spec: { shape: "scalar", required: ["min1"] } }`.

TUI reference (`glances/plugins/load/render_curses_v5.py` docstring):

```
    LOAD     4core
    1 min     0.86
    5 min     0.72
    15 min    0.80
```

- [ ] **Step 1: Put the labels in the schema**

In `glances/plugins/load/model_v5.py`, add `short_name` to the three load fields:

```python
        "min1": {..., "short_name": "1 min"},
        "min5": {..., "short_name": "5 min"},
        "min15": {..., "short_name": "15 min"},
```

Keep every existing key in those dicts; you are adding one entry to each, not rewriting them.

- [ ] **Step 2: Make the TUI read the schema**

In `glances/plugins/load/render_curses_v5.py`, replace the hardcoded label list:

```python
    # Lines 2-4: "{N min}" + value, per-row label.
    for key, label in [("min1", "1 min"), ("min5", "5 min"), ("min15", "15 min")]:
        label_cell = Cell(text=label.ljust(_LOAD_LABEL_WIDTH))
```

with the schema lookup, importing `field_label` from `glances.outputs.curses_renderer_v5` alongside the existing imports:

```python
    # Lines 2-4: label from the schema (short_name -> label -> field name),
    # so the string exists in exactly one place and the WebUI, which resolves
    # its labels from /api/5/load/info, shows the same one.
    for key in ("min1", "min5", "min15"):
        label = field_label(fields_desc.get(key, {}), key, prefer_short=True)
        label_cell = Cell(text=label.ljust(_LOAD_LABEL_WIDTH))
```

If `render()` does not already receive `fields_desc`, match the signature `cpu`/`memswap` use — check `glances/plugins/memswap/render_curses_v5.py::render` and follow it, including how the caller passes it.

- [ ] **Step 3: Prove the TUI did not change**

```bash
uv run pytest tests/test_plugin_load_render_curses_v5.py tests/test_plugin_load_v5.py -q
```
Expected: PASS, **with no edit to either test file**. If a test fails, the refactor changed the rendered output — stop and report rather than adjusting the test.

- [ ] **Step 4: Write the failing render assertion**

Add the `load` fixtures to `tests/fixtures/webui_render_probe.js` — an `INFO_FIXTURES.load` mirroring the schema you just wrote, and a `load` scenario in `ALL_FIXTURES`:

```js
	load: {
		min1: { short_name: "1 min" },
		min5: { short_name: "5 min" },
		min15: { short_name: "15 min" },
		cpucore: {},
	},
```

```js
	load: {
		load: { min1: 0.86, min5: 0.72, min15: 0.8, cpucore: 4, _levels: {} },
	},
```

Then in `tests/test_webserver_v5.py`:

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_load_renders_the_three_averages_and_the_core_count():
    """TUI reference (load/render_curses_v5.py docstring): a header carrying
    LOAD and the core count, then three rows labelled from the schema.

    `cpucore` is `internal: true` -- it is the header's suffix, never a row
    of its own, so this asserts the label "cpucore" is absent.
    """
    payload = _run_render_probe("load")
    text = payload["pluginText"].get("load", "")

    for expected in ("LOAD", "4core", "1 min", "0.86", "5 min", "0.72", "15 min", "0.80"):
        assert expected in text, f"expected {expected!r} in the LOAD plugin text, got {text!r}"
    assert "cpucore" not in text, f"cpucore is internal and must not be a row: {text!r}"
```

- [ ] **Step 5: Run to verify it fails**

```bash
uv run pytest tests/test_webserver_v5.py -q -k load
```
Expected: FAIL — no `load` component is registered, so nothing renders.

- [ ] **Step 6: Write the component**

Create `glances/outputs/static/js/v5/PluginLoad.vue`:

```html
<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">LOAD</h2>
			<span v-if="coreLabel" class="gl-muted">{{ coreLabel }}</span>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<template v-for="stat in rows" :key="stat.field">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd class="gl-num" :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";

const FIELDS = ["min1", "min5", "min15"];

export default {
	name: "PluginLoad",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// `cpucore` is internal: true in the schema -- the TUI shows it as the
		// header's "{N}core" suffix and never as a row. Same here.
		coreLabel() {
			const cores = this.payload?.cpucore;
			return typeof cores === "number" && cores > 0 ? `${Math.trunc(cores)}core` : "";
		},
		rows() {
			return FIELDS.map((field) => {
				const value = this.payload?.[field];
				return { field, value: typeof value === "number" ? value.toFixed(2) : "-" };
			});
		},
	},
	methods: { levelClass, scalarLevel, labelFor },
};
</script>
```

`min1` carries no alert in v4, and `scalarLevel` returns nothing for a field with no `_levels` entry — so routing all three through the same call reproduces v4 without a special case.

`.gl-plugin-title` does not exist yet: `PluginMem.vue` has the same shape as a scoped `.gl-mem-title`. Promote it to `css/v5.css` beside `.gl-stat-grid`, delete the scoped copy from `PluginMem.vue`, and use the shared class in both. A scoped copy per component is the `.gl-muted` mistake of G9-2 in slow motion.

```css
/* Plugin title row: the <h2> and the one value that belongs beside it
 * (mem's percent, load's core count). Global, like .gl-stat-grid: every
 * plugin with a title-line value reuses it. */
.gl-plugin-title {
  display: flex;
  gap: var(--gl-gap);
  align-items: baseline;
}
```

- [ ] **Step 7: Register it**

In `glances/outputs/static/js/v5/plugins/index.js`, add the import and the entry:

```js
import PluginLoad from "../PluginLoad.vue";
```
```js
	{
		name: "load",
		component: PluginLoad,
		spec: { shape: "scalar", required: ["min1"] },
	},
```

- [ ] **Step 8: Build, verify, stage**

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py \
              tests/test_plugin_load_render_curses_v5.py -q
```
Note `test_the_registry_renders_every_registered_plugin` now expects `["mem", "network", "load"]` — update that assertion to match the registry's order.

```bash
git add glances/outputs/static/js/v5/PluginLoad.vue glances/outputs/static/js/v5/PluginMem.vue \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/css/v5.css \
        glances/outputs/static/public/glances5.js glances/plugins/load/model_v5.py \
        glances/plugins/load/render_curses_v5.py tests/fixtures/webui_render_probe.js \
        tests/test_webserver_v5.py
```

---

### Task 5: `memswap`

**Files:**
- Create: `glances/outputs/static/js/v5/PluginMemswap.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`

**Interfaces:**
- Consumes: `formatBytes`, `formatRate`, `formatPercent` from `format.js`; `labelFor`; `levelClass`, `scalarLevel`.
- Produces: registry entry `{ name: "memswap", component: PluginMemswap, spec: { shape: "scalar", required: ["total"] } }`.

No schema or TUI change: `memswap`'s field names already ARE the TUI's labels, and its renderer already reads `field_label()`.

TUI reference:

```
    SWAP   25.0%
    total  16.0G
    sin   100.0K/s
    sout    0.0K/s
```

- [ ] **Step 1: Add the fixtures**

To `INFO_FIXTURES` in the probe (empty objects: the schema declares no labels, and `labelFor` falls back to the field name — which is the point):

```js
	memswap: { total: {}, used: {}, free: {}, percent: {}, sin: {}, sout: {} },
```

To `ALL_FIXTURES`, two scenarios — one with rates, one before the second cycle:

```js
	memswap: {
		memswap: { total: 17179869184, used: 4294967296, free: 12884901888, percent: 25.0, sin: 102400, sout: 0, _levels: {} },
	},
	"memswap-no-rates": {
		memswap: { total: 17179869184, used: 4294967296, free: 12884901888, percent: 25.0, sin: null, sout: null, _levels: {} },
	},
```

- [ ] **Step 2: Write the failing tests**

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_memswap_renders_total_and_the_paging_rates():
    """TUI reference (memswap/render_curses_v5.py docstring): SWAP + percent,
    then total, sin, sout.

    `used` and `free` are deliberately absent: v5 trades that redundant pair
    (they are derivable from total and percent) for the live paging rates.
    Asserting their VALUES are absent, not just their labels, is what makes
    this a parity test rather than a spelling test.
    """
    payload = _run_render_probe("memswap")
    text = payload["pluginText"].get("memswap", "")

    for expected in ("SWAP", "25.0%", "total", "16.0G", "sin", "100.0K/s", "sout", "0.0K/s"):
        assert expected in text, f"expected {expected!r} in the SWAP plugin text, got {text!r}"
    assert "4.0G" not in text, f"`used` must not be rendered: {text!r}"
    assert "12.0G" not in text, f"`free` must not be rendered: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_memswap_shows_a_dash_for_rates_before_the_second_cycle():
    """`sin`/`sout` are rate fields: null until a baseline exists, and PRESENT
    in the payload while null. The component must render "-" for them and
    still render everything else.
    """
    payload = _run_render_probe("memswap-no-rates")
    text = payload["pluginText"].get("memswap", "")

    assert "16.0G" in text, f"total must still render: {text!r}"
    assert "-" in text, f"expected the missing marker for the null rates: {text!r}"
    assert "K/s" not in text, f"no rate should be formatted when both are null: {text!r}"
```

- [ ] **Step 3: Run to verify they fail**

```bash
uv run pytest tests/test_webserver_v5.py -q -k memswap
```
Expected: FAIL — nothing renders.

- [ ] **Step 4: Write the component**

Create `glances/outputs/static/js/v5/PluginMemswap.vue`:

```html
<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">SWAP</h2>
			<span v-if="payload" :class="levelClass(scalarLevel(payload, 'percent'))">{{
				formatPercent(payload.percent)
			}}</span>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<template v-for="stat in rows" :key="stat.field">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd class="gl-num" :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { formatBytes, formatPercent, formatRate } from "./format.js";
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";

export default {
	name: "PluginMemswap",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// `used` and `free` are deliberately absent -- see
		// glances/plugins/memswap/render_curses_v5.py: v5 trades that
		// redundant pair for the live paging rates. Adding them back here
		// would diverge from v5, not return to v4.
		rows() {
			return [
				{ field: "total", value: formatBytes(this.payload?.total) },
				{ field: "sin", value: formatRate(this.payload?.sin) },
				{ field: "sout", value: formatRate(this.payload?.sout) },
			];
		},
	},
	methods: { levelClass, scalarLevel, labelFor, formatPercent },
};
</script>
```

`formatRate` already returns `-` for `null`, so the second test passes without a branch.

- [ ] **Step 5: Register, build, verify, stage**

Add the import and entry to `plugins/index.js`, update `test_the_registry_renders_every_registered_plugin`'s expected list, then:

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check, then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
git add glances/outputs/static/js/v5/PluginMemswap.vue glances/outputs/static/js/v5/plugins/index.js \
        glances/outputs/static/public/glances5.js tests/fixtures/webui_render_probe.js \
        tests/test_webserver_v5.py
```

---

### Task 6: `cpu` — the three-column grid

**Files:**
- Create: `glances/outputs/static/js/v5/PluginCpu.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`

**Interfaces:**
- Consumes: `formatPercent`, `formatCount` (Task 1); `labelFor`; `levelClass`, `scalarLevel`.
- Produces: registry entry `{ name: "cpu", component: PluginCpu, spec: { shape: "scalar", required: ["total"] } }`.

No schema or TUI change: `cpu` already declares the three `short_name`s it needs and already reads `field_label()`.

TUI reference:

```
    CPU      4.5%      idle   95.5%       ctx_sw   6.7K
      user   3.8%       irq    0.0%   interrupts   3.0K
    system   0.7%      nice    0.0%       sw_int   1.8K
    iowait   0.0%     steal    0.0%        guest   0.0%
```

**The selection rules, from `glances/plugins/cpu/render_curses_v5.py:181-200`.** Read that code before writing the component; the table below is a summary, not a substitute.

| Column | Rows 2-4 |
|---|---|
| 1 | `user`, `system`, `iowait` — or `idle`, `cpucore`, `dpc` when `"user" not in payload` |
| 2 | `irq`, `nice`, `steal` — always |
| 3 | `interrupts`; then `soft_interrupts` if `!= null`, else `ctx_switches`; then `guest` if the KEY is present, else `syscalls` if `!= null`, else an empty cell |

**Two different kinds of check, and they are not interchangeable.** `guest` is tested for key presence (`"guest" in payload`); `soft_interrupts` and `syscalls` are tested for value (`!= null`). A `rate` field in v5 is `null` but present, so collapsing the two silently changes which column renders.

**The `core`/`cpucore` bug.** The TUI writes `_kl("core")` at line 183, but the schema declares `cpucore` and v4 stores `stats['cpucore']`. Port this component against **`cpucore`** and leave this comment on the line:

```js
	// The TUI writes `core` here (cpu/render_curses_v5.py:183) but no such
	// field exists -- the schema and v4 both call it `cpucore`. Ported
	// against the real field on purpose; see §10 of the G9-4 design spec,
	// which owns fixing the TUI side.
```

- [ ] **Step 1: Add the fixtures**

`INFO_FIXTURES.cpu` must mirror the real schema's three `short_name`s and leave the rest bare:

```js
	cpu: {
		total: {}, user: {}, system: {}, iowait: {}, idle: {}, irq: {}, nice: {}, steal: {},
		guest: {}, dpc: {}, cpucore: {}, syscalls: {},
		ctx_switches: { short_name: "ctx_sw" },
		interrupts: { short_name: "inter" },
		soft_interrupts: { short_name: "sw_int" },
	},
```

Three `ALL_FIXTURES` scenarios, because the component has three branches:

```js
	cpu: {
		cpu: {
			total: 4.5, user: 3.8, system: 0.7, iowait: 0.0, idle: 95.5, irq: 0.0,
			nice: 0.0, steal: 0.0, guest: 0.0, cpucore: 4,
			ctx_switches: 6860, interrupts: 3072, soft_interrupts: 1843, _levels: {},
		},
	},
	// No `user` key -> column 1 becomes idle/cpucore/dpc. `soft_interrupts`
	// is null-but-present (a rate before its baseline) so column 3 falls to
	// ctx_switches; `guest` is absent as a KEY so it falls to syscalls.
	"cpu-idle-tag": {
		cpu: {
			total: 4.5, idle: 95.5, cpucore: 8, dpc: 1.2, irq: 0.0, nice: 0.0, steal: 0.0,
			ctx_switches: 6860, interrupts: 3072, soft_interrupts: null, syscalls: 2048, _levels: {},
		},
	},
	// Neither `guest` nor `syscalls`: column 3's last cell is empty.
	"cpu-no-third-row": {
		cpu: {
			total: 4.5, user: 3.8, system: 0.7, iowait: 0.0, idle: 95.5, irq: 0.0,
			nice: 0.0, steal: 0.0, cpucore: 4,
			ctx_switches: 6860, interrupts: 3072, soft_interrupts: 1843, syscalls: null, _levels: {},
		},
	},
```

- [ ] **Step 2: Write the failing tests**

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_renders_the_linux_three_column_grid():
    """TUI reference (cpu/render_curses_v5.py docstring, lines 17-21)."""
    payload = _run_render_probe("cpu")
    text = payload["pluginText"].get("cpu", "")

    for expected in ("CPU", "4.5%", "idle", "95.5%", "ctx_sw", "6.7K",
                     "user", "3.8%", "inter", "3.0K",
                     "system", "0.7%", "sw_int", "1.8K",
                     "iowait", "steal", "guest"):
        assert expected in text, f"expected {expected!r} in the CPU plugin text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_switches_column_one_and_column_three_on_payload_content():
    """The TUI branches on payload CONTENT, never on the OS, so the WebUI can
    reproduce it exactly (cpu/render_curses_v5.py:181-200).

    This fixture has no `user` key (column 1 becomes idle/cpucore/dpc), a
    null-but-present `soft_interrupts` (column 3 falls back to ctx_switches),
    and no `guest` key (column 3's last row falls back to syscalls). It fails
    if the two kinds of check -- key presence vs value -- are collapsed into
    one.
    """
    payload = _run_render_probe("cpu-idle-tag")
    text = payload["pluginText"].get("cpu", "")

    assert "dpc" in text, f"the idle-tag branch must show dpc: {text!r}"
    assert "user" not in text, f"no `user` key, so no user row: {text!r}"
    assert "sw_int" not in text, f"soft_interrupts is null -> ctx_switches instead: {text!r}"
    assert "syscalls" in text, f"no `guest` key -> syscalls instead: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cpu_leaves_column_three_short_when_neither_guest_nor_syscalls():
    """The TUI emits an empty cell rather than shifting a row up."""
    payload = _run_render_probe("cpu-no-third-row")
    text = payload["pluginText"].get("cpu", "")

    assert "guest" not in text, f"no guest key: {text!r}"
    assert "syscalls" not in text, f"syscalls is null: {text!r}"
    assert "sw_int" in text, f"the rest of column 3 must still render: {text!r}"
```

- [ ] **Step 3: Run to verify they fail**

```bash
uv run pytest tests/test_webserver_v5.py -q -k cpu
```
Expected: FAIL — nothing renders.

- [ ] **Step 4: Write the component**

Create `glances/outputs/static/js/v5/PluginCpu.vue`. The template is `PluginMem.vue`'s with a third `<dl>`; the logic is the selection rules:

```html
<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">CPU</h2>
			<span v-if="payload" :class="levelClass(scalarLevel(payload, 'total'))">{{
				formatPercent(payload.total)
			}}</span>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl v-for="(column, i) in columns" :key="i">
				<template v-for="stat in column" :key="stat.field">
					<dt class="gl-header">{{ stat.field ? labelFor(labels, stat.field) : "" }}</dt>
					<dd class="gl-num" :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { formatCount, formatPercent } from "./format.js";
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";

// Column 3 holds counters, not percentages -- see formatCount.
const COUNTER_FIELDS = new Set(["interrupts", "soft_interrupts", "ctx_switches", "syscalls"]);

export default {
	name: "PluginCpu",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// Mirrors glances/plugins/cpu/render_curses_v5.py:181-200. The TUI
		// branches on payload CONTENT, never on the operating system, which
		// is why a browser can reproduce it without knowing the server's OS.
		columns() {
			const p = this.payload || {};
			const col1 = !("user" in p)
				? // The TUI writes `core` here (cpu/render_curses_v5.py:183) but
					// no such field exists -- the schema and v4 both call it
					// `cpucore`. Ported against the real field on purpose; see §10
					// of the G9-4 design spec, which owns fixing the TUI side.
					["idle", "cpucore", "dpc"]
				: ["user", "system", "iowait"];
			const col2 = ["irq", "nice", "steal"];

			// Key presence for `guest`, value for the rates: a `rate` field is
			// null BUT PRESENT until its second cycle, so `in` and `!= null`
			// select different columns and are not interchangeable.
			const col3 = ["interrupts"];
			col3.push(p.soft_interrupts != null ? "soft_interrupts" : "ctx_switches");
			if ("guest" in p) col3.push("guest");
			else if (p.syscalls != null) col3.push("syscalls");
			else col3.push("");

			return [col1, col2, col3].map((fields) => fields.map((f) => this.statFor(f)));
		},
	},
	methods: {
		levelClass,
		scalarLevel,
		labelFor,
		formatPercent,
		statFor(field) {
			if (!field) return { field: "", value: "" };
			const value = this.payload?.[field];
			return { field, value: COUNTER_FIELDS.has(field) ? formatCount(value) : formatPercent(value) };
		},
	},
};
</script>
```

`cpucore` is a count, not a percentage, and is not in `COUNTER_FIELDS` — check what the TUI renders for it in the idle-tag branch and match; if it is a bare integer, add it to a small `PLAIN_FIELDS` set rather than letting `formatPercent` print `4.0%`.

- [ ] **Step 5: Register, build, verify, stage**

Same shape as Task 5's step 5, plus `tests/test_plugin_cpu_render_curses_v5.py` in the pytest run to confirm the TUI is untouched. Stage `PluginCpu.vue`, `plugins/index.js`, the bundle, the probe fixture and `test_webserver_v5.py`.

---

### Task 7: `gpu` — two layouts, a computed title, and its schema

**Files:**
- Create: `glances/outputs/static/js/v5/PluginGpu.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `glances/plugins/gpu/model_v5.py`, `glances/plugins/gpu/render_curses_v5.py`
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`

**Interfaces:**
- Consumes: `toFahrenheit` (Task 1); `serverArgs` (Task 3); `labelFor`; `levelClass`, `itemLevel` from `levels.js`; `cellClassFor` from `columns.js` for the multi-card table.
- Produces: registry entry `{ name: "gpu", component: PluginGpu, spec: { shape: "collection", required: ["gpu_id"] } }`.

TUI reference (`glances/plugins/gpu/render_curses_v5.py`):

```
    GeForce RTX 3080         <- header: name / "N NAME" / "N GPUs"
    proc:              30%   <- summary: 1 card, or view["meangpu"]
    mem:               40%
    temperature:       55C

    3 GeForce RTX 3080       <- multi: >1 card and no meangpu
    GeForce..   30%  mem 40%
```

- [ ] **Step 1: Put the labels in the schema**

In `glances/plugins/gpu/model_v5.py`, add `short_name` to three fields — the bare word only:

```python
        "proc": {..., "short_name": "proc"},
        "mem": {..., "short_name": "mem"},
        "temperature": {..., "short_name": "temperature"},
```

- [ ] **Step 2: Make the TUI read the schema**

In `glances/plugins/gpu/render_curses_v5.py`, `_summary_rows` currently hardcodes both forms:

```python
    for key, label, label_mean in (("proc", "proc:", "proc mean:"), ("mem", "mem:", "mem mean:")):
```

Replace with a schema lookup that **composes** the punctuation and the `mean` suffix — a schema holds one string per field, not two:

```python
    for key in ("proc", "mem"):
        word = field_label(fields_desc.get(key, {}), key, prefer_short=True)
        label = f"{word} mean:" if is_multi else f"{word}:"
```

Do the same for the temperature row, whose TUI strings are `temp mean:` and `temperature:` — note they use **different words**, so the schema's `temperature` cannot produce `temp mean:` by suffixing. Keep the `mean` form as a literal and take only the non-mean form from the schema, with a comment saying why. `render()` must now pass `fields_desc` down to `_summary_rows`; thread it through.

- [ ] **Step 3: Prove the TUI did not change**

```bash
uv run pytest tests/test_plugin_gpu_render_curses_v5.py tests/test_plugin_gpu_v5.py -q
```
Expected: PASS, **with no edit to either test file**.

- [ ] **Step 4: Add the fixtures — all four cases**

```js
	gpu: { gpu_id: {}, name: {}, fan_speed: {},
		proc: { short_name: "proc" }, mem: { short_name: "mem" },
		temperature: { short_name: "temperature" } },
```

```js
	"gpu-one-card": {
		gpu: { _key: "gpu_id", data: [{ gpu_id: 0, name: "GeForce RTX 3080", proc: 30, mem: 40, temperature: 55 }], _levels: {} },
	},
	"gpu-three-cards": {
		gpu: { _key: "gpu_id", data: [
			{ gpu_id: 0, name: "GeForce RTX 3080", proc: 30, mem: 40, temperature: 55 },
			{ gpu_id: 1, name: "GeForce RTX 3080", proc: 45, mem: 38, temperature: 61 },
			{ gpu_id: 2, name: "GeForce RTX 3080", proc: 12, mem: 20, temperature: 49 },
		], _levels: {} },
	},
	"gpu-no-memory": {
		gpu: { _key: "gpu_id", data: [
			{ gpu_id: 0, name: "Radeon RX 7900", proc: 30, mem: null, temperature: 55 },
			{ gpu_id: 1, name: "Radeon RX 7900", proc: 45, mem: null, temperature: 61 },
		], _levels: {} },
	},
```

The `--meangpu` and `--fahrenheit` cases need the probe's `/api/5/args` stub to answer per scenario. Extend `fakeFetch`'s `api/5/args` branch with an `ARGS_FIXTURES[scenario] || {}` lookup, and add:

```js
const ARGS_FIXTURES = {
	"gpu-three-cards-mean": { meangpu: true },
	"gpu-one-card-fahrenheit": { fahrenheit: true },
};
```

with `ALL_FIXTURES` entries for those two scenarios reusing the same card data as `gpu-three-cards` and `gpu-one-card`.

- [ ] **Step 5: Write the failing tests**

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_one_card_renders_the_summary_block():
    payload = _run_render_probe("gpu-one-card")
    text = payload["pluginText"].get("gpu", "")

    assert "GeForce RTX 3080" in text, f"the title is the card's name: {text!r}"
    for expected in ("proc:", "30%", "mem:", "40%", "temperature:", "55C"):
        assert expected in text, f"expected {expected!r} in the GPU plugin text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_several_cards_render_one_row_each_without_temperature():
    """v4 quirk reproduced on purpose: multi mode shows name + proc + mem, and
    NO temperature -- unlike summary mode, which shows all three.
    """
    payload = _run_render_probe("gpu-three-cards")
    text = payload["pluginText"].get("gpu", "")

    assert "3 GeForce RTX 3080" in text, f"title counts the cards: {text!r}"
    for expected in ("30%", "45%", "12%"):
        assert expected in text, f"expected every card's proc: {text!r}"
    assert "55C" not in text, f"multi mode shows no temperature: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_meangpu_forces_the_summary_and_the_mean_labels():
    """`--meangpu` reaches the WebUI through /api/5/args (design spec §5)."""
    payload = _run_render_probe("gpu-three-cards-mean")
    text = payload["pluginText"].get("gpu", "")

    assert "proc mean:" in text, f"meangpu switches the labels: {text!r}"
    assert "29%" in text, f"the mean of 30/45/12 rounds to 29: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_drops_the_memory_column_only_when_no_card_reports_it():
    """#3631: an unavailable sensor on ONE card shows N/A rather than being
    hidden, because hiding it per card misaligns heterogeneous rows. The
    column disappears only when no card reports memory at all.
    """
    payload = _run_render_probe("gpu-no-memory")
    text = payload["pluginText"].get("gpu", "")

    assert "mem" not in text, f"no card reports memory -> no mem column: {text!r}"
    assert "30%" in text and "45%" in text, f"proc must still render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_gpu_honours_fahrenheit():
    payload = _run_render_probe("gpu-one-card-fahrenheit")
    text = payload["pluginText"].get("gpu", "")

    assert "131F" in text, f"55C is 131F: {text!r}"
    assert "55C" not in text, f"Celsius must not also render: {text!r}"
```

- [ ] **Step 6: Run to verify they fail**, then write the component

```bash
uv run pytest tests/test_webserver_v5.py -q -k gpu
```
Expected: FAIL — nothing renders.

Create `glances/outputs/static/js/v5/PluginGpu.vue`. Model the summary block on `PluginLoad.vue`'s `<dl>` and the multi table on `PluginNetwork.vue`'s. The logic, mirroring the TUI:

```js
const HEADER_FALLBACK = "GPU";

function mean(cards, key) {
	const values = cards.map((c) => c && c[key]).filter((v) => typeof v === "number");
	return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

// Mirrors _format_value() in gpu/render_curses_v5.py. gpu's missing marker is
// "N/A", not the "-" every other v5 formatter uses, which is why this lives
// here rather than in format.js.
function gpuValue(value, unit = "%") {
	return typeof value === "number" ? `${Math.round(value)}${unit}` : "N/A";
}
```

- `cards` — `this.payload?.data || []`.
- `title` — one card: its `name` or `GPU`. Several: `{n} {name}` when every card reports the same name, otherwise `{n} GPUs`. **No 17-character truncation** (design spec §8.4).
- `isSummary` — `cards.length === 1 || !!this.serverArgs.meangpu`.
- Summary rows — `proc`, `mem`, then temperature. Labels: `` `${labelFor(labels, field)}${isMulti ? " mean:" : ":"}` `` for proc and mem; temperature uses the literal `temp mean:` in the multi case, because the TUI shortens the word there and a schema cannot hold two forms. Values: `gpuValue(mean(cards, field))`, and for temperature `gpuValue(fahrenheit ? toFahrenheit(m) : m, fahrenheit ? "F" : "C")`.
- **Colour from the FIRST card's `_levels`**, not from the mean — `itemLevel(payload, cards[0].gpu_id, field)`. Comment it as a v4 quirk so a later reader does not "fix" it.
- Multi rows — one per card: `name`, `gpuValue(card.proc)`, and `gpuValue(card.mem)` only when `cards.some((c) => c.mem != null)`. Cell classes from `cellClassFor(payload, card, field)`. **No card-name truncation.**

- [ ] **Step 7: Register, build, verify, stage**

Same shape as Task 5's step 5, with `tests/test_plugin_gpu_render_curses_v5.py` in the run. Update `test_the_registry_renders_every_registered_plugin` to the final six-plugin list.

---

### Task 8: The `network` retrofit, then full verification

**Files:**
- Modify: `glances/plugins/network/render_curses_v5.py`
- Then: everything the group touched.

- [ ] **Step 1: Close the double source**

`network`'s schema already carries `interface`, `Rx/s` and `Tx/s` (added in G9-3), but its renderer still hardcodes the header strings. Make it read `field_label(fields_desc.get(key, {}), key, prefer_short=True)`, exactly as `memswap` does.

The first header cell is the TUI's block title (`NETWORK`), not a field label — it stays a literal. Only the value column headers come from the schema.

- [ ] **Step 2: Prove the TUI did not change**

```bash
uv run pytest tests/test_plugin_network_render_curses_v5.py tests/test_plugin_network_v5.py -q
```
Expected: PASS, **with no edit to either test file**.

- [ ] **Step 3: Full suite**

```bash
uv run pytest -q
```
No NEW failures versus the pre-existing state. If `test_051` fails, re-run it alone. If `test_mcp.py` fails, check for a squatter on 61235 first.

- [ ] **Step 4: v4 untouched**

```bash
git diff --stat HEAD -- glances/outputs/glances_restful_api.py \
  glances/outputs/static/js/app.js glances/outputs/static/js/browser.js \
  glances/outputs/static/js/services.js glances/outputs/static/js/components/ \
  glances/outputs/static/js/App.vue glances/outputs/static/js/Browser.vue \
  glances/outputs/static/js/store.js glances/outputs/static/js/filters.js \
  glances/outputs/static/css/custom.scss glances/outputs/static/css/style.scss \
  glances/outputs/static/templates/index.html
```
Expected: empty. Then the v4 bundle identity check one final time.

- [ ] **Step 5: Hooks and final stage**

```bash
git add -A
make pre-commit
git add -A
git status --short
```
`make pre-commit` runs ~23 hooks and some rewrite files; gitleaks scans the INDEX, which is why it is `add`, `run`, `add`. **If a hook rewrites a v4 file, STOP and report** — do not stage it and do not revert it. Do NOT commit.

- [ ] **Step 6: Report, do not write**

In the task report only, never in the repo:

- The manual UI smoke test owed to the maintainer, with **`gpu`'s title width as its named point of attention** (design spec §8.4). Test with a LONG card name — `NVIDIA GeForce RTX 3080 Ti Laptop GPU` is 37 characters and no fixture carries one. If the title distorts the layout, the fix is `max-width` plus `text-overflow: ellipsis` with the full name in a `title` attribute, never a character count copied from the terminal.
- The `core`/`cpucore` TUI bug (design spec §10): an issue is owed against `glances/plugins/cpu/render_curses_v5.py:183`.
- Release-notes items: the v5 WebUI renders `cpu`, `load`, `memswap` and `gpu`; the WebUI now honours `--meangpu` and `--fahrenheit`.
- Whether the six-component registry has made any part of `AppShell` or the probe feel strained — the next group ports the wide plugins, and this is the last cheap moment to say so.

---

## Self-review notes

Checked against the spec, section by section:

- §5 `serverArgs` → Task 3, including the fallthrough-attribute test the spec calls out.
- §6 `data-plugin` → Task 2, as a pure refactor guarded by the existing render tests.
- §7 formatters → Task 1, base 1024 per the spec's correction, and `toFahrenheit` rather than `formatTemperature` for the reason the spec gives.
- §8.1 `cpu` → Task 6, with all three branches tested and the `core`/`cpucore` obligation carried into the code as a comment.
- §8.2 `load` → Task 4. §8.3 `memswap` → Task 5. §8.4 `gpu` → Task 7, all four render cases plus `--meangpu` and `--fahrenheit`.
- §9 schema refactor → Tasks 4, 7 and 8, each with the "tests must pass unmodified" gate.
- §10 `core` bug → Task 6 (do not propagate) and Task 8 step 6 (issue owed).
- §12 testing → every component task writes its assertions before its component; the manual smoke test is Task 8 step 6.

One thing this plan does that the spec does not require: it promotes `PluginMem.vue`'s scoped `.gl-mem-title` to a global `.gl-plugin-title` in Task 4, because `load`, `memswap` and `cpu` all need the same title row and a scoped copy in each is the `.gl-muted` mistake of G9-2 repeated four times. If a reviewer disagrees, the alternative is four scoped copies, and it costs one line each to revert.

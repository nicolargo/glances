# G9-3 — Making the v5 WebUI foundation scale: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three architectural gaps G9-2's final review found, plus the information-density gap the maintainer raised — one request per tick, a plugin registry, a column model, and TUI parity for `mem` and `network`.

**Architecture:** Backend first (`_key`), because the column model depends on it. Then the single fetch, then the registry and label resolution, then the two components reworked onto all of it, then the folded-in debts and verification. Nothing depends on a later task.

**Tech Stack:** Python/FastAPI, Vue 3 SFC, modern CSS custom properties, webpack 5, `node --test`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-06-glances-v5-g9-3-webui-scaling-design.md`

**Depends on:** G9-2, staged (not yet committed) on `develop-v5`.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.**
- **v4 is read-only.** `glances/outputs/glances_restful_api.py`, `js/app.js`, `js/browser.js`, `js/services.js`, `js/components/**`, `js/App.vue`, `js/Browser.vue`, `js/store.js`, `js/filters.js`, `css/*.scss`, `templates/index.html`. In `webpack.config.js`, **only `v5Config`** may be edited.
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
- **`levels.js` exports exactly `levelClass`, `scalarLevel`, `itemLevel`** — a test asserts that surface. Extend it only deliberately, and update that test in the same change.
- **No dead code may be merged**, with one named exception: the `priority` field in the column descriptor (Task 4), which the spec declares as a deliberate seam.
- **A test whose name claims something structural must actually observe it.** G9-2 shipped two tests that did not (`typeof globalThis.X`, and a probe reading the DOM before any fetch resolved). Prefer asserting real behaviour or a dynamically imported module's export surface.
- `tests/test_restful.py::test_051` is flaky by construction (hard-coded `time.sleep(5)` on a subprocess server) — re-run it alone before believing it. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/plugins/plugin/base_v5.py` | `get_api_payload()` publishes `_key` for collections. |
| `glances/outputs/static/js/v5/api.js` | `fetchAll()` replaces `fetchPlugins()`. |
| `glances/outputs/static/js/v5/labels.js` | Label resolution from `/api/5/<plugin>/info` (new). |
| `glances/outputs/static/js/v5/columns.js` | Column descriptor helpers for collections (new). |
| `glances/outputs/static/js/v5/plugins/index.js` | The plugin registry (new). |
| `glances/outputs/static/js/v5/AppShell.vue` | Renders the registry; one fetch per tick. |
| `glances/outputs/static/js/v5/PluginMem.vue` | Reworked to TUI parity. |
| `glances/outputs/static/js/v5/PluginNetwork.vue` | Reworked onto the column model. |
| `glances/outputs/static/webpack.config.js` | `v5Config`: alias removed, dev server fixed. |
| `eslint.config.mjs` | Extend to `js/v5/**` and `tests/js/**`. |
| `tests/test_plugin_base_v5.py` | `_key` tests (append). |
| `tests/js/api.test.mjs`, `labels.test.mjs`, `columns.test.mjs` | `node --test` units. |
| `tests/test_webserver_v5.py`, `tests/fixtures/webui_render_probe.js` | Render assertions. |

---

### Task 1: `_key` in the API payload

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py` (`get_api_payload()`)
- Test: `tests/test_plugin_base_v5.py` (append)

**Interfaces:**
- Produces: `get_api_payload()` output gains `_key: <primary key field name>` for collection plugins only. Scalar payloads are unchanged.

`self._primary_key` already exists on `GlancesPluginBase` — collection plugins must declare exactly one field with `primary_key: True`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_base_v5.py`, reusing its `FakeScalarPlugin` / `FakeCollectionPlugin` and `make_config`:

```python
# ------------------------------------------------------------------ _key


@pytest.mark.asyncio
async def test_api_payload_publishes_the_primary_key_name_for_a_collection(config):
    """`_levels` for a collection is keyed by the primary key's VALUE. Without
    the key's NAME in the payload, every WebUI component has to hardcode it —
    32 copies of a rule that should live in one place."""
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    payload = plugin.get_api_payload()

    assert payload["_key"] == "name"
    # The value it names really does index _levels.
    assert set(payload["_levels"]) <= {item[payload["_key"]] for item in payload["data"]}


@pytest.mark.asyncio
async def test_api_payload_omits_the_key_for_a_scalar(config):
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)
    await plugin.update()

    assert "_key" not in plugin.get_api_payload()


@pytest.mark.asyncio
async def test_export_view_is_unchanged_by_the_key(config):
    """`_key` is an API-view concept. Exporters must not see it: the export
    layer already injects its own `key` field with different semantics."""
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    for item in plugin.get_export():
        assert "_key" not in item


@pytest.mark.asyncio
async def test_api_payload_is_still_empty_before_the_first_cycle(config):
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)

    assert plugin.get_api_payload() == {}
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_plugin_base_v5.py -k "_key or key_for_a_scalar or unchanged_by_the_key" -v
```
Expected: FAIL — `KeyError: '_key'`.

- [ ] **Step 3: Write the implementation**

In `get_api_payload()`, inside the existing `if self.IS_COLLECTION:` block, beside the `out["data"] = ...` line:

```python
            # The primary key's NAME. `_levels` is keyed by its VALUE, so a
            # consumer that does not know the name cannot walk it without
            # hardcoding the field — which is what 32 WebUI components would
            # otherwise each do. Underscore-prefixed like `_levels`: it is
            # metadata about the payload, not a metric, and `_project()`
            # therefore keeps it out of the export view.
            if self._primary_key:
                out["_key"] = self._primary_key
```

Extend the method's docstring to mention `_key` beside `_levels`.

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_plugin_base_v5.py tests/test_export_base_v5.py tests/test_routes_v5.py tests/test_mcp_adapter_v5.py -q
```
Expected: PASS. `test_export_base_v5.py` must pass **unedited** — if `get_export()` changed, the implementation is in the wrong place.

- [ ] **Step 5: Confirm the live payload**

```bash
timeout 20 uv run python -m glances.main_v5 -s --port 61841 --quiet &
until curl -s --max-time 1 -o /dev/null http://127.0.0.1:61841/api/5/network; do sleep 0.5; done
sleep 2
curl -s http://127.0.0.1:61841/api/5/network | python3 -c "import sys,json; d=json.load(sys.stdin); print('_key =', d.get('_key')); print('levels keys', list(d['_levels'])[:3])"
curl -s http://127.0.0.1:61841/api/5/mem | python3 -c "import sys,json; print('_key in mem:', '_key' in json.load(sys.stdin))"
wait
```
Expected: `_key = interface_name`, `_key in mem: False`. Paste the actual output.

- [ ] **Step 6: Stage**

```bash
git add glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5.py
```

---

### Task 2: One request per tick

**Files:**
- Modify: `glances/outputs/static/js/v5/api.js`
- Modify: `glances/outputs/static/js/v5/AppShell.vue`
- Test: `tests/js/api.test.mjs`

**Interfaces:**
- Consumes: nothing from Task 1 (the shapes are independent).
- Produces: `fetchAll(specs) -> Promise<{results, errors}>` — same return shape as `fetchPlugins`, one HTTP request. `fetchPlugins` is REMOVED, not kept as a wrapper: G9-2 left a dead wrapper behind and it had to be deleted afterwards.

- [ ] **Step 1: Write the failing tests**

Replace `api.test.mjs`'s `fetchPlugins` test with these, keeping every other test in the file untouched:

```js
test("fetchAll issues exactly one request", async () => {
	let calls = 0;
	globalThis.fetch = async () => {
		calls += 1;
		return { ok: true, status: 200, json: async () => ({ mem: { percent: 1 }, network: { data: [] } }) };
	};
	await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	]);
	assert.equal(calls, 1);
});

test("a plugin absent from /all is loading, not an error", async () => {
	// /api/5/all omits a plugin that has not published yet (scheduler cycle 0).
	// That is the same state the per-plugin `200 null` used to signal.
	globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ mem: { percent: 1 } }) });
	const { results, errors } = await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	]);
	assert.deepEqual(results.mem, { percent: 1 });
	assert.equal(results.network, null);
	assert.equal(errors.network, undefined);
});

test("a wrong-shaped slice errors only its own plugin", async () => {
	globalThis.fetch = async () => ({
		ok: true,
		status: 200,
		json: async () => ({ mem: { percent: 1 }, network: { detail: "boom" } }),
	});
	const { results, errors } = await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	]);
	assert.deepEqual(results.mem, { percent: 1 });
	assert.match(errors.network, /shape/i);
	assert.equal(errors.mem, undefined);
});

test("an unreachable /all errors every plugin", async () => {
	// The honest cost of one request: one failure blanks the page. Pinned so
	// the trade is visible rather than discovered.
	globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });
	const { results, errors } = await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
	]);
	assert.equal(results.mem, undefined);
	assert.match(errors.mem, /HTTP 503/);
});
```

Update the import at the top of the file: `fetchPlugins` → `fetchAll`.

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `fetchAll` is not exported.

- [ ] **Step 3: Write the implementation**

In `api.js`, replace `fetchPlugins` entirely with:

```js
export async function fetchAll(specs) {
	// ONE request per tick, not one per plugin. At 34 components and a 2 s
	// cadence, per-plugin fan-out is 17 req/s per open tab against a loop v4
	// hits once. /api/5/all already applies the export filter and keeps
	// `_levels`, so this is a drop-in.
	//
	// The trade, stated plainly: a single failure now blanks every plugin
	// instead of one. That is pinned by a test.
	let all;
	try {
		all = await getJson("api/5/all");
	} catch (e) {
		const errors = {};
		specs.forEach((s) => {
			errors[s.name] = e.message;
		});
		return { results: {}, errors };
	}

	const results = {};
	const errors = {};
	for (const spec of specs) {
		if (!(spec.name in all)) {
			// Absent means the plugin has registered but not published
			// (scheduler cycle 0) -- a loading state, not an error. null is
			// what the component's `v-else-if="!payload"` branch expects.
			results[spec.name] = null;
			continue;
		}
		try {
			results[spec.name] = validate(all[spec.name], spec.spec);
		} catch (e) {
			errors[spec.name] = e.message;
		}
	}
	return { results, errors };
}
```

Note each spec no longer needs a `path`. Leave `getJson`, `validate` and `resolveConfig` untouched.

- [ ] **Step 4: Point the shell at it**

In `AppShell.vue`: change the import from `fetchPlugins` to `fetchAll`, change the call, and drop the now-unused `path` from each entry of the `PLUGINS` array.

- [ ] **Step 5: Run the tests and build**

```bash
uv run pytest tests/test_webui_v5_js.py -q
cd glances/outputs/static && npm run build && cd -
```
Then the v4 bundle identity check. Both IDENTICAL.

```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_tokens.py -q
```

- [ ] **Step 6: Confirm one request, not many**

Start a server, load the page's bundle through the render probe, and confirm from the probe's own fetch stub that `api/5/all` is requested and no `api/5/mem` is. If the probe cannot report request counts, add a counter to its stub and say so.

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/api.js glances/outputs/static/js/v5/AppShell.vue \
        glances/outputs/static/public/glances5.js tests/js/api.test.mjs
```

---

### Task 3: The plugin registry and label resolution

**Files:**
- Create: `glances/outputs/static/js/v5/plugins/index.js`, `glances/outputs/static/js/v5/labels.js`
- Modify: `glances/outputs/static/js/v5/AppShell.vue`
- Test: `tests/js/labels.test.mjs`

**Interfaces:**
- Consumes: `getJson` from `api.js`.
- Produces:
  - `PLUGINS` from `plugins/index.js` — an array of `{ name, spec, component }`.
  - `labels.js`: `resolveLabels(pluginName) -> Promise<Record<field, string>>` and `labelFor(labels, field) -> string`.

- [ ] **Step 1: Write the failing label tests**

Create `tests/js/labels.test.mjs`:

```js
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { resolveLabels, labelFor } from "../../glances/outputs/static/js/v5/labels.js";

beforeEach(() => {
	delete globalThis.fetch;
});

function stubInfo(body, ok = true) {
	globalThis.fetch = async () => ({ ok, status: ok ? 200 : 500, json: async () => body });
}

test("short_name wins over label, which wins over the field name", () => {
	const labels = { a: "SN", b: "Label", c: undefined };
	assert.equal(labelFor(labels, "a"), "SN");
	assert.equal(labelFor(labels, "b"), "Label");
	assert.equal(labelFor(labels, "c"), "c");
	assert.equal(labelFor(labels, "missing"), "missing");
});

test("resolveLabels applies the field_label precedence", async () => {
	// Mirrors glances/outputs/curses_renderer_v5.py:243 field_label():
	// short_name -> label -> field name. Reproducing it means a label improved
	// in the schema improves the TUI and the WebUI at once.
	stubInfo({
		total: { short_name: "total", label: "Total memory" },
		available: { label: "avail" },
		buffers: {},
	});
	const labels = await resolveLabels("mem");
	assert.equal(labels.total, "total");
	assert.equal(labels.available, "avail");
	assert.equal(labelFor(labels, "buffers"), "buffers");
});

test("an unreachable /info degrades to field names, never to blank", async () => {
	globalThis.fetch = async () => {
		throw new TypeError("network error");
	};
	const labels = await resolveLabels("mem");
	assert.deepEqual(labels, {});
	assert.equal(labelFor(labels, "total"), "total");
});

test("resolveLabels fetches once per plugin and caches", async () => {
	let calls = 0;
	globalThis.fetch = async () => {
		calls += 1;
		return { ok: true, status: 200, json: async () => ({ x: { label: "X" } }) };
	};
	await resolveLabels("cachetest");
	await resolveLabels("cachetest");
	assert.equal(calls, 1);
});
```

> **NOTE:** this snippet has a bug the shipped test does not. Its second and third tests both call `resolveLabels("mem")`, and the module-level cache is never cleared between tests, so the third would read the cached value from the second instead of exercising the unreachable-`/info` path. `tests/js/labels.test.mjs` as shipped uses a distinct plugin name there.

- [ ] **Step 2: Run to verify they fail**, then write `labels.js`

```js
// Glances v5 WebUI -- field labels, resolved from the plugin schema.
//
// `/api/5/<plugin>/info` serves `fields_description`. The schema does not
// change at runtime, so it is fetched once per plugin and cached.
//
// The precedence mirrors field_label() in
// glances/outputs/curses_renderer_v5.py:243 exactly: short_name -> label ->
// field name. Reproducing it is the point: a label improved in the schema
// then improves the TUI and the WebUI together, and a plugin component
// writes no labels at all.

import { getJson } from "./api.js";

const cache = new Map();

export async function resolveLabels(pluginName) {
	if (cache.has(pluginName)) return cache.get(pluginName);

	let schema;
	try {
		schema = await getJson(`api/5/${pluginName}/info`);
	} catch {
		// A missing label must never blank a value: fall back to field names.
		cache.set(pluginName, {});
		return {};
	}

	const labels = {};
	for (const [field, desc] of Object.entries(schema || {})) {
		const label = (desc && (desc.short_name || desc.label)) || undefined;
		if (label) labels[field] = label;
	}
	cache.set(pluginName, labels);
	return labels;
}

export function labelFor(labels, field) {
	return (labels && labels[field]) || field;
}
```

- [ ] **Step 3: Write the registry**

Create `glances/outputs/static/js/v5/plugins/index.js`:

```js
// Glances v5 WebUI -- the plugin registry.
//
// Adding a plugin is ONE new .vue file plus ONE entry here. Before this,
// AppShell named every plugin in four places (import, components map, spec
// list, template): 32 ports x 4 edits to one file is 32 merge-conflict
// surfaces, and it contradicts the project's rule to prefer discovery
// mechanisms over hardcoded lists that require touching a central file.
//
// `spec` is what the service layer validates the payload against. `shape` is
// "scalar" or "collection" -- the only two payload shapes v5 has.

import PluginMem from "../PluginMem.vue";
import PluginNetwork from "../PluginNetwork.vue";

export const PLUGINS = [
	{
		name: "mem",
		component: PluginMem,
		spec: { shape: "scalar", required: ["percent", "total"] },
	},
	{
		name: "network",
		component: PluginNetwork,
		spec: { shape: "collection", required: ["interface_name"] },
	},
];
```

- [ ] **Step 4: Reduce the shell to rendering the registry**

In `AppShell.vue`: import `PLUGINS` from `./plugins/index.js`, drop the per-plugin imports and the `components` map, and replace the three hardcoded `<PluginX>` tags with a loop:

```html
		<section class="gl-plugins">
			<component
				:is="plugin.component"
				v-for="plugin in plugins"
				:key="plugin.name"
				:payload="results[plugin.name]"
				:error="errors[plugin.name]"
				:labels="labels[plugin.name] || {}"
			/>
		</section>
```

Resolve labels once at mount, in parallel, and store them by plugin name:

```js
		const entries = await Promise.all(
			PLUGINS.map(async (p) => [p.name, await resolveLabels(p.name)]),
		);
		this.labels = Object.fromEntries(entries);
```

- [ ] **Step 5: Prove the registry is a real seam**

Add to `tests/test_webserver_v5.py` a test that renders the bundle through the probe and asserts BOTH registered plugins appear. Then, temporarily, add a third trivial entry to `plugins/index.js` pointing at an existing component, rebuild, and confirm it renders **without any edit to `AppShell.vue`**. Remove it, rebuild, confirm green. Report both outcomes — a registry nobody has added to is a registry nobody knows works.

- [ ] **Step 6: Build, check, stage**

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check, then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
git add glances/outputs/static/js/v5/labels.js glances/outputs/static/js/v5/plugins/index.js \
        glances/outputs/static/js/v5/AppShell.vue glances/outputs/static/public/glances5.js \
        tests/js/labels.test.mjs tests/test_webserver_v5.py
```

---

### Task 4: The column model, and `network` at TUI parity

**Files:**
- Create: `glances/outputs/static/js/v5/columns.js`
- Modify: `glances/outputs/static/js/v5/PluginNetwork.vue`
- Test: `tests/js/columns.test.mjs`

**Interfaces:**
- Consumes: `levelClass`, `itemLevel` from `levels.js`; `_key` from the payload (Task 1); `labelFor` from `labels.js`.
- Produces: `cellClassFor(payload, item, field) -> string` and `columnLabel(columns, labels, field) -> string` from `columns.js`.

- [ ] **Step 1: Write the failing tests**

Create `tests/js/columns.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { cellClassFor } from "../../glances/outputs/static/js/v5/columns.js";

const PAYLOAD = {
	_key: "interface_name",
	data: [{ interface_name: "eth0", bytes_recv: 10 }],
	_levels: { eth0: { bytes_recv: { level: "warning", prominent: true } } },
};

test("the tier class is resolved through the payload's _key", () => {
	const item = PAYLOAD.data[0];
	assert.equal(cellClassFor(PAYLOAD, item, "bytes_recv"), "gl-level-warning gl-prominent");
	assert.equal(cellClassFor(PAYLOAD, item, "interface_name"), "");
});

test("a payload without _key falls back rather than throwing", () => {
	// An older server does not publish _key. A component must still render.
	const legacy = { data: PAYLOAD.data, _levels: PAYLOAD._levels };
	assert.equal(cellClassFor(legacy, legacy.data[0], "bytes_recv"), "");
});

test("an item whose key value has no _levels entry yields no class", () => {
	const item = { interface_name: "lo", bytes_recv: 0 };
	assert.equal(cellClassFor(PAYLOAD, item, "bytes_recv"), "");
});
```

- [ ] **Step 2: Run to verify they fail**, then write `columns.js`

```js
// Glances v5 WebUI -- collection column helpers.
//
// `_levels` for a collection is keyed by the primary key's VALUE. The payload
// now publishes the key's NAME as `_key` (see get_api_payload), so this rule
// lives here once instead of being retyped in every collection component.

import { levelClass, itemLevel } from "./levels.js";

export function cellClassFor(payload, item, field) {
	const keyField = payload && payload._key;
	if (!keyField) return "";
	return levelClass(itemLevel(payload, item[keyField], field));
}
```

- [ ] **Step 3: Rework `PluginNetwork.vue` onto a descriptor**

Replace its hand-written `<th>`/`<td>` markup with a `COLUMNS` descriptor and a loop. The descriptor's shape:

```js
const COLUMNS = [
	{ field: "interface_name", format: (v) => v, priority: 0 },
	{ field: "bytes_recv", format: formatRate, priority: 1 },
	{ field: "bytes_sent", format: formatRate, priority: 1 },
];
```

`priority` is **declared and unread in this group** — it is the seam responsive
dropping will need, and retro-fitting it across 32 descriptors later is the
expensive alternative. The spec names this as the one permitted exception to
the no-dead-code rule; do not add a dropping mechanism to justify it.

Labels come from the `labels` prop via `labelFor`, not from strings in the
component. Header cells keep `class="gl-header"` and never a tier class; only
value cells get `cellClassFor(...)`.

- [ ] **Step 4: Tests, build, stage**

```bash
uv run pytest tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check, then `uv run pytest tests/test_webserver_v5.py -q`, then:
```bash
git add glances/outputs/static/js/v5/columns.js glances/outputs/static/js/v5/PluginNetwork.vue \
        glances/outputs/static/public/glances5.js tests/js/columns.test.mjs
```

---

### Task 5: `mem` at TUI parity

**Files:**
- Modify: `glances/outputs/static/js/v5/PluginMem.vue`
- Modify: `glances/outputs/static/css/v5.css` (grid utility only)
- Test: `tests/test_webserver_v5.py` (append)

**Interfaces:**
- Consumes: `formatBytes`, `formatPercent`; `levelClass`, `scalarLevel`; `labelFor`.
- Produces: no new module.

Reference — what the TUI renders (`glances/plugins/mem/render_curses_v5.py:16-28`):

```
    MEM    53.2%      active   5.8G
    total  15.3G    inactive   4.4G
    avail   7.2G     buffers   185M
    free    2.6G      cached   4.2G
```

Eight statistics, a 2-column grid of (label, value) pairs, the title line carrying the percent, and an `avail`-vs-`used` switch: show `available` when the payload has it (Linux, macOS), otherwise `used`.

- [ ] **Step 1: Write the failing render assertions**

Append to `tests/test_webserver_v5.py` a probe-driven test that stubs `/api/5/all` with a full `mem` payload and asserts the rendered text contains all eight statistics, and a second that stubs a payload WITHOUT `available` and asserts `used` is shown instead. Follow the existing probe test's structure; extend the probe's fetch stub rather than writing a second harness.

- [ ] **Step 2: Rework the component**

Two columns of (label, value) pairs; the title row carries `MEM` (with `gl-header`) and the percent, whose class comes from `scalarLevel(payload, "percent")`. Column 1: `total`, then `avail` or `used`, then `free`. Column 2: `active`, `inactive`, `buffers`, `cached`.

Labels via `labelFor(labels, field)`. No hardcoded label strings, and no colour literals — the grid utility goes in `css/v5.css` beside the other global utilities, not in a scoped block (G9-2 shipped a `.gl-muted` that never applied because it was scoped).

- [ ] **Step 3: Build, verify, stage**

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check, then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_tokens.py -q
```
Then a real end-to-end look: start `python -m glances.main_v5 -s --port 61842 --quiet`, fetch `/api/5/mem`, and confirm every field the component reads is present in the live payload. Paste the output.

```bash
git add glances/outputs/static/js/v5/PluginMem.vue glances/outputs/static/css/v5.css \
        glances/outputs/static/public/glances5.js tests/test_webserver_v5.py
```

---

### Task 6: Folded-in debts, then full verification

**Files:**
- Modify: `glances/outputs/static/webpack.config.js` (`v5Config` only), `eslint.config.mjs`
- Then: all files touched by Tasks 1-5.

- [ ] **Step 1: Remove the `vue.esm-bundler` alias**

Delete the `resolve: { alias: { vue: ... } }` entry from `v5Config`. Measured: 61.7 KB of a 192 KB bundle, and the compiler is not tree-shaken. Every component is a compiled SFC and no `template:` string survives, so the runtime build suffices.

Rebuild, then confirm BOTH: `public/glances5.js` shrank by roughly 60 KB, and `test_the_v5_bundle_actually_renders_an_element` still passes. That test is precisely the guard against this change being wrong — report the before and after sizes.

- [ ] **Step 2: Make `npm start` serve the v5 app**

`v5Config`'s `devServer` currently has no `/api` proxy and no HTML plugin, so `npm start` serves v4's generated index and every `fetch("api/5/…")` 404s. Add an `HtmlWebpackPlugin` pointing at `templates/index_v5.html` and a `proxy`
entry. Copy `v4Config`'s block verbatim — it is the array form
webpack-dev-server 5 expects, and inventing the object form silently does
nothing:

```js
			proxy: [
				{
					context: ["/api"],
					target: "http://0.0.0.0:61208",
				},
			],
```

Verify by starting the dev server and fetching its root and one API path. If you cannot run it in this environment, say so plainly rather than claiming it works.

- [ ] **Step 3: Bring the v5 JS under eslint**

`eslint.config.mjs` covers `**/*.{ts,vue}` only, so `js/v5/*.js` and `tests/js/*.mjs` are unlinted, and eslint is absent from `.pre-commit-config.yaml` entirely. Extend the config's file globs to cover them. Do NOT add eslint to pre-commit in this task — that is a repo-wide decision with its own blast radius; report it as a follow-up.

Run `npx eslint js/v5 ../../../tests/js` from `glances/outputs/static/` (adjust the path as needed) and fix what it reports in files this group owns. If it flags v4 files, leave them and say so.

- [ ] **Step 4: Full suite**

```bash
uv run pytest -q
```
No new failures. `test_051` flaky — re-run alone. `test_mcp.py` — check for a squatter on 61235 first.

- [ ] **Step 5: v4 untouched**

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

- [ ] **Step 6: Hooks and final stage**

```bash
git add -A
make pre-commit
git add -A
git status --short
```
Do NOT commit.

- [ ] **Step 7: Report, do not write**

In the task report only, never in the repo:

- Release-notes items: `_key` added to the `/api/5` payload (additive, underscore-prefixed beside `_levels`); the v5 WebUI now renders `mem` and `network` at TUI parity.
- Bundle size before and after the alias removal.
- Whether `node --test` is still sufficient, now that there are five JS test files and a column model — or whether a real runner is now warranted.
- Whether eslint should join `.pre-commit-config.yaml`.

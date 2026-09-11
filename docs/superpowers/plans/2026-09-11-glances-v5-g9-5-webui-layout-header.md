# G9-5 — v5 WebUI page skeleton and header plugins: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the v5 WebUI the TUI's page structure (header / top / left / right, alerts in the footer), render the five header plugins in it, batch the schema fetch into `/api/5/all/info`, and stop rendering plugins the server never instantiated.

**Architecture:** Server route first (Task 1), then the pure JS modules that carry every decision the shell makes (Task 2), then the shell itself re-laid-out around a `slot` attribute on the registry, with the drift guard that pays for keeping that attribute in JS (Task 3). The five header components follow in two tasks by difficulty (Tasks 4 and 5), then full verification (Task 6). No TUI Python file changes anywhere in this plan.

**Tech Stack:** Vue 3.5 SFC (options API), webpack 5, `node --test`, pytest, FastAPI, Python 3.

**Spec:** `docs/superpowers/specs/2026-09-11-glances-v5-g9-5-webui-layout-header-design.md`

**Depends on:** G9-4, committed as `5ba16bb2`; parity wave 1, committed as `7f407948`.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer. Never `git clean`, never `git checkout`/`restore` over working files, never `git stash`.
- **Never touch `NEWS.rst`.**
- **No TUI Python file may change.** Nothing under `glances/plugins/*/render_curses_v5.py`, `glances/plugins/*/model_v5.py`, `glances/outputs/curses_renderer_v5.py`, `glances/outputs/glances_curses_v5.py`, `glances/outputs/curses_formatters_v5.py`. Consequently no `tests/test_*render_curses_v5.py` and no `tests/test_curses_renderer_v5.py` may change either. If a task seems to need one, STOP and report.
- **v4 is read-only.** `glances/outputs/glances_restful_api.py`, `js/app.js`, `js/browser.js`, `js/services.js`, `js/components/**`, `js/App.vue`, `js/Browser.vue`, `js/store.js`, `js/filters.js`, `js/uiconfig.json`, `css/*.scss`, `templates/index.html`. `webpack.config.js` is not touched by this plan. `css/v5.css` IS in scope.
- **After every `npm run build`, the v4 bundles must be byte-identical:**
  ```bash
  for f in glances.js browser.js; do
    W=$(git hash-object glances/outputs/static/public/$f)
    C=$(git rev-parse HEAD:glances/outputs/static/public/$f)
    [ "$W" = "$C" ] && echo "$f IDENTICAL" || echo "$f DIFFERS"
  done
  ```
  Both must print IDENTICAL. If either DIFFERS, STOP and report — do not rebuild, do not `git checkout`, do not stage them.
- **Build with `npm run build` only**, from `glances/outputs/static`. Never `npm install` (`package-lock.json` is tracked); `npm ci` is acceptable if `node_modules` is missing.
- **No new npm dependency. No new Python dependency.**
- **No colour literal under `js/v5/`** — enforced by `tests/test_webui_v5_tokens.py`. Use the tokens in `css/v5.css`.
- **`levels.js` exports exactly `levelClass`, `scalarLevel`, `itemLevel`** — a test asserts that surface. Do not extend it. `columns.js` is not touched either.
- **No dead code may be merged.** A function added in one task and first called in a later task of this plan is acceptable only where the plan says so; nothing may be left uncalled at the end of Task 6.
- **A test whose name claims something must actually observe it.** Prefer asserting rendered behaviour through the probe over asserting source text.
- **Lint the JS you touch:** from the repository root,
  ```bash
  glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
  ```
  It must print nothing. (`.vue` files are covered by `make pre-commit` in Task 6.) If `npx`/the binary fails through the harness, say so in the report — do not skip silently.
- **Reports must not invent mechanisms.** If you observe something you cannot explain (a byte delta, a flaky pass), write "I cannot explain this" rather than a plausible cause.
- `tests/test_restful.py::test_050/051` are flaky by construction (hard-coded `time.sleep(5)` on a subprocess server) — re-run alone before believing a failure. `tests/test_mcp.py` fails when a stale server squats port 61235 (`ss -lptn 'sport = :61235'`).

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/routes_v5.py` | `GET /api/5/all/info` (Task 1). |
| `glances/outputs/static/js/v5/layout.js` | **New.** `visiblePlugins(registry, names)`, `groupBySlot(entries)` — pure (Task 2). |
| `glances/outputs/static/js/v5/labels.js` | `resolveAllLabels()` replaces `resolveLabels(name)` (added Task 2, old one removed Task 3). |
| `glances/outputs/static/js/v5/api.js` | `resolvePluginNames()` (Task 2). |
| `glances/outputs/static/js/v5/format.js` | `formatSeconds(value)` (Task 4). |
| `glances/outputs/static/js/v5/plugins/index.js` | `slot` on every entry, TUI order (Task 3); five new entries (Tasks 4, 5). |
| `glances/outputs/static/js/v5/AppShell.vue` | Zones from slots, visibility, batch labels, footer cadence, top bar removed (Task 3). |
| `glances/outputs/static/js/v5/PluginSystem.vue`, `PluginUptime.vue`, `PluginNow.vue` | **New** (Task 4). |
| `glances/outputs/static/js/v5/PluginIp.vue`, `PluginCloud.vue` | **New** (Task 5). |
| `glances/outputs/static/css/v5.css` | `.gl-inline`, `.gl-truncate` (Task 4). |
| `tests/test_routes_v5.py` | `/all/info` tests (Task 1). |
| `tests/js/layout.test.mjs` | **New** (Task 2). Auto-discovered by `tests/test_webui_v5_js.py`. |
| `tests/js/labels.test.mjs`, `tests/js/api.test.mjs`, `tests/js/format.test.mjs` | Unit tests (Tasks 2, 3, 4). |
| `tests/fixtures/webui_render_probe.js` | `/all/info` + `pluginslist` stubs, `[data-plugin]` collection, `slots`, `pluginHidden`, header fixtures (Tasks 3–5). |
| `tests/test_webserver_v5.py` | Drift guard, visibility, footer, header render tests (Tasks 3–5). |
| `glances/outputs/static/public/glances5.js` | Rebuilt bundle (Tasks 3–5). |

---

### Task 1: `GET /api/5/all/info`

**Files:**
- Modify: `glances/routes_v5.py` (module docstring route table; new handler after `all_limits`)
- Test: `tests/test_routes_v5.py`

**Interfaces:**
- Produces: `GET /api/5/all/info` → `200`, JSON object `{plugin_name: fields_description}` for **every registered plugin, published or not**. Empty registry → `{}`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_routes_v5.py`, directly after `test_plugin_info_unknown_404`, add:

```python
def test_all_info_returns_every_registered_schema(config_factory, store):
    """One request for every schema: the WebUI resolves its labels once at
    page load instead of one /info call per plugin (G9-5 spec §6.2).

    Neither plugin is populated. Unlike /api/5/all, which skips a plugin that
    has not published, a schema is static and must be served regardless --
    otherwise a plugin still at cycle 0 when the tab opens would keep
    field-name labels for the tab's whole life.

    Also the route-ordering guard: before the handler exists, `all` is read as
    a plugin name by /{plugin_name}/info and the request 404s.
    """
    config = config_factory()
    scalar = FakeScalarPlugin(store, config)
    collection = FakeCollectionPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[scalar, collection])
    with TestClient(app) as client:
        r = client.get("/api/5/all/info")
    assert r.status_code == 200
    assert r.json() == {
        "fakescalar": FakeScalarPlugin.fields_description,
        "fakecollection": FakeCollectionPlugin.fields_description,
    }


def test_all_info_empty_registry(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/all/info")
    assert r.status_code == 200
    assert r.json() == {}
```

In the module docstring's `Coverage:` list, after the `/api/5/<plugin>/info` line, add:

```
- /api/5/all/info: every registered schema, published or not; {} when empty
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_routes_v5.py -q -k all_info
```
Expected: 2 FAIL, both with status 404 (`all` captured as a plugin name).

- [ ] **Step 3: Implement**

In `glances/routes_v5.py`, directly after the `all_limits` handler (and therefore before `@router.get("/{plugin_name}/info")`), add:

```python
    @router.get("/all/info")
    async def all_info(request: Request) -> dict[str, Any]:
        # Declared BEFORE /{plugin_name}/info, for the same reason as
        # /all/limits above. Every registered plugin is included, published
        # or not: a schema is static, unlike the payloads /all skips at
        # cycle 0. The WebUI fetches this once per page load.
        return {name: plugin.fields_description for name, plugin in _plugins(request).items()}
```

In the module docstring's route table, after the `/api/5/all/limits` row, add a row aligned like its neighbours:

```
| ``/api/5/all/info``           | GET    | per-plugin ``fields_description`` |
```

- [ ] **Step 4: Run to verify they pass, and nothing else moved**

```bash
uv run pytest tests/test_routes_v5.py -q
uv run ruff check glances/routes_v5.py tests/test_routes_v5.py
```
Expected: all PASS; ruff clean. `build_router()` is near ruff's complexity ceiling (see `_redact_args`'s docstring). If ruff reports C901 or PLR0915 on it, move the dict comprehension into a module-level helper `_all_info(request)` beside `_redact_args` and call it from the handler — do not add a `noqa`.

- [ ] **Step 5: Stage**

```bash
git add glances/routes_v5.py tests/test_routes_v5.py
```

---

### Task 2: The pure modules — `layout.js`, `resolveAllLabels`, `resolvePluginNames`

**Files:**
- Create: `glances/outputs/static/js/v5/layout.js`
- Modify: `glances/outputs/static/js/v5/labels.js` (add `resolveAllLabels`; `resolveLabels` stays until Task 3)
- Modify: `glances/outputs/static/js/v5/api.js` (add `resolvePluginNames`)
- Create: `tests/js/layout.test.mjs`
- Test: `tests/js/labels.test.mjs`, `tests/js/api.test.mjs` (append)

**Interfaces:**
- Consumes: `getJson(path)` from `api.js`; `GET /api/5/all/info` (Task 1); `GET /api/5/pluginslist` (existing, returns a sorted `string[]`).
- Produces:
  - `visiblePlugins(registry: Entry[], names: string[] | null) -> Entry[]` — registry order preserved; `names` not an array → the registry itself.
  - `groupBySlot(entries: Entry[]) -> { [slot: string]: Entry[] }` — registry order kept inside each slot; a slot no entry uses is absent.
  - `resolveAllLabels() -> Promise<{ [plugin: string]: { [field: string]: string } }>` — one fetch; failure → `{}`. No cache (it is called once per page load).
  - `resolvePluginNames() -> Promise<string[] | null>` — failure or non-array body → `null`. No cache.

`resolveAllLabels` and `resolvePluginNames` have no caller until Task 3, which also removes `resolveLabels`. That transient is permitted by the Global Constraints; nothing is built in this task.

- [ ] **Step 1: Write the failing tests**

Create `tests/js/layout.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { visiblePlugins, groupBySlot } from "../../glances/outputs/static/js/v5/layout.js";

const REGISTRY = [
	{ name: "system", slot: "header-left" },
	{ name: "uptime", slot: "header-right" },
	{ name: "cloud", slot: "header-right" },
	{ name: "now", slot: "header-right" },
	{ name: "cpu", slot: "top" },
	{ name: "network", slot: "left" },
];

test("visiblePlugins keeps only what the server instantiated, in registry order", () => {
	// pluginslist is SORTED server-side; the registry order must win, or the
	// page would lay out alphabetically.
	const names = ["cloud", "cpu", "network", "now", "system", "uptime"].filter((n) => n !== "cloud");
	assert.deepEqual(
		visiblePlugins(REGISTRY, names).map((e) => e.name),
		["system", "uptime", "now", "cpu", "network"],
	);
});

test("visiblePlugins ignores a server plugin the registry has no component for", () => {
	assert.deepEqual(
		visiblePlugins(REGISTRY, ["cpu", "processlist"]).map((e) => e.name),
		["cpu"],
	);
});

test("an unreadable pluginslist renders the whole registry", () => {
	// null is what resolvePluginNames() returns on failure. Falling back to
	// the full registry is exactly the behaviour before visibility existed.
	assert.equal(visiblePlugins(REGISTRY, null), REGISTRY);
	assert.equal(visiblePlugins(REGISTRY, { detail: "nope" }), REGISTRY);
});

test("groupBySlot keeps registry order inside a slot and omits unused slots", () => {
	const slots = groupBySlot(REGISTRY);
	assert.deepEqual(Object.keys(slots).sort(), ["header-left", "header-right", "left", "top"]);
	assert.deepEqual(slots["header-right"].map((e) => e.name), ["uptime", "cloud", "now"]);
	assert.equal(slots.right, undefined);
});
```

Append to `tests/js/labels.test.mjs`, and add `resolveAllLabels` to the import at the top (keep `resolveLabels` imported for now):

```js
test("resolveAllLabels applies the field_label precedence per plugin, in one fetch", async () => {
	const paths = [];
	globalThis.fetch = async (path) => {
		paths.push(path);
		return {
			ok: true,
			status: 200,
			json: async () => ({
				mem: { total: { short_name: "total", label: "Total memory" }, available: { label: "avail" }, buffers: {} },
				network: { bytes_recv: { short_name: "Rx/s" } },
			}),
		};
	};
	const labels = await resolveAllLabels();
	// ONE request whatever the number of plugins -- the point of the batch.
	assert.deepEqual(paths, ["api/5/all/info"]);
	assert.equal(labels.mem.total, "total");
	assert.equal(labels.mem.available, "avail");
	assert.equal(labelFor(labels.mem, "buffers"), "buffers");
	assert.equal(labels.network.bytes_recv, "Rx/s");
});

test("an unreachable /all/info degrades to field names for every plugin", async () => {
	globalThis.fetch = async () => ({ ok: false, status: 500, json: async () => ({ detail: "boom" }) });
	const labels = await resolveAllLabels();
	assert.deepEqual(labels, {});
	assert.equal(labelFor(labels.mem, "total"), "total");
});
```

`labelFor(undefined, "total")` must return `"total"` — it already does (`(labels && labels[field]) || field`); the second test pins it, because `AppShell` will pass `labels[name] || {}` but a component may not.

Append to `tests/js/api.test.mjs`, adding `resolvePluginNames` to the import at the top:

```js
test("resolvePluginNames returns the server's plugin list", async () => {
	stubFetch({ "api/5/pluginslist": { body: ["cpu", "mem"] } });
	assert.deepEqual(await resolvePluginNames(), ["cpu", "mem"]);
});

test("resolvePluginNames returns null when the list cannot be read", async () => {
	stubFetch({ "api/5/pluginslist": { status: 500, body: { detail: "boom" } } });
	assert.equal(await resolvePluginNames(), null);
	// A 200 carrying the wrong shape is not a list either.
	stubFetch({ "api/5/pluginslist": { body: { detail: "nope" } } });
	assert.equal(await resolvePluginNames(), null);
	// Network failure: stubFetch throws for an unknown route.
	stubFetch({});
	assert.equal(await resolvePluginNames(), null);
});
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `layout.js` missing, `resolveAllLabels` and `resolvePluginNames` not exported.

- [ ] **Step 3: Implement `layout.js`**

Create `glances/outputs/static/js/v5/layout.js`:

```js
// Glances v5 WebUI -- page layout: which registered plugins render, and where.
//
// Pure: no DOM, no fetch, no imports. It is not in plugins/index.js because
// that module imports .vue files, which `node --test` cannot load -- logic
// placed there could never be unit-tested.

export function visiblePlugins(registry, names) {
	// `names` is /api/5/pluginslist: the plugins the server instantiated. A
	// disabled plugin is never instantiated (glances/main_v5.py:372), so it is
	// never in /api/5/all either, and fetchAll() would read its absence as
	// "loading" forever -- `cloud` is disabled by default.
	//
	// Anything but an array means the list could not be read: render the whole
	// registry, which is exactly the behaviour before this function existed.
	if (!Array.isArray(names)) return registry;
	const enabled = new Set(names);
	// Filter the REGISTRY, not the names: pluginslist is sorted server-side,
	// and the registry order is the layout order.
	return registry.filter((entry) => enabled.has(entry.name));
}

export function groupBySlot(entries) {
	const slots = {};
	for (const entry of entries) {
		if (!slots[entry.slot]) slots[entry.slot] = [];
		slots[entry.slot].push(entry);
	}
	return slots;
}
```

- [ ] **Step 4: Implement `resolveAllLabels`**

In `glances/outputs/static/js/v5/labels.js`, extract the precedence loop into a private helper and add the batch function. The file becomes (keeping `resolveLabels` and its cache for Task 3 to remove):

```js
// Glances v5 WebUI -- field labels, resolved from the plugin schema.
//
// `/api/5/all/info` serves every plugin's `fields_description` in one
// request. The schema does not change at runtime, so it is fetched once per
// page load (AppShell.mounted).
//
// The precedence mirrors field_label() in
// glances/outputs/curses_renderer_v5.py:243 exactly: short_name -> label ->
// field name. Reproducing it is the point: a label improved in the schema
// then improves the TUI and the WebUI together, and a plugin component
// writes no labels at all.

import { getJson } from "./api.js";

const cache = new Map();

function labelsFromSchema(schema) {
	const labels = {};
	for (const [field, desc] of Object.entries(schema || {})) {
		const label = (desc && (desc.short_name || desc.label)) || undefined;
		if (label) labels[field] = label;
	}
	return labels;
}

export async function resolveAllLabels() {
	let schemas;
	try {
		schemas = await getJson("api/5/all/info");
	} catch {
		// A missing label must never blank a value: fall back to field names.
		// A transient failure here pins field-name labels for the tab's life --
		// acceptable because this is ONE request per page load, where G9-4 made
		// one per plugin.
		return {};
	}
	const labels = {};
	for (const [plugin, schema] of Object.entries(schemas || {})) {
		labels[plugin] = labelsFromSchema(schema);
	}
	return labels;
}

export async function resolveLabels(pluginName) {
	if (cache.has(pluginName)) return cache.get(pluginName);

	let schema;
	try {
		schema = await getJson(`api/5/${pluginName}/info`);
	} catch {
		cache.set(pluginName, {});
		return {};
	}

	const labels = labelsFromSchema(schema);
	cache.set(pluginName, labels);
	return labels;
}

export function labelFor(labels, field) {
	return (labels && labels[field]) || field;
}
```

- [ ] **Step 5: Implement `resolvePluginNames`**

In `glances/outputs/static/js/v5/api.js`, directly after `resolveArgs()`, add:

```js
export async function resolvePluginNames() {
	// /api/5/pluginslist: the plugins the server actually instantiated. Read
	// once per page load. When runtime plugin toggling lands (#3548), a plugin
	// enabled after the tab opened appears on the next reload -- a known
	// limitation, not a bug to fix with a per-tick fetch.
	//
	// null, never [], on failure: an empty list would hide every plugin, while
	// null tells visiblePlugins() to fall back to the whole registry.
	try {
		const names = await getJson("api/5/pluginslist");
		return Array.isArray(names) ? names : null;
	} catch {
		return null;
	}
}
```

- [ ] **Step 6: Run to verify they pass, then lint**

```bash
uv run pytest tests/test_webui_v5_js.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
```
Expected: PASS; eslint prints nothing.

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/layout.js glances/outputs/static/js/v5/labels.js \
        glances/outputs/static/js/v5/api.js tests/js/layout.test.mjs \
        tests/js/labels.test.mjs tests/js/api.test.mjs
```

---

### Task 3: The page skeleton

**Files:**
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `glances/outputs/static/js/v5/AppShell.vue` (full rewrite given below)
- Modify: `glances/outputs/static/js/v5/labels.js` (remove `resolveLabels` and its cache)
- Modify: `tests/js/labels.test.mjs` (remove the three `resolveLabels` tests)
- Modify: `tests/fixtures/webui_render_probe.js`
- Modify: `tests/test_webserver_v5.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: `visiblePlugins`, `groupBySlot` (layout.js), `resolveAllLabels` (labels.js), `resolvePluginNames` (api.js) — all from Task 2.
- Produces:
  - Every registry entry has `slot` ∈ {`header-left`, `header-right`, `top`, `left`, `right`}.
  - DOM: `<main class="gl-app">` → zones (`<header class="gl-zone gl-zone-header">`, `<section class="gl-zone gl-zone-top">`, `<div class="gl-zone gl-zone-body">`) → `<section class="gl-slot gl-slot-<slot>" data-slot="<slot>">` → plugin roots carrying `data-plugin`. Then `<footer class="gl-alerts">` holding the alert list and `<span class="gl-muted gl-refresh">refresh Ns</span>`.
  - Probe output gains `slots: { [slot]: string[] }` (ordered `data-plugin` values per `[data-slot]`). `pluginNames`/`pluginText`/`pluginAttrs`/… are now collected from every element carrying `data-plugin`, not only `.gl-plugin` articles.
  - Probe scenarios `gpu-disabled` and `pluginslist-unreachable`.

- [ ] **Step 1: Teach the probe the new endpoints and the slot structure**

In `tests/fixtures/webui_render_probe.js`:

(a) Replace the comment above `INFO_FIXTURES` (the block starting `// \`fields_description\` shape for \`/api/5/<plugin>/info\``) with:

```js
// `/api/5/all/info` answer: plugin -> fields_description, as labels.js'
// resolveAllLabels() expects it. Real enough that the short_name -> label ->
// field name precedence has something to resolve, rather than degrading to
// field names by accident. short_names for the mem fields are copied from
// glances/plugins/mem/model_v5.py so the rendered labels match the TUI
// ("avail", "inacti", "buffer"). Keyed by plugin: a single schema shared by
// every plugin would make a network header assertion meaningless.
```

(b) Directly after `INFO_FIXTURES`, add:

```js
// `/api/5/pluginslist` default answer: every plugin a v5 server instantiates
// when nothing is disabled -- the plugin directories carrying a model_v5.py.
// `cloud` is included although it is disabled by default on a real server:
// the header render tests need it instantiated. A scenario absent from
// PLUGINSLIST_FIXTURES gets this list.
const SERVER_PLUGINS = [
	"amps", "cloud", "connections", "containers", "core", "cpu", "diskio", "folders", "fs", "gpu",
	"ip", "irq", "load", "mem", "memswap", "mpp", "network", "now", "npu", "percpu", "ports",
	"processcount", "processlist", "programlist", "psutilversion", "quicklook", "raid", "sensors",
	"smart", "system", "uptime", "version", "vms", "wifi",
];

// Per-scenario `/api/5/pluginslist` answers. `null` means the endpoint fails
// (HTTP 500), which must render the whole registry.
const PLUGINSLIST_FIXTURES = {
	"gpu-disabled": SERVER_PLUGINS.filter((name) => name !== "gpu"),
	"pluginslist-unreachable": null,
};
```

(c) Replace the whole `fakeFetch` function with:

```js
async function fakeFetch(url) {
	const path = String(url);
	if (path.includes("api/5/alert")) {
		return { ok: true, status: 200, json: async () => ALERT_FIXTURES };
	}
	// BEFORE the `api/5/all` check below: "api/5/all/info" contains
	// "api/5/all", and would otherwise be answered with the stats payload.
	if (path.includes("api/5/all/info")) {
		return { ok: true, status: 200, json: async () => INFO_FIXTURES };
	}
	if (path.includes("api/5/pluginslist")) {
		const names = scenario in PLUGINSLIST_FIXTURES ? PLUGINSLIST_FIXTURES[scenario] : SERVER_PLUGINS;
		if (names === null) {
			return { ok: false, status: 500, json: async () => ({ detail: "boom" }) };
		}
		return { ok: true, status: 200, json: async () => names };
	}
	if (path.includes("api/5/all")) {
		return { ok: true, status: 200, json: async () => ALL_FIXTURES[scenario] || {} };
	}
	if (path.includes("api/5/args")) {
		return { ok: true, status: 200, json: async () => ARGS_FIXTURES[scenario] || {} };
	}
	return { ok: true, status: 200, json: async () => ({}) };
}
```

The per-plugin `/api/5/<plugin>/info` branch is gone: nothing calls that route any more.

(d) Add `"gpu-disabled": {},` and `"pluginslist-unreachable": {},` to `ALL_FIXTURES` (after `default: {},`). Empty payloads are enough: these scenarios observe which plugins render, not what they show.

(e) Replace `findAllByClass` (and the comment above it) with:

```js
// Every rendered plugin root carries its registry name as `data-plugin`
// (AppShell binds it; Vue's fallthrough puts it on the component's single
// root). Collected by that attribute, not by `.gl-plugin`: the header
// components are one-line <span>s, not <article class="gl-plugin"> panels.
// Walks the whole tree so the assertions see the SET that rendered.
function findAllByAttr(root, attr, acc = []) {
	for (const child of root.childNodes) {
		if (child.nodeType === ELEMENT_NODE) {
			if (child.getAttribute(attr) !== null) acc.push(child);
			findAllByAttr(child, attr, acc);
		}
	}
	return acc;
}
```

(f) In `collect()`: add to the `result` literal, after `pluginAttrs: {},`:

```js
		// Ordered `data-plugin` values inside each `[data-slot]` container,
		// keyed by the slot name -- what the drift guard compares against the
		// TUI's slot tuples (curses_renderer_v5.py:58-80).
		slots: {},
```

then replace `const articles = findAllByClass(first, "gl-plugin");` with `const articles = findAllByAttr(first, "data-plugin");`, and directly after the `articles.forEach(...)` block add:

```js
			for (const section of findAllByAttr(first, "data-slot")) {
				result.slots[section.getAttribute("data-slot")] = findAllByAttr(section, "data-plugin").map((el) =>
					el.getAttribute("data-plugin"),
				);
			}
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_webserver_v5.py`:

(a) Add to the imports at the top of the file:

```python
from glances.outputs.curses_renderer_v5 import HEADER_SLOT_LEFT, HEADER_SLOT_RIGHT, LEFT_SLOT, RIGHT_SLOT, TOP_SLOT
```

(b) Replace the assertion in `test_the_registry_renders_every_registered_plugin` with the new document order (top zone, then left), and append this paragraph to its docstring: "The order is the DOCUMENT order, i.e. zone by zone: a registry entry whose `slot` is missing or misspelled is rendered in no zone at all, and this explicit list is what catches it — the drift guard below only sees what rendered."

```python
    assert payload["pluginNames"] == ["cpu", "gpu", "mem", "memswap", "load", "network"], (
        f"expected all registered plugins to render, got {payload['pluginNames']!r}"
    )
```

(c) After that test, add:

```python
_TUI_SLOTS = {
    "header-left": HEADER_SLOT_LEFT,
    "header-right": HEADER_SLOT_RIGHT,
    "top": TOP_SLOT,
    "left": LEFT_SLOT,
    "right": RIGHT_SLOT,
}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_every_slot_orders_its_plugins_like_the_tui():
    """The drift guard G9-5's decision D4 depends on.

    The WebUI keeps its own copy of the TUI's slot lists (a `slot` attribute
    per entry in plugins/index.js, order = registry order). Nothing prevents
    the two copies from drifting apart; this test makes drift a failure. It
    compares the RENDERED layout -- not the registry source -- against the
    tuples imported from glances.outputs.curses_renderer_v5, which it must
    never restate.

    For each slot container, the plugins rendered in it must be exactly the
    TUI tuple for that slot, filtered to the plugins that rendered, in the
    tuple's order. A plugin placed in the wrong slot is absent from that
    slot's tuple and fails; two plugins swapped within a slot fail on order.
    """
    payload = _run_render_probe("default")
    rendered = payload["pluginNames"]
    slots = payload["slots"]

    assert rendered, "vacuous: nothing rendered"
    assert set(slots) <= set(_TUI_SLOTS), f"a slot the TUI does not have rendered: {sorted(slots)!r}"
    placed = [name for names in slots.values() for name in names]
    assert sorted(placed) == sorted(rendered), f"every plugin must sit in exactly one slot: {slots!r}"
    for slot, names in slots.items():
        expected = [name for name in _TUI_SLOTS[slot] if name in rendered]
        assert names == expected, f"slot {slot!r}: rendered {names!r}, the TUI orders {expected!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_plugin_the_server_did_not_instantiate_is_not_rendered():
    """A disabled plugin is never instantiated (glances/main_v5.py:372), so it
    is never in /api/5/all, and before G9-5 the WebUI showed it as "loading…"
    forever. `gpu-disabled` answers /api/5/pluginslist without `gpu`.
    """
    payload = _run_render_probe("gpu-disabled")
    assert "gpu" not in payload["pluginNames"], f"gpu is disabled: {payload['pluginNames']!r}"
    assert "cpu" in payload["pluginNames"], f"vacuous: the other plugins must still render: {payload['pluginNames']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unreadable_pluginslist_renders_the_whole_registry():
    """/api/5/pluginslist failing must degrade to the pre-G9-5 behaviour --
    every registered plugin rendered -- never to an empty page.
    """
    payload = _run_render_probe("pluginslist-unreachable")
    assert payload["pluginNames"] == ["cpu", "gpu", "mem", "memswap", "load", "network"], (
        f"expected the whole registry, got {payload['pluginNames']!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_refresh_cadence_renders_in_the_footer():
    """G9-5 decision D5: the top bar is gone and the cadence moved to the
    footer. The probe answers /api/5/config with `{}`, so the cadence is
    api.js' DEFAULT_REFRESH_SECONDS (2).
    """
    payload = _run_render_probe("default")
    assert "refresh 2s" in (payload["footerText"] or ""), f"got {payload['footerText']!r}"
```

`test_network_column_headers_are_the_tui_strings` needs no edit, and is now also the end-to-end proof that labels arrive through `/api/5/all/info`: its `Rx/s`/`Tx/s` headers exist only in `INFO_FIXTURES.network`.

- [ ] **Step 3: Run to verify they fail against the current bundle**

```bash
uv run pytest tests/test_webserver_v5.py -q
```
Expected: FAIL for the registry order, the drift guard (`slots` empty → `placed` ≠ `rendered`), `gpu-disabled`, and the footer cadence. The network header test also fails: the old bundle requests per-plugin `/info`, which the probe no longer answers. Every other test passes.

- [ ] **Step 4: Add `slot` to the registry**

Replace `glances/outputs/static/js/v5/plugins/index.js` with:

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
//
// `slot` is where the page puts the component: "header-left",
// "header-right", "top", "left" or "right" -- the TUI's HEADER_SLOT_LEFT,
// HEADER_SLOT_RIGHT, TOP_SLOT, LEFT_SLOT and RIGHT_SLOT
// (glances/outputs/curses_renderer_v5.py). Order within a slot is THIS
// list's order, so keep entries in the TUI's order.
//
// This is a second copy of those tuples (G9-5 decision D4). Two tests keep it
// honest: test_every_slot_orders_its_plugins_like_the_tui fails on a plugin
// in the wrong slot or out of order, and
// test_the_registry_renders_every_registered_plugin fails on a missing or
// misspelled slot (such an entry renders in no zone at all). There is no
// fallback slot, unlike the TUI's slot_for().

import PluginMem from "../PluginMem.vue";
import PluginNetwork from "../PluginNetwork.vue";
import PluginLoad from "../PluginLoad.vue";
import PluginMemswap from "../PluginMemswap.vue";
import PluginCpu from "../PluginCpu.vue";
import PluginGpu from "../PluginGpu.vue";

export const PLUGINS = [
	{
		name: "cpu",
		component: PluginCpu,
		slot: "top",
		spec: { shape: "scalar", required: ["total"] },
	},
	{
		name: "gpu",
		component: PluginGpu,
		slot: "top",
		spec: { shape: "collection", required: ["gpu_id"] },
	},
	{
		name: "mem",
		component: PluginMem,
		slot: "top",
		spec: { shape: "scalar", required: ["percent", "total"] },
	},
	{
		name: "memswap",
		component: PluginMemswap,
		slot: "top",
		spec: { shape: "scalar", required: ["total"] },
	},
	{
		name: "load",
		component: PluginLoad,
		slot: "top",
		spec: { shape: "scalar", required: ["min1"] },
	},
	{
		name: "network",
		component: PluginNetwork,
		slot: "left",
		spec: { shape: "collection", required: ["interface_name"] },
	},
];
```

- [ ] **Step 5: Rewrite `AppShell.vue`**

Replace `glances/outputs/static/js/v5/AppShell.vue` with:

```vue
<template>
	<main class="gl-app">
		<!--
			Zones mirror the TUI's page: header line, top row, then the left and
			right columns. AppShell still never names a plugin -- the registry's
			`slot` decides where each one lands.
		-->
		<component :is="zone.tag" v-for="zone in zones" :key="zone.name" :class="['gl-zone', `gl-zone-${zone.name}`]">
			<!-- `slotName`, not `slot`: `slot` is a reserved attribute name in Vue templates. -->
			<template v-for="slotName in zone.slots" :key="slotName">
				<section v-if="slots[slotName]" :class="['gl-slot', `gl-slot-${slotName}`]" :data-slot="slotName">
					<component
						:is="plugin.component"
						v-for="plugin in slots[slotName]"
						:key="plugin.name"
						:data-plugin="plugin.name"
						:payload="results[plugin.name]"
						:error="errors[plugin.name]"
						:labels="labels[plugin.name] || {}"
						:server-args="serverArgs"
					/>
				</section>
			</template>
		</component>

		<footer class="gl-alerts">
			<span v-if="!alerts.length" class="gl-muted">No alert</span>
			<ul v-else>
				<li v-for="(alert, i) in alerts" :key="i" :class="levelClass(alert)">
					{{ alertLabel(alert) }}
				</li>
			</ul>
			<!-- G9-5 D5: moved here from the removed top bar. -->
			<span class="gl-muted gl-refresh">{{ refreshLabel }}</span>
		</footer>
	</main>
</template>

<script>
import { fetchAll, resolveConfig, resolveArgs, resolvePluginNames, getJson } from "./api.js";
import { levelClass } from "./levels.js";
import { resolveAllLabels } from "./labels.js";
import { visiblePlugins, groupBySlot } from "./layout.js";
import { PLUGINS } from "./plugins/index.js";

// The page's zones, top to bottom, and the registry slots each one holds.
// `tag` is the element the zone renders as: the header zone stays a real
// <header>, which the render probe asserts.
const ZONES = [
	{ name: "header", tag: "header", slots: ["header-left", "header-right"] },
	{ name: "top", tag: "section", slots: ["top"] },
	{ name: "body", tag: "div", slots: ["left", "right"] },
];

export default {
	name: "AppShell",
	data() {
		return {
			results: {},
			errors: {},
			labels: {},
			serverArgs: {},
			// /api/5/pluginslist. null until read, and null if it cannot be read:
			// visiblePlugins() then renders the whole registry.
			pluginNames: null,
			alerts: [],
			refresh: null,
			timer: null,
			ticking: false,
		};
	},
	computed: {
		// NOT data(): Vue makes data()'s return value deeply reactive, so each
		// `plugin.component` would reach <component :is> as a Proxy of the
		// component options object -- which the dev build warns about
		// ("Vue received a Component that was made a reactive object") on
		// every vnode creation. A computed over the raw PLUGINS array returns
		// raw entries.
		plugins() {
			return visiblePlugins(PLUGINS, this.pluginNames);
		},
		slots() {
			return groupBySlot(this.plugins);
		},
		// A zone none of whose slots holds a plugin is not rendered, so it
		// leaves no empty bordered band on the page.
		zones() {
			return ZONES.filter((zone) => zone.slots.some((slot) => this.slots[slot]));
		},
		refreshLabel() {
			return this.refresh === null ? "…" : `refresh ${this.refresh}s`;
		},
	},
	async mounted() {
		const { refreshSeconds, theme } = await resolveConfig();
		this.refresh = refreshSeconds;
		// [outputs] theme, mapped straight to data-theme -- see the G9-2 design
		// spec, section 5. The static template hardcodes "dark" so the page
		// has a theme before this fetch resolves.
		document.documentElement.dataset.theme = theme;
		// The schema, the server's CLI arguments and its plugin list never
		// change while the server runs, so all three are resolved once here:
		// three requests whatever the number of plugins.
		const [labels, serverArgs, pluginNames] = await Promise.all([
			resolveAllLabels(),
			resolveArgs(),
			resolvePluginNames(),
		]);
		this.labels = labels;
		this.serverArgs = serverArgs;
		this.pluginNames = pluginNames;
		await this.tick();
		this.timer = setInterval(() => this.tick(), this.refresh * 1000);
	},
	unmounted() {
		// The poll must stop with the component, or a hot reload leaves timers
		// stacking up against the API.
		if (this.timer) clearInterval(this.timer);
	},
	methods: {
		levelClass,
		// `_build_event()` (glances/alerts_v5.py:706-716) is the only source of
		// this shape: {ts, plugin, key, field, level, previous_level, value,
		// prominent, is_initial, hostname}. There is no `description` field --
		// identify the alert from what actually exists: the plugin, the
		// collection item key when there is one, and the field.
		alertLabel(alert) {
			const parts = [alert.plugin];
			if (alert.key) parts.push(alert.key);
			parts.push(alert.field);
			return `${parts.join(" ")} — ${alert.level}`;
		},
		async tick() {
			// The interval fires unconditionally every `refresh` seconds
			// regardless of whether the previous tick's awaits have settled.
			// Without this guard, two overlapping ticks against a slow/loaded
			// server can resolve out of order and an older response clobbers
			// `results`/`errors`/`alerts` with stale data.
			if (this.ticking) return;
			this.ticking = true;
			try {
				// Visible plugins only: a disabled plugin is absent from /all by
				// construction, and asking for it would only produce a
				// permanent loading state nobody renders.
				const { results, errors } = await fetchAll(this.plugins);
				this.results = results;
				this.errors = errors;
				// The footer alert list is its own endpoint; its failure must not
				// disturb the plugins above it.
				try {
					const history = await getJson("api/5/alert");
					// get_history() (glances/alerts_v5.py:181) documents its return
					// as most-recent-LAST. `slice(0, 10)` would take the ten OLDEST
					// entries once history exceeds ten -- the footer would freeze on
					// stale alerts and never show a new one. Take the last ten, then
					// reverse so the newest alert reads first in the vertical list.
					this.alerts = Array.isArray(history) ? history.slice(-10).reverse() : [];
				} catch {
					this.alerts = [];
				}
			} finally {
				this.ticking = false;
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
/* Lightweight separators between zones, as the removed top bar had. */
.gl-zone {
	border-bottom: 1px solid var(--gl-border);
	padding-bottom: var(--gl-gap);
}
/* Header line. `3ch` is the TUI's _HEADER_GAP = 3 (glances_curses_v5.py): a
 * spacing, not a truncation, so the character unit is legitimate here. The
 * right group is pushed to the right edge, like _paint_header() does; when the
 * line wraps it stays right-aligned on its own row. */
.gl-zone-header {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	column-gap: 3ch;
}
.gl-slot-header-left,
.gl-slot-header-right {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	column-gap: 3ch;
	/* Lets the header's long strings shrink into their ellipsis. */
	min-width: 0;
}
.gl-slot-header-right {
	margin-left: auto;
}
/* Top row: first block flush left, last flush right, gaps distributed --
 * _paint_top_row()'s rule. */
.gl-slot-top {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: calc(var(--gl-gap) * 2);
	flex: 1;
}
.gl-zone-top {
	display: flex;
}
/* Left column sized by its content, right column takes the rest. */
.gl-zone-body {
	display: grid;
	grid-template-columns: max-content 1fr;
	gap: calc(var(--gl-gap) * 2);
}
.gl-slot-left,
.gl-slot-right {
	display: flex;
	flex-direction: column;
	gap: calc(var(--gl-gap) * 2);
	min-width: 0;
}
/* Pinned to the second column so it does not slide left when no plugin is in
 * the left slot. */
.gl-slot-right {
	grid-column: 2;
}
/* 48rem matches no TUI rule: it is the browser's own threshold (G9-5 D3),
 * kept in this single rule so it can be tuned. Below it the columns stack. */
@media (max-width: 48rem) {
	.gl-zone-body {
		grid-template-columns: 1fr;
	}
	.gl-slot-right {
		grid-column: auto;
	}
}
.gl-alerts {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: var(--gl-gap);
}
.gl-alerts ul {
	margin: 0;
	padding-left: 1rem;
}
</style>
```

- [ ] **Step 6: Remove `resolveLabels`**

It has no caller now. In `glances/outputs/static/js/v5/labels.js`, delete `const cache = new Map();` and the whole `resolveLabels` function. In `tests/js/labels.test.mjs`, delete the three tests that call it (`"resolveLabels applies the field_label precedence"`, `"an unreachable /info degrades to field names, never to blank"`, `"resolveLabels fetches once per plugin and caches"`) and drop `resolveLabels` from the import. The precedence and failure behaviours they covered are covered by Task 2's `resolveAllLabels` tests.

Then confirm nothing references it:

```bash
grep -rn "resolveLabels\b" glances/outputs/static/js tests
```
Expected: no output.

- [ ] **Step 7: Build, then verify**

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
```
Expected: all PASS, including every pre-existing G9-3/G9-4 render test **without any edit other than the registry-order assertion of Step 2(b)**. If a mem/network/cpu/gpu/load/memswap render assertion fails, the skeleton changed a component's rendering — fix the shell, never the assertion.

- [ ] **Step 8: Stage**

```bash
git add glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/js/v5/AppShell.vue \
        glances/outputs/static/js/v5/labels.js glances/outputs/static/public/glances5.js \
        tests/js/labels.test.mjs tests/fixtures/webui_render_probe.js tests/test_webserver_v5.py
```

---

### Task 4: `system`, `uptime`, `now`

**Files:**
- Create: `glances/outputs/static/js/v5/PluginSystem.vue`, `PluginUptime.vue`, `PluginNow.vue`
- Modify: `glances/outputs/static/js/v5/format.js` (append `formatSeconds`)
- Modify: `glances/outputs/static/js/v5/plugins/index.js` (three entries)
- Modify: `glances/outputs/static/css/v5.css` (`.gl-inline`, `.gl-truncate`)
- Modify: `tests/js/format.test.mjs`, `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: the Task 3 skeleton (`slot`, `data-plugin`, the four props).
- Produces:
  - `formatSeconds(value) -> string` from `format.js`.
  - Global CSS classes `.gl-inline` (one-line header block) and `.gl-truncate` (ellipsis).
  - The header-component contract Task 5 repeats: one root `<span class="gl-inline">` with `v-show="error || <guard>"`; an error renders as `<span class="gl-level-critical">`; registry `spec: { shape: "scalar", required: [] }`.
  - Probe output `pluginHidden: { [name]: boolean }` — `true` when the root's `style.display === "none"`.
  - Probe scenarios `header` (system, uptime, now — Task 5 adds ip and cloud to it) and `system-no-hostname`.

- [ ] **Step 1: Write the failing `formatSeconds` tests**

Append to `tests/js/format.test.mjs`, adding `formatSeconds` to the import at the top:

```js
test("formatSeconds mirrors the TUI's format_seconds exactly", () => {
	// glances/outputs/curses_formatters_v5.py:66-80. Each boundary on both
	// sides: the unit changes at 60, 3600 and 86400.
	assert.equal(formatSeconds(0), "0s");
	assert.equal(formatSeconds(59), "59s");
	assert.equal(formatSeconds(60), "1m00s");
	assert.equal(formatSeconds(3599), "59m59s");
	assert.equal(formatSeconds(3600), "1h00m");
	assert.equal(formatSeconds(86399), "23h59m");
	assert.equal(formatSeconds(86400), "1d00h");
	assert.equal(formatSeconds(273600), "3d04h");
});

test("formatSeconds truncates like int(float(value))", () => {
	assert.equal(formatSeconds(61.9), "1m01s");
	assert.equal(formatSeconds("61.9"), "1m01s");
});

test("formatSeconds returns the TUI's empty string for what it cannot parse", () => {
	// NOT this module's "-": format_seconds() catches TypeError/ValueError and
	// returns "", and the TUI then renders nothing.
	assert.equal(formatSeconds(null), "");
	assert.equal(formatSeconds(undefined), "");
	assert.equal(formatSeconds(""), "");
	assert.equal(formatSeconds("abc"), "");
});
```

Before implementing, check every expected value against the Python function itself, not against this plan:

```bash
uv run python -c "
from glances.outputs.curses_formatters_v5 import format_seconds as f
for v in (0, 59, 60, 3599, 3600, 86399, 86400, 273600, 61.9, '61.9', None, '', 'abc'):
    print(repr(v), repr(f(v)))
"
```
If any Python output differs from the JS expectation above, the plan is wrong: report it and match Python.

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_webui_v5_js.py -q
```
Expected: FAIL — `formatSeconds` is not exported.

- [ ] **Step 3: Implement `formatSeconds`**

Append to `glances/outputs/static/js/v5/format.js`:

```js
// Uptime units. Mirrors format_seconds()
// (glances/outputs/curses_formatters_v5.py:66-80) exactly -- including its
// missing marker, "" rather than this module's "-": the Python function
// catches TypeError/ValueError and returns "", and the TUI renders nothing.
export function formatSeconds(value) {
	const parsed = parseSeconds(value);
	if (!Number.isFinite(parsed)) return "";
	let secs = Math.trunc(parsed); // int(float(value))
	if (secs < 60) return `${secs}s`;
	let minutes = Math.floor(secs / 60);
	secs %= 60;
	if (minutes < 60) return `${minutes}m${pad2(secs)}s`;
	let hours = Math.floor(minutes / 60);
	minutes %= 60;
	if (hours < 24) return `${hours}h${pad2(minutes)}m`;
	const days = Math.floor(hours / 24);
	hours %= 24;
	return `${days}d${pad2(hours)}h`;
}

// float() accepts a number or a numeric string. Number("") is 0 and
// Number(null) is 0, where float() raises -- hence the explicit cases.
function parseSeconds(value) {
	if (typeof value === "number") return value;
	if (typeof value === "string" && value.trim() !== "") return Number(value);
	return Number.NaN;
}

function pad2(n) {
	return String(n).padStart(2, "0");
}
```

Run `uv run pytest tests/test_webui_v5_js.py -q` → PASS.

- [ ] **Step 4: Add the two CSS utilities**

Append to `glances/outputs/static/css/v5.css`:

```css
/* One-line header block (system, ip, uptime, cloud, now): its cells side by
 * side on a baseline. The gap stands in for the single space the TUI painter
 * inserts between cells. Global, like .gl-stat-grid: five components share
 * it, and a scoped copy only matches the component that declares it. */
.gl-inline {
  display: inline-flex;
  align-items: baseline;
  gap: 1ch;
  min-width: 0;
  max-width: 100%;
}

/* Ellipsis for a string too long for its line (system's OS name, ip's
 * geolocation). Pair it with a `title` attribute carrying the full text.
 * `min-width: 0` is load-bearing: a flex item otherwise refuses to shrink
 * below its content, and the ellipsis never triggers. A browser truncates
 * with the layout; never copy a terminal character count instead. */
.gl-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
```

- [ ] **Step 5: Teach the probe `pluginHidden` and the header fixtures**

In `tests/fixtures/webui_render_probe.js`:

(a) Add to `INFO_FIXTURES` (the header plugins declare no `short_name`/`label`; empty objects keep the stub honest about that):

```js
	system: { os_name: {}, hostname: {}, platform: {}, linux_distro: {}, os_version: {}, hr_name: {} },
	uptime: { seconds: {} },
	now: { custom: {}, iso: {} },
```

(b) Before `const ALL_FIXTURES = {`, add:

```js
// Header plugin payloads, shaped like their model_v5.py `_collect()` output.
// 273600 s is exactly 3 days 4 hours -> "3d04h".
const SYSTEM_FIXTURE = {
	os_name: "Linux",
	hostname: "test-host",
	platform: "64bit",
	linux_distro: "Ubuntu 26.04",
	os_version: "7.0.0-31-generic",
	hr_name: "Ubuntu 26.04 64bit / Linux 7.0.0-31-generic",
	_levels: {},
};
const UPTIME_FIXTURE = { seconds: 273600, _levels: {} };
const NOW_FIXTURE = { iso: "2026-09-11T10:20:30+02:00", custom: "2026-09-11 10:20:30 CEST", _levels: {} };
```

(c) Add to `ALL_FIXTURES`:

```js
	header: { system: SYSTEM_FIXTURE, uptime: UPTIME_FIXTURE, now: NOW_FIXTURE },
	// The TUI's guard (system/render_curses_v5.py:25): no hostname, no block --
	// even with an OS name to show.
	"system-no-hostname": { system: { ...SYSTEM_FIXTURE, hostname: "" } },
```

(d) In `collect()`, add to the `result` literal after `slots: {},`:

```js
		// Whether each plugin root is hidden by `v-show` (Vue writes
		// `style.display = "none"`, runtime-dom's setDisplay()). The header
		// components stay in the DOM while hidden, so presence in pluginNames
		// says nothing about visibility -- this does.
		pluginHidden: {},
```

and inside `articles.forEach(...)`, after `result.pluginAttrs[name] = …;`, add:

```js
				result.pluginHidden[name] = article.style.display === "none";
```

- [ ] **Step 6: Write the failing render tests**

In `tests/test_webserver_v5.py`:

(a) Update `test_the_registry_renders_every_registered_plugin`'s assertion (and the one in `test_an_unreadable_pluginslist_renders_the_whole_registry`) to:

```python
["system", "uptime", "now", "cpu", "gpu", "mem", "memswap", "load", "network"]
```

(b) In `test_server_args_does_not_leak_into_the_dom_as_an_attribute`, change `== 6` to `== 9` and "Six" to "Nine" in its comment and message.

(c) Append a new section at the end of the file:

```python
# ------------------------------------------------------- header plugins (G9-5)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_blocks_are_hidden_while_their_plugin_has_not_published():
    """The `default` scenario publishes nothing. The TUI renders `[]` for an
    empty payload, so the header blocks are hidden -- not "loading…", which
    would fill the banner with placeholders.

    `mem` is asserted NOT hidden in the same run: without that, a probe that
    reported every element as hidden would pass this test.
    """
    payload = _run_render_probe("default")
    hidden = payload["pluginHidden"]
    for name in ("system", "uptime", "now"):
        assert hidden.get(name) is True, f"{name} must be hidden before it publishes: {hidden!r}"
    assert hidden.get("mem") is False, f"vacuous: a panel plugin is never hidden: {hidden!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_system_renders_the_hostname_and_the_os_name():
    """system/render_curses_v5.py: `hostname` then `hr_name`."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("system", "")
    assert payload["pluginHidden"].get("system") is False
    assert "test-host" in text, f"got {text!r}"
    assert "Ubuntu 26.04 64bit / Linux 7.0.0-31-generic" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_system_without_a_hostname_is_hidden():
    payload = _run_render_probe("system-no-hostname")
    assert payload["pluginHidden"].get("system") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_uptime_renders_in_the_tui_format():
    """uptime/render_curses_v5.py: `Uptime:` then format_seconds(seconds)."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("uptime", "")
    assert "Uptime:" in text and "3d04h" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_now_renders_the_custom_date():
    """now/render_curses_v5.py: the `custom` string only; `iso` is REST-only."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("now", "")
    assert text == "2026-09-11 10:20:30 CEST", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_header_plugins_sit_in_the_header_zone():
    payload = _run_render_probe("header")
    assert payload["slots"].get("header-left") == ["system"], f"got {payload['slots']!r}"
    assert payload["slots"].get("header-right") == ["uptime", "now"], f"got {payload['slots']!r}"
```

- [ ] **Step 7: Run to verify they fail**

```bash
uv run pytest tests/test_webserver_v5.py -q
```
Expected: the new header tests, the registry order and the attribute count FAIL (no components yet); everything else PASS.

- [ ] **Step 8: Write the three components**

Create `glances/outputs/static/js/v5/PluginSystem.vue`:

```vue
<template>
	<span v-show="error || hostname" class="gl-inline">
		<!--
			v-show, not v-if, on the root: a hidden block stays in the DOM, so it
			keeps its data-plugin (the probe finds it) and takes no header gap.
			The TUI renders [] under the same condition. This comment sits INSIDE
			the root on purpose: the build keeps template comments, and one
			placed before the <span> would make a second root node, which stops
			Vue from putting data-plugin on the component at all.
		-->
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<span class="gl-header">{{ hostname }}</span>
			<span v-if="hrName" class="gl-truncate" :title="hrName">{{ hrName }}</span>
		</template>
	</span>
</template>

<script>
export default {
	name: "PluginSystem",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the root.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// glances/plugins/system/render_curses_v5.py: no hostname, no block.
		// `hr_name` already carries `[system] system_info_msg`, applied by the
		// model. The TUI's `hide_os_info` is terminal-width degradation and is
		// not reproduced (G9-5 D3): the OS name truncates with an ellipsis.
		hostname() {
			return this.payload?.hostname || "";
		},
		hrName() {
			return this.payload?.hr_name || "";
		},
	},
};
</script>
```

Create `glances/outputs/static/js/v5/PluginUptime.vue`:

```vue
<template>
	<span v-show="error || text" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<span>Uptime:</span>
			<span>{{ text }}</span>
		</template>
	</span>
</template>

<script>
import { formatSeconds } from "./format.js";

export default {
	name: "PluginUptime",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the root.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// glances/plugins/uptime/render_curses_v5.py: `seconds is None` -> no
		// block. "Uptime:" is a block tag, not a field label, and the TUI does
		// not read it from the schema either (G9-5 spec §7.3).
		text() {
			const seconds = this.payload?.seconds;
			return seconds === null || seconds === undefined ? "" : formatSeconds(seconds);
		},
	},
};
</script>
```

Create `glances/outputs/static/js/v5/PluginNow.vue`:

```vue
<template>
	<span v-show="error || custom" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<span v-else>{{ custom }}</span>
	</span>
</template>

<script>
export default {
	name: "PluginNow",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the root.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// glances/plugins/now/render_curses_v5.py: the `custom` string only
		// (`[global] strftime_format` is applied by the model); `iso` is
		// REST-only.
		custom() {
			return this.payload?.custom || "";
		},
	},
};
</script>
```

- [ ] **Step 9: Register them**

In `glances/outputs/static/js/v5/plugins/index.js`, add the imports after `PluginGpu`:

```js
import PluginSystem from "../PluginSystem.vue";
import PluginUptime from "../PluginUptime.vue";
import PluginNow from "../PluginNow.vue";
```

and insert at the very START of `PLUGINS`, in this order:

```js
	// The header plugins declare `required: []`: a missing guard field
	// (hostname, seconds, custom) is the component's hide rule -- the TUI
	// renders nothing -- not a shape error for validate() to display.
	{
		name: "system",
		component: PluginSystem,
		slot: "header-left",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "uptime",
		component: PluginUptime,
		slot: "header-right",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "now",
		component: PluginNow,
		slot: "header-right",
		spec: { shape: "scalar", required: [] },
	},
```

(Task 5 inserts `ip` after `system` and `cloud` between `uptime` and `now`.)

- [ ] **Step 10: Build, then verify**

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
```
Expected: all PASS — including `test_every_slot_orders_its_plugins_like_the_tui`, now observing `header-left`/`header-right` for the first time.

- [ ] **Step 11: Stage**

```bash
git add glances/outputs/static/js/v5/PluginSystem.vue glances/outputs/static/js/v5/PluginUptime.vue \
        glances/outputs/static/js/v5/PluginNow.vue glances/outputs/static/js/v5/format.js \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/css/v5.css \
        glances/outputs/static/public/glances5.js tests/js/format.test.mjs \
        tests/fixtures/webui_render_probe.js tests/test_webserver_v5.py
```

---

### Task 5: `ip` and `cloud`

**Files:**
- Create: `glances/outputs/static/js/v5/PluginIp.vue`, `glances/outputs/static/js/v5/PluginCloud.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js` (two entries)
- Modify: `tests/fixtures/webui_render_probe.js`, `tests/test_webserver_v5.py`
- Rebuild: `glances/outputs/static/public/glances5.js`

**Interfaces:**
- Consumes: the Task 4 header-component contract, `.gl-inline`, `.gl-truncate`, `pluginHidden`; `serverArgs.hide_public_info` from `/api/5/args` (the `--hide-public-info` flag, `glances/main_v5.py:229`).
- Produces: probe scenarios `header` (extended), `header-hide-public`, `ip-no-cidr`, `ip-no-address`, `cloud-no-name`, `cloud-no-region`, `cloud-disabled`.

- [ ] **Step 1: Fixtures**

In `tests/fixtures/webui_render_probe.js`:

(a) Add to `INFO_FIXTURES`:

```js
	ip: { address: {}, mask: {}, mask_cidr: {}, gateway: {}, public_address: {}, public_info_human: {} },
	cloud: { id: {}, platform: {}, name: {}, type: {}, region: {} },
```

(b) After `NOW_FIXTURE`, add:

```js
// Addresses from the documentation ranges (RFC 5737): 203.0.113.0/24 is
// TEST-NET-3, never routed.
const IP_FIXTURE = {
	address: "192.168.1.10",
	mask: "255.255.255.0",
	mask_cidr: 24,
	gateway: null,
	public_address: "203.0.113.42",
	public_info_human: "Paris, France (AS64496 Example Net)",
	_levels: {},
};
// cloud/render_curses_v5.py's own docstring example.
const CLOUD_FIXTURE = {
	id: "b7c1e2d3",
	platform: "OpenStack",
	name: "my-vm",
	type: "gold",
	region: "eu-west-1a",
	_levels: {},
};
```

(c) In `ALL_FIXTURES`, replace the `header` entry and add the new scenarios:

```js
	header: { system: SYSTEM_FIXTURE, ip: IP_FIXTURE, uptime: UPTIME_FIXTURE, cloud: CLOUD_FIXTURE, now: NOW_FIXTURE },
	// Same payloads as `header`; only ARGS_FIXTURES differs, so a masked
	// address can only come from the flag.
	"header-hide-public": { ip: IP_FIXTURE },
	"ip-no-cidr": { ip: { ...IP_FIXTURE, mask_cidr: null } },
	// Neither address: the TUI returns [] (ip/render_curses_v5.py:71).
	"ip-no-address": { ip: { ...IP_FIXTURE, address: "", public_address: "" } },
	// platform present, name absent: the #2485 guard hides the block.
	"cloud-no-name": { cloud: { id: "b7c1e2d3", platform: "OpenStack", type: "gold", region: "eu-west-1a", _levels: {} } },
	// region absent as a KEY: the TUI's `payload.get("region", "Unknown")`.
	"cloud-no-region": { cloud: { id: "b7c1e2d3", platform: "OpenStack", name: "my-vm", type: "gold", _levels: {} } },
	"cloud-disabled": { system: SYSTEM_FIXTURE, cloud: CLOUD_FIXTURE },
```

(d) Add to `ARGS_FIXTURES`:

```js
	"header-hide-public": { hide_public_info: true },
```

(e) Add to `PLUGINSLIST_FIXTURES`:

```js
	// The shipped default: `[cloud] disable` is true (cloud/model_v5.py:100).
	"cloud-disabled": SERVER_PLUGINS.filter((name) => name !== "cloud"),
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_webserver_v5.py`:

(a) Update both full-registry assertions (`test_the_registry_renders_every_registered_plugin`, `test_an_unreadable_pluginslist_renders_the_whole_registry`) to:

```python
["system", "ip", "uptime", "cloud", "now", "cpu", "gpu", "mem", "memswap", "load", "network"]
```

(b) In `test_server_args_does_not_leak_into_the_dom_as_an_attribute`, `== 9` → `== 11`, "Nine" → "Eleven".

(c) In `test_header_blocks_are_hidden_while_their_plugin_has_not_published`, extend the tuple to `("system", "ip", "uptime", "cloud", "now")`. In `test_header_plugins_sit_in_the_header_zone`, expect `["system", "ip"]` and `["uptime", "cloud", "now"]`.

(d) Append to the header section:

```python
@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_renders_the_private_and_public_addresses():
    """ip/render_curses_v5.py: `IP addr/cidr`, then `Pub addr` and the
    geolocation string."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("ip", "")
    for expected in ("IP", "192.168.1.10/24", "Pub", "203.0.113.42", "Paris, France (AS64496 Example Net)"):
        assert expected in text, f"expected {expected!r} in the ip text, got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_without_a_cidr_shows_the_bare_address():
    """`mask_cidr is not None` gates the suffix (ip/render_curses_v5.py:53)."""
    payload = _run_render_probe("ip-no-cidr")
    text = payload["pluginText"].get("ip", "")
    assert "192.168.1.10" in text, f"got {text!r}"
    assert "192.168.1.10/" not in text, f"no cidr -> no slash: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_masks_the_public_address_with_hide_public_info():
    """`--hide-public-info` reaches the WebUI through /api/5/args. Same payload
    as `header`; only the args fixture differs.

    Display-only, like the TUI: the API still serves the address in clear
    (G9-5 spec §11). This test proves the rendered text, nothing more.
    """
    payload = _run_render_probe("header-hide-public")
    text = payload["pluginText"].get("ip", "")
    assert "203.0.*.*" in text, f"got {text!r}"
    assert "113.42" not in text, f"the masked octets must not render: {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_ip_with_no_address_is_hidden():
    payload = _run_render_probe("ip-no-address")
    assert payload["pluginHidden"].get("ip") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_renders_the_platform_and_the_instance_summary():
    """cloud/render_curses_v5.py docstring: `OpenStack gold instance my-vm (eu-west-1a)`."""
    payload = _run_render_probe("header")
    text = payload["pluginText"].get("cloud", "")
    assert "OpenStack" in text, f"got {text!r}"
    assert "gold instance my-vm (eu-west-1a)" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_without_a_name_is_hidden():
    """#2485: platform and name are both mandatory, or nothing renders."""
    payload = _run_render_probe("cloud-no-name")
    assert payload["pluginHidden"].get("cloud") is True, f"got {payload['pluginHidden']!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_fills_a_missing_part_with_unknown():
    payload = _run_render_probe("cloud-no-region")
    text = payload["pluginText"].get("cloud", "")
    assert "gold instance my-vm (Unknown)" in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_cloud_disabled_on_the_server_is_not_rendered():
    """The shipped default. Before G9-5 this block would have sat in the header
    as a permanent loading state for most users."""
    payload = _run_render_probe("cloud-disabled")
    assert "cloud" not in payload["pluginNames"], f"got {payload['pluginNames']!r}"
    assert "system" in payload["pluginNames"], f"vacuous: the header still renders: {payload['pluginNames']!r}"
```

- [ ] **Step 3: Run to verify they fail**

```bash
uv run pytest tests/test_webserver_v5.py -q
```
Expected: the new ip/cloud tests, the registry order, the attribute count and the header-zone test FAIL; everything else PASS.

- [ ] **Step 4: Write the two components**

Create `glances/outputs/static/js/v5/PluginIp.vue`:

```vue
<template>
	<span v-show="error || address || publicAddress" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<template v-if="address">
				<span class="gl-header">IP</span>
				<span>{{ privateText }}</span>
			</template>
			<template v-if="publicAddress">
				<span class="gl-header">Pub</span>
				<span>{{ publicShown }}</span>
				<!--
					`title` carries the geolocation string ONLY. Never the public
					address: a hover would bypass --hide-public-info.
				-->
				<span v-if="publicInfo" class="gl-truncate" :title="publicInfo">{{ publicInfo }}</span>
			</template>
		</template>
	</span>
</template>

<script>
// glances/plugins/ip/render_curses_v5.py:35-37 -- a.b.c.d -> a.b.*.*
function hideIp(ip) {
	return `${String(ip).split(".").slice(0, 2).join(".")}.*.*`;
}

export default {
	name: "PluginIp",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// READ here: `hide_public_info` is the --hide-public-info CLI flag.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// Mirrors glances/plugins/ip/render_curses_v5.py: the private cells
		// need `address`, the public cells need `public_address`, and a block
		// with no cell at all is not rendered. "IP" and "Pub" are block tags,
		// not field labels (G9-5 spec §7.3).
		address() {
			return this.payload?.address || "";
		},
		privateText() {
			const cidr = this.payload?.mask_cidr;
			return cidr === null || cidr === undefined ? String(this.address) : `${this.address}/${cidr}`;
		},
		publicAddress() {
			return this.payload?.public_address || "";
		},
		// DISPLAY-ONLY masking, exactly like the TUI. /api/5/ip and /api/5/all
		// still serve the address in clear -- G9-5 spec §11 tracks that; do not
		// mistake this for a privacy control.
		publicShown() {
			return this.serverArgs.hide_public_info ? hideIp(this.publicAddress) : String(this.publicAddress);
		},
		// The TUI's `hide_ip_location` is terminal-width degradation and is not
		// reproduced (G9-5 D3): the string truncates with an ellipsis instead.
		publicInfo() {
			return this.payload?.public_info_human || "";
		},
	},
};
</script>
```

Create `glances/outputs/static/js/v5/PluginCloud.vue`:

```vue
<template>
	<span v-show="error || (platform && name)" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<!-- .gl-header is already bold: the TUI's HEADER role + bold=True. -->
			<span class="gl-header">{{ platform }}</span>
			<span>{{ summary }}</span>
		</template>
	</span>
</template>

<script>
const UNKNOWN = "Unknown";

export default {
	name: "PluginCloud",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the root.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// glances/plugins/cloud/render_curses_v5.py: platform AND name are
		// mandatory (#2485), or nothing renders.
		platform() {
			return this.payload?.platform || "";
		},
		name() {
			return this.payload?.name || "";
		},
		// `payload.get(key, "Unknown")` falls back on an ABSENT key only, hence
		// `in` rather than a null check. The TUI's summary opens with a space
		// because its painter adds another between cells; here .gl-inline's
		// gap does that, so the leading space is dropped.
		summary() {
			const p = this.payload || {};
			const part = (key) => (key in p ? String(p[key]) : UNKNOWN);
			return `${part("type")} instance ${part("name")} (${part("region")})`;
		},
	},
};
</script>
```

- [ ] **Step 5: Register them**

In `glances/outputs/static/js/v5/plugins/index.js`, add the imports after `PluginNow`:

```js
import PluginIp from "../PluginIp.vue";
import PluginCloud from "../PluginCloud.vue";
```

Insert the `ip` entry directly after `system`, and the `cloud` entry directly after `uptime`:

```js
	{
		name: "ip",
		component: PluginIp,
		slot: "header-left",
		spec: { shape: "scalar", required: [] },
	},
```

```js
	{
		name: "cloud",
		component: PluginCloud,
		slot: "header-right",
		spec: { shape: "scalar", required: [] },
	},
```

- [ ] **Step 6: Build, then verify**

```bash
cd glances/outputs/static && npm run build && cd -
```
v4 bundle identity check (both IDENTICAL), then:
```bash
uv run pytest tests/test_webserver_v5.py tests/test_webui_v5_js.py tests/test_webui_v5_tokens.py -q
glances/outputs/static/node_modules/.bin/eslint --config glances/outputs/static/eslint.config.mjs glances/outputs/static/js/v5 tests/js
```
Expected: all PASS.

- [ ] **Step 7: Stage**

```bash
git add glances/outputs/static/js/v5/PluginIp.vue glances/outputs/static/js/v5/PluginCloud.vue \
        glances/outputs/static/js/v5/plugins/index.js glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_probe.js tests/test_webserver_v5.py
```

---

### Task 6: Full verification

**Files:** everything the group touched. No new code unless a hook rewrites something.

- [ ] **Step 1: No TUI file moved**

```bash
git diff --stat HEAD -- glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py \
  glances/outputs/curses_formatters_v5.py 'glances/plugins/*/render_curses_v5.py' \
  'glances/plugins/*/model_v5.py' 'tests/test_*render_curses_v5.py' tests/test_curses_renderer_v5.py
```
Expected: empty. Anything else is a STOP.

- [ ] **Step 2: v4 untouched**

```bash
git diff --stat HEAD -- glances/outputs/glances_restful_api.py \
  glances/outputs/static/js/app.js glances/outputs/static/js/browser.js \
  glances/outputs/static/js/services.js glances/outputs/static/js/components/ \
  glances/outputs/static/js/App.vue glances/outputs/static/js/Browser.vue \
  glances/outputs/static/js/store.js glances/outputs/static/js/filters.js \
  glances/outputs/static/js/uiconfig.json glances/outputs/static/webpack.config.js \
  glances/outputs/static/css/custom.scss glances/outputs/static/css/style.scss \
  glances/outputs/static/templates/index.html
```
Expected: empty. Then the v4 bundle identity check one final time.

- [ ] **Step 3: No dead code**

```bash
grep -rn "resolveLabels\b\|findAllByClass\|gl-topbar\|gl-plugins\b" glances/outputs/static/js/v5 glances/outputs/static/css/v5.css tests
```
Expected: no output. Then confirm each new export has a caller outside its own test: `visiblePlugins`, `groupBySlot`, `resolveAllLabels`, `resolvePluginNames` (AppShell.vue), `formatSeconds` (PluginUptime.vue), `.gl-inline`/`.gl-truncate` (the header components).

- [ ] **Step 4: Full suite**

```bash
uv run pytest -q
```
No NEW failures versus the pre-existing state. If `test_050/051` fail, re-run `tests/test_restful.py` alone. If `test_mcp.py` fails, check for a squatter on 61235 first.

- [ ] **Step 5: Hooks and final stage**

```bash
git add -A
make pre-commit
git add -A
git status --short
```
`make pre-commit` runs ~23 hooks and some rewrite files; gitleaks scans the INDEX, which is why it is `add`, `run`, `add`. **If a hook rewrites a v4 or TUI file, STOP and report** — do not stage it and do not revert it. Do NOT commit.

- [ ] **Step 6: Report, do not write**

In the task report only, never in the repo:

- **Manual UI smoke test owed to the maintainer** (`python -m glances.main_v5 -s`, open the page): a narrow viewport (the body stacks below 48rem, nothing is hidden); a long `hr_name` (set `[system] system_info_msg` to a 120-character string) and a long IP geolocation, both truncating with the full text on hover; both themes; `--hide-public-info`; `--disable-plugin gpu` (the block disappears). Plus G9-4's owed check of `gpu`'s title with a long card name — `.gl-truncate` now exists if it is needed.
- **Issue owed** (G9-5 spec §11): `--hide-public-info` masks at display only; `/api/5/ip` and `/api/5/all` serve `public_address` in clear, in v4 and v5.
- **Still owed from G9-4:** the `cpu` `core`/`cpucore` TUI issue (`glances/plugins/cpu/render_curses_v5.py:183`).
- **Release-notes items:** the v5 WebUI page follows the TUI layout (header, top row, left and right columns, alerts in the footer); it shows `system`, `ip`, `uptime`, `cloud` and `now`; a plugin disabled on the server no longer shows as loading; new route `GET /api/5/all/info`; the v5 WebUI top bar is gone and the refresh cadence moved to the footer.
- **Pressure report for the next group:** the probe's size (it was 631 lines before G9-5) and `tests/test_webserver_v5.py`'s — the next group brings the left sidebar's collections.

---

## Self-review notes

Checked against the spec, section by section:

- §3 D1 scope → Tasks 1–5. D2 layout reference → Task 3 zones + Task 3/4/5 slots. D3 CSS only → Task 3 styles, Task 4 `.gl-truncate`; no `hide_*` flag is ported (comments in `PluginSystem.vue`, `PluginIp.vue`). D4 JS slot + drift guard → Task 3 Steps 2(c) and 4. D5 top bar → Task 3 Step 5 (footer cadence + test). D6 visibility → Task 2 (`visiblePlugins`, `resolvePluginNames`) + Task 3 (wiring, two probe tests) + Task 5 (`cloud-disabled`).
- §6.2 four requests → Task 3 `mounted()`; `/all/info` → Task 1; `resolveLabels` replaced → Task 2 adds, Task 3 removes.
- §6.3 `layout.js` → Task 2. §6.4 `data-slot` containers, empty slot not rendered → Task 3 (`v-if="slots[slot]"`, `zones` computed). §6.5 route → Task 1.
- §7.1 contract (single `<span>` root, `v-show`, visible error, `required: []`) → Task 4 Step 8/9, repeated in Task 5. §7.2 the five renderings and guards → Tasks 4, 5, one test per guard. §7.3 literal tags → component comments. §7.4 `formatSeconds` → Task 4, values checked against Python in Step 1.
- §8 CSS table → Task 3 scoped styles; `.gl-truncate` → Task 4. §9 failure modes → Task 2 unit tests (`/all/info`, `pluginslist` failure), Task 3 probe tests, Task 4 hidden-while-loading. `serverArgs` unreachable → existing `resolveArgs()` fallback, unchanged.
- §10 testing → every bullet mapped above; the `v-show` probe support is Task 4 Step 5(d); the TUI non-regression gate is Global Constraints + Task 6 Step 1.
- §11 → Task 5 test docstring + component comment + Task 6 report. §13 deliverables → File Structure table.

Two places this plan decides what the spec left open:

1. **`AppShell` renders zones from a `ZONES` constant with `<component :is="zone.tag">`** rather than three hand-written zone blocks. It keeps the single `<component :is="plugin.component">` binding site G9-3 established; three copies of a five-prop binding would reintroduce the per-zone duplication G9-3 removed.
2. **The drift guard filters the TUI tuples to what RENDERED**, so it cannot see a plugin that rendered nowhere (a misspelled `slot`). That case is caught by the explicit name list in `test_the_registry_renders_every_registered_plugin`, and the registry's header comment says which test catches what.

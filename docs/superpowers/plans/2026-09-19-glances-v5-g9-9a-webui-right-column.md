# Glances v5 — G9-9A WebUI right column (batch 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port `vms`, `containers`, `processcount` and `amps` into the v5
WebUI's right column, taking the plugin registry from 25 to 29 of 32, and
introduce the per-block horizontal column cascade that `processlist` will
reuse in G9-9B.

**Architecture:** Each plugin is one new `.vue` component plus one entry in
`js/v5/plugins/index.js` — the registry's own rule. Three blocks are
collections rendered through the existing `CollectionBlock` shell; the
fourth (`processcount`) is a single text line. `containers` additionally
gets a width-driven column cascade: the TUI's `_DROP_ORDER` is copied into a
pure JS module, resolved by the existing `resolveDegrade()`, and measured by
a new per-component mixin — the cascade state lives in the component, never
in `AppShell`.

**Tech Stack:** Vue 3 (options API, `.vue` SFCs), webpack (`npm run build`
in `glances/outputs/static/`), pytest, `node --test` for pure JS modules, a
DOM-less node render probe (`tests/fixtures/webui_render_probe.js`).

**Spec:** `docs/superpowers/specs/2026-09-19-glances-v5-g9-9a-webui-right-column-design.md`

---

## Global Constraints

- **Branch:** `develop-v5`. Every task **stages** its files (`git add`) and
  **STOPS**. Never `git commit`, never `git push`, never open a PR — the
  maintainer does all commits personally. Never add a `Co-Authored-By`
  trailer.
- **Never unstage or reset anything.** After each task run
  `git status --short | grep -v '^[AM] '` and report any line it prints:
  the maintainer may have other staged work in the tree.
- **Never touch `NEWS.rst`.** The changelog is a release-time job.
- **Never modify a TUI renderer** (`glances/plugins/*/render_curses_v5.py`)
  or a model (`model_v5.py`). They are this group's reference, read-only.
- **The bundle must be rebuilt after every `.vue`/`.js` change**, or the
  render probe tests read a stale bundle and pass for the wrong reason:
  `cd glances/outputs/static && npm run build` (output:
  `glances/outputs/static/public/glances5.js`). Rebuild BEFORE running any
  `tests/test_webui_v5_render.py` test.
- **Placeholder for a missing value is `-`**, from `format.js` (its
  `MISSING`). Never `_`, even where the `containers` TUI renderer prints `_`
  (spec divergence 5).
- **Tier colours come from `levels.js` only** (`cellClassFor` for a
  collection item). Never test `level === "critical"` in a component, never
  a colour literal — `tests/test_webui_v5_tokens.py` enforces the latter.
- **A tier class goes on the `<span>` inside the `<td>`**, never on the
  `<td>`: a prominent badge's background would otherwise fill the cell.
- **Headers are never tier-coloured** (`levels.js` module docstring).
- **Every component declares all four props** (`payload`, `error`, `labels`,
  `serverArgs`, `degrade`) even when unused: an undeclared prop leaks into
  the DOM as a fallthrough attribute, which
  `test_cross_cutting_props_do_not_leak_into_the_dom_as_attributes` fails on.
- **Registry order is the TUI's `RIGHT_SLOT` order**
  (`glances/outputs/curses_renderer_v5.py:75`): `vms`, `containers`,
  `processcount`, `amps`. `test_every_slot_orders_its_plugins_like_the_tui`
  fails otherwise.
- Run the whole suite with `python -m pytest tests/ -x -q`; a single file
  with `python -m pytest tests/test_webui_v5_render.py -k <name> -v`.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `glances/outputs/static/js/v5/PluginProcesscount.vue` | the `TASKS …` line | 1 |
| `glances/outputs/static/js/v5/PluginAmps.vue` | AMP name / count / result | 2 |
| `glances/outputs/static/js/v5/PluginVms.vue` | VM table | 3 |
| `glances/outputs/static/js/v5/PluginContainers.vue` | container table | 4, 6 |
| `glances/outputs/static/js/v5/plugins/index.js` | registry entries | 1–4 |
| `glances/outputs/static/js/v5/drop_order.js` | the TUI's `_DROP_ORDER`, as data | 5 |
| `glances/outputs/static/js/v5/containers_columns.js` | pure column-visibility rules | 5 |
| `glances/outputs/static/js/v5/fit_block.js` | per-block measure + cascade mixin | 6 |
| `glances/outputs/static/css/v5.css` | `.gl-command` measuring exclusion | 6 |
| `tests/fixtures/webui_render_fixtures.js` | payloads, args, block widths | 1–6 |
| `tests/fixtures/webui_render_probe.js` | per-block width application + refit hook | 6 |
| `tests/test_webui_v5_render.py` | probe assertions | 1–6 |
| `tests/js/drop_order.test.mjs` | `node --test` unit tests | 5 |
| `tests/js/containers_columns.test.mjs` | `node --test` unit tests | 5 |
| `tests/test_webui_v5_containers_drop_order_drift.py` | Python ↔ JS drift | 5 |

---

## Task 1: `processcount` — the TASKS line

**Files:**
- Create: `glances/outputs/static/js/v5/PluginProcesscount.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the registry's first `slot: "right"` entry, proving the right
  zone renders. Tasks 2–4 append after it in `RIGHT_SLOT` order — i.e. this
  entry must end up THIRD in the right group once Tasks 3 and 4 land
  (`vms`, `containers`, `processcount`, `amps`).

**Reference:** `glances/plugins/processcount/render_curses_v5.py:73-113`.
Rendered line: `TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth`.
Rules: `(N thr)` only when `thread` is not null (issue #1463); `oth` =
`total − running − sleeping`; when `total` is absent (scheduler cycle 0)
only the word `TASKS` — never `TASKS 0`. The `N/M` truncation counter
(`_count_text`, `:37`) and the `Threads sorted automatically by …`
indicator (`_sort_indicator_cell`, `:58`) are **out of scope** (spec D7):
both read TUI runtime view state that has no server mirror.

- [ ] **Step 1: Add the fixtures**

In `tests/fixtures/webui_render_fixtures.js`, next to the other payload
fixtures:

```js
// processcount is a scalar plugin: total/running/sleeping/thread/pid_max
// (processcount/model_v5.py). 215 - 3 - 195 = 17 "oth", the value the
// TUI computes rather than reads.
const PROCESSCOUNT_FIXTURE = {
	total: 215,
	running: 3,
	sleeping: 195,
	thread: 1452,
	pid_max: 32768,
	_levels: {},
};
```

Add three `ALL_FIXTURES` entries:

```js
	processcount: { processcount: PROCESSCOUNT_FIXTURE },
	// psutil exposes no thread count on some systems (issue #1463): the
	// "(N thr)" group disappears, the comma after the total stays.
	"processcount-no-thread": {
		processcount: { ...PROCESSCOUNT_FIXTURE, thread: null },
	},
	// Scheduler cycle 0: the plugin is registered and published an empty
	// payload. Only the title, never "TASKS 0".
	"processcount-empty": { processcount: {} },
```

and export `PROCESSCOUNT_FIXTURE` is **not** needed — only `ALL_FIXTURES`
is imported by the probe. Do not touch `module.exports` for this task.

- [ ] **Step 2: Write the failing tests**

In `tests/test_webui_v5_render.py`, at the end of the file:

```python
# ------------------------------------------------- processcount TUI parity (G9-9A Task 1)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_renders_the_tui_tasks_line():
    """processcount/render_curses_v5.py:73-113 paints ONE line:
    `TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth`. `oth` is computed
    (total - running - sleeping), so 17 proves the arithmetic and not a
    field read.
    """
    payload = _run_render_probe("processcount")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_drops_the_thread_group_when_psutil_has_no_count():
    """`thread` is None on some systems (issue #1463): the TUI emits
    `TASKS 215, 3 run, …` -- the comma moves onto the total."""
    payload = _run_render_probe("processcount-no-thread")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS 215, 3 run, 195 slp, 17 oth", f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_processcount_shows_only_its_title_before_the_first_aggregate():
    """No `total` yet (scheduler cycle 0) -> the title alone. A component
    that defaulted the aggregates to 0 would render `TASKS 0, 0 run…`,
    which the TUI explicitly avoids."""
    payload = _run_render_probe("processcount-empty")
    text = " ".join((payload["pluginText"].get("processcount") or "").split())
    assert text == "TASKS", f"got {text!r}"
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_render.py -k processcount -v
```

Expected: 3 FAILED — `pluginText` has no `processcount` key (the plugin is
not in the registry), so the text is `''`.

- [ ] **Step 4: Write the component**

Create `glances/outputs/static/js/v5/PluginProcesscount.vue`:

```vue
<template>
	<article class="gl-plugin" :aria-label="TITLE">
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else class="gl-tasks">
			<span class="gl-header">{{ TITLE }}</span>
			<template v-if="total !== null">{{ counts }}</template>
		</p>
	</article>
</template>

<script>
const TITLE = "TASKS";

export default {
	name: "PluginProcesscount",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: the TUI's sort indicator reads TUI view state
		// (sort_key / auto_sort / programs), which has no server mirror --
		// spec D7 defers it to G9-9B with `--programs`.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this block never shrinks, it is one line.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// processcount/render_curses_v5.py:82-86: no aggregate yet -> the title
		// alone, never `TASKS 0`.
		total() {
			const total = this.payload?.total;
			return typeof total === "number" ? total : null;
		},
		// One string, built exactly as the TUI concatenates its cells
		// (:88-110). Rendered as text rather than as cells because nothing in
		// this line is individually coloured or aligned.
		counts() {
			const total = this.total;
			const thread = this.payload?.thread;
			const running = this.payload?.running;
			const sleeping = this.payload?.sleeping;
			// The TUI writes ` (N thr),` when the count is known and a bare `,`
			// when it is not -- the comma belongs to the total either way.
			let text = ` ${total}${typeof thread === "number" ? ` (${thread} thr)` : ""},`;
			if (typeof running === "number") text += ` ${running} run,`;
			if (typeof sleeping === "number") text += ` ${sleeping} slp,`;
			// "oth" is computed, not published: total - running - sleeping.
			text += ` ${total - (running || 0) - (sleeping || 0)} oth`;
			return text;
		},
	},
};
</script>

<style scoped>
.gl-tasks {
	margin: 0;
}
</style>
```

Register it in `glances/outputs/static/js/v5/plugins/index.js` — add the
import next to the others:

```js
import PluginProcesscount from "../PluginProcesscount.vue";
```

and append this entry at the END of the `PLUGINS` array (it is the first
`right` entry; Tasks 3 and 4 will insert `vms` and `containers` BEFORE it):

```js
	{
		name: "processcount",
		component: PluginProcesscount,
		slot: "right",
		// No required field: at scheduler cycle 0 the payload has no `total`,
		// and the TUI's answer to that is "render the title only" -- a hide
		// rule, not a shape error for validate() to display.
		spec: { shape: "scalar", required: [] },
	},
```

- [ ] **Step 5: Rebuild the bundle and run the tests**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k processcount -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Run the WebUI test files to catch registry invariants**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_degrade_drift.py \
  tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py -q
```

Expected: all pass. `test_the_registry_renders_every_registered_plugin` and
`test_every_slot_orders_its_plugins_like_the_tui` now cover 26 plugins.
If `test_an_unreadable_pluginslist_renders_the_whole_registry` fails, append
`"processcount"` to its expected list — it asserts the registry verbatim.

- [ ] **Step 7: Stage, do not commit**

```bash
cd /home/nicolargo/dev/glances
git add glances/outputs/static/js/v5/PluginProcesscount.vue \
        glances/outputs/static/js/v5/plugins/index.js \
        glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_fixtures.js \
        tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' || true
```

Report anything the `grep` prints. Do **not** commit.

---

## Task 2: `amps` — name, count, result

**Files:**
- Create: `glances/outputs/static/js/v5/PluginAmps.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `CollectionBlock` (existing), `cellClassFor` from `columns.js`.
- Produces: the LAST entry of the right group; every later task inserts
  before it.

**Reference:** `glances/plugins/amps/render_curses_v5.py`. Three columns:
name (16ch), count, result. **No title row and no column header** — v4
parity; pass no `#head` slot and `CollectionBlock` renders no `<thead>`
(`CollectionBlock.vue:18`, the `ports` case). An item whose `result` is
`null` is skipped entirely (`:70-73`). The count is blank for a regex-less
AMP (`:76`). The name cell carries the `count` tier and its prominent
badge. Spec D6: the multi-line result goes in **one** cell with
`white-space: pre-line`, not one `<tr>` per line. No `… +N lines` marker
(spec §4 — there is no vertical budget).

- [ ] **Step 1: Add the fixtures**

```js
// amps: one row per AMP, `result` is the AMP's own output and may carry
// newlines (amps/render_curses_v5.py:82). `Dropped` has result: null --
// the AMP has not produced anything yet and v4 skips it. `Kernel` has no
// regex, so its count is not displayed even though it is set.
const AMPS_FIXTURE = {
	_key: "name",
	data: [
		{ name: "Python", count: 2, regex: true, result: "CPU: 1.0% | MEM: 2.0%" },
		{ name: "Systemd", count: 1, regex: true, result: "Services\nactive: 3" },
		{ name: "Dropped", count: 4, regex: true, result: null },
		{ name: "Kernel", count: 7, regex: false, result: "up" },
	],
	_levels: { Python: { count: { level: "warning", prominent: true } } },
};
```

`ALL_FIXTURES` entries:

```js
	amps: { amps: AMPS_FIXTURE },
	"amps-empty": { amps: { _key: "name", data: [], _levels: {} } },
```

- [ ] **Step 2: Write the failing tests**

```python
# ------------------------------------------------------- amps TUI parity (G9-9A Task 2)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_amps_renders_name_count_and_result_without_a_header_row():
    """amps/render_curses_v5.py has NO title row and NO column header
    (module docstring, v4 parity), like `ports` in G9-7 -- so the block
    renders no <thead> at all.
    """
    payload = _run_render_probe("amps")
    rows = _table_rows(payload, "amps", 3)
    assert rows == [
        ["Python", "2", "CPU: 1.0% | MEM: 2.0%"],
        ["Systemd", "1", "Services active: 3"],
        ["Kernel", "", "up"],
    ], f"got {rows!r}"
    assert not payload["pluginHeaderCells"].get("amps"), (
        f"amps must render no header row, got {payload['pluginHeaderCells'].get('amps')!r}"
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_amps_skips_an_amp_that_has_produced_nothing():
    """`result is None` -> v4 renders no row at all
    (amps/render_curses_v5.py:70-73). `Dropped` must be absent, and its
    count (4) must not appear anywhere in the block.
    """
    payload = _run_render_probe("amps")
    text = payload["pluginText"].get("amps") or ""
    assert "Dropped" not in text, f"got {text!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_amps_badges_the_count_tier_on_the_name():
    """The TUI colours the NAME cell from `_levels[name].count`
    (amps/render_curses_v5.py:78-79), not the count cell."""
    payload = _run_render_probe("amps")
    classes = payload["pluginValueClasses"].get("amps") or []
    assert "gl-level-warning gl-prominent" in classes, f"got {classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_amps_renders_no_block():
    """The TUI returns [] for an empty collection, so the block disappears
    entirely -- the G9-7 rule for ports/folders/irq/raid/smart."""
    payload = _run_render_probe("amps-empty")
    assert "amps" not in payload["slots"].get("right", []), f"got {payload['slots']!r}"
```

`_table_rows(payload, name, width)` (it takes the column count: the probe
returns one flat `<td>` list per plugin) and `pluginValueClasses` already
exist. **`pluginHeaderCells` does not** — verified absent from the probe —
so add it in `collect()`, next to `pluginValueClasses`, inside the same
`if` that fills the other per-plugin maps:

```js
				const thead = findAllByTag(el, "THEAD");
				result.pluginHeaderCells[name] = thead.length
					? findAllByTag(thead[0], "TH").map((th) => th.textContent.trim())
					: [];
```

with `pluginHeaderCells: {}` added to the `result` initialiser.

- [ ] **Step 3: Run to verify failure**

```bash
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k amps -v
```

Expected: FAIL — no `amps` rows (`[]`).

- [ ] **Step 4: Write the component**

Create `glances/outputs/static/js/v5/PluginAmps.vue`:

```vue
<template>
	<!-- No #head slot: the TUI paints no title and no column header
	(amps/render_curses_v5.py module docstring, v4 parity), so
	CollectionBlock renders no <thead> -- the `ports` case from G9-7 D4.
	`title` is still required by the shell: it names the block for assistive
	technology and shows while loading or erroring. -->
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td>
						<!-- The tier comes from the item's `count` level and lands on the
						NAME, as the TUI does (amps/render_curses_v5.py:78-79). -->
						<span class="gl-name gl-truncate" :class="cellClassFor(payload, item, 'count')" :title="item.name">{{
							item.name
						}}</span>
					</td>
					<td class="gl-num">
						<span>{{ countOf(item) }}</span>
					</td>
					<!-- Spec D6: the whole result, newlines included, in ONE cell.
					The TUI emits one row per line with the name and count blanked
					after the first; `pre-line` paints the same thing. -->
					<td><span class="gl-amp-result">{{ item.result }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { cellClassFor } from "./columns.js";
import CollectionBlock from "./CollectionBlock.vue";

const TITLE = "AMPS";

export default {
	name: "PluginAmps",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: nothing in this block depends on a CLI flag.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: hidden as a whole, never shrunk.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// amps/render_curses_v5.py:70-73: an AMP that has produced nothing yet
		// renders no row at all -- v4 skips it rather than painting an empty
		// one. Payload order: the TUI does not sort this block.
		rows() {
			return (this.payload?.data || []).filter((item) => item.result !== null && item.result !== undefined);
		},
	},
	methods: {
		cellClassFor,
		// amps/render_curses_v5.py:76: a regex-less AMP has nothing to count,
		// so the cell stays empty even when `count` is set.
		countOf(item) {
			return !item.regex || item.count === null || item.count === undefined ? "" : String(item.count);
		},
	},
};
</script>

<style scoped>
/* The TUI's name column (amps/render_curses_v5.py _NAME_COL_WIDTH = 16). */
.gl-plugin {
	--gl-name-width: 16ch;
}
/* Spec D6: a multi-line AMP result keeps its newlines in one cell. */
.gl-amp-result {
	white-space: pre-line;
}
</style>
```

Register it — import plus an entry appended at the END of `PLUGINS`
(`amps` is last in `RIGHT_SLOT`):

```js
	{
		name: "amps",
		component: PluginAmps,
		slot: "right",
		spec: { shape: "collection", required: ["name"] },
	},
```

- [ ] **Step 5: Rebuild and run**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k amps -v
```

Expected: 4 PASSED. Then the four WebUI files as in Task 1 Step 6 (27
plugins now; extend the verbatim registry list with `"amps"` if that test
fails).

- [ ] **Step 6: Stage, do not commit**

```bash
cd /home/nicolargo/dev/glances
git add glances/outputs/static/js/v5/PluginAmps.vue \
        glances/outputs/static/js/v5/plugins/index.js \
        glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_fixtures.js tests/fixtures/webui_render_probe.js \
        tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' || true
```

---

## Task 3: `vms` — the VM table

**Files:**
- Create: `glances/outputs/static/js/v5/PluginVms.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `CollectionBlock`, `cellClassFor`, `displayName` (`rows.js`),
  `formatAutoUnit` and `formatPercent` (`format.js`).
- Produces: the FIRST entry of the right group (`vms` leads `RIGHT_SLOT`).

**Reference:** `glances/plugins/vms/render_curses_v5.py:83-155`. Header:
`Engine?` `Name` `Status` `Core` `CPU%` `MEM/MAX` `LOAD 1/5/15min?`
`Release`. `Engine` only with more than one distinct engine (`:157`);
`LOAD` only when the first item publishes `load_1min` (`:162`). `MEM/MAX`
is ONE cell carrying the `memory_percent` tier over both halves
(deliberate, per the renderer's docstring). `CPU%` takes the `cpu_time`
tier, `LOAD` the `load_1min` tier; `Status` keeps its own status→role
mapping and is never `_levels`-coloured. No width cascade (spec D5): the
TUI defines none for `vms`. No `N/M` counter (spec §4).

- [ ] **Step 1: Add the fixtures**

```js
// vms: two engines on purpose, so the Engine column is shown (the TUI
// shows it only with >1 distinct engine, vms/render_curses_v5.py:157).
// `load_1min` present -> the LOAD column is shown (:162).
const VMS_FIXTURE = {
	_key: "name",
	data: [
		{
			name: "builder",
			engine: "virsh",
			status: "running",
			cpu_count: 4,
			cpu_time: 12.5,
			memory_usage: 2147483648,
			memory_total: 4294967296,
			load_1min: 0.5,
			load_5min: 0.7,
			load_15min: 1.2,
			release: "24.04",
		},
		{
			name: "sandbox",
			engine: "multipass",
			status: "stopped",
			cpu_count: 2,
			cpu_time: null,
			memory_usage: null,
			memory_total: null,
			load_1min: 0.0,
			load_5min: 0.0,
			load_15min: 0.0,
			release: null,
		},
	],
	max_name_size: 20,
	_levels: { builder: { cpu_time: { level: "careful" }, memory_percent: { level: "warning" } } },
};

// One engine and no load: both conditional columns disappear.
const VMS_ONE_ENGINE = {
	_key: "name",
	data: [
		{
			name: "builder",
			engine: "virsh",
			status: "running",
			cpu_count: 4,
			cpu_time: 12.5,
			memory_usage: 2147483648,
			memory_total: 4294967296,
			load_1min: null,
			release: "24.04",
		},
	],
	max_name_size: 20,
	_levels: {},
};
```

`ALL_FIXTURES`:

```js
	vms: { vms: VMS_FIXTURE },
	"vms-one-engine": { vms: VMS_ONE_ENGINE },
	"vms-empty": { vms: { _key: "name", data: [], _levels: {} } },
```

- [ ] **Step 2: Write the failing tests**

```python
# -------------------------------------------------------- vms TUI parity (G9-9A Task 3)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_renders_the_tui_columns_and_rows():
    """vms/render_curses_v5.py:83-155. Engine shown (two engines), LOAD
    shown (load_1min present), MEM and MAX in ONE cell, a missing value as
    `-` (spec divergence 5, `format.js` MISSING) -- never `_`.
    """
    payload = _run_render_probe("vms")
    assert payload["pluginHeaderCells"].get("vms") == [
        "Engine",
        "Name",
        "Status",
        "Core",
        "CPU%",
        "MEM/MAX",
        "LOAD 1/5/15min",
        "Release",
    ], f"got {payload['pluginHeaderCells'].get('vms')!r}"
    rows = _table_rows(payload, "vms", 8)
    assert rows == [
        ["virsh", "builder", "running", "4", "12.5%", "2.00G/4.00G", "0.5/0.7/1.2", "24.04"],
        ["multipass", "sandbox", "stopped", "2", "-", "-/-", "0.0/0.0/0.0", "-"],
    ], f"got {rows!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_hides_engine_and_load_when_the_data_makes_them_irrelevant():
    """One distinct engine -> no Engine column
    (vms/render_curses_v5.py:157). No `load_1min` -> no LOAD column
    (:162). Both are data-driven, never width-driven.
    """
    payload = _run_render_probe("vms-one-engine")
    assert payload["pluginHeaderCells"].get("vms") == [
        "Name",
        "Status",
        "Core",
        "CPU%",
        "MEM/MAX",
        "Release",
    ], f"got {payload['pluginHeaderCells'].get('vms')!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_vms_colours_cpu_and_memory_from_levels_and_never_the_status():
    """CPU% takes `cpu_time`'s tier, MEM/MAX takes `memory_percent`'s, and
    `status` keeps its own mapping -- the TUI never reads `_levels` for it
    (vms/render_curses_v5.py `_status_role`)."""
    payload = _run_render_probe("vms")
    classes = payload["pluginValueClasses"].get("vms") or []
    assert "gl-level-careful" in classes, f"got {classes!r}"
    assert "gl-level-warning" in classes, f"got {classes!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_vms_renders_no_block():
    payload = _run_render_probe("vms-empty")
    assert "vms" not in payload["slots"].get("right", []), f"got {payload['slots']!r}"
```

- [ ] **Step 3: Run to verify failure**

```bash
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k vms -v
```

Expected: FAIL — no header cells, no rows.

- [ ] **Step 4: Write the component**

Create `glances/outputs/static/js/v5/PluginVms.vue`:

```vue
<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header literals (vms/render_curses_v5.py:83-107), not
			schema labels: the renderer hardcodes them too, and the vms schema
			declares no short_name. -->
			<tr>
				<th v-if="showEngine" class="gl-header">Engine</th>
				<th class="gl-header">Name</th>
				<th class="gl-header gl-num">Status</th>
				<th class="gl-header gl-num">Core</th>
				<th class="gl-header gl-num">CPU%</th>
				<th class="gl-header gl-num">MEM/MAX</th>
				<th v-if="showLoad" class="gl-header gl-num">LOAD 1/5/15min</th>
				<th class="gl-header">Release</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td v-if="showEngine"><span>{{ item.engine }}</span></td>
					<td>
						<span class="gl-name gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
					</td>
					<!-- `status` keeps the TUI's own mapping and is never coloured
					from `_levels` (vms/render_curses_v5.py `_status_role`). Colour
					is out of scope for this port: the status TEXT is the signal. -->
					<td class="gl-num"><span>{{ item.status || "-" }}</span></td>
					<td class="gl-num"><span>{{ fmt(item.cpu_count) }}</span></td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_time')">{{ formatPercent(item.cpu_time) }}</span>
					</td>
					<!-- ONE cell for MEM and MAX, both carrying the memory_percent
					tier: the TUI glues them deliberately (renderer docstring). -->
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{ memText(item) }}</span>
					</td>
					<td v-if="showLoad" class="gl-num">
						<span :class="cellClassFor(payload, item, 'load_1min')">{{ loadText(item) }}</span>
					</td>
					<td><span>{{ fmt(item.release) }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatAutoUnit, formatPercent } from "./format.js";
import { cellClassFor } from "./columns.js";
import { displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";

const TITLE = "VMS";

export default {
	name: "PluginVms",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: no vms column depends on a CLI flag.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: spec D5, vms has no width cascade because the
		// TUI defines none for it -- the block scrolls instead.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// Payload order: the sort is server-side (vms/model_v5.py
		// `sort_vm_stats`, aligned on the process sort), and the renderer does
		// not re-sort.
		rows() {
			return this.payload?.data || [];
		},
		// vms/render_curses_v5.py:157 -- more than one DISTINCT engine.
		showEngine() {
			return new Set(this.rows.map((item) => String(item.engine ?? ""))).size > 1;
		},
		// :162 -- the FIRST item decides, exactly as the TUI does: the engine
		// either publishes load for all its VMs or for none.
		showLoad() {
			return this.rows.length > 0 && this.rows[0].load_1min !== null && this.rows[0].load_1min !== undefined;
		},
	},
	methods: {
		cellClassFor,
		formatPercent,
		nameOf(item) {
			return displayName(item, "name");
		},
		// vms/render_curses_v5.py `_fmt`: a null renders as the placeholder.
		fmt(value) {
			return value === null || value === undefined ? "-" : String(value);
		},
		memText(item) {
			return `${formatAutoUnit(item.memory_usage)}/${formatAutoUnit(item.memory_total)}`;
		},
		// The TUI formats the three averages at one decimal and drops the whole
		// cell if any is missing (`except (KeyError, TypeError)`); showLoad has
		// already established that the engine publishes them.
		loadText(item) {
			const parts = [item.load_1min, item.load_5min, item.load_15min];
			if (parts.some((value) => typeof value !== "number")) return "-";
			return parts.map((value) => value.toFixed(1)).join("/");
		},
	},
};
</script>

<style scoped>
/* The TUI's name column (vms/render_curses_v5.py max_name_size default 20). */
.gl-plugin {
	--gl-name-width: 20ch;
}
</style>
```

Register it — import plus an entry inserted **before** the `processcount`
entry, so the right group reads `vms`, `processcount`, `amps` for now:

```js
	{
		name: "vms",
		component: PluginVms,
		slot: "right",
		spec: { shape: "collection", required: ["name"] },
	},
```

- [ ] **Step 5: Rebuild and run**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k vms -v
```

Expected: 4 PASSED. If `formatPercent(12.5)` renders `12.5%` but the test
expected something else, trust `format.js` and fix the test — the helper is
the shared contract.

Then the four WebUI files (28 plugins).

- [ ] **Step 6: Stage, do not commit** — same `git add` shape as Task 2,
with `PluginVms.vue`, then `git status --short | grep -v '^[AM] '`.

---

## Task 4: `containers` — the table, all columns

**Files:**
- Create: `glances/outputs/static/js/v5/PluginContainers.vue`
- Modify: `glances/outputs/static/js/v5/plugins/index.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `CollectionBlock`, `cellClassFor`, `displayName`,
  `formatAutoUnit`, `formatPercent`, `formatNetworkRate`.
- Produces: `PluginContainers.vue` with a `visibleColumns` computed that
  Task 6 replaces with the cascade-aware version. Task 6 relies on the
  column keys being exactly: `engine`, `pod`, `name`, `status`, `uptime`,
  `cpu`, `mem`, `memory_max`, `diskio`, `networkio`, `ports`, `command`
  — the keys of `_COL_GEOMETRY` plus `name`.

**Reference:** `glances/plugins/containers/render_curses_v5.py:124-165`
(header), `:168-215` (cells), `:261-265` (data-driven columns). This task
implements the **data-driven** family only (spec §5.1); the width cascade
is Tasks 5–6. `disable_stats` and `max_name_size` arrive in the payload as
metadata (`containers/model_v5.py:220-221`). Network rates follow
`serverArgs.byte`, identically to `network` — reuse `formatNetworkRate`.
IO cells are `formatAutoUnit(value) + "B"` (`_io_cell`, the renderer's
`auto_unit(int(value)) + "B"`).

- [ ] **Step 1: Add the fixtures**

```js
// containers: two engines (Engine column shown), one pod (Pod column
// shown), a memory limit (the /MAX column shown). The second item has no
// rates yet -- cycle 1 -- so every missing cell must read "-".
const CONTAINERS_FIXTURE = {
	_key: "name",
	data: [
		{
			name: "web",
			engine: "docker",
			pod_name: "frontend",
			status: "running",
			uptime: "2 days",
			cpu_percent: 12.5,
			memory_usage_no_cache: 536870912,
			memory_limit: 2147483648,
			io_rx: 1024,
			io_wx: 2048,
			network_rx: 100,
			network_tx: 200,
			ports: "0.0.0.0:80->80/tcp",
			command: "nginx -g daemon off;",
		},
		{
			name: "db",
			engine: "podman",
			pod_name: null,
			status: "paused",
			uptime: null,
			cpu_percent: null,
			memory_usage_no_cache: null,
			memory_limit: null,
			io_rx: null,
			io_wx: null,
			network_rx: null,
			network_tx: null,
			ports: null,
			command: null,
		},
	],
	max_name_size: 20,
	disable_stats: [],
	_levels: { web: { cpu_percent: { level: "careful" }, memory_percent: { level: "critical", prominent: true } } },
};

// `[containers] disable_stats=ports,command` -- config, not width: those
// two columns are gone whatever the window size.
const CONTAINERS_DISABLED_STATS = {
	...CONTAINERS_FIXTURE,
	disable_stats: ["ports", "command"],
};
```

`ALL_FIXTURES`:

```js
	containers: { containers: CONTAINERS_FIXTURE },
	"containers-disable-stats": { containers: CONTAINERS_DISABLED_STATS },
	"containers-empty": { containers: { _key: "name", data: [], _levels: {} } },
```

- [ ] **Step 2: Write the failing tests**

```python
# ------------------------------------------------- containers TUI parity (G9-9A Task 4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_renders_the_tui_columns_and_rows():
    """containers/render_curses_v5.py:124-215. `CONTAINER` IS the title (no
    separate title row, G9-6 D6). Engine, Pod and /MAX are shown because the
    data makes them relevant (:261-265). Rates follow `network`'s bit
    default: 100 B/s -> "800b".
    """
    payload = _run_render_probe("containers")
    assert payload["pluginHeaderCells"].get("containers") == [
        "Engine",
        "Pod",
        "CONTAINER",
        "Status",
        "Uptime",
        "CPU%",
        "MEM",
        "/MAX",
        "IOR/s",
        "IOW/s",
        "Rx/s",
        "Tx/s",
        "Ports",
        "Command",
    ], f"got {payload['pluginHeaderCells'].get('containers')!r}"
    rows = _table_rows(payload, "containers", 14)
    assert rows[0] == [
        "docker",
        "frontend",
        "web",
        "running",
        "2 days",
        "12.5%",
        "512M",
        "/2.00G",
        "1024B",
        "2KB",
        "800b",
        "1.6Kb",
        "0.0.0.0:80->80/tcp",
        "nginx -g daemon off;",
    ], f"got {rows[0]!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_shows_the_placeholder_for_every_missing_value():
    """Spec divergence 5: the WebUI's single placeholder is `-`
    (`format.js` MISSING), not the `_` this TUI renderer prints. The `db`
    row has no rate, no uptime and no command yet.
    """
    payload = _run_render_probe("containers")
    row = _table_rows(payload, "containers", 14)[1]
    assert "_" not in " ".join(row), f"got {row!r}"
    assert row[4] == "-", f"uptime must be the placeholder, got {row!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_containers_honours_disable_stats_from_the_config():
    """`[containers] disable_stats` reaches the browser as payload metadata
    (containers/model_v5.py:220-221) and removes columns regardless of
    width (spec §5.1)."""
    payload = _run_render_probe("containers-disable-stats")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Ports" not in headers, f"got {headers!r}"
    assert "Command" not in headers, f"got {headers!r}"
    assert "CPU%" in headers, f"vacuous: the rest must survive: {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_empty_containers_renders_no_block():
    payload = _run_render_probe("containers-empty")
    assert "containers" not in payload["slots"].get("right", []), f"got {payload['slots']!r}"
```

- [ ] **Step 3: Run to verify failure**

```bash
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k containers -v
```

Expected: FAIL — no header cells, no rows.

- [ ] **Step 4: Write the component**

Create `glances/outputs/static/js/v5/PluginContainers.vue`:

```vue
<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header literals (containers/render_curses_v5.py:124-165).
			`CONTAINER` is the block title -- no separate title row, as `fs` does
			in G9-6 D6. -->
			<tr>
				<th v-if="shows('engine')" class="gl-header">Engine</th>
				<th v-if="shows('pod')" class="gl-header">Pod</th>
				<th v-if="shows('name')" class="gl-header">{{ TITLE }}</th>
				<th v-if="shows('status')" class="gl-header gl-num">Status</th>
				<th v-if="shows('uptime')" class="gl-header gl-num">Uptime</th>
				<th v-if="shows('cpu')" class="gl-header gl-num">CPU%</th>
				<th v-if="shows('mem')" class="gl-header gl-num">MEM</th>
				<th v-if="shows('memory_max')" class="gl-header">/MAX</th>
				<template v-if="shows('diskio')">
					<th class="gl-header gl-num">IOR/s</th>
					<th class="gl-header gl-num">IOW/s</th>
				</template>
				<template v-if="shows('networkio')">
					<th class="gl-header gl-num">Rx/s</th>
					<th class="gl-header gl-num">Tx/s</th>
				</template>
				<th v-if="shows('ports')" class="gl-header">Ports</th>
				<th v-if="shows('command')" class="gl-header">Command</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td v-if="shows('engine')"><span>{{ fmt(item.engine) }}</span></td>
					<td v-if="shows('pod')"><span>{{ fmt(item.pod_name) }}</span></td>
					<td v-if="shows('name')">
						<span class="gl-name gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
					</td>
					<!-- The TUI colours `status` from its own mapping, never from
					`_levels` (containers/render_curses_v5.py `_status_role`). -->
					<td v-if="shows('status')" class="gl-num"><span>{{ fmt(item.status) }}</span></td>
					<td v-if="shows('uptime')" class="gl-num"><span>{{ fmt(item.uptime) }}</span></td>
					<td v-if="shows('cpu')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_percent')">{{
							formatPercent(item.cpu_percent)
						}}</span>
					</td>
					<!-- The displayed MEM is the no-cache value (the v4 MEM column);
					`memory_usage` is the export value and is NOT shown. -->
					<td v-if="shows('mem')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{
							formatAutoUnit(item.memory_usage_no_cache)
						}}</span>
					</td>
					<!-- The limit is never coloured. -->
					<td v-if="shows('memory_max')"><span>/{{ formatAutoUnit(item.memory_limit) }}</span></td>
					<template v-if="shows('diskio')">
						<td class="gl-num"><span>{{ ioText(item.io_rx) }}</span></td>
						<td class="gl-num"><span>{{ ioText(item.io_wx) }}</span></td>
					</template>
					<template v-if="shows('networkio')">
						<td class="gl-num"><span>{{ netText(item.network_rx) }}</span></td>
						<td class="gl-num"><span>{{ netText(item.network_tx) }}</span></td>
					</template>
					<td v-if="shows('ports')"><span class="gl-truncate">{{ fmt(item.ports) }}</span></td>
					<td v-if="shows('command')">
						<span class="gl-command gl-truncate" :title="fmt(item.command)">{{ fmt(item.command) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatAutoUnit, formatNetworkRate, formatPercent } from "./format.js";
import { cellClassFor } from "./columns.js";
import { displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";

const TITLE = "CONTAINER";

export default {
	name: "PluginContainers",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// `byte` (--byte) switches the network rates from bits to bytes, as the
		// TUI reads `view["byte"]` (containers/render_curses_v5.py:208).
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused in this task: Task 6 replaces `hiddenColumns`
		// with the measured width cascade, which this component owns itself
		// rather than reading from the shell.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// Payload order: the sort is server-side (containers/model_v5.py
		// `_sort`, aligned on the process sort).
		rows() {
			return this.payload?.data || [];
		},
		// Spec §5.1 -- the DATA-DRIVEN family, plus the config's own list.
		// Width-driven hiding is added in Task 6.
		hiddenColumns() {
			const hidden = new Set(this.payload?.disable_stats || []);
			if (new Set(this.rows.map((item) => String(item.engine ?? ""))).size <= 1) hidden.add("engine");
			if (!this.rows.some((item) => item.pod_name)) hidden.add("pod");
			if (!this.rows.some((item) => typeof item.memory_limit === "number")) hidden.add("memory_max");
			return hidden;
		},
	},
	methods: {
		cellClassFor,
		formatAutoUnit,
		formatPercent,
		shows(column) {
			return !this.hiddenColumns.has(column);
		},
		nameOf(item) {
			return displayName(item, "name");
		},
		fmt(value) {
			return value === null || value === undefined || value === "" ? "-" : String(value);
		},
		// containers/render_curses_v5.py `_io_cell`: auto_unit() plus a "B".
		ioText(value) {
			return typeof value === "number" ? `${formatAutoUnit(value)}B` : "-";
		},
		// `_net_cell` is `network`'s rule: bits by default, bytes under --byte.
		netText(value) {
			return formatNetworkRate(value, !!this.serverArgs.byte);
		},
	},
};
</script>

<style scoped>
/* The TUI's name column (containers/render_curses_v5.py `max_name_size`,
 * default 20 -- published in the payload, capped here at the same value). */
.gl-plugin {
	--gl-name-width: 20ch;
}
/* The unbounded column: the TUI budgets it at _MIN_COMMAND_WIDTH = 8, and
 * Task 6's measuring pass depends on this cap holding. */
.gl-command {
	max-width: 24ch;
}
</style>
```

Register it — import plus an entry inserted **between** `vms` and
`processcount`, giving the TUI's order `vms`, `containers`,
`processcount`, `amps`:

```js
	{
		name: "containers",
		component: PluginContainers,
		slot: "right",
		spec: { shape: "collection", required: ["name"] },
	},
```

- [ ] **Step 5: Rebuild and run**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k containers -v
```

Expected: 4 PASSED. If a formatted number disagrees with the test, verify
against `format.js` (`formatAutoUnit(536870912)` → `512M`, `formatAutoUnit(2147483648)` → `2.00G`,
`formatAutoUnit(1024)` → `1024`, `formatAutoUnit(2048)` → `2K`,
`formatNetworkRate(100, false)` → `800b`, `formatNetworkRate(200, false)` →
`1.6Kb` — all verified by running the module under node) and correct the test, not the
helper.

- [ ] **Step 6: Run every WebUI test file**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_degrade_drift.py \
  tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py -q
```

Expected: all pass, 29 plugins registered. The right group must read
`["vms", "containers", "processcount", "amps"]` in
`test_every_slot_orders_its_plugins_like_the_tui`.

- [ ] **Step 7: Stage, do not commit** — `PluginContainers.vue`,
`plugins/index.js`, the bundle, the fixtures, the test file. Then
`git status --short | grep -v '^[AM] '`.

---

## Task 5: the drop order and the column rules, as pure modules

**Files:**
- Create: `glances/outputs/static/js/v5/drop_order.js`
- Create: `glances/outputs/static/js/v5/containers_columns.js`
- Create: `tests/js/drop_order.test.mjs`
- Create: `tests/js/containers_columns.test.mjs`
- Create: `tests/test_webui_v5_containers_drop_order_drift.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `drop_order.js`: `export const CONTAINERS_DROP_ORDER` (array of column
    keys, the TUI's order) and
    `export function dropCascade(order)` → `[{key: "drop_<column>", value: true}, …]`,
    the shape `resolveDegrade()` consumes.
  - `containers_columns.js`:
    `export function dataDrivenHidden(rows, disableStats)` → `Set<string>`
    and `export function hiddenColumns(rows, disableStats, flags)` →
    `Set<string>`, where `flags` is the object `resolveDegrade()` returns.
    Task 6's component calls `hiddenColumns` only.

- [ ] **Step 1: Write the failing node tests**

Create `tests/js/drop_order.test.mjs`:

```js
import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTAINERS_DROP_ORDER, dropCascade } from "../../glances/outputs/static/js/v5/drop_order.js";

test("the drop order is the TUI's, in the TUI's order", () => {
	assert.deepEqual(CONTAINERS_DROP_ORDER, [
		"command",
		"ports",
		"memory_max",
		"pod",
		"engine",
		"diskio",
		"networkio",
		"uptime",
		"status",
	]);
});

test("the columns the TUI never drops are absent from the order", () => {
	for (const column of ["name", "cpu", "mem"]) {
		assert.ok(!CONTAINERS_DROP_ORDER.includes(column), `${column} must never be droppable`);
	}
});

test("dropCascade produces one resolveDegrade step per column, in order", () => {
	assert.deepEqual(dropCascade(["command", "ports"]), [
		{ key: "drop_command", value: true },
		{ key: "drop_ports", value: true },
	]);
});
```

Create `tests/js/containers_columns.test.mjs`:

```js
import assert from "node:assert/strict";
import { test } from "node:test";

import { dataDrivenHidden, hiddenColumns } from "../../glances/outputs/static/js/v5/containers_columns.js";

const ONE_ENGINE = [{ engine: "docker", pod_name: null, memory_limit: null }];
const TWO_ENGINES = [
	{ engine: "docker", pod_name: "frontend", memory_limit: 2147483648 },
	{ engine: "podman", pod_name: null, memory_limit: null },
];

test("a single engine hides the Engine column", () => {
	assert.ok(dataDrivenHidden(ONE_ENGINE, []).has("engine"));
	assert.ok(!dataDrivenHidden(TWO_ENGINES, []).has("engine"));
});

test("no pod hides the Pod column, one pod shows it", () => {
	assert.ok(dataDrivenHidden(ONE_ENGINE, []).has("pod"));
	assert.ok(!dataDrivenHidden(TWO_ENGINES, []).has("pod"));
});

test("no memory limit anywhere hides the /MAX column", () => {
	assert.ok(dataDrivenHidden(ONE_ENGINE, []).has("memory_max"));
	assert.ok(!dataDrivenHidden(TWO_ENGINES, []).has("memory_max"));
});

test("disable_stats hides its columns whatever the data says", () => {
	const hidden = dataDrivenHidden(TWO_ENGINES, ["ports", "command"]);
	assert.ok(hidden.has("ports"));
	assert.ok(hidden.has("command"));
});

test("an empty collection hides every conditional column", () => {
	const hidden = dataDrivenHidden([], []);
	for (const column of ["engine", "pod", "memory_max"]) assert.ok(hidden.has(column));
});

test("cascade flags add to the data-driven set, never remove from it", () => {
	const hidden = hiddenColumns(TWO_ENGINES, [], { drop_command: true, drop_ports: true });
	assert.ok(hidden.has("command"));
	assert.ok(hidden.has("ports"));
	assert.ok(!hidden.has("engine"), "two engines: Engine must survive the cascade");
});

test("a flag that is not a drop_ flag is ignored", () => {
	assert.ok(!hiddenColumns(TWO_ENGINES, [], { hide_gpu: true }).has("gpu"));
});

test("the never-dropped columns survive every flag", () => {
	const every = {};
	for (const column of ["command", "ports", "memory_max", "pod", "engine", "diskio", "networkio", "uptime", "status"]) {
		every[`drop_${column}`] = true;
	}
	const hidden = hiddenColumns(TWO_ENGINES, [], every);
	for (const column of ["name", "cpu", "mem"]) assert.ok(!hidden.has(column), `${column} must survive`);
});
```

Create the Python drift test,
`tests/test_webui_v5_containers_drop_order_drift.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI's container column drop order is the TUI's.

`containers/render_curses_v5.py:60` decides which column a narrow terminal
loses first; js/v5/drop_order.js keeps a copy, because the browser cannot
import Python. A silent divergence there means the WebUI hides a DIFFERENT
column than the terminal, so this test makes drift a failure — as
tests/test_webui_v5_degrade_drift.py does for the two zone cascades.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from glances.plugins.containers.render_curses_v5 import _COL_GEOMETRY, _DROP_ORDER

_DROP_ORDER_JS = (
    Path(__file__).resolve().parent.parent / "glances" / "outputs" / "static" / "js" / "v5" / "drop_order.js"
)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _js_order() -> list[str]:
    """Import drop_order.js under node and return its array as data."""
    script = (
        f"import({json.dumps(_DROP_ORDER_JS.as_uri())})"
        ".then((m) => process.stdout.write(JSON.stringify(m.CONTAINERS_DROP_ORDER)))"
    )
    result = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_the_js_copy_is_the_tui_order():
    assert _js_order() == list(_DROP_ORDER)


def test_the_copy_is_not_empty():
    """Guard: an empty list would make the comparison above vacuous if the
    plugin constant ever emptied too."""
    assert _js_order()


def test_no_undroppable_column_leaked_into_the_order():
    """`name`, `cpu` and `mem` are absent from `_DROP_ORDER` by design —
    they are what the block is for. A future edit adding one to either copy
    must fail here even if both copies agree."""
    for column in ("name", "cpu", "mem"):
        assert column not in _js_order()


def test_every_droppable_column_has_a_geometry_in_the_tui():
    """The inverse mistake: a column dropped by the WebUI that the TUI has
    no geometry for is a name that no longer exists in the renderer."""
    known = set(_COL_GEOMETRY) | {"name"}
    assert set(_js_order()) <= known, f"unknown columns: {set(_js_order()) - known}"
```

- [ ] **Step 2: Run all three to verify they fail**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_containers_drop_order_drift.py -v
python -m pytest tests/test_webui_v5_js.py -v
```

Expected: FAIL — `drop_order.js` and `containers_columns.js` do not exist
(node exits non-zero, `ERR_MODULE_NOT_FOUND`).

- [ ] **Step 3: Write the two pure modules**

Create `glances/outputs/static/js/v5/drop_order.js`:

```js
// Glances v5 WebUI -- the container table's column drop order, the TUI's.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it.
//
// A copy of `_DROP_ORDER` (glances/plugins/containers/render_curses_v5.py:60):
// the browser cannot import Python. `name`, `cpu` and `mem` are deliberately
// absent -- they are what the block is for, and the TUI never drops them.
// tests/test_webui_v5_containers_drop_order_drift.py compares the two copies;
// never edit one side alone.
export const CONTAINERS_DROP_ORDER = [
	"command",
	"ports",
	"memory_max",
	"pod",
	"engine",
	"diskio",
	"networkio",
	"uptime",
	"status",
];

// The shape resolveDegrade() (degrade.js) consumes: one cumulative flag per
// step, applied in order, until the block fits. Keyed `drop_<column>` so a
// block's flag set never collides with the shell's own zone flags.
export function dropCascade(order) {
	return order.map((column) => ({ key: `drop_${column}`, value: true }));
}
```

Create `glances/outputs/static/js/v5/containers_columns.js`:

```js
// Glances v5 WebUI -- which container columns are visible.
//
// Pure: no DOM, no fetch, so `node --test` can load it. Logic inside a .vue
// file cannot be unit-tested, and these rules are the ones most likely to
// drift from the TUI, so they live here.
//
// Two unrelated families, kept apart on purpose (spec §5):
//   - DATA-DRIVEN: the data (or the config) makes a column irrelevant. No
//     measurement, no window size -- containers/render_curses_v5.py:261-265
//     and the `disable_stats` seed at :80.
//   - WIDTH-DRIVEN: the row does not fit, so the cascade in drop_order.js
//     hides the least useful column first. That is `flags` below.

// containers/render_curses_v5.py:261-265 plus the config's own list.
export function dataDrivenHidden(rows, disableStats) {
	const hidden = new Set(disableStats || []);
	const items = rows || [];
	// `show_engine`: strictly MORE than one distinct engine. An empty
	// collection has none, so the column is hidden -- as the TUI's `len({...})
	// > 1` also resolves to false.
	if (new Set(items.map((item) => String(item.engine ?? ""))).size <= 1) hidden.add("engine");
	// `show_pod`: any item with a pod name.
	if (!items.some((item) => item.pod_name)) hidden.add("pod");
	// `show_mem_max`: any item with a memory limit. `0` is not a limit.
	if (!items.some((item) => typeof item.memory_limit === "number" && item.memory_limit > 0)) hidden.add("memory_max");
	return hidden;
}

// The union of both families. Never the difference: a cascade flag can only
// ADD to what the data already made irrelevant, so a column the config
// disabled cannot come back when the window widens.
export function hiddenColumns(rows, disableStats, flags) {
	const hidden = dataDrivenHidden(rows, disableStats);
	for (const [key, value] of Object.entries(flags || {})) {
		if (value && key.startsWith("drop_")) hidden.add(key.slice("drop_".length));
	}
	return hidden;
}
```

- [ ] **Step 4: Run all three to verify they pass**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_containers_drop_order_drift.py tests/test_webui_v5_js.py -v
```

Expected: all PASSED. `test_js_test_files_exist` picks the two new
`.test.mjs` files up automatically (it globs `tests/js/*.test.mjs`).

- [ ] **Step 5: Stage, do not commit**

```bash
cd /home/nicolargo/dev/glances
git add glances/outputs/static/js/v5/drop_order.js \
        glances/outputs/static/js/v5/containers_columns.js \
        tests/js/drop_order.test.mjs tests/js/containers_columns.test.mjs \
        tests/test_webui_v5_containers_drop_order_drift.py
git status --short | grep -v '^[AM] ' || true
```

No bundle rebuild is needed yet: nothing imports these modules until
Task 6.

---

## Task 6: measure the block and run the cascade

**Files:**
- Create: `glances/outputs/static/js/v5/fit_block.js`
- Modify: `glances/outputs/static/js/v5/PluginContainers.vue`
- Modify: `glances/outputs/static/css/v5.css:252`
- Modify: `tests/fixtures/webui_render_probe.js`
- Modify: `tests/fixtures/webui_render_fixtures.js`
- Test: `tests/test_webui_v5_render.py`

**Interfaces:**
- Consumes: `dropCascade` and `CONTAINERS_DROP_ORDER` (Task 5),
  `hiddenColumns` (Task 5), `resolveDegrade` (existing `degrade.js`).
- Produces: `fit_block.js` exporting `fitBlockMixin` — a Vue mixin giving
  the component `this.dropFlags` (object, `{}` when nothing is dropped) and
  `this.fitBlock(cascade)` (async). G9-9B's `processlist` reuses it
  unchanged.

**Reference:** spec §5.2 and §5.3. `AppShell.measureZone()` /
`AppShell.refit()` are the model to copy — including the two guards that
make them safe: an in-flight flag (`refitting`) and the "only reassign when
the flag set actually changed" comparison (`sameFlags`).

- [ ] **Step 1: Extend the probe to measure blocks**

In `tests/fixtures/webui_render_fixtures.js`, add block widths and export
them:

```js
// Per-BLOCK widths, keyed by the `data-plugin` attribute the shell puts on
// each component's root. Same contract as WIDTH_FIXTURES: `available` is
// clientWidth, `content` scrollWidth, and the harness shrinks `content` by
// CONTENT_PER_NOTCH per applied flag (FakeElement.scrollWidth).
const BLOCK_WIDTH_FIXTURES = {
	// Fits as it is: every column survives.
	"containers-wide": { containers: { available: 1400, content: 900 } },
	// 1000 - 150 = 850 <= 900: exactly one notch, so `command` alone goes.
	"containers-one-notch": { containers: { available: 900, content: 1000 } },
	// 2000 - 9*150 = 650 > 300: the cascade runs to its last step, so all
	// nine droppable columns go and only CONTAINER / CPU% / MEM survive.
	"containers-narrow": { containers: { available: 300, content: 2000 } },
};
```

Add `BLOCK_WIDTH_FIXTURES` to this file's `module.exports`, and the three
scenarios to `ALL_FIXTURES`, all three reusing the Task 4 payload:

```js
	"containers-wide": { containers: CONTAINERS_FIXTURE },
	"containers-one-notch": { containers: CONTAINERS_FIXTURE },
	"containers-narrow": { containers: CONTAINERS_FIXTURE },
```

In `tests/fixtures/webui_render_probe.js`: add `BLOCK_WIDTH_FIXTURES` to
the destructured `require(...)`, then add a block-width applier next to
`applyWidths()`:

```js
// Same as applyWidths(), one level down: blocks are addressed by their
// `data-plugin` attribute rather than by `data-slot`, because a per-block
// cascade (js/v5/fit_block.js) measures the component's own root.
function applyBlockWidths() {
	const widths = BLOCK_WIDTH_FIXTURES[scenario];
	if (!widths) return false;
	for (const [plugin, { available, content }] of Object.entries(widths)) {
		for (const block of findAllByAttr(appDiv, "data-plugin")) {
			if (block.getAttribute("data-plugin") !== plugin) continue;
			block._width = available;
			block._content = content;
		}
	}
	return true;
}
```

and drive the block refits from the existing `setImmediate` tail:

```js
setImmediate(async () => {
	if (applyWidths() && sandbox.__glancesRefit) await sandbox.__glancesRefit();
	// The blocks measure themselves (fit_block.js registers each instance's
	// refit here); the harness never fires their ResizeObserver, so it calls
	// them once, after the widths are in place.
	if (applyBlockWidths() && Array.isArray(sandbox.__glancesBlockRefits)) {
		for (const refit of sandbox.__glancesBlockRefits) await refit();
	}
	process.stdout.write(JSON.stringify(collect()));
});
```

Add `__glancesBlockRefits: []` to the `sandbox` object so the mixin has an
array to push into (a real browser gets it from the mixin itself; see
Step 3).

- [ ] **Step 2: Write the failing tests**

```python
# ------------------------------------- containers column cascade (G9-9A Task 6)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_wide_containers_block_keeps_every_column():
    """The cascade starts from NO flag on every pass (degrade.js
    `resolveDegrade`), so a block that fits drops nothing -- this is also
    what gives the columns back when the window widens."""
    payload = _run_render_probe("containers-wide")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Command" in headers, f"got {headers!r}"
    assert "Status" in headers, f"got {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_one_notch_drops_the_command_column_first():
    """`_DROP_ORDER`'s first entry (containers/render_curses_v5.py:60):
    `command` goes before anything else -- the deliberate divergence from
    processlist, where Command is the protected tail."""
    payload = _run_render_probe("containers-one-notch")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Command" not in headers, f"got {headers!r}"
    assert "Ports" in headers, f"only ONE notch was budgeted: {headers!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_a_narrow_containers_block_keeps_only_the_undroppable_columns():
    """The cascade run to its last step: `name`, `cpu` and `mem` are absent
    from `_DROP_ORDER`, so CONTAINER / CPU% / MEM always survive."""
    payload = _run_render_probe("containers-narrow")
    assert payload["pluginHeaderCells"].get("containers") == [
        "CONTAINER",
        "CPU%",
        "MEM",
    ], f"got {payload['pluginHeaderCells'].get('containers')!r}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_an_unmeasurable_containers_block_keeps_every_column():
    """The `containers` scenario sets no block width, so clientWidth is 0 --
    `fits()` reads that as "cannot measure" and must never degrade on it
    (degrade.js). A hidden tab must not lose the user's columns."""
    payload = _run_render_probe("containers")
    headers = payload["pluginHeaderCells"].get("containers") or []
    assert "Command" in headers, f"got {headers!r}"
```

- [ ] **Step 3: Run to verify failure**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k "notch or narrow or wide or unmeasurable" -v
```

Expected: the wide and unmeasurable tests PASS (no cascade yet, so nothing
is ever dropped — they are the regression guards), and the one-notch and
narrow tests FAIL (every column still present).

- [ ] **Step 4: Write the mixin**

Create `glances/outputs/static/js/v5/fit_block.js`:

```js
// Glances v5 WebUI -- per-BLOCK horizontal degradation.
//
// AppShell measures ZONES, because the top and header cascades hide whole
// blocks: that is the shell's business. A cascade that hides columns INSIDE
// one block is the component's business (AppShell.vue's spec D7: "a block
// that disappears is the shell's business; a block that merely shrinks is
// the component's"), so the state lives here, in a mixin the component adds.
//
// The ORDER and the fit test still come from degrade.js -- this module owns
// only the measurement, exactly as AppShell.measureZone() does for a zone.

import { resolveDegrade } from "./degrade.js";

// Same rule as AppShell's sameFlags(): both cascades resolve to a flat object
// of primitives, `resolveDegrade` always returns a fresh object, and without
// this comparison a `===` test would never be true -- so the component would
// re-render on every pass and its ResizeObserver would oscillate.
function sameFlags(a, b) {
	const aKeys = Object.keys(a);
	const bKeys = Object.keys(b);
	return aKeys.length === bKeys.length && aKeys.every((key) => a[key] === b[key]);
}

export const fitBlockMixin = {
	data() {
		return {
			// {} = nothing dropped, which is also what an environment without
			// measurement keeps.
			dropFlags: {},
			// In-flight guard, like AppShell.refitting: fitBlock() is triggered
			// from mounted(), from every payload change and from every
			// ResizeObserver callback, and measuring MUTATES dropFlags (and
			// therefore the DOM) once per candidate notch.
			fitting: false,
			blockObserver: null,
		};
	},
	mounted() {
		// The render probe drives the pass through this hook: its fake DOM has
		// no ResizeObserver and no layout until the harness sets widths.
		if (typeof window !== "undefined") {
			if (!Array.isArray(window.__glancesBlockRefits)) window.__glancesBlockRefits = [];
			window.__glancesBlockRefits.push(() => this.fitBlock());
		}
		if (typeof ResizeObserver === "function" && this.$el?.nodeType === 1) {
			// Not awaited: a rejection here would surface as an unhandled promise
			// rejection. The in-flight guard is cleared by fitBlock()'s `finally`,
			// so a failed pass simply retries on the next resize.
			this.blockObserver = new ResizeObserver(() => {
				this.fitBlock().catch(() => {});
			});
			this.blockObserver.observe(this.$el);
		}
	},
	unmounted() {
		if (this.blockObserver) this.blockObserver.disconnect();
	},
	methods: {
		// Apply a candidate flag set, let Vue re-render, and report what the
		// browser says about the table inside this block.
		async measureBlock(flags) {
			if (!sameFlags(flags, this.dropFlags)) this.dropFlags = flags;
			await this.$nextTick();
			const block = this.$el;
			if (!block || block.nodeType !== 1) return { content: 0, available: 0 };
			// Harness hook, as AppShell.measureZone() does: a real element
			// ignores this expando; the probe's FakeElement models scrollWidth
			// shrinking by one CONTENT_PER_NOTCH per applied flag.
			block._notches = Object.keys(flags).length;
			// Measure the text at its natural width: shrunk into its ellipsis it
			// never overflows and the cascade would never run. `.gl-command` and
			// `.gl-name` keep their caps (css/v5.css) -- the TUI budgets Command
			// at _MIN_COMMAND_WIDTH for the same reason.
			block.classList.add("gl-measuring");
			const table = block.querySelector?.("table");
			const reading = {
				content: table ? table.scrollWidth : block.scrollWidth,
				available: block.clientWidth,
			};
			block.classList.remove("gl-measuring");
			return reading;
		},
		// Re-run the cascade from scratch: starting from no flag is what gives
		// the columns back when the window widens.
		async fitBlock(cascade) {
			const steps = cascade || this.dropCascadeSteps;
			if (this.fitting || !steps) return;
			this.fitting = true;
			const previous = this.dropFlags;
			try {
				const flags = await resolveDegrade(steps, (candidate) => this.measureBlock(candidate));
				// Only publish the steady state when it actually differs from what
				// was in effect before this pass -- this is what stops an observer
				// feedback loop.
				if (!sameFlags(flags, previous)) this.dropFlags = flags;
				else if (!sameFlags(this.dropFlags, previous)) this.dropFlags = previous;
			} finally {
				this.fitting = false;
			}
		},
	},
};
```

- [ ] **Step 5: Wire it into `PluginContainers.vue`**

Three edits:

1. Import and register the mixin and the Task 5 modules:

```js
import { CONTAINERS_DROP_ORDER, dropCascade } from "./drop_order.js";
import { hiddenColumns } from "./containers_columns.js";
import { fitBlockMixin } from "./fit_block.js";
```

```js
	name: "PluginContainers",
	components: { CollectionBlock },
	mixins: [fitBlockMixin],
```

2. Replace the `hiddenColumns` computed written in Task 4 with the
cascade-aware one, and add the cascade the mixin reads:

```js
		// The cascade the mixin resolves: the TUI's drop order, as steps.
		// A computed so the array reaching resolveDegrade() is not a reactive
		// Proxy of component data.
		dropCascadeSteps: () => dropCascade(CONTAINERS_DROP_ORDER),
		// Both families, unioned (containers_columns.js): the data-driven set
		// plus whatever the width cascade dropped this pass.
		hiddenColumns() {
			return hiddenColumns(this.rows, this.payload?.disable_stats, this.dropFlags);
		},
```

3. Re-run the pass when the payload changes, since a new container widens
the table:

```js
	watch: {
		// A new container, a longer command or a wider port list changes the
		// natural width, so the cascade must be re-resolved -- the
		// ResizeObserver does not fire when only the CONTENT changes.
		payload() {
			this.fitBlock().catch(() => {});
		},
	},
```

- [ ] **Step 6: Add the CSS exclusion (spec D4)**

In `glances/outputs/static/css/v5.css:252`, extend the measuring rule so
`.gl-command` keeps its cap, exactly as `.gl-name` already does:

```css
.gl-measuring .gl-inline,
.gl-measuring .gl-truncate:not(.gl-name):not(.gl-command) {
  min-width: max-content;
  max-width: none;
}
```

Update that rule's comment to say why: the TUI budgets `command` at
`_MIN_COMMAND_WIDTH = 8` because the data is unbounded, so measuring it at
its natural width would drop every droppable column on a window that has
room for them.

- [ ] **Step 7: Rebuild and run the cascade tests**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run build
cd /home/nicolargo/dev/glances && python -m pytest tests/test_webui_v5_render.py -k containers -v
```

Expected: every `containers` test PASSES, the Task 4 ones included — the
cascade must not change what a block with no measurable width renders.

- [ ] **Step 8: Run every WebUI test file, then the whole suite**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_render.py tests/test_webui_v5_degrade_drift.py \
  tests/test_webui_v5_tokens.py tests/test_webui_v5_js.py \
  tests/test_webui_v5_containers_drop_order_drift.py -q
python -m pytest tests/ -x -q
```

Expected: green. Two known-flaky tests, per the project's memory: re-run
`tests/test_perf.py` and `test_restful.py::test_050/051` in isolation
before diagnosing anything, and check `ss -lptn 'sport = :61235'` for a
leaked server if every MCP test fails with a 404.

- [ ] **Step 9: Stage, do not commit**

```bash
cd /home/nicolargo/dev/glances
git add glances/outputs/static/js/v5/fit_block.js \
        glances/outputs/static/js/v5/PluginContainers.vue \
        glances/outputs/static/css/v5.css \
        glances/outputs/static/public/glances5.js \
        tests/fixtures/webui_render_probe.js tests/fixtures/webui_render_fixtures.js \
        tests/test_webui_v5_render.py
git status --short | grep -v '^[AM] ' || true
```

---

## Task 7: group verification

**Files:** none created; this task only verifies and re-stages.

- [ ] **Step 1: Confirm the registry reached 29**

```bash
cd /home/nicolargo/dev/glances
grep -c 'component: Plugin' glances/outputs/static/js/v5/plugins/index.js
```

Expected: `29`.

- [ ] **Step 2: Confirm the right group's order**

```bash
cd /home/nicolargo/dev/glances
python -m pytest tests/test_webui_v5_render.py -k "slot or registry" -v
```

Expected: PASS, with the right slot reading
`["vms", "containers", "processcount", "amps"]`.

- [ ] **Step 3: Run the JS linter**

```bash
cd /home/nicolargo/dev/glances/glances/outputs/static && npm run lint
```

Expected: no error on the new `.vue` and `.js` files. Fix with
`npm run lint-fix` if it only reports formatting.

- [ ] **Step 4: Run the pre-commit hooks**

```bash
cd /home/nicolargo/dev/glances && make pre-commit
```

This supersedes `make lint && make format` (~23 hooks). **gitleaks scans
the index**, so anything a hook rewrote must be re-staged and the command
re-run until it is clean:

```bash
cd /home/nicolargo/dev/glances
git add -u && make pre-commit
```

- [ ] **Step 5: Full suite, one last time**

```bash
cd /home/nicolargo/dev/glances && python -m pytest tests/ -q
```

- [ ] **Step 6: Report, do not commit**

Print, for the maintainer:
- `git status --short` in full;
- the suite's pass/fail counts, verbatim;
- the manual smoke still owed: `python -m glances.main_v5 -w` (the v5
  server is `glances.main_v5`, never `python -m glances`), then a browser at
  `http://localhost:61208` — check the four new blocks in the right column
  and narrow the window to watch the `containers` columns drop in
  `_DROP_ORDER`'s order and come back on widening;
- the five spec divergences (§9), for the release changelog.

---

## Self-Review

**Spec coverage:**

| Spec | Task |
|---|---|
| §1 four blocks, 29/32 | 1–4, verified in 7 |
| §4 / D1 no vertical cap, no `N/M` | 1–4 (no counter is implemented anywhere) |
| §5.1 data-driven columns | 4, unit-tested in 5 |
| §5.2 / D2, D3 width cascade in the component | 5 (pure), 6 (wiring) |
| §5.3 / D4 `.gl-command` exclusion | 6 Step 6 |
| §5.4 row shape, `-` placeholder (divergence 5) | 4 |
| §6.1 / D5 `vms`, no cascade | 3 |
| §6.2 / D6 AMP result in one cell | 2 |
| §6.3 / D7 `processcount` text line, deferrals | 1 |
| §7 registry, specs, `hidden` | 1–4 |
| §8 tests 1–4 | 5 (drift, node), 1–4 and 6 (probe) |
| §10 risks: Command measurement, observer loops, `disable_stats` | 6 (tests), 6 (`sameFlags`/`fitting` guards), 4 (`containers-disable-stats` scenario + Task 7 Step 6 live check) |

**Type consistency:** `hiddenColumns(rows, disableStats, flags)` and
`dataDrivenHidden(rows, disableStats)` are used with those exact
signatures in Tasks 5 and 6. The component's `shows(column)` reads the
`hiddenColumns` computed in both Task 4 and Task 6 — the computed's name
and meaning are unchanged, only its body. `fitBlockMixin` supplies
`dropFlags`, `fitBlock()`, `measureBlock()` and reads
`this.dropCascadeSteps`, which `PluginContainers.vue` defines in Task 6
Step 5.

**Note for the executor:** Task 4 writes a `hiddenColumns` computed that
Task 6 replaces. This is deliberate — Task 4 must be reviewable and
shippable on its own (all columns, data-driven hiding only), and splitting
it from the cascade is what lets a reviewer reject one without the other.

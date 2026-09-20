// Minimal DOM + vm harness used by test_webui_v5_render.py to prove that the
// v5 bundle actually RENDERS, rather than merely being served as bytes.
//
// It stubs only what glances5.js touches: document (element/text/comment
// node creation + a `#app` querySelector), window (existence check only)
// and fetch (resolved with empty JSON so the component's data-fetching
// paths don't throw). No jsdom, no npm dependency -- just enough of the
// DOM tree API for Vue's runtime-dom nodeOps to walk.
//
// Usage: node webui_render_probe.js <path-to-bundle.js>
// Prints one JSON line to stdout: {"childCount", "nodeType", "tagName"}
// describing what ended up inside the <div id="app"> mount target.

"use strict";

const fs = require("fs");
const vm = require("vm");

const ELEMENT_NODE = 1;
const TEXT_NODE = 3;
const COMMENT_NODE = 8;

class FakeNode {
	constructor(nodeType) {
		this.nodeType = nodeType;
		this.parentNode = null;
		this.childNodes = [];
	}

	get nextSibling() {
		if (!this.parentNode) return null;
		const idx = this.parentNode.childNodes.indexOf(this);
		return this.parentNode.childNodes[idx + 1] ?? null;
	}

	appendChild(child) {
		return this.insertBefore(child, null);
	}

	insertBefore(child, anchor) {
		if (child.parentNode) child.parentNode.removeChild(child);
		if (anchor == null) {
			this.childNodes.push(child);
		} else {
			const idx = this.childNodes.indexOf(anchor);
			this.childNodes.splice(idx === -1 ? this.childNodes.length : idx, 0, child);
		}
		child.parentNode = this;
		return child;
	}

	removeChild(child) {
		const idx = this.childNodes.indexOf(child);
		if (idx !== -1) this.childNodes.splice(idx, 1);
		child.parentNode = null;
		return child;
	}

	// The real DOM concatenates only the Text and Element descendants of an
	// element -- comment nodes are excluded (DOM standard, textContent). Vue
	// emits a comment node as the anchor of every inactive `v-if` branch and
	// keeps `<!-- -->` template comments in its render output, so aggregating
	// them here injected "v-if" and whole paragraphs of template prose into
	// every plugin's text, and therefore into the substring assertions built on
	// it (a test could pass on words that only ever appeared in a comment). A
	// comment node still reports its OWN data, like the real thing.
	get textContent() {
		if (this.nodeType === TEXT_NODE || this.nodeType === COMMENT_NODE) return this._text ?? "";
		return this.childNodes
			.filter((c) => c.nodeType !== COMMENT_NODE)
			.map((c) => c.textContent)
			.join("");
	}

	set textContent(value) {
		if (this.nodeType === TEXT_NODE || this.nodeType === COMMENT_NODE) {
			this._text = value;
			return;
		}
		for (const child of this.childNodes.splice(0)) child.parentNode = null;
		if (value) {
			const t = new FakeNode(TEXT_NODE);
			t._text = value;
			this.appendChild(t);
		}
	}

	get nodeValue() {
		return this._text ?? null;
	}

	set nodeValue(value) {
		this._text = value;
	}
}

class FakeElement extends FakeNode {
	constructor(tag) {
		super(ELEMENT_NODE);
		this.tagName = String(tag).toUpperCase();
		this._attrs = new Map();
		this._classes = new Set();
		this.classList = {
			add: (...cs) => cs.forEach((c) => this._classes.add(c)),
			remove: (...cs) => cs.forEach((c) => this._classes.delete(c)),
			toggle: (c) => (this._classes.has(c) ? this._classes.delete(c) : this._classes.add(c)),
			contains: (c) => this._classes.has(c),
		};
		this.style = { cssText: "", setProperty() {}, removeProperty() {} };
		// AppShell.mounted() sets `document.documentElement.dataset.theme` --
		// a plain object is enough to observe the assignment without
		// reflecting it into an actual `data-theme` attribute.
		this.dataset = {};
		// Layout, faked. A real DOM computes these; this harness reads them from
		// WIDTH_FIXTURES so a scenario can drive the degradation cascade
		// (js/v5/degrade.js). Unset -> 0, which degrade.js reads as "cannot
		// measure" and never degrades on.
		this._width = 0;
		this._content = 0;
		this._notches = 0;
		// Vertical layout, faked, exactly as `_width`/`_content` fake the
		// horizontal axis. Unset -> 0, which AppShell reads as "cannot
		// measure" and never budgets on (design section 4.8).
		this._top = 0;
		this._height = 0;
		// One text row, in px. A real browser resolves this from the computed
		// line-height; there is none here, so the harness supplies it.
		this._rowPx = 0;
	}

	get id() {
		return this._attrs.get("id") ?? "";
	}

	// Vue's patchClass sets `el.className = "a b c"` directly for a
	// non-SVG element (only SVG goes through setAttribute("class", ...)),
	// so classList must stay in sync with plain property assignment too.
	get className() {
		return Array.from(this._classes).join(" ");
	}

	set className(value) {
		this._classes = new Set(String(value).split(/\s+/).filter(Boolean));
	}

	get clientWidth() {
		return this._width;
	}

	// One notch removes roughly one column or one block (CONTENT_PER_NOTCH in
	// webui_render_fixtures.js): the shell's own re-measure after applying a
	// candidate flag set would see the DOM having shrunk by that much. Real
	// layout isn't available here, so AppShell.vue's measureZone() sets
	// `_notches` to the number of flags in the candidate it just applied, and
	// this getter models the resulting scrollWidth from that.
	get scrollWidth() {
		return Math.max(0, this._content - CONTENT_PER_NOTCH * this._notches);
	}

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

	setAttribute(name, value) {
		this._attrs.set(name, String(value));
		if (name === "class") this.className = value;
	}

	getAttribute(name) {
		return this._attrs.has(name) ? this._attrs.get(name) : null;
	}

	getAttributeNames() {
		return Array.from(this._attrs.keys());
	}

	removeAttribute(name) {
		this._attrs.delete(name);
	}

	addEventListener() {}
	removeEventListener() {}

	// AppShell.vue's measureZone() calls `this.$el.querySelector('[data-slot="..."]')`,
	// fit_block.js's measureBlock() calls `block.querySelector("table")`, and
	// AppShell.vue's measureBodyRows() calls `this.$el.querySelector(".gl-alerts")`
	// -- the three selector shapes this fake DOM needs to support. Searches
	// descendants only, like the real Element.querySelector (never matches the
	// element it is called on).
	querySelector(selector) {
		const tagMatch = /^[a-z][a-z0-9]*$/.exec(selector);
		if (tagMatch) {
			// Depth-first, same order as the attribute-selector branch below --
			// reuses findAllByTag() rather than a second walk implementation.
			return findAllByTag(this, selector.toUpperCase())[0] ?? null;
		}
		const classMatch = /^\.([\w-]+)$/.exec(selector);
		if (classMatch) {
			// Reuses findAllByClass() rather than a third walk implementation --
			// same depth-first order as the other two branches.
			return findAllByClass(this, classMatch[1])[0] ?? null;
		}
		const match = /^\[([\w-]+)="([^"]*)"\]$/.exec(selector);
		if (!match) return null;
		const [, attr, value] = match;
		const search = (node) => {
			for (const child of node.childNodes) {
				if (child.nodeType !== ELEMENT_NODE) continue;
				if (child.getAttribute(attr) === value) return child;
				const found = search(child);
				if (found) return found;
			}
			return null;
		};
		return search(this);
	}
}

function findById(root, id) {
	if (root.nodeType === ELEMENT_NODE && root.id === id) return root;
	for (const child of root.childNodes) {
		const found = findById(child, id);
		if (found) return found;
	}
	return null;
}

const head = new FakeElement("head");
const body = new FakeElement("body");
const documentElement = new FakeElement("html");
documentElement.appendChild(head);
documentElement.appendChild(body);
const appDiv = new FakeElement("div");
appDiv.setAttribute("id", "app");
body.appendChild(appDiv);

const document = {
	createElement: (tag) => new FakeElement(tag),
	createElementNS: (_ns, tag) => new FakeElement(tag),
	createTextNode: (text) => {
		const n = new FakeNode(TEXT_NODE);
		n._text = text;
		return n;
	},
	createComment: (text) => {
		const n = new FakeNode(COMMENT_NODE);
		n._text = text;
		return n;
	},
	// style-loader (pulled in by the CSS these components import) inserts
	// each <style> tag via `document.querySelector("head")` -- without a
	// head node it throws "Couldn't find a style target" before Vue ever
	// gets to mount.
	querySelector: (selector) => {
		if (selector === "head") return head;
		if (selector.startsWith("#")) return findById(body, selector.slice(1));
		return null;
	},
	documentElement,
	head,
	body,
};

const {
	ALERT_FIXTURES,
	ALERT_SCENARIOS,
	ALERT_INCIDENTS_FIXTURE,
	ALERT_INCIDENTS_SCENARIOS,
	ALERT_INCIDENTS_SEQUENCES,
	ALERT_INCIDENTS_UNREACHABLE_SCENARIOS,
	INFO_FIXTURES,
	SERVER_PLUGINS,
	PLUGINSLIST_FIXTURES,
	ALL_UNREACHABLE_SCENARIOS,
	ARGS_FIXTURES,
	CONFIG_FIXTURES,
	ALL_FIXTURES,
	WIDTH_FIXTURES,
	CONTENT_PER_NOTCH,
	BLOCK_WIDTH_FIXTURES,
	HEIGHT_FIXTURES,
} = require("./webui_render_fixtures.js");

const scenario = process.argv[3] || "default";

// Fix round 3: opt-in, per-call sequence for the tick-ordering test --
// consumed one envelope per `api/5/alert/incidents` call, holding on the
// last entry once exhausted. A scenario absent from ALERT_INCIDENTS_SEQUENCES
// (every scenario but one, today) is completely unaffected: fakeFetch falls
// through to the existing single-static-envelope lookup below, unchanged.
let alertIncidentsSequenceIndex = 0;

async function fakeFetch(url) {
	const path = String(url);
	// BEFORE the `api/5/alert` check below: "api/5/alert/incidents" contains
	// "api/5/alert", and would otherwise be answered with the raw history
	// fixture -- the same trap "api/5/all/info" documents against "api/5/all".
	if (path.includes("api/5/alert/incidents")) {
		if (ALERT_INCIDENTS_UNREACHABLE_SCENARIOS.has(scenario)) {
			return { ok: false, status: 500, json: async () => ({ detail: "boom" }) };
		}
		const sequence = ALERT_INCIDENTS_SEQUENCES[scenario];
		if (sequence) {
			const envelope = sequence[Math.min(alertIncidentsSequenceIndex, sequence.length - 1)];
			alertIncidentsSequenceIndex += 1;
			return { ok: true, status: 200, json: async () => envelope };
		}
		// Envelope, not a bare array (fix round 2, IMPORTANT 2) -- default is
		// the populated, warmed-up fixture; a handful of scenarios override it
		// to exercise the initializing/empty states.
		const envelope = ALERT_INCIDENTS_SCENARIOS[scenario] || {
			is_initializing: false,
			incidents: ALERT_INCIDENTS_FIXTURE,
		};
		return { ok: true, status: 200, json: async () => envelope };
	}
	if (path.includes("api/5/alert")) {
		return { ok: true, status: 200, json: async () => ALERT_SCENARIOS[scenario] || ALERT_FIXTURES };
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
		if (ALL_UNREACHABLE_SCENARIOS.has(scenario)) {
			return { ok: false, status: 500, json: async () => ({ detail: "boom" }) };
		}
		return { ok: true, status: 200, json: async () => ALL_FIXTURES[scenario] || {} };
	}
	if (path.includes("api/5/args")) {
		return { ok: true, status: 200, json: async () => ARGS_FIXTURES[scenario] || {} };
	}
	// PluginProcesslist.vue (task 7) reads `[outputs] max_processes_display`
	// straight from this endpoint, same as AppShell's resolveConfig() does for
	// `[global] refresh` / `[outputs] theme` -- a scenario absent from
	// CONFIG_FIXTURES gets `{}`, i.e. no cap.
	if (path.includes("api/5/config")) {
		return { ok: true, status: 200, json: async () => CONFIG_FIXTURES[scenario] || {} };
	}
	return { ok: true, status: 200, json: async () => ({}) };
}

// Vue's mount() does `instanceof Element` / `instanceof SVGElement` checks
// on the container node. Map the globals to our fake classes so those
// checks resolve instead of throwing ReferenceError, and so our appDiv
// (a FakeElement) is correctly recognised as an Element.
class FakeSVGElement extends FakeElement {}

// AppShell.mounted() calls setInterval() as its last statement to schedule
// the poll; without it in the sandbox the hook throws ReferenceError at that
// line, which vm swallows as an unhandled rejection instead of surfacing --
// see Finding 3. No-ops are fine: the probe observes the first paint, it
// does not drive time.
const sandbox = {
	document,
	fetch: fakeFetch,
	console,
	Node: FakeNode,
	Element: FakeElement,
	SVGElement: FakeSVGElement,
	setInterval: () => 0,
	clearInterval: () => {},
	// AppShell observes zone widths with this; the harness never fires it, so
	// the cascade runs exactly once, on the shell's own post-payload pass.
	ResizeObserver: class {
		observe() {}
		disconnect() {}
	},
	// The blocks (js/v5/fit_block.js) register each instance's own refit here,
	// as the harness never fires their ResizeObserver -- see applyBlockWidths.
	__glancesBlockRefits: [],
	// AppShell.measureBodyRows() reads window.innerHeight. 0 means "cannot
	// measure", which is the safe answer (design section 4.8).
	innerHeight: 0,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

function findDescendantTag(root, tagName) {
	for (const child of root.childNodes) {
		if (child.nodeType === ELEMENT_NODE) {
			if (child.tagName === tagName) return child;
			const found = findDescendantTag(child, tagName);
			if (found) return found;
		}
	}
	return null;
}

const bundlePath = process.argv[2];
const code = fs.readFileSync(bundlePath, "utf8");
vm.runInContext(code, sandbox, { filename: bundlePath });

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

function findAllByTag(root, tagName, acc = []) {
	for (const child of root.childNodes) {
		if (child.nodeType === ELEMENT_NODE) {
			if (child.tagName === tagName) acc.push(child);
			findAllByTag(child, tagName, acc);
		}
	}
	return acc;
}

// Every element whose class list contains `cls` -- used for `.gl-bar` and its
// sub-parts, which are <div>/<span> elements with no other distinguishing tag.
function findAllByClass(root, cls, acc = []) {
	for (const child of root.childNodes) {
		if (child.nodeType === ELEMENT_NODE) {
			if (child.classList.contains(cls)) acc.push(child);
			findAllByClass(child, cls, acc);
		}
	}
	return acc;
}

function findDescendantByClass(root, cls) {
	for (const child of root.childNodes) {
		if (child.nodeType === ELEMENT_NODE) {
			if (child.classList.contains(cls)) return child;
			const found = findDescendantByClass(child, cls);
			if (found) return found;
		}
	}
	return null;
}

function collect() {
	const result = {
		childCount: appDiv.childNodes.length,
		nodeType: null,
		tagName: null,
		hasClass: false,
		hasHeader: false,
		hasFooter: false,
		footerText: null,
		pluginHeaders: [],
		// The ordered `data-plugin` values -- stable identity, unlike
		// pluginHeaders below, which is the ordered <h2> TEXT and is only
		// meaningful for components whose title is a constant.
		pluginNames: [],
		// Full textContent of each rendered <article class="gl-plugin">, keyed
		// by its data-plugin (registry name) -- lets a test assert on the
		// formatted values a plugin actually rendered (e.g. the eight mem
		// statistics) without a second, per-plugin harness.
		pluginText: {},
		// The <th> texts of each rendered collection plugin, keyed by its
		// data-plugin (registry name) -- lets a test observe the resolved
		// column HEADERS specifically, rather than searching the whole
		// article's text.
		pluginColumnHeaders: {},
		// The <th> class lists, same keying -- lets a test observe which
		// columns a component marked numeric (.gl-num) through the real
		// render, rather than asserting on the descriptor's source.
		pluginColumnClasses: {},
		// The class lists of each plugin's VALUE cells -- every <dd> then
		// every <td>, in document order, keyed by data-plugin. A component
		// uses one or the other, never both. This is the only way a test can
		// observe which `_levels` entry a value was coloured from: the tier
		// reaches the DOM as a `gl-level-*` class and nowhere else, so an
		// assertion on textContent cannot see it.
		pluginValueClasses: {},
		// Elements with a `title` attribute, keyed by data-plugin.
		pluginTitles: {},
		// Each plugin's own title LINE -- the trimmed text of its <h2> -- keyed
		// by data-plugin, `null` for a block that renders none. `pluginHeaders`
		// above carries the same text but positionally, which makes an
		// assertion depend on the plugin ORDER; this one is addressable, and is
		// how a test can tell a title that lives on its own line from one that
		// was folded into the grid's first <th> (PluginAlert's used to be).
		pluginTitleLine: {},
		// The trimmed <th> texts of each plugin's <thead>, keyed by
		// data-plugin -- [] when the plugin renders no <thead> at all (e.g.
		// `amps`, `ports`: no title row and no column header, v4 parity).
		// Lets a test assert the ABSENCE of a header row, which
		// pluginColumnHeaders (only set when `ths.length` is truthy) cannot:
		// it has no entry at all for a header-less plugin, indistinguishable
		// from "not rendered yet".
		pluginHeaderCells: {},
		// Each rendered <col>'s inline width, in document order, keyed by
		// data-plugin -- [] when the table renders no <colgroup> at all (most
		// of them: Task 7 makes the slot optional). Same "absence is
		// observable" distinction as pluginHeaderCells above: an entry missing
		// entirely would be indistinguishable from "not rendered yet", so
		// every table gets a key, empty or not.
		pluginColWidths: {},
		// The <table>'s own class list, keyed by data-plugin -- lets a test
		// observe the optional `table-class` prop (e.g. `gl-process-table`,
		// carrying `table-layout: fixed`) alongside the base `.gl-table`
		// every block renders.
		pluginTableClasses: {},
		// The rendered attribute names of each plugin's root <article>, keyed
		// by data-plugin -- lets a test assert that a prop like `serverArgs`
		// never leaked through as a fallthrough attribute (Vue stringifies an
		// undeclared object prop onto the DOM), observing the render rather
		// than the component source.
		pluginAttrs: {},
		// Ordered `data-plugin` values inside each `[data-slot]` container,
		// keyed by the slot name -- what the drift guard compares against the
		// TUI's slot tuples (curses_renderer_v5.py:58-80).
		slots: {},
		// Whether each plugin root is hidden by `v-show` (Vue writes
		// `style.display = "none"`, runtime-dom's setDisplay()). The header
		// components stay in the DOM while hidden, so presence in pluginNames
		// says nothing about visibility -- this does.
		pluginHidden: {},
		// Every <dl> of a scalar plugin as its (dt, dd) text pairs, keyed by
		// data-plugin: [[[label, value], ...], ...], one inner list per column.
		// Lets a test observe which pair opens a column and how many lines each
		// column has -- the TUI grid shape -- rather than a flat text blob.
		pluginGrid: {},
		// The class of each <dl> column of a scalar plugin, same keying and
		// order as pluginGrid -- lets a test observe which column takes the
		// wider formatRate() width floor (`gl-col-rate`).
		pluginGridClasses: {},
		// Every <td> of a collection plugin, keyed by data-plugin: the cell's
		// own classes and those of the <span> around its value. Lets a test
		// observe that the tier (and the prominent badge) sits on the value
		// text, not on the whole cell.
		pluginTableCells: {},
		// Each `.gl-bar` row of a plugin: the label, the fill's inline width and
		// class list, the value's class list, and the ARIA attributes. The fill's
		// WIDTH is the only place a bar's value reaches the DOM, so a test cannot
		// see a wrong bar any other way.
		bars: {},
		// The ordered bar labels, keyed by data-plugin -- `[quicklook] list`
		// drives both the selection and the order, and this is what pins it.
		barLabels: {},
		// Each <tbody> of a plugin as its rows' raw cell texts:
		// [[[cell, cell], ...], ...], one inner list per row group. `raid` and
		// `smart` emit one group per array/device (G9-7 D3), and this is the
		// only way a test can see that grouping rather than a flat table. NOT
		// trimmed, unlike pluginTableCells: `smart`'s attribute names carry the
		// TUI's leading-space indent, and trimming would hide it.
		pluginRowGroups: {},
		// The name <span class~="gl-name"> of each row of a collection plugin,
		// keyed by data-plugin: its text, classes, `title` and whether the text
		// sits in a <bdi>. Lets a test observe the displayed name (alias or raw
		// key), which truncation side it uses, and that the full name is on
		// hover -- none of which textContent or the <td> classes show.
		pluginNameCells: {},
		// One entry per footer alert <li>: its classes, and the text and
		// classes of the <span> holding the level word. Lets a test observe
		// WHERE the prominent badge lands (the level word, not the whole line).
		footerAlerts: [],
		// The tagName of each `.gl-inline` element in a plugin, keyed by
		// data-plugin -- `.gl-inline` zeroes no margin of its own (css/v5.css),
		// it only supplies the baseline/gap layout, so a `<p>` picking that
		// class up still keeps the browser's default `margin: 1em 0` and
		// drifts the block down (quicklook's CPU name/frequency header, G9-8
		// smoke fix 1). Lets a test pin the tag directly instead of inferring
		// it from a layout side effect the probe's fake DOM cannot measure.
		pluginInlineTags: {},
		// The flags AppShell resolved for each zone -- the cascade's decision,
		// which the DOM alone cannot show (a hidden block looks like a disabled
		// one).
		degrade: sandbox.__glancesDegrade ? { ...sandbox.__glancesDegrade } : {},
		// The row quota AppShell.refitVertical() settled on -- the vertical
		// twin of `degrade` above, same "absent/unmeasurable -> {}" default.
		rowBudget: sandbox.__glancesRowBudget ? { ...sandbox.__glancesRowBudget } : {},
		// The vertical budget inputs AppShell.measureBodyRows() reads: the
		// viewport height, the right slot's own row height, and its distance
		// from the viewport's top edge. Defaults to "unmeasurable" (0/0/0),
		// same convention as `degrade`, until the right slot is found below.
		geometry: { viewport: sandbox.window.innerHeight, rowPx: 0, slotTop: 0 },
	};
	const first = appDiv.childNodes[0];
	if (first) {
		result.nodeType = first.nodeType;
		result.tagName = first.tagName ?? null;
		if (first.nodeType === ELEMENT_NODE) {
			result.hasClass = first.classList.contains("gl-app");
			const header = findDescendantTag(first, "HEADER");
			const footer = findDescendantTag(first, "FOOTER");
			result.hasHeader = !!header;
			result.hasFooter = !!footer;
			result.footerText = footer ? footer.textContent : null;
			if (footer) {
				result.footerAlerts = findAllByTag(footer, "LI").map((li) => {
					const level = findDescendantTag(li, "SPAN");
					return {
						className: li.className,
						level: level ? level.textContent : null,
						levelClass: level ? level.className : null,
					};
				});
			}
			const articles = findAllByAttr(first, "data-plugin");
			result.pluginHeaders = articles.map((article) => {
				const h2 = findDescendantTag(article, "H2");
				return h2 ? h2.textContent : null;
			});
			articles.forEach((article, i) => {
				// Keyed by data-plugin (the registry name), NOT by the <h2>
				// text: gpu's title is built from the hardware it finds
				// ("GeForce RTX 3080" / "3 GPUs"), so a title key would make
				// these assertions depend on the machine running the test.
				const name = article.getAttribute("data-plugin");
				if (!name) return;
				result.pluginNames.push(name);
				const title = findDescendantTag(article, "H2");
				result.pluginTitleLine[name] = title ? title.textContent.trim() : null;
				result.pluginText[name] = article.textContent;
				result.pluginAttrs[name] = article.getAttributeNames();
				result.pluginHidden[name] = article.style.display === "none";
				const ths = findAllByTag(article, "TH");
				if (ths.length) {
					result.pluginColumnHeaders[name] = ths.map((th) => th.textContent);
					result.pluginColumnClasses[name] = ths.map((th) => th.className);
				}
				const values = [...findAllByTag(article, "DD"), ...findAllByTag(article, "TD")];
				if (values.length) {
					result.pluginValueClasses[name] = values.map((cell) => cell.className);
					// Every element carrying a `title`, so a test can check that a
					// capped cell still offers its full value on hover. `.gl-name`
					// spans have their own richer field; this one is for the rest.
					result.pluginTitles[name] = findAllByAttr(article, "title").map((el) => ({
						text: el.textContent.trim(),
						title: el.getAttribute("title"),
					}));
				}
				const thead = findAllByTag(article, "THEAD");
				result.pluginHeaderCells[name] = thead.length
					? findAllByTag(thead[0], "TH").map((th) => th.textContent.trim())
					: [];
				// Only the <table> CollectionBlock itself renders can carry a
				// <colgroup> or the tableClass prop -- reads the first (no plugin
				// renders more than one today).
				const tables = findAllByTag(article, "TABLE");
				const cols = tables.length ? findAllByTag(tables[0], "COL") : [];
				result.pluginColWidths[name] = cols.map((col) => col.style.width);
				result.pluginTableClasses[name] = tables.length
					? tables[0].className.split(" ").filter(Boolean)
					: [];
				const tds = findAllByTag(article, "TD");
				if (tds.length) {
					result.pluginTableCells[name] = tds.map((td) => {
						const span = findDescendantTag(td, "SPAN");
						return { cell: td.className, value: span ? span.className : null, text: td.textContent.trim() };
					});
				}
				const groups = findAllByTag(article, "TBODY");
				if (groups.length) {
					result.pluginRowGroups[name] = groups.map((tbody) =>
						findAllByTag(tbody, "TR").map((tr) => findAllByTag(tr, "TD").map((td) => td.textContent)),
					);
				}
				const bars = findAllByClass(article, "gl-bar");
				if (bars.length) {
					result.bars[name] = bars.map((bar) => {
						const label = findDescendantByClass(bar, "gl-bar-label");
						const fill = findDescendantByClass(bar, "gl-bar-fill");
						const value = findDescendantByClass(bar, "gl-bar-value");
						const track = findDescendantByClass(bar, "gl-bar-track");
						return {
							label: label ? label.textContent.trim() : null,
							width: fill ? fill.style.width : null,
							fillClass: fill ? fill.className : null,
							valueClass: value ? value.className : null,
							role: track ? track.getAttribute("role") : null,
							valuenow: track ? track.getAttribute("aria-valuenow") : null,
						};
					});
					result.barLabels[name] = result.bars[name].map((bar) => bar.label);
				}
				const inlines = findAllByClass(article, "gl-inline");
				if (inlines.length) {
					result.pluginInlineTags[name] = inlines.map((el) => el.tagName);
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
				const dls = findAllByTag(article, "DL");
				if (dls.length) {
					// dt and dd alternate inside a scalar <dl>, so zipping the two
					// ordered lists yields the rendered (label, value) lines.
					result.pluginGrid[name] = dls.map((dl) => {
						const dds = findAllByTag(dl, "DD");
						return findAllByTag(dl, "DT").map((dt, i) => [
							dt.textContent.trim(),
							dds[i] ? dds[i].textContent.trim() : null,
						]);
					});
					result.pluginGridClasses[name] = dls.map((dl) => dl.className);
				}
			});
			const slotSections = findAllByAttr(first, "data-slot");
			for (const section of slotSections) {
				result.slots[section.getAttribute("data-slot")] = findAllByAttr(section, "data-plugin").map((el) =>
					el.getAttribute("data-plugin"),
				);
			}
			// AppShell.measureBodyRows() reads the right slot's top edge to work
			// out how much of the viewport is left below it -- the reading a real
			// browser would produce, here taken straight off the fake element the
			// scenario's HEIGHT_FIXTURES drove (applyHeights() below).
			const rightSlot = slotSections.find((zone) => zone.getAttribute("data-slot") === "right") || null;
			result.geometry = {
				viewport: sandbox.window.innerHeight,
				rowPx: rightSlot ? rightSlot._rowPx : 0,
				slotTop: rightSlot ? rightSlot.getBoundingClientRect().top : 0,
			};
		}
	}
	return result;
}

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

// Same as applyWidths(), one level down: blocks are addressed by their
// `data-plugin` attribute rather than by `data-slot`, because a per-block
// cascade (js/v5/fit_block.js) measures the component's own root.
function applyBlockWidths() {
	const widths = BLOCK_WIDTH_FIXTURES[scenario];
	if (!widths) return false;
	for (const [plugin, { available, content }] of Object.entries(widths)) {
		for (const block of findAllByAttr(appDiv, "data-plugin")) {
			if (block.getAttribute("data-plugin") !== plugin) continue;
			// `available` (clientWidth) belongs to the block itself -- the
			// shell's grid constrains ITS box. `content` (scrollWidth) belongs
			// to whichever element fit_block.js's measureBlock() actually
			// reads: the inner <table> when there is one (the real production
			// target -- a table can overflow its container), falling back to
			// the block's own scrollWidth otherwise, exactly mirroring
			// measureBlock()'s own `table ? table.scrollWidth : block.scrollWidth`.
			block._width = available;
			const table = findAllByTag(block, "TABLE")[0];
			(table || block)._content = content;
		}
	}
	return true;
}

// Same contract as applyWidths(), for the vertical axis: window.innerHeight
// plus each slot's top/height. The "footer" key is not a `data-slot` --
// AppShell renders the alert block as `<footer class="gl-alerts">` -- so it
// is matched by class instead, same as `collect()` does for the footer.
function applyHeights() {
	const heights = HEIGHT_FIXTURES[scenario];
	if (!heights) return false;
	sandbox.window.innerHeight = heights.viewport;
	for (const [slot, { top, height }] of Object.entries(heights.slots)) {
		const el =
			slot === "footer"
				? findDescendantByClass(appDiv, "gl-alerts")
				: findAllByAttr(appDiv, "data-slot").find((zone) => zone.getAttribute("data-slot") === slot);
		if (!el) continue;
		el._top = top;
		el._height = height;
		if (slot === "right") el._rowPx = heights.rowPx;
	}
	return true;
}

// AppShell's `mounted()` hook is async (resolveConfig, then tick(),
// which itself awaits fetchAll() and the /api/5/alert call) -- none of
// that has run yet the instant vm.runInContext() returns; only the initial,
// pre-fetch render exists at that point. All our fakes resolve promises
// immediately (no real timers), so Node's microtask queue fully drains
// before any macrotask runs -- one `setImmediate` is enough to observe the
// footer AFTER the fetched alert has been rendered, not just the "No
// alert" placeholder from the first paint.
setImmediate(async () => {
	if (applyWidths() && sandbox.__glancesRefit) await sandbox.__glancesRefit();
	// The blocks measure themselves (fit_block.js registers each instance's
	// refit here); the harness never fires their ResizeObserver, so it calls
	// them once, after the widths are in place.
	if (applyBlockWidths() && Array.isArray(sandbox.__glancesBlockRefits)) {
		for (const refit of sandbox.__glancesBlockRefits) await refit();
	}
	// Drives the raw geometry inputs collect() reads back under `geometry`,
	// AND -- like the applyWidths() branch above -- re-runs the shell's own
	// hook so AppShell.refitVertical() sees the scenario's real numbers
	// rather than the all-zero ("cannot measure") state it read at mount
	// time, before this scenario's heights existed.
	if (applyHeights() && sandbox.__glancesRefit) await sandbox.__glancesRefit();
	// Fix round 3: a scenario opted into ALERT_INCIDENTS_SEQUENCES needs a
	// SECOND poll cycle to consume its second envelope -- mounted()'s own
	// tick() (before this setImmediate ever runs) already consumed the
	// first. `tick()` itself calls fetchAll(), the alert endpoint, and
	// refit()/refitVertical() in AppShell's real order, so this is what
	// exercises the tick-ordering fix rather than the `__glancesRefit`
	// shortcut every other test above uses.
	if (ALERT_INCIDENTS_SEQUENCES[scenario] && sandbox.__glancesTick) await sandbox.__glancesTick();
	process.stdout.write(JSON.stringify(collect()));
});

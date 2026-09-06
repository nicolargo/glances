// Minimal DOM + vm harness used by test_webserver_v5.py to prove that the
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

	get textContent() {
		if (this.nodeType === TEXT_NODE || this.nodeType === COMMENT_NODE) return this._text ?? "";
		return this.childNodes.map((c) => c.textContent).join("");
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

	setAttribute(name, value) {
		this._attrs.set(name, String(value));
		if (name === "class") this.className = value;
	}

	getAttribute(name) {
		return this._attrs.has(name) ? this._attrs.get(name) : null;
	}

	removeAttribute(name) {
		this._attrs.delete(name);
	}

	addEventListener() {}
	removeEventListener() {}
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

// Real event shape from `_build_event()` (glances/alerts_v5.py:706-716) --
// the ONLY fields `/api/5/alert` ever sends. There is no `description`
// field; AppShell.vue must compose the footer line from these.
//
// Twelve entries, oldest first -- matching get_history()'s documented
// most-recent-LAST contract (glances/alerts_v5.py:181) -- with a
// distinguishable `plugin` per entry ("plugin0".."plugin11"). A single-alert
// fixture cannot tell a correct `slice(-10).reverse()` apart from the buggy
// `slice(0, 10)` that shipped in fix round 1: both show one alert. Twelve
// distinguishable entries let the assertion check that the footer holds the
// ten MOST RECENT ("plugin2".."plugin11"), newest first, and has dropped the
// two oldest ("plugin0", "plugin1").
const ALERT_FIXTURES = Array.from({ length: 12 }, (_, i) => ({
	ts: `2026-01-01T00:00:0${i}Z`,
	plugin: `plugin${i}`,
	key: null,
	field: "total",
	level: "critical",
	previous_level: "ok",
	value: 97.2,
	prominent: true,
	is_initial: false,
	hostname: "test-host",
}));

// `fields_description` shape for `/api/5/<plugin>/info`, as labels.js
// expects it: field -> {short_name, label}. Real enough that resolveLabels'
// short_name -> label -> field name precedence has something to resolve,
// rather than degrading to field names by accident. short_names for the mem
// fields are copied from glances/plugins/mem/model_v5.py so the rendered
// labels match the TUI ("avail", "inacti", "buffer").
// The stub is keyed BY PLUGIN NAME: answering every `/info` with the mem
// schema made a network header assertion meaningless (network's fields are
// absent from it, so labelFor silently degraded to field names and any
// expected string would have had to be the field name itself).
const INFO_FIXTURES = {
	mem: {
		total: { short_name: "total", label: "Total" },
		available: { short_name: "avail" },
		used: { short_name: "used" },
		free: { short_name: "free" },
		active: { short_name: "active" },
		inactive: { short_name: "inacti" },
		buffers: { short_name: "buffer" },
		cached: { short_name: "cached" },
	},
	// short_names copied from glances/plugins/network/model_v5.py, which
	// carries the TUI's own header strings (render_curses_v5.render()).
	network: {
		interface_name: { short_name: "interface" },
		bytes_recv: { short_name: "Rx/s" },
		bytes_sent: { short_name: "Tx/s" },
		errors_in: {},
		errors_out: {},
	},
};

// `/api/5/all` fixtures for the `mem` render-parity tests
// (test_mem_renders_all_eight_statistics_with_avail /
// test_mem_shows_used_when_available_is_absent in test_webserver_v5.py).
// Values are exact powers of 1024 so formatBytes() rounds to one predictable
// decimal (e.g. 16*1024**3 -> "16.0G"), and `used` carries a value distinct
// from `available` so a switch that rendered the wrong one, or both, cannot
// pass unnoticed.
const MEM_FIXTURE_WITH_AVAILABLE = {
	percent: 53.2,
	total: 17179869184, // 16.0G
	available: 8589934592, // 8.0G
	used: 9663676416, // 9.0G -- must NOT render: `available` wins
	free: 2147483648, // 2.0G
	active: 5368709120, // 5.0G
	inactive: 4294967296, // 4.0G
	buffers: 104857600, // 100.0M
	cached: 3221225472, // 3.0G
};
const MEM_FIXTURE_NO_AVAILABLE = {
	percent: 53.2,
	total: 17179869184, // 16.0G
	used: 9663676416, // 9.0G -- must render: no `available` field at all
	free: 2147483648, // 2.0G
	active: 5368709120, // 5.0G
	inactive: 4294967296, // 4.0G
	buffers: 104857600, // 100.0M
	cached: 3221225472, // 3.0G
};

// argv[3] selects which `/api/5/all` fixture this run answers with; the
// mem render-parity tests invoke the probe twice, once per scenario.
// A network collection payload, in the envelope shape `/api/5/all` publishes
// (`data` + `_key` + `_levels`) -- PluginNetwork only renders its <table>,
// and therefore its <th> headers, when `data` is non-empty.
const NETWORK_FIXTURE = {
	_key: "interface_name",
	data: [{ interface_name: "eth0", bytes_recv: 1048576, bytes_sent: 524288 }],
	_levels: { eth0: { bytes_recv: { level: "ok", prominent: false } } },
};

const ALL_FIXTURES = {
	default: {},
	"mem-with-available": { mem: MEM_FIXTURE_WITH_AVAILABLE },
	"mem-no-available": { mem: MEM_FIXTURE_NO_AVAILABLE },
	network: { network: NETWORK_FIXTURE },
};
const scenario = process.argv[3] || "default";

async function fakeFetch(url) {
	if (String(url).includes("api/5/alert")) {
		return { ok: true, status: 200, json: async () => ALERT_FIXTURES };
	}
	const info = String(url).match(/api\/5\/([^/]+)\/info/);
	if (info) {
		return { ok: true, status: 200, json: async () => INFO_FIXTURES[info[1]] || {} };
	}
	if (String(url).includes("api/5/all")) {
		return { ok: true, status: 200, json: async () => ALL_FIXTURES[scenario] || {} };
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

// Every registered plugin renders as an <article class="gl-plugin"> with an
// <h2 class="gl-header"> naming it (PluginMem.vue, PluginNetwork.vue). This
// walks the whole tree (not just one level, like findDescendantTag) so the
// registry test can assert on the SET of plugins that actually rendered,
// not just the first one found.
function findAllByClass(root, className, acc = []) {
	for (const child of root.childNodes) {
		if (child.nodeType === ELEMENT_NODE) {
			if (child.classList.contains(className)) acc.push(child);
			findAllByClass(child, className, acc);
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
		// Full textContent of each rendered <article class="gl-plugin">, keyed
		// by its <h2> title -- lets a test assert on the formatted values a
		// plugin actually rendered (e.g. the eight mem statistics) without a
		// second, per-plugin harness.
		pluginText: {},
		// The <th> texts of each rendered collection plugin, keyed by its
		// <h2> title -- lets a test observe the resolved column HEADERS
		// specifically, rather than searching the whole article's text.
		pluginColumnHeaders: {},
		// The <th> class lists, same keying -- lets a test observe which
		// columns a component marked numeric (.gl-num) through the real
		// render, rather than asserting on the descriptor's source.
		pluginColumnClasses: {},
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
			const articles = findAllByClass(first, "gl-plugin");
			result.pluginHeaders = articles.map((article) => {
				const h2 = findDescendantTag(article, "H2");
				return h2 ? h2.textContent : null;
			});
			articles.forEach((article, i) => {
				const name = result.pluginHeaders[i];
				if (!name) return;
				result.pluginText[name] = article.textContent;
				const ths = findAllByTag(article, "TH");
				if (ths.length) {
					result.pluginColumnHeaders[name] = ths.map((th) => th.textContent);
					result.pluginColumnClasses[name] = ths.map((th) => th.className);
				}
			});
		}
	}
	return result;
}

// AppShell's `mounted()` hook is async (resolveConfig, then tick(),
// which itself awaits fetchAll() and the /api/5/alert call) -- none of
// that has run yet the instant vm.runInContext() returns; only the initial,
// pre-fetch render exists at that point. All our fakes resolve promises
// immediately (no real timers), so Node's microtask queue fully drains
// before any macrotask runs -- one `setImmediate` is enough to observe the
// footer AFTER the fetched alert has been rendered, not just the "No
// alert" placeholder from the first paint.
setImmediate(() => {
	process.stdout.write(JSON.stringify(collect()));
});

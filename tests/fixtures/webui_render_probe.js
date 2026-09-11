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

	getAttributeNames() {
		return Array.from(this._attrs.keys());
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

// `/api/5/all/info` answer: plugin -> fields_description, as labels.js'
// resolveAllLabels() expects it. Real enough that the short_name -> label ->
// field name precedence has something to resolve, rather than degrading to
// field names by accident. short_names for the mem fields are copied from
// glances/plugins/mem/model_v5.py so the rendered labels match the TUI
// ("avail", "inacti", "buffer"). Keyed by plugin: a single schema shared by
// every plugin would make a network header assertion meaningless.
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
	load: {
		min1: { short_name: "1 min" },
		min5: { short_name: "5 min" },
		min15: { short_name: "15 min" },
		cpucore: {},
	},
	// Empty objects: the schema declares no labels for memswap, and
	// `labelFor` falls back to the field name -- which is the point (the
	// field names already ARE the TUI's labels).
	memswap: { total: {}, used: {}, free: {}, percent: {}, sin: {}, sout: {} },
	// glances/plugins/cpu/model_v5.py declares exactly three short_names --
	// the rest of the fields carry none, so their labels ARE the field names.
	cpu: {
		total: {}, user: {}, system: {}, iowait: {}, idle: {}, irq: {}, nice: {}, steal: {},
		guest: {}, dpc: {}, cpucore: {}, syscalls: {},
		ctx_switches: { short_name: "ctx_sw" },
		interrupts: { short_name: "inter" },
		soft_interrupts: { short_name: "sw_int" },
	},
	// short_names copied from glances/plugins/gpu/model_v5.py -- the bare word
	// only; both the TUI and the component compose the ":" and the " mean:"
	// suffix themselves. `gpu_id`, `name` and `fan_speed` declare none.
	gpu: {
		gpu_id: {},
		name: {},
		fan_speed: {},
		proc: { short_name: "proc" },
		mem: { short_name: "mem" },
		temperature: { short_name: "temperature" },
	},
	system: { os_name: {}, hostname: {}, platform: {}, linux_distro: {}, os_version: {}, hr_name: {} },
	uptime: { seconds: {} },
	now: { custom: {}, iso: {} },
	ip: { address: {}, mask: {}, mask_cidr: {}, gateway: {}, public_address: {}, public_info_human: {} },
	cloud: { id: {}, platform: {}, name: {}, type: {}, region: {} },
};

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
	// The shipped default: `[cloud] disable` is true (cloud/model_v5.py:100).
	"cloud-disabled": SERVER_PLUGINS.filter((name) => name !== "cloud"),
};

// Scenarios whose `/api/5/all` answers with an HTTP 500, same shape as the
// `pluginslist-unreachable` handling above -- spec §9: "`/api/5/all` fails ->
// every visible block shows its error, header included."
const ALL_UNREACHABLE_SCENARIOS = new Set(["all-unreachable"]);

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

// gpu card sets, in the `/api/5/all` collection envelope. One card and three
// identically-named cards are the two branches of the layout switch; the
// three cards' proc values (30/45/12) average to exactly 29, so the mean
// assertion cannot pass on a rounding accident.
const GPU_ONE_CARD = {
	_key: "gpu_id",
	data: [{ gpu_id: 0, name: "GeForce RTX 3080", proc: 30, mem: 40, temperature: 55 }],
	_levels: {},
};
const GPU_THREE_CARDS = {
	_key: "gpu_id",
	data: [
		{ gpu_id: 0, name: "GeForce RTX 3080", proc: 30, mem: 40, temperature: 55 },
		{ gpu_id: 1, name: "GeForce RTX 3080", proc: 45, mem: 38, temperature: 61 },
		{ gpu_id: 2, name: "GeForce RTX 3080", proc: 12, mem: 20, temperature: 49 },
	],
	_levels: {},
};
// Two cards where NO card reports memory: the only case that drops the mem
// column (#3631 -- one card missing it still shows N/A).
const GPU_NO_MEMORY = {
	_key: "gpu_id",
	data: [
		{ gpu_id: 0, name: "Radeon RX 7900", proc: 30, mem: null, temperature: 55 },
		{ gpu_id: 1, name: "Radeon RX 7900", proc: 45, mem: null, temperature: 61 },
	],
	_levels: {},
};

// Two cards where exactly ONE reports memory -- the half of #3631 that
// GPU_NO_MEMORY cannot observe. A component hiding the cell per card (rather
// than dropping the whole column only when no card reports it) renders no
// "N/A" here and passes every other gpu fixture, so this is the only fixture
// that tells the two behaviours apart.
const GPU_MIXED_MEMORY = {
	_key: "gpu_id",
	data: [
		{ gpu_id: 0, name: "Radeon RX 7900", proc: 30, mem: 40, temperature: 55 },
		{ gpu_id: 1, name: "Radeon RX 7900", proc: 45, mem: null, temperature: 61 },
	],
	_levels: {},
};

// A gpu payload with no card at all -- the machine has no GPU, or every
// backend failed. Design spec section 11: the plugin renders nothing beyond
// its title.
const GPU_ZERO_CARDS = { _key: "gpu_id", data: [], _levels: {} };

// The SAME card objects as GPU_THREE_CARDS, with a populated `_levels`: card
// 0 is critical on `proc`, cards 1 and 2 are ok. Summary mode averages
// 30/45/12 -- two thirds of which are ok -- so a colour derived from the mean,
// or from any card but the first, cannot come out critical. That is what
// makes this fixture able to tell the v4 quirk (colour from the FIRST card)
// apart from the "fix" a later reader might apply.
const GPU_FIRST_CARD_LEVELS = {
	_key: "gpu_id",
	data: GPU_THREE_CARDS.data,
	_levels: {
		0: { proc: { level: "critical" } },
		1: { proc: { level: "ok" } },
		2: { proc: { level: "ok" } },
	},
};

// Per-scenario `/api/5/args` answers. `--meangpu` and `--fahrenheit` are
// server-side CLI flags, so the ONLY way they reach the WebUI is this
// endpoint; a scenario absent from here gets `{}`, i.e. no flag set.
const ARGS_FIXTURES = {
	"gpu-three-cards-mean": { meangpu: true },
	"gpu-one-card-fahrenheit": { fahrenheit: true },
	"gpu-first-card-colour": { meangpu: true },
	"header-hide-public": { hide_public_info: true },
};

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

const ALL_FIXTURES = {
	default: {},
	"gpu-disabled": {},
	"pluginslist-unreachable": {},
	"mem-with-available": { mem: MEM_FIXTURE_WITH_AVAILABLE },
	"mem-no-available": { mem: MEM_FIXTURE_NO_AVAILABLE },
	network: { network: NETWORK_FIXTURE },
	// eth0's Rx rate prominent-warning: the badge must wrap the formatted
	// value, not fill the whole .gl-num cell.
	"network-prominent": {
		network: { ...NETWORK_FIXTURE, _levels: { eth0: { bytes_recv: { level: "warning", prominent: true } } } },
	},
	// The first-card-levels cards WITHOUT --meangpu: the per-card table, where
	// card 0's proc cell is critical.
	"gpu-multi-levels": { gpu: GPU_FIRST_CARD_LEVELS },
	load: {
		load: { min1: 0.86, min5: 0.72, min15: 0.8, cpucore: 4, _levels: {} },
	},
	memswap: {
		memswap: { total: 17179869184, used: 4294967296, free: 12884901888, percent: 25.0, sin: 102400, sout: 0, _levels: {} },
	},
	"memswap-no-rates": {
		memswap: { total: 17179869184, used: 4294967296, free: 12884901888, percent: 25.0, sin: null, sout: null, _levels: {} },
	},
	// The three cpu scenarios, one per branch of the TUI's own selection
	// rules (glances/plugins/cpu/render_curses_v5.py:181-200). Counter values
	// are chosen so formatCount's base-1024 scaling lands on a checkable
	// string: 6860 -> "6.7K", 3072 -> "3.0K", 1843 -> "1.8K".
	// Linux: `user` present, `soft_interrupts` a real rate, `guest` present.
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
	// `guest` present but NULL, `syscalls` with a value: `guest` is selected
	// on key presence, so it still wins the last row (rendered as the missing
	// marker) and `syscalls` never appears. This is the only fixture that
	// tells the key-presence check apart from a `!= null` value check.
	"cpu-guest-null": {
		cpu: {
			total: 4.5, user: 3.8, system: 0.7, iowait: 0.0, idle: 95.5, irq: 0.0,
			nice: 0.0, steal: 0.0, guest: null, cpucore: 4,
			ctx_switches: 6860, interrupts: 3072, soft_interrupts: 1843, syscalls: 4096, _levels: {},
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
	// `ctx_switches` null-but-present (a rate before its baseline): the
	// col-3 first entry is dropped, so `ctx_sw` renders nowhere at all --
	// `soft_interrupts` is populated, so the col-3 fallback does not bring
	// it back either.
	"cpu-ctx-switches-null": {
		cpu: {
			total: 4.5, user: 3.8, system: 0.7, iowait: 0.0, idle: 95.5, irq: 0.0,
			nice: 0.0, steal: 0.0, guest: 0.0, cpucore: 4,
			ctx_switches: null, interrupts: 3072, soft_interrupts: 1843, _levels: {},
		},
	},
	// The gpu scenarios. The -mean and -fahrenheit pairs carry the SAME card
	// data as their plain counterparts on purpose: what differs between them
	// is only the ARGS_FIXTURES entry, so a difference in the rendered text
	// can only come from the flag.
	"gpu-one-card": { gpu: GPU_ONE_CARD },
	"gpu-three-cards": { gpu: GPU_THREE_CARDS },
	"gpu-no-memory": { gpu: GPU_NO_MEMORY },
	"gpu-three-cards-mean": { gpu: GPU_THREE_CARDS },
	"gpu-one-card-fahrenheit": { gpu: GPU_ONE_CARD },
	"gpu-first-card-colour": { gpu: GPU_FIRST_CARD_LEVELS },
	"gpu-mixed-memory": { gpu: GPU_MIXED_MEMORY },
	"gpu-zero-cards": { gpu: GPU_ZERO_CARDS },
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
	// The TUI's guard (system/render_curses_v5.py:25): no hostname, no block --
	// even with an OS name to show.
	"system-no-hostname": { system: { ...SYSTEM_FIXTURE, hostname: "" } },
};

// Every plugin that renders the SCALAR grid (<dl> of <dt>/<dd> pairs),
// populated in one run: `gl-num`'s 9ch floor is calibrated for a collection
// TABLE, so a scalar <dd> carrying it renders that plugin at a different
// width from its neighbours. Only a single scenario holding all five can
// observe that they agree -- a per-plugin scenario leaves the other four
// showing "loading…", i.e. no <dd> at all. gpu is here with ONE card, the
// card count that selects its summary grid.
ALL_FIXTURES["scalar-grids"] = {
	mem: MEM_FIXTURE_WITH_AVAILABLE,
	load: ALL_FIXTURES.load.load,
	memswap: ALL_FIXTURES.memswap.memswap,
	cpu: ALL_FIXTURES.cpu.cpu,
	gpu: GPU_ONE_CARD,
};
const scenario = process.argv[3] || "default";

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
		if (ALL_UNREACHABLE_SCENARIOS.has(scenario)) {
			return { ok: false, status: 500, json: async () => ({ detail: "boom" }) };
		}
		return { ok: true, status: 200, json: async () => ALL_FIXTURES[scenario] || {} };
	}
	if (path.includes("api/5/args")) {
		return { ok: true, status: 200, json: async () => ARGS_FIXTURES[scenario] || {} };
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
		// One entry per footer alert <li>: its classes, and the text and
		// classes of the <span> holding the level word. Lets a test observe
		// WHERE the prominent badge lands (the level word, not the whole line).
		footerAlerts: [],
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
				}
				const tds = findAllByTag(article, "TD");
				if (tds.length) {
					result.pluginTableCells[name] = tds.map((td) => {
						const span = findDescendantTag(td, "SPAN");
						return { cell: td.className, value: span ? span.className : null };
					});
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
			for (const section of findAllByAttr(first, "data-slot")) {
				result.slots[section.getAttribute("data-slot")] = findAllByAttr(section, "data-plugin").map((el) =>
					el.getAttribute("data-plugin"),
				);
			}
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

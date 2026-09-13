// Fixtures for webui_render_probe.js: the answers its fake `fetch` gives,
// per scenario (argv[3]). Moved out of the probe unchanged (G9-6 Task 0), so
// the harness and the data it serves can be read -- and grown -- separately.

"use strict";

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
	// short_names copied from glances/plugins/network/model_v5.py. The name
	// column declares none: its header cell is the block title (G9-6 D6).
	network: {
		interface_name: {},
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
	// short_names copied from glances/plugins/diskio/model_v5.py and
	// glances/plugins/fs/model_v5.py (G9-6 Task 3).
	diskio: { disk_name: {}, read_bytes: { short_name: "R/s" }, write_bytes: { short_name: "W/s" } },
	fs: { mnt_point: {}, size: { short_name: "Total" }, used: { short_name: "Used" }, free: { short_name: "Free" }, percent: {} },
	// short_name copied from glances/plugins/wifi/model_v5.py (G9-6 Task 3);
	// sensors declares none -- its value column has no header in the TUI.
	wifi: { ssid: {}, quality_link: {}, quality_level: { short_name: "dBm" } },
	sensors: { label: {}, type: {}, unit: {}, value: {}, warning: {}, critical: {}, status: {} },
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
	// short_names copied from glances/plugins/raid/model_v5.py.
	raid: { name: {}, used: { short_name: "Used" }, available: { short_name: "Avail" } },
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
	// quicklook absent -> percpu renders standalone (title, `total` column,
	// row labels). `percpu-with-quicklook` is deliberately NOT overridden
	// here: the SERVER_PLUGINS default already includes quicklook.
	percpu: SERVER_PLUGINS.filter((name) => name !== "quicklook"),
	"percpu-cap-2": SERVER_PLUGINS.filter((name) => name !== "quicklook"),
	"percpu-empty": SERVER_PLUGINS.filter((name) => name !== "quicklook"),
};

// Scenarios whose `/api/5/all` answers with an HTTP 500, same shape as the
// `pluginslist-unreachable` handling above -- spec §9: "`/api/5/all` fails ->
// every visible block shows its error, header included."
const ALL_UNREACHABLE_SCENARIOS = new Set(["all-unreachable"]);

// `/api/5/all` fixtures for the `mem` render-parity tests
// (test_mem_renders_all_eight_statistics_with_avail /
// test_mem_shows_used_when_available_is_absent in test_webui_v5_render.py).
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

// The network rows the TUI renderer skips, next to two it shows
// (network/render_curses_v5.py:129-142): a down interface, one hide_zero still
// hides, one with no rate yet. `lo` comes FIRST with an alias: the TUI keeps
// payload order, so "Loopback" must render before "eth0" -- a component
// sorting by raw key ("eth0" < "lo") would put "eth0" first.
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

// diskio (render_curses_v5.py:109-140): sorted by RAW disk_name, a hide_zero
// row and a rate-less row skipped, the alias displayed. `sdb`'s alias
// "Backup" sorts before "nvme0n1" but its raw key sorts after it, so a sort
// on the display name cannot pass. 855.6 B/s truncates ("855B"); 1280 is an
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

// fs (render_curses_v5.py:99-124): sorted by RAW mount point, an empty mount
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

// wifi (render_curses_v5.py:82-104): sorted by ssid, an empty ssid and a
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

// Two rows sharing a label, as on a real Dell laptop: v4 names sensor rows
// chip + " " + index per sub-type, so the first temperature and the first fan
// of `dell_smm` are both "dell_smm 0" (glances/plugins/sensors/__init__.py:369).
const SENSORS_DUPLICATE_LABELS = {
	_key: "label",
	data: [
		{ label: "dell_smm 0", type: "temperature_core", unit: "C", value: 52, warning: null, critical: null },
		{ label: "dell_smm 0", type: "fan_speed", unit: "R", value: 2418, warning: null, critical: null },
	],
	_levels: {},
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
	// `percpu` never renders without `--percpu` (cpu/percpu exclusivity, final
	// review Critical 1) -- this scenario needs `percpu` specifically visible
	// (test_cross_cutting_props_do_not_leak_into_the_dom_as_attributes checks
	// its `serverPlugins` inject does not leak as a DOM attribute).
	"mem-with-available": { percpu: true },
	"gpu-three-cards-mean": { meangpu: true },
	"gpu-one-card-fahrenheit": { fahrenheit: true },
	"gpu-first-card-colour": { meangpu: true },
	"header-hide-public": { hide_public_info: true },
	"network-byte": { byte: true },
	"sensors-fahrenheit": { fahrenheit: true },
	"npu-fahrenheit": { fahrenheit: true },
	// The per-core replacement is gated on the server's --percpu.
	"quicklook-percpu": { percpu: true },
	// `percpu` never renders without `--percpu` (cpu/percpu exclusivity, final
	// review Critical 1) -- every scenario exercising percpu's OWN rendering
	// needs it set. `percpu-with-quicklook` is deliberately EXCLUDED here: it
	// exists specifically to prove percpu stays hidden without --percpu even
	// though quicklook is instantiated (see its test) -- the interaction
	// between Critical 1 and Critical 2's fixes.
	percpu: { percpu: true },
	"percpu-cap-2": { percpu: true },
	"percpu-empty": { percpu: true },
	"percpu-loading": { percpu: true },
	// The other half of `percpu-with-quicklook`: quicklook instantiated AND
	// actually drawing per-core bars (--percpu set), so percpu correctly
	// drops its title/total/labels (Critical 2).
	"percpu-with-quicklook-percpu": { percpu: true },
	// --full-quicklook (G9-8 Task 6): server state, the only way it reaches
	// the WebUI is this endpoint too. `percpu: true` isolates what
	// full_quicklook itself hides from the shell's OWN cpu/percpu
	// exclusivity rule (final review, Minor 2 -- see the ALL_FIXTURES entry).
	"quicklook-full": { full_quicklook: true, percpu: true },
	// cpu/percpu mutual exclusion (final review, Critical 1):
	// glances_curses_v5.py:565-567 shows exactly one of them in the TUI, and
	// AppShell.vue now mirrors that off `serverArgs.percpu`.
	"cpu-percpu-on": { percpu: true },
	// "cpu-percpu-off" is deliberately absent here: a scenario absent from
	// this map gets `{}`, i.e. no flag set -- exactly the state under test.
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
// The fourth item has no usable path (folders/render_curses_v5.py:93-94, 103
// keeps every dict item and coalesces a missing/falsy path to "" rather than
// dropping the row): it must still render, with an empty name cell.
const FOLDERS_FIXTURE = {
	_key: "path",
	data: [
		{ path: "/tmp", size: 131072000, errno: 0 },
		{ path: "/home/nicolargo/media/library/Videos", size: 18253611008, errno: 0 },
		{ path: "/nonexisting", size: null, errno: 13 },
		{ path: "", size: 4096, errno: 0 },
	],
	_levels: {
		"/tmp": { size: { level: "ok", prominent: false } },
		"/home/nicolargo/media/library/Videos": { size: { level: "warning", prominent: false } },
	},
};

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
		// `type: null` -- exercises _format_name's UNKNOWN branch
		// (raid/render_curses_v5.py:50) and nothing else: active, no sub-lines.
		// Named so the string sort puts it last (md99 sorts after md9) and
		// leaves every other row's position unchanged.
		{ name: "md99", type: null, status: "active", used: 2, available: 2, components: { sdg1: "0", sdh1: "1" }, config: "UU" },
	],
	_levels: {
		md0: { status: { level: "ok", prominent: false } },
		md9: { status: { level: "ok", prominent: false } },
		md12: { status: { level: "critical", prominent: false } },
		md4: { status: { level: "warning", prominent: false } },
		md99: { status: { level: "ok", prominent: false } },
	},
};

// `smart` -- two devices, so the per-device grouping this fixture exists to
// prove cannot be faked by a component that flattens everything into one
// <tbody>. The first device covers one attribute per branch of
// _attr_value_text: a plain integer, a zero, a LARGE_VALUE_KEYS raw formatted
// with auto_unit(), and a null raw (rendered as an empty cell). The second
// device carries its own, different attributes (a different LARGE_VALUE_KEYS
// key at a different magnitude, and a plain integer) so its group is
// distinguishable from the first rather than a copy of it.
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
		{
			name: "/dev/sdb Crucial MX500",
			attributes: [
				{ name: "Bytes_Read", key: "bytesRead", raw: 2202009087 },
				{ name: "Power_Cycle_Count", key: "powerCycleCount", raw: 87 },
			],
		},
	],
	_levels: {},
};

// `mpp` — one engine per branch of mpp/render_curses_v5.py:32-57: a load with
// sessions, a load with ZERO sessions (v4 omits the session cell entirely),
// and a null load rendered "N/A". Only the load is coloured.
const MPP_FIXTURE = {
	_key: "engine_id",
	data: [
		{ engine_id: "rkvenc", name: "RKVENC", type: "enc", load: 24.8, sessions: 2 },
		{ engine_id: "jpegd", name: "JPEGD", type: "jpeg", load: 0.0, sessions: 0 },
		{ engine_id: "rkvdec", name: "RKVDEC", type: "dec", load: null, sessions: 0 },
	],
	_levels: {
		rkvenc: { load: { level: "careful", prominent: false } },
		jpegd: { load: { level: "ok", prominent: false } },
	},
};

// `npu` — TWO devices on purpose: the renderer shows the FIRST only (v4
// parity, npu/render_curses_v5.py:40-43), so a component that rendered both
// must fail. The first has a load; the second would show the freq fallback,
// which the dedicated scenario below exercises instead.
const NPU_FIXTURE = {
	_key: "npu_id",
	data: [
		{
			npu_id: "npu0", name: "Intel NPU 3720 (very long name that gets cut)", load: 45.0,
			freq: 80.0, mem: null, freq_current: 1000000000, freq_max: 2000000000, temperature: 55.0, power: null,
		},
		{ npu_id: "npu1", name: "Second NPU", load: 10.0, freq: 20.0, mem: 5.0, freq_current: 1, freq_max: 2, temperature: 30.0 },
	],
	_levels: { npu0: { load: { level: "careful", prominent: false }, temperature: { level: "ok", prominent: false } } },
};

// Load absent -> the percentage cell falls back to the FREQUENCY percentage
// (npu/render_curses_v5.py:47-54), coloured from the `freq` level.
const NPU_NO_LOAD = {
	_key: "npu_id",
	data: [{ ...NPU_FIXTURE.data[0], load: null, freq: 80.0 }],
	_levels: { npu0: { freq: { level: "warning", prominent: false } } },
};

// `quicklook` — the scalar payload: the bars `stats_list` selects and in which
// order, the CPU name/frequency header, and the per-core list with the mean of
// the cores the cap hides (`percpu_other`, published by the model).
const QUICKLOOK_FIXTURE = {
	cpu: 45.0,
	mem: 71.2,
	swap: 12.0,
	load: 18.0,
	cpu_name: "Intel Core i7-9750H",
	cpu_hz_current: 2600000000,
	cpu_hz: 4500000000,
	cpu_log_core: 12,
	cpu_phys_core: 6,
	stats_list: ["cpu", "mem", "load"],
	bar_char: "|",
	max_cpu_display: 2,
	percpu: [
		{ cpu_number: 0, total: 90.0, level: "critical" },
		{ cpu_number: 1, total: 40.0, level: "careful" },
		{ cpu_number: 2, total: 10.0, level: "ok" },
		{ cpu_number: 3, total: 20.0, level: "ok" },
	],
	percpu_other: { total: 15.0, level: "ok" },
	// `prominent: false` on every entry -- the real schema (quicklook/model_v5.py,
	// G9-8 smoke fix 2) never sets it True for cpu/mem/load/gpu_mem/gpu_proc; the
	// filled badge look was rejected after a smoke test. `quicklook-prominent`
	// below overrides `cpu` to prove the component still honours a True it is
	// given, rather than having hard-coded the flag away.
	_levels: {
		cpu: { level: "careful", prominent: false },
		mem: { level: "warning", prominent: false },
		load: { level: "ok", prominent: false },
	},
};

// `percpu` — six cores so the cap bites, with DESCENDING totals so the
// renderer's sort (by `total`, descending) is observable, plus the full set of
// Linux columns the grid shows. `max_cpu_display` is the field Task 1 added.
// `stat_fields` -- the Linux TUI order (`_os_headers()`, final review,
// Important 3): a SUBSET of the raw core's numeric keys (`softirq` and
// `guest_nice` are carried by the core but never in this list) and in a
// DIFFERENT order than the raw payload -- exactly what pins the component
// reading the published field instead of the first core's own key order.
const PERCPU_FIXTURE = {
	_key: "cpu_number",
	max_cpu_display: 4,
	stat_fields: ["user", "system", "iowait", "idle", "irq", "nice", "steal", "guest"],
	data: [0, 1, 2, 3, 4, 5].map((n) => ({
		cpu_number: n,
		total: 90 - n * 10,
		user: 50 - n * 5, system: 20 - n * 2, idle: 10 + n * 10, iowait: 1, irq: 0,
		softirq: 0, nice: 0, steal: 0, guest: 0, guest_nice: 0,
	})),
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
	"network-rows": { network: NETWORK_ROWS },
	// Same rows as `network-rows`; only ARGS_FIXTURES differs (--byte).
	"network-byte": { network: NETWORK_ROWS },
	"network-empty": { network: { _key: "interface_name", data: [], _levels: {} } },
	diskio: { diskio: DISKIO_FIXTURE },
	fs: { fs: FS_FIXTURE },
	// `free_space` is envelope metadata (fs/model_v5.py:117-119): the config
	// key merged with --fs-free-space, which is why the component reads it
	// from the payload and not from /api/5/args.
	"fs-free-space": { fs: { ...FS_FIXTURE, free_space: true } },
	wifi: { wifi: WIFI_FIXTURE },
	sensors: { sensors: SENSORS_FIXTURE },
	// Same payload as `sensors`; only ARGS_FIXTURES differs (--fahrenheit).
	"sensors-fahrenheit": { sensors: SENSORS_FIXTURE },
	"sensors-duplicate-labels": { sensors: SENSORS_DUPLICATE_LABELS },
	ports: { ports: PORTS_FIXTURE },
	"ports-empty": { ports: { _key: "indice", data: [], _levels: {} } },
	folders: { folders: FOLDERS_FIXTURE },
	"folders-empty": { folders: { _key: "path", data: [], _levels: {} } },
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
	raid: { raid: RAID_FIXTURE },
	"raid-empty": { raid: { _key: "name", data: [], _levels: {} } },
	smart: { smart: SMART_FIXTURE },
	"smart-empty": { smart: { _key: "name", data: [], _levels: {} } },
	mpp: { mpp: MPP_FIXTURE },
	"mpp-empty": { mpp: { _key: "engine_id", data: [], _levels: {} } },
	npu: { npu: NPU_FIXTURE },
	"npu-no-load": { npu: NPU_NO_LOAD },
	"npu-empty": { npu: { _key: "npu_id", data: [], _levels: {} } },
	// Same payload as `npu`; only ARGS_FIXTURES differs (--fahrenheit).
	"npu-fahrenheit": { npu: NPU_FIXTURE },
	// Standalone (no quicklook instantiated -- see PLUGINSLIST_FIXTURES below):
	// title, `total` column and row labels all render.
	percpu: { percpu: PERCPU_FIXTURE },
	// Same payload; quicklook IS instantiated (PLUGINSLIST_FIXTURES leaves this
	// one at the SERVER_PLUGINS default, which already includes quicklook).
	"percpu-with-quicklook": { percpu: PERCPU_FIXTURE },
	"percpu-cap-2": { percpu: { ...PERCPU_FIXTURE, max_cpu_display: 2 } },
	"percpu-empty": { percpu: { _key: "cpu_number", max_cpu_display: 4, data: [], _levels: {} } },
	// quicklook (G9-8 Task 5): as-is, `stats_list` selects cpu/mem/load only --
	// `swap` is in the payload and must NOT render.
	quicklook: { quicklook: QUICKLOOK_FIXTURE },
	// Same payload; only ARGS_FIXTURES differs (--percpu): the `cpu` bar is
	// replaced by the per-core view, capped by `max_cpu_display` (2 here).
	"quicklook-percpu": { quicklook: QUICKLOOK_FIXTURE },
	// Same payload; `cpu`'s `_levels` entry asks for the prominent badge --
	// dormant in the real schema (every field ships `prominent: false`, G9-8
	// smoke fix 2), but the component must still honour a payload that sets
	// it, the way `levelClass()` does for every other collection.
	"quicklook-prominent": {
		quicklook: { ...QUICKLOOK_FIXTURE, _levels: { ...QUICKLOOK_FIXTURE._levels, cpu: { level: "careful", prominent: true } } },
	},
	// `gpu_mem`/`gpu_proc` pin the two renamed labels (GMEM/GPU).
	"quicklook-gpu": {
		quicklook: {
			...QUICKLOOK_FIXTURE,
			stats_list: ["cpu", "mem", "gpu_mem", "gpu_proc"],
			gpu_mem: 30.0,
			gpu_proc: 55.0,
		},
	},
	// `cpu_hz_current: null` -- the header disappears entirely.
	"quicklook-no-freq": { quicklook: { ...QUICKLOOK_FIXTURE, cpu_hz_current: null } },
	"quicklook-empty": { quicklook: {} },
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
// width from its neighbours. Only a single scenario holding all six can
// observe that they agree -- a per-plugin scenario leaves the other five
// showing "loading…", i.e. no <dd> at all. gpu is here with ONE card, the
// card count that selects its summary grid. connections carries a real
// Tracked row (nf_conntrack_percent) so its one coloured <dd> is exercised
// here too.
ALL_FIXTURES["scalar-grids"] = {
	mem: MEM_FIXTURE_WITH_AVAILABLE,
	load: ALL_FIXTURES.load.load,
	memswap: ALL_FIXTURES.memswap.memswap,
	cpu: ALL_FIXTURES.cpu.cpu,
	gpu: GPU_ONE_CARD,
	connections: CONNECTIONS_FIXTURE,
};

ALL_FIXTURES["degrade-header-location"] = ALL_FIXTURES.header;
ALL_FIXTURES["degrade-header-os"] = ALL_FIXTURES.header;

// A payload is required for `mem`/`cpu` to render their <dl> grid at all --
// without it the component shows only its "loading…" placeholder and
// `pluginGrid` carries no entry to inspect. `degrade-medium` only resolves a
// `mem_cols` notch (test_a_narrow_top_row_degrades_in_the_tui_order), so only
// mem needs data here; `degrade-narrow` runs the whole TOP_CASCADE including
// both `cpu_cols` steps, so it needs the Linux three-column `cpu` fixture.
ALL_FIXTURES["degrade-medium"] = { mem: MEM_FIXTURE_WITH_AVAILABLE };
ALL_FIXTURES["degrade-narrow"] = { cpu: ALL_FIXTURES.cpu.cpu };

// --full-quicklook (G9-8 Task 6): the six blocks the flag hides, plus `load`
// and `percpu`, which must survive it (curses_renderer_v5.py:89
// `_FULL_QUICKLOOK_HIDDEN`). `npu` and `mpp` are the two other TOP-slot
// plugins the six-block list must also cover (final review, Minor 2).
// `percpu: true` in ARGS_FIXTURES below keeps the shell's OWN cpu/percpu
// exclusivity rule (Critical 1) from hiding `percpu` for an unrelated
// reason, so this scenario observes ONLY what full_quicklook itself hides.
ALL_FIXTURES["quicklook-full"] = {
	quicklook: QUICKLOOK_FIXTURE,
	cpu: ALL_FIXTURES.cpu.cpu,
	mem: MEM_FIXTURE_WITH_AVAILABLE,
	memswap: ALL_FIXTURES.memswap.memswap,
	load: ALL_FIXTURES.load.load,
	gpu: GPU_ONE_CARD,
	npu: NPU_FIXTURE,
	mpp: MPP_FIXTURE,
	percpu: PERCPU_FIXTURE,
};

// TOP_CASCADE steps (d) and (e) (G9-8 Task 6): a `quicklook` payload is
// enough, the same fixture the plain `quicklook` scenario uses, so the header
// text is observable at every notch.
ALL_FIXTURES["top-narrow-quicklook"] = { quicklook: QUICKLOOK_FIXTURE };
ALL_FIXTURES["top-narrowest-quicklook"] = { quicklook: QUICKLOOK_FIXTURE };

// cpu/percpu mutual exclusion (final review, Critical 1): both plugins carry
// a payload here so a test observes which one the SHELL actually dropped
// from the DOM (AppShell.vue's `slots()`), not merely which one has data.
// PLUGINSLIST_FIXTURES is deliberately NOT overridden for either scenario:
// the SERVER_PLUGINS default already instantiates both `cpu` and `percpu`,
// so the exclusion under test can only be the shell's, never pluginslist's.
ALL_FIXTURES["cpu-percpu-on"] = { cpu: ALL_FIXTURES.cpu.cpu, percpu: PERCPU_FIXTURE };
ALL_FIXTURES["cpu-percpu-off"] = ALL_FIXTURES["cpu-percpu-on"];

// percpu/quicklook label-drop regression (final review, Critical 2): same
// payload and pluginslist as `percpu-with-quicklook` above (quicklook
// instantiated) -- only ARGS_FIXTURES differs (--percpu), so this is the
// scenario where quicklook actually DRAWS per-core bars and percpu's
// title/total/labels are correctly dropped.
ALL_FIXTURES["percpu-with-quicklook-percpu"] = { percpu: PERCPU_FIXTURE };

// Zone widths per scenario, keyed by the `data-slot` the shell renders. The
// numbers are what a browser would report: `available` is clientWidth,
// `content` scrollWidth. `content` is what the cascade shrinks -- the harness
// re-reads it after each notch through CONTENT_STEPS below.
const WIDTH_FIXTURES = {
	// Fits as it is: no notch.
	"degrade-wide": { top: { available: 1400, content: 900 }, "header-left": { available: 1400, content: 300 } },
	// 850 - 150 = 700: exactly one notch (mem_cols=1). The header fits.
	"degrade-medium": { top: { available: 700, content: 850 }, "header-left": { available: 1400, content: 300 } },
	// cpu_cols appears twice in TOP_CASCADE, so the cumulative flag object can
	// only ever reach 6 distinct keys: 1500 - 6*150 = 600 > 200, so neither
	// cascade ever fits and both run to their last step.
	"degrade-narrow": { top: { available: 200, content: 1500 }, "header-left": { available: 200, content: 1500 } },
	// 1250 - 2*150 = 950 <= 1000, and one notch alone leaves 1100 > 1000: the
	// cascade stops at step (1), hide_ip_location.
	"degrade-header-location": { "header-left": { available: 1000, content: 1250 } },
	// 1400 - 3*150 = 950 <= 1000, and two notches leave 1100 > 1000: it stops at
	// step (2), hide_os_info.
	"degrade-header-os": { "header-left": { available: 1000, content: 1400 } },
	// TOP_CASCADE steps (d)/(e) (G9-8 Task 6). `mem_cols` and both `cpu_cols`
	// notches land first but add only 2 distinct keys (`cpu_cols` overwrites
	// itself), so the cumulative key count after 3 steps is 3 (mem_cols,
	// cpu_cols, quicklook_freq_only): 1400 - 3*150 = 950 <= 1000, and 2 notches
	// alone leave 1100 > 1000 -- the cascade stops exactly at step (d).
	"top-narrow-quicklook": { top: { available: 1000, content: 1400 }, "header-left": { available: 1400, content: 300 } },
	// One step further: 1400 - 4*150 = 800 <= 850, and 3 notches alone leave
	// 950 > 850 -- the cascade stops at step (e), hide_quicklook.
	"top-narrowest-quicklook": { top: { available: 850, content: 1400 }, "header-left": { available: 1400, content: 300 } },
};

// One notch removes roughly one column or one block. The exact figure does not
// matter: what the tests assert is WHICH notches land, not the pixels.
const CONTENT_PER_NOTCH = 150;

module.exports = {
	ALERT_FIXTURES,
	INFO_FIXTURES,
	SERVER_PLUGINS,
	PLUGINSLIST_FIXTURES,
	ALL_UNREACHABLE_SCENARIOS,
	ARGS_FIXTURES,
	ALL_FIXTURES,
	WIDTH_FIXTURES,
	CONTENT_PER_NOTCH,
};

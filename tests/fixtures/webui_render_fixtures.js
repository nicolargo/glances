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
	"gpu-three-cards-mean": { meangpu: true },
	"gpu-one-card-fahrenheit": { fahrenheit: true },
	"gpu-first-card-colour": { meangpu: true },
	"header-hide-public": { hide_public_info: true },
	"network-byte": { byte: true },
	"sensors-fahrenheit": { fahrenheit: true },
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

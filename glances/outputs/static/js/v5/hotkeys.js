// Glances v5 WebUI -- the SHOW/HIDE hotkeys.
//
// A mirror of the `hide` entries of `TuiV5._HOTKEYS`
// (glances/outputs/glances_curses_v5.py): the browser cannot import Python.
// Same keys, same targets, same descriptions, so the two surfaces cannot tell
// a user different things -- tests/test_webui_v5_hotkeys_drift.py fails on
// any divergence, including the descriptions the help overlay shows.
//
// Kept in its own module, not part of AppShell.vue, because a `.vue` file
// cannot be imported under node -- the same reason degrade.js and
// full_quicklook.js are `.js` modules.
//
// GENERATED FROM THE PYTHON TABLE, then committed. Regenerate rather than
// hand-edit when a key changes; the drift test is what catches a stale copy.

// Keys naming their plugins outright.
export const HIDE_KEYS = {
	A: { desc: "Show/hide AMPs", plugins: ["amps"] },
	C: { desc: "Show/hide cloud", plugins: ["cloud"] },
	d: { desc: "Show/hide disk I/O", plugins: ["diskio"] },
	D: { desc: "Show/hide containers", plugins: ["containers"] },
	f: { desc: "Show/hide filesystem and folders", plugins: ["fs", "folders"] },
	G: { desc: "Show/hide GPU", plugins: ["gpu"] },
	I: { desc: "Show/hide IP module", plugins: ["ip"] },
	K: { desc: "Show/hide TCP connections", plugins: ["connections"] },
	l: { desc: "Show/hide alerts", plugins: ["alert"] },
	n: { desc: "Show/hide network stats", plugins: ["network"] },
	N: { desc: "Show/hide current time", plugins: ["now"] },
	P: { desc: "Show/hide ports stats", plugins: ["ports"] },
	Q: { desc: "Show/hide IRQ module", plugins: ["irq"] },
	r: { desc: "Show/hide SMART stats", plugins: ["smart"] },
	R: { desc: "Show/hide RAID plugin", plugins: ["raid"] },
	s: { desc: "Show/hide sensors", plugins: ["sensors"] },
	V: { desc: "Show/hide VMs", plugins: ["vms"] },
	W: { desc: "Show/hide wifi module", plugins: ["wifi"] },
	z: { desc: "Show/hide processes", plugins: ["processlist", "programlist", "processcount"] },
	7: { desc: "Show/hide NPU", plugins: ["npu"] },
	8: { desc: "Show/hide MPP", plugins: ["mpp"] },
	3: { desc: "Show/hide quicklook", plugins: ["quicklook"] }
};

// Keys covering a whole layout slot. The members are resolved from the plugin
// registry at press time rather than listed here: `plugins/index.js` already
// carries every plugin's slot, and a test keeps that registry in the TUI's
// slot order, so resolving is drift-proof where a second literal list would
// not be.
export const HIDE_SLOT_KEYS = {
	2: { desc: "Show/hide left sidebar", slot: "left" },
	5: { desc: "Show/hide top menu", slot: "top" }
};

// The TOGGLE VIEW keys. Unlike SHOW/HIDE, these do not remove a block -- they
// flip HOW something is shown, and each one has a server-side default the
// viewer is overriding (`serverArgs`, from /api/5/args). `flag` is the key
// that default lives under.
//
// `process_short_name` is the exception: the TUI defaults it to true
// (`ViewState`) and no CLI option sets it, so the browser defaults it to true
// as well and the server never has an opinion.
export const VIEW_KEYS = {
	"1": { desc: "Per-CPU / aggregated CPU", flag: "percpu" },
	"4": { desc: "Full quicklook (hide the rest of the row)", flag: "full_quicklook" },
	"/": { desc: "Short / full process name", flag: "process_short_name" },
	j: { desc: "Threads / programs view", flag: "programs" },
	b: { desc: "Network I/O in bit/s or byte/s", flag: "byte" },
	"6": { desc: "GPU: per-card or mean", flag: "meangpu" },
	F: { desc: "Filesystem: used or free space", flag: "fs_free_space" },
	B: { desc: "Disk I/O in byte/s or IOPS", flag: "diskio_iops" },
	"0": { desc: "Load average or Irix percentage", flag: "load_irix" },
	T: { desc: "Network Rx/Tx apart or combined", flag: "network_sum" }
};

/** The view flag `key` flips, or null when `key` is not a TOGGLE VIEW key. */
export function viewFlag(key) {
	const entry = VIEW_KEYS[key];
	return entry ? entry.flag : null;
}

// The key that opens the overlay listing all of the above, mirroring the TUI's
// `h`. Not a `hide` entry, so it is not part of the drift comparison.
export const HELP_KEY = "h";

/**
 * The plugin names `key` hides, or null when `key` is not a SHOW/HIDE key.
 *
 * `plugins` is the live registry (`AppShell.plugins`), so a slot key covers
 * exactly the plugins that are actually registered -- never a name the server
 * does not serve.
 */
export function hideTargets(key, plugins) {
	const literal = HIDE_KEYS[key];
	if (literal) return literal.plugins;
	const slotKey = HIDE_SLOT_KEYS[key];
	if (!slotKey) return null;
	return plugins.filter((plugin) => plugin.slot === slotKey.slot).map((plugin) => plugin.name);
}

/**
 * Toggle `names` in `hidden` as ONE unit, returning a new Set.
 *
 * Keyed on the FIRST name, exactly like the TUI's dispatcher
 * (`glances_curses_v5._handle_key`): a compound key (`f` -> fs+folders) must
 * never land half-hidden, however its members were toggled individually
 * beforehand.
 *
 * Returns a new Set rather than mutating: the caller assigns it, which is what
 * makes Vue re-render.
 */
export function toggleHidden(hidden, names) {
	const next = new Set(hidden);
	if (!names.length) return next;
	if (next.has(names[0])) {
		for (const name of names) next.delete(name);
	} else {
		for (const name of names) next.add(name);
	}
	return next;
}

/**
 * `[{ key, desc, group }]` for the help overlay, grouped the way the TUI
 * groups its own (`_HELP_GROUPS`: TOGGLE VIEW before SHOW/HIDE).
 *
 * Built from the same two objects the dispatcher reads, so a key cannot be
 * bound and undocumented (the property the TUI gets from generating its
 * overlay out of `_HOTKEYS`).
 */
export function helpRows() {
	const rows = (table, group) => Object.entries(table).map(([key, entry]) => ({ key, desc: entry.desc, group }));
	return [
		...rows(VIEW_KEYS, "TOGGLE VIEW"),
		...rows(HIDE_KEYS, "SHOW/HIDE"),
		...rows(HIDE_SLOT_KEYS, "SHOW/HIDE")
	];
}

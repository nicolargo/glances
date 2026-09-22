// Glances v5 WebUI -- process/program row helpers shared by
// PluginProcesslist.vue and PluginProgramlist.vue.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it.
//
// processlist (per-thread) and programlist (per-program) share every column
// except PID/NPROCS (programlist/render_curses_v5.py's module docstring:
// "Every other column is identical, so this renderer reuses the processlist
// cell builders verbatim"). These three were duplicated byte-for-byte across
// the two components -- extracted here so a
// future change to the terminal's sort-key mapping or its I/O-rate/command
// conventions cannot be ported to one component and silently missed in the
// other.

// A copy of `_HEADER_SORT_KEY` (glances/plugins/processlist/render_curses_v5.py
// :97): the browser cannot import Python. NPROCS (programlist) and PID
// (processlist) both have no entry -- neither TUI renderer ever underlines
// them (programlist/render_curses_v5.py's own docstring, :22).
export const HEADER_SORT_KEY = {
	"CPU%": "cpu_percent",
	"MEM%": "memory_percent",
	USER: "username",
	"TIME+": "cpu_times",
	"R/s": "io_counters",
	"W/s": "io_counters",
	Command: "name",
};

// A copy of `_io_rate` (processlist/render_curses_v5.py): engine convention
// `io_counters = [r_new, w_new, r_old, w_old, io_tag]`, `io_tag !== 1` means
// access denied or the process's/program's first observed cycle -- render as
// missing, not zero.
export function ioRate(item, read) {
	const raw = item && item.io_counters;
	if (!Array.isArray(raw) || raw.length < 5 || raw[4] !== 1) return null;
	const elapsed = Number(item.time_since_update);
	if (!Number.isFinite(elapsed) || elapsed <= 0) return null;
	const [newIndex, oldIndex] = read ? [0, 2] : [1, 3];
	const delta = Number(raw[newIndex]) - Number(raw[oldIndex]);
	if (!Number.isFinite(delta)) return null;
	return Math.max(delta, 0) / elapsed;
}

// A copy of `_split_cmdline`
// (glances/plugins/processlist/render_curses_v5.py): returns
// `{ path, cmd, args }`.
//
// `cmdline[0]` starting with psutil's bare `name` is taken as the command
// whole, with no path split -- the TUI's rule, and what keeps an interpreter
// invoked as `python3` from being mistaken for a path.
export function splitCmdline(item) {
	const cmdline = item && item.cmdline;
	const name = String((item && item.name) || "");
	if (!Array.isArray(cmdline) || cmdline.length === 0) {
		return { path: "", cmd: name, args: "" };
	}
	const head = String(cmdline[0]);
	const cut = head.lastIndexOf("/");
	const [path, cmd] = name && head.startsWith(name) ? ["", head] : [head.slice(0, Math.max(cut, 0)), head.slice(cut + 1)];
	const args = cmdline
		.slice(1)
		.filter((token) => token !== null && token !== undefined)
		.map(String)
		.join(" ");
	return { path, cmd, args };
}

// A copy of `_command_cells` (same file), flattened to text: unlike the TUI,
// no WebUI collection component decorates part of a cell's text today, so the
// bold/plain split is dropped.
//
// `shortName` is the `/` hotkey (TUI: `ViewState.process_short_name`,
// default true). false prefixes the executable with its directory.
//
// KNOWN DIVERGENCE from the terminal. The TUI shows the prefix only when
// `os.path.isdir(path)` holds (render_curses_v5.py:329); a browser has no
// filesystem, so it cannot make that check and shows the prefix whenever
// `cmdline[0]` carried one. The two disagree only for a `cmdline[0]` that
// looks like a path but is not one -- `./foo/bar` from a deleted tree, say --
// where the browser prints the prefix and the terminal does not.
export function commandText(item, shortName = true) {
	const cmdline = item && item.cmdline;
	if (!Array.isArray(cmdline) || cmdline.length === 0) {
		// Kernel threads have no cmdline in /proc: the `[name]` convention.
		const name = String((item && item.name) || "");
		return name ? `[${name}]` : "";
	}
	const { path, cmd, args } = splitCmdline(item);
	// No space between the path and the exe name -- "/usr/bin/python3".
	const command = !shortName && path ? `${path}/${cmd}` : cmd;
	return args ? `${command} ${args}` : command;
}

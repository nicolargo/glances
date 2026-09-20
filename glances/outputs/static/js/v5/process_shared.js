// Glances v5 WebUI -- process/program row helpers shared by
// PluginProcesslist.vue and PluginProgramlist.vue.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it.
//
// processlist (per-thread) and programlist (per-program) share every column
// except PID/NPROCS (programlist/render_curses_v5.py's module docstring:
// "Every other column is identical, so this renderer reuses the processlist
// cell builders verbatim"). These three were duplicated byte-for-byte across
// the two components until G9-9B Task 8 fix round 1 -- extracted here so a
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

// A copy of `_split_cmdline` + `_command_cells` (`short_name=True`, the only
// mode either WebUI block has -- there is no `/` hotkey to toggle the full
// path view in the browser). No bold/plain split either: unlike the TUI, no
// WebUI collection component decorates part of a cell's text today.
export function commandText(item) {
	const cmdline = item && item.cmdline;
	const name = String((item && item.name) || "");
	if (!Array.isArray(cmdline) || cmdline.length === 0) {
		return name ? `[${name}]` : "";
	}
	const head = String(cmdline[0]);
	const cmd = name && head.startsWith(name) ? head : head.slice(head.lastIndexOf("/") + 1);
	const args = cmdline
		.slice(1)
		.filter((token) => token !== null && token !== undefined)
		.map(String)
		.join(" ");
	return args ? `${cmd} ${args}` : cmd;
}

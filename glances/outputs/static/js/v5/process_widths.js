// Glances v5 WebUI -- static column widths, in CHARACTER COLUMNS.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it -- the
// same contract degrade.js, processlist_columns.js and row_budget.js state
// in their own headers. `PROCESS_COL_WIDTHS`, `ALERT_COL_WIDTHS` and the
// constants beside them are copies of a terminal renderer's own constants,
// because the browser cannot import Python;
// tests/test_webui_v5_width_drift.py compares the two sides. Never edit one
// side alone. `WEBUI_COL_WIDTHS` and `COL_SEPARATOR` below are the browser's
// OWN numbers -- what the DOM is actually sized with -- and are deliberately
// outside that drift check; each carries its own justification.
//
// These are character counts, so the CSS derived from them uses
// `calc(N * var(--gl-col))` and never `ch` -- `ch` resolves to 0.5em under the
// shipped font stack and would render 0.83 of every intended character
// (css/v5.css, and the per-declaration allowlist in test_webui_v5_tokens.py).
// This module itself declares no CSS.

// glances/plugins/processlist/render_curses_v5.py:55-65
// The property names below must stay written as string literals: the
// drift check that compares this object against the Python side uses a
// regex that only matches names given in that quoted form.
export const PROCESS_COL_WIDTHS = {
	// 7: kept equal to the terminal's `_W_CPU` (render_curses_v5.py, see its
	// own comment for why 5 is too narrow), so
	// test_webui_v5_width_drift.py stays green with no allowlist.
	"CPU%": 7,
	"MEM%": 5,
	"VIRT": 5,
	"RES": 5,
	"PID": 7,
	"USER": 10,
	"THR": 3,
	"NI": 3,
	"S": 1,
	"TIME+": 8,
	"R/s": 5,
	"W/s": 5,
};

// Characters of separator BETWEEN two adjacent cells, reserved by
// `.gl-table.gl-process-table th/td:not(:last-child)`'s `padding-right`
// (css/v5.css). The terminal puts ONE space between its columns; the browser
// puts two -- a maintainer readability call, not TUI drift: a 0.88rem
// proportional-looking grid needs more air than a terminal cell does.
//
// Under `table-layout: fixed` the <col> is the column's WHOLE box and the
// padding comes OUT of it, so every `<col>` is `contentWidth + COL_SEPARATOR`
// and every `--gl-fixed-cols` sum charges one separator per inter-cell
// boundary. This constant is the single place those two agree;
// test_webui_v5_tokens.py reads it and requires the stylesheet's own
// multiplier to match.
export const COL_SEPARATOR = 2;

// What the BROWSER needs per column, which is not always what the terminal
// needs: `formatPercent()` (format.js) appends a `%` the curses renderer never
// prints, so a WebUI percent cell is one character longer than its terminal
// counterpart. `MEM%` is the only column that pushes past its terminal budget
// because of it -- `100.0%` is 6 characters against `_W_MEM`'s 5. Every other
// column renders the same string on both surfaces, `CPU%` included (7 already
// fits `9999.9%`).
//
// A separate literal map rather than a spread of `PROCESS_COL_WIDTHS` so the
// numbers a reader (and the regex-based tests) sees are the numbers the
// <colgroup> gets. tests/js/process_widths.test.mjs keeps it honest from both
// sides: every entry must cover the longest string its own formatter can
// produce, AND must equal the terminal width unless this comment explains why
// it does not.
export const WEBUI_COL_WIDTHS = {
	"CPU%": 7, // 9999.9%
	"MEM%": 6, // 100.0% -- one more than `_W_MEM`, for the `%` the TUI omits
	"VIRT": 5, // 1023G / 99.9T
	"RES": 5,
	"PID": 7, // 4194304, Linux's `pid_max` ceiling of 2**22
	"USER": 10, // `formatUsername()` crops at 10
	"THR": 3,
	"NI": 3, // -20
	"S": 1,
	"TIME+": 8, // 99h59:59
	"R/s": 5, // as VIRT/RES -- the same `formatProcessBytes()`
	"W/s": 5,
};

// The fixed columns in DISPLAY order -- what a <colgroup> needs, and not the
// same thing as PROCESS_COL_WIDTHS' key order, which no test would catch if it
// changed. Copy of `_FIXED_COL_KEYS`
// (glances/plugins/processlist/render_curses_v5.py:91).
export const FIXED_COL_KEYS = ["CPU%", "MEM%", "VIRT", "RES", "PID", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s"];

// programlist replaces PID with NPROCS -- same width, different meaning
// (glances/plugins/programlist/render_curses_v5.py:58).
export const NPROCS_WIDTH = 7;

// programlist's fixed columns, in DISPLAY order: FIXED_COL_KEYS with NPROCS
// in PID's place (glances/plugins/programlist/render_curses_v5.py:99-113).
// The renderer never imports processlist's `_DROP_ORDER` -- this list is the
// block's full, constant column set, not a candidate for a `shows()` filter.
export const PROGRAM_FIXED_COL_KEYS = [
	"CPU%",
	"MEM%",
	"VIRT",
	"RES",
	"NPROCS",
	"USER",
	"THR",
	"NI",
	"S",
	"TIME+",
	"R/s",
	"W/s",
];

// The floor below which the width cascade drops another column
// (processlist/render_curses_v5.py:87). Command is never dropped.
export const MIN_COMMAND_WIDTH = 8;

// glances/outputs/curses_renderer_v5.py:525-528. TARGET and TOP are elastic
// and carry floors instead of fixed widths.
// The property names below must stay written as string literals: the
// drift check that compares this object against the Python side uses a
// regex that only matches names given in that quoted form.
export const ALERT_COL_WIDTHS = { "GLYPH": 1, "TIME": 8, "DURATION": 8, "LEVEL": 8 };
export const ALERT_MIN_TARGET = 12; // :529
export const ALERT_MIN_TOP = 22; // :537

// Block widths at or above which each column still fits without starving
// TARGET below its floor (:532-533, :540). TOP drops FIRST, by construction.
//
// PluginAlert.vue's own `fixedColsStyle()` does NOT sum to these numbers, and
// never did: the terminal gives its TIME and DURATION cells one trailing pad
// column each so its painter lands the spec's curses offsets
// (curses_renderer_v5.py:814-829, `_fit_text(..., _ALERT_W_TIME + 1)` and
// `... + " "`); CSS already reserves that character as part of the
// `padding-right` separator (`COL_SEPARATOR` above), so adding the terminal's
// own pad on top of it would double-count a separator that is already there.
// The browser sum also gives TARGET its NATURAL width rather than this floor,
// exactly as the terminal does when it is not width-constrained
// (curses_renderer_v5.py:781-784), so the two sums cannot agree in absolute
// terms at all. Do not "correct" either side to make the numbers match -- the
// cascade still fires at the same RELATIVE points (the deltas between these
// three thresholds hold exactly on the browser side too).
export const ALERT_W_WITH_TOP = 66;
export const ALERT_W_WITH_LEVEL = 43;
export const ALERT_W_WITH_DURATION = 34;

// glances/plugins/containers/render_curses_v5.py `_COL_GEOMETRY`: the same
// key -> (painted cells, total width) table, split in two maps so the drift
// check can read each one with the `"key": <int>` regex it already uses for
// PROCESS_COL_WIDTHS above. `command` carries `_MIN_COMMAND_WIDTH`, not a
// real width: its data is unbounded, so the terminal budgets the column at
// that floor and the browser's elastic tail uses the same number.
//
// The property names below must stay written as string literals: the drift
// check that compares these against the Python side uses a regex that only
// matches names given in that quoted form.
export const CONTAINER_COL_WIDTHS = {
	"engine": 6,
	"pod": 12,
	"status": 10,
	"uptime": 10,
	"cpu": 6,
	"mem": 7,
	"memory_max": 8,
	"diskio": 14,
	"networkio": 14,
	"ports": 16,
	"command": 8,
};

// How many cells each key above paints. The IO and network pairs are ONE key
// over TWO cells (7 characters each), so a half-pair can never be shown --
// and a <colgroup> needs one <col> per cell, not per key.
export const CONTAINER_COL_CELLS = {
	"engine": 1,
	"pod": 1,
	"status": 1,
	"uptime": 1,
	"cpu": 1,
	"mem": 1,
	"memory_max": 1,
	"diskio": 2,
	"networkio": 2,
	"ports": 1,
	"command": 1,
};

// The container columns in DISPLAY order -- what a <colgroup> needs, and not
// the key order of the two maps above (`name` has no entry there at all: the
// terminal sizes that column from the data, `name_w` at
// containers/render_curses_v5.py:262, never from a constant).
export const CONTAINER_COL_KEYS = [
	"engine",
	"pod",
	"name",
	"status",
	"uptime",
	"cpu",
	"mem",
	"memory_max",
	"diskio",
	"networkio",
	"ports",
	"command",
];

// The browser's own container widths, `WEBUI_COL_WIDTHS`' counterpart for
// this block and for the same reason: `formatPercent()` appends a `%` curses
// never prints. `cpu` is the only column it changes -- the terminal's
// `{cpu:>6.1f}` holds `9999.9`, but the browser renders `9999.9%`, and a
// container spread over many cores genuinely passes 1000%. Every other
// column renders the same string on both surfaces.
// tests/js/containers_columns.test.mjs checks each entry against the longest
// string its own formatter can produce, and against the terminal width.
export const WEBUI_CONTAINER_COL_WIDTHS = {
	"engine": 6,
	"pod": 12,
	"status": 10, // `restarting`, the longest status the TUI maps
	"uptime": 10,
	"cpu": 7, // 9999.9% -- one more than `_COL_GEOMETRY`, for the `%` the TUI omits
	"mem": 7,
	"memory_max": 8,
	"diskio": 14,
	"networkio": 14,
	"ports": 16,
	"command": 8,
};

// `[containers] max_name_size`'s own default, for a payload that carries none
// (containers/render_curses_v5.py:261).
export const CONTAINER_MAX_NAME_SIZE = 20;

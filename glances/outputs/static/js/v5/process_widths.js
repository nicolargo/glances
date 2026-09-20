// Glances v5 WebUI -- static column widths, in CHARACTER COLUMNS.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it -- the
// same contract degrade.js, processlist_columns.js and row_budget.js state
// in their own headers. Every value is a copy of a terminal renderer's
// constant, because the browser cannot import Python;
// tests/test_webui_v5_width_drift.py compares the two sides. Never edit one
// side alone.
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
// PluginAlert.vue's own `fixedColsStyle()` does NOT sum to these numbers --
// its sums are INTENTIONALLY 2, 2 and 1 short of these three constants
// respectively. The terminal gives its TIME and DURATION cells one trailing
// pad column each so its painter lands the spec's curses offsets
// (curses_renderer_v5.py:814-829, `_fit_text(..., _ALERT_W_TIME + 1)` and
// `... + " "`); CSS already reserves that same character as the
// `padding-right: var(--gl-col)` separator (colStyle()'s `+1` in
// PluginAlert.vue), so adding the terminal's own pad on top of it would
// double-count a separator that is already there. Do not "correct" either
// side to make the numbers match -- the cascade still fires at the same
// RELATIVE points (the deltas between these three thresholds hold exactly
// on the browser side too), just anchored a few characters earlier in
// absolute terms than these constants.
export const ALERT_W_WITH_TOP = 66;
export const ALERT_W_WITH_LEVEL = 43;
export const ALERT_W_WITH_DURATION = 34;

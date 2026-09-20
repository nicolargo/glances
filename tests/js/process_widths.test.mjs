import { test } from "node:test";
import assert from "node:assert/strict";
import {
	ALERT_COL_WIDTHS,
	COL_SEPARATOR,
	FIXED_COL_KEYS,
	PROCESS_COL_WIDTHS,
	WEBUI_COL_WIDTHS,
} from "../../glances/outputs/static/js/v5/process_widths.js";
import { formatCpuTime, formatPercent, formatProcessBytes, formatUsername } from "../../glances/outputs/static/js/v5/format.js";

// The WORST CASE each processlist/programlist column can ever render, as the
// string its own formatter actually produces -- the maintainer requirement
// these widths answer: "for every column there is a theoretical maximum
// number of characters, and the width has to cover it".
//
// Under `table-layout: fixed` a cell that overflows by so much as a fraction
// of a character loses its last one to `text-overflow: ellipsis`, so a width
// that merely ALMOST covers the worst case reads as a truncation bug on a
// real host -- which is exactly how this was found.
const WORST_CASE = {
	// A process spread over many cores genuinely passes 1000%; formatPercent
	// keeps its one decimal all the way up.
	"CPU%": () => formatPercent(9999.9),
	// memory_percent is bounded by 100, and the browser appends the `%` the
	// terminal's own 5-wide column does not print.
	"MEM%": () => formatPercent(100),
	// formatProcessBytes drops the decimal at 100 and over, so the widest
	// string is 4 digits + a unit letter, whatever the magnitude.
	"VIRT": () => formatProcessBytes(1023 * 1024 ** 3),
	"RES": () => formatProcessBytes(1023 * 1024 ** 3),
	// Linux's `pid_max` ceiling is 2**22 = 4194304.
	"PID": () => String(4194304),
	// formatUsername crops at PROCESS_COL_WIDTHS.USER with a trailing `+`.
	"USER": () => formatUsername("abcdefghijklmnop"),
	// Threads are unbounded in principle; the terminal budgets 3 and lets a
	// four-digit count overflow, and the browser matches it rather than
	// spending a character every host pays for on the few that need it.
	"THR": () => "999",
	// The nice ladder is -20..19, so the sign is the widest case.
	"NI": () => "-20",
	"S": () => "R",
	// formatCpuTime: `{H}h{MM:SS}` up to 99h, then a bare `{hours}h`.
	"TIME+": () => formatCpuTime({ user: 99 * 3600 + 59 * 60 + 59, system: 0 }),
	"R/s": () => formatProcessBytes(1023 * 1024 ** 3),
	"W/s": () => formatProcessBytes(1023 * 1024 ** 3),
};

test("every WebUI process column is wide enough for its own worst case", () => {
	for (const key of FIXED_COL_KEYS) {
		const worst = WORST_CASE[key]();
		assert.ok(
			WEBUI_COL_WIDTHS[key] >= worst.length,
			`${key}: ${WEBUI_COL_WIDTHS[key]} character(s) cannot hold ${worst.length} ("${worst}")`,
		);
	}
});

test("a WebUI process column is no wider than it has to be", () => {
	// The other half of the requirement: a column that is merely generous
	// steals space from the elastic Command column for nothing. Every width
	// is the worst case EXACTLY, except the two the terminal's own constants
	// pin above it (CPU% carries 7 for `9999.9%`, THR 3 by TUI parity).
	const slack = { "CPU%": 7, "THR": 3 };
	for (const key of FIXED_COL_KEYS) {
		const expected = slack[key] ?? WORST_CASE[key]().length;
		assert.equal(WEBUI_COL_WIDTHS[key], expected, `${key} is not sized to its worst case`);
	}
});

test("the WebUI widths only ever diverge from the terminal's for the `%` suffix", () => {
	// process_widths.js's PROCESS_COL_WIDTHS is drift-tested against the
	// curses renderer 1:1 (tests/test_webui_v5_width_drift.py); WEBUI_COL_WIDTHS
	// is not, so this is what keeps the second map from quietly wandering off.
	// MEM% is the ONE documented divergence: `formatPercent()` appends a `%`
	// curses never prints, and `100.0%` no longer fits `_W_MEM`'s 5.
	for (const key of FIXED_COL_KEYS) {
		const expected = key === "MEM%" ? PROCESS_COL_WIDTHS[key] + 1 : PROCESS_COL_WIDTHS[key];
		assert.equal(WEBUI_COL_WIDTHS[key], expected, `${key} diverges from the terminal with no reason given`);
	}
});

test("every alert column is wide enough for its own worst case", () => {
	// TIME: `HH:MM:SS`, `YY-MM-DD` and the `--:--:--` placeholder are all 8.
	assert.equal(ALERT_COL_WIDTHS.TIME, 8);
	// DURATION: `_format_duration_compact` tops out at `{days}d{HH}h`, plus the
	// `>` a partial incident carries -- and its own HEADER is 8 characters too,
	// which is what actually sets the floor here.
	assert.ok(ALERT_COL_WIDTHS.DURATION >= ">365d12h".length);
	assert.ok(ALERT_COL_WIDTHS.DURATION >= "DURATION".length);
	// LEVEL: the longest of ok/careful/warning/critical, upper-cased.
	assert.ok(ALERT_COL_WIDTHS.LEVEL >= "CRITICAL".length);
	// The glyph is a single ●/○/*/-.
	assert.equal(ALERT_COL_WIDTHS.GLYPH, 1);
});

test("the column separator is a positive character count", () => {
	// Both the <col> boxes and the `--gl-fixed-cols` sums add it; the
	// stylesheet's own `padding-right` multiplier is checked against it in
	// tests/test_webui_v5_tokens.py.
	assert.ok(Number.isInteger(COL_SEPARATOR) && COL_SEPARATOR >= 1);
});

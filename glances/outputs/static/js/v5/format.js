// Glances v5 WebUI — value formatting.
//
// Shared by every plugin component, so the same number reads the same way
// everywhere. Pure: no DOM, no fetch, no imports.
//
// Every function accepts null/undefined and returns "-". This is not
// defensive padding: a v5 `rate` field is genuinely null until its second
// cycle (the plugin base keeps the field present rather than dropping it),
// so null IS a value the API sends.

const UNITS = ["B", "K", "M", "G", "T", "P"];
const MISSING = "-";

function isNumber(value) {
	return typeof value === "number" && Number.isFinite(value);
}

export function formatBytes(value) {
	if (!isNumber(value)) return MISSING;
	let n = value;
	let i = 0;
	while (n >= 1024 && i < UNITS.length - 1) {
		n /= 1024;
		i += 1;
	}
	return i === 0 ? `${Math.round(n)}${UNITS[0]}` : `${n.toFixed(1)}${UNITS[i]}`;
}

export function formatRate(value) {
	if (!isNumber(value)) return MISSING;
	return `${formatBytes(value)}/s`;
}

export function formatPercent(value) {
	if (!isNumber(value)) return MISSING;
	return `${value.toFixed(1)}%`;
}

// Counter units. Base 1024, deliberately: the TUI's _ctx_sw_value_cell()
// scales these at >= 1024 to match v4's auto_unit, and D1 makes the TUI the
// authority. Changing this to base 1000 is a TUI change first.
const COUNT_UNITS = ["", "K", "M", "G", "T", "P"];

export function formatCount(value) {
	if (!isNumber(value)) return MISSING;
	let n = value;
	let i = 0;
	while (n >= 1024 && i < COUNT_UNITS.length - 1) {
		n /= 1024;
		i += 1;
	}
	// Math.trunc, not Math.round: the TUI's _ctx_sw_value_cell()
	// (cpu/render_curses_v5.py) formats an unscaled counter with
	// `f"{int(value)}"`, which TRUNCATES. These are `rate` fields, so the
	// values are floats and an idle machine's interrupts/s sits below 1024
	// most of the time: 855.6 reads 855 on the TUI, and must here too.
	// At or above 1024 both sides go through one decimal and already agree.
	return i === 0 ? `${Math.trunc(n)}` : `${n.toFixed(1)}${COUNT_UNITS[i]}`;
}

export function toFahrenheit(celsius) {
	// glances/globals.py:205 -- the conversion only. Rendering (rounding,
	// unit letter, missing marker) belongs to the caller.
	return celsius * 1.8 + 32;
}

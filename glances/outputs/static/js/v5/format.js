// Glances v5 WebUI — value formatting.
//
// Shared by every plugin component, so the same number reads the same way
// everywhere. Pure: no DOM, no fetch, no imports (except PROCESS_COL_WIDTHS
// below, itself pure).
//
// Every function accepts null/undefined and returns "-". This is not
// defensive padding: a v5 `rate` field is genuinely null until its second
// cycle (the plugin base keeps the field present rather than dropping it),
// so null IS a value the API sends.
//
// This module holds THREE byte formatters, deliberately: `formatBytes`
// mirrors the WebUI's own rule (_auto_unit() in curses_formatters_v5.py),
// `formatAutoUnit` mirrors glances.globals.auto_unit() (what `smart` uses),
// and `formatProcessBytes` below mirrors one plugin's local renderer
// (processlist/render_curses_v5.py::_format_bytes()). Say which surface you
// mean before reaching for one.

import { PROCESS_COL_WIDTHS } from "./process_widths.js";

const UNITS = ["B", "K", "M", "G", "T", "P"];
const MISSING = "-";
const USER_WIDTH = PROCESS_COL_WIDTHS.USER;

function isNumber(value) {
	return typeof value === "number" && Number.isFinite(value);
}

// Render a value that is not a number: the value itself, or the missing
// marker. The two rules differ only on the empty string, and both exist in
// the terminal renderers -- keep them apart so a caller states which one it
// means.

// `_fmt` (vms/render_curses_v5.py): only a null renders as the placeholder,
// so a field the engine publishes as "" stays empty.
export function dashIfMissing(value) {
	return value === null || value === undefined ? MISSING : String(value);
}

// The containers/processlist/programlist rule: an empty string is a missing
// value too (an unnamed pod, a process whose command line is unreadable).
export function dashIfBlank(value) {
	return value === null || value === undefined || value === "" ? MISSING : String(value);
}

// Mirrors _auto_unit() (glances/outputs/curses_formatters_v5.py) and the
// renderers' copies of it: one decimal from 1K up, and below 1K the TUI's
// int(value) -- a truncation, not a rounding: 855.6 bytes is "855B".
// Dividing by 1024 is exact, so the tie rule below sees the true value.
function autoUnit(value, subKiloUnit, suffix) {
	let n = value;
	let i = 0;
	while (n >= 1024 && i < UNITS.length - 1) {
		n /= 1024;
		i += 1;
	}
	return i === 0 ? `${Math.trunc(n)}${subKiloUnit}${suffix}` : `${toFixedHalfEven(n, 1)}${UNITS[i]}${suffix}`;
}

export function formatBytes(value) {
	if (!isNumber(value)) return MISSING;
	return autoUnit(value, UNITS[0], "");
}

// The prefixes of v4's auto_unit(), largest first -- its
// `for symbol in reversed(symbols)` (glances/globals.py:450-471).
const AUTO_UNIT_PREFIXES = [
	["Y", 1208925819614629174706176],
	["Z", 1180591620717411303424],
	["E", 1152921504606846976],
	["P", 1125899906842624],
	["T", 1099511627776],
	["G", 1073741824],
	["M", 1048576],
	["K", 1024],
];

// Mirrors glances.globals.auto_unit() -- v4's OTHER auto-unit, the one `smart`
// uses for its LARGE_VALUE_KEYS raw values. Deliberately NOT formatBytes():
// that function mirrors _auto_unit() in curses_formatters_v5.py, and the two
// algorithms disagree on almost everything. auto_unit() takes the largest
// prefix whose quotient is > 1 (so 1G prints "1024M"), varies its precision
// with the quotient (2 decimals up to 9.995, 1 below 99.95, 0 above, and
// always 0 for K), returns "0" for zero, and below 1K formats the number
// itself with 0 decimals for an integer and 2 for a float.
// `low_precision` and the non-default min_symbol/none_symbol arguments are not
// ported: `smart` passes none of them.
export function formatAutoUnit(value) {
	if (!isNumber(value)) return MISSING;
	if (value === 0) return "0";
	// Python picks 2 decimals for a float and 0 for an int; JS has one number
	// type, so an integral value takes the int branch.
	const fallbackDecimals = Number.isInteger(value) ? 0 : 2;
	for (const [symbol, prefix] of AUTO_UNIT_PREFIXES) {
		const quotient = value / prefix;
		if (quotient > 1) {
			let decimals = 0;
			if (quotient <= 9.995) decimals = 2;
			else if (quotient < 99.95) decimals = 1;
			if (symbol === "K") decimals = 0;
			return `${toFixedHalfEven(quotient, decimals)}${symbol}`;
		}
	}
	return toFixedHalfEven(value, fallbackDecimals);
}

// Mirrors diskio/render_curses_v5.py::_format_count_rate(), the `B` key's
// IOPS mode. Counts, not bytes: 1000 is the step (not 1024) and there is no
// unit suffix. Deliberately NOT formatCount() below, which is 1024-based --
// the two surfaces must print the same string for the same number.
export function formatIops(value) {
	if (!isNumber(value)) return MISSING;
	const abs = Math.abs(value);
	for (const [symbol, threshold] of [
		["G", 1e9],
		["M", 1e6],
		["K", 1e3]
	]) {
		if (abs >= threshold) return `${(value / threshold).toFixed(1)}${symbol}`;
	}
	return String(Math.trunc(value));
}

// Mirrors network/render_curses_v5.py::_format_rate(). Bits by default --
// bytes x 8, with a `b` on every magnitude ("800b", "8.0Mb") -- and the
// plain byte count with no `b` suffix under --byte ("100", "1.0M").
// No "/s": the column header carries the per-second meaning, as in the TUI.
export function formatNetworkRate(value, byte) {
	if (!isNumber(value)) return MISSING;
	return byte ? autoUnit(value, "", "") : autoUnit(value * 8, "", "b");
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

// Mirrors npu/render_curses_v5.py::_auto_hz(): base 1000 (G/M/K), NOT
// formatAutoUnit's binary prefixes, one decimal once scaled, a plain
// truncated integer below 1K, and "?" -- not this module's usual "-" -- for
// whatever `float(hz)` cannot parse. No unit suffix: the caller appends "Hz"
// once, after joining the current/max pair.
export function formatAutoHz(value) {
	let v;
	if (typeof value === "number") v = value;
	else if (typeof value === "string" && value.trim() !== "") v = Number(value);
	else return "?";
	if (!Number.isFinite(v)) return "?";
	const abs = Math.abs(v);
	if (abs >= 1e9) return `${toFixedHalfEven(v / 1e9, 1)}G`;
	if (abs >= 1e6) return `${toFixedHalfEven(v / 1e6, 1)}M`;
	if (abs >= 1e3) return `${toFixedHalfEven(v / 1e3, 1)}K`;
	return `${Math.trunc(v)}`;
}

export function toFahrenheit(celsius) {
	// glances/globals.py:205 -- the conversion only. Rendering (rounding,
	// unit letter, missing marker) belongs to the caller.
	return celsius * 1.8 + 32;
}

// Python's float formatting, which JS does not have. f"{x:.1f}" and
// f"{x:.0f}" round the exact binary value and break an EXACT tie to the even
// digit; toFixed() rounds the same exact value but breaks a tie away from
// zero. The two differ on exact ties only: 1.25 is "1.2" in Python, "1.3" in
// JS; 42.5 is "42" and "43".
//
// A value is a tie at `digits` exactly when value * 2 ** (digits + 1) is an
// odd integer. That product is exact (a power-of-two multiply), unlike
// value * 10 ** digits: 0.15 * 10 === 1.5 in floating point, although 0.15 is
// stored below 0.15 and is no tie at all.
export function toFixedHalfEven(value, digits) {
	const scaled = value * 2 ** (digits + 1);
	if (!Number.isInteger(scaled) || Math.abs(scaled) % 2 !== 1) return value.toFixed(digits);
	// A tie: |value| * 10 ** digits is exactly k + 0.5 (a small multiple of
	// one half is representable), so floor() yields k exactly.
	let k = Math.floor(Math.abs(value) * 10 ** digits);
	if (k % 2 === 1) k += 1;
	return `${value < 0 ? "-" : ""}${(k / 10 ** digits).toFixed(digits)}`;
}

// f"{value:.0f}" -- the sensors and wifi values. Half-even on an exact tie,
// like every Python float format.
export function formatFixed0(value) {
	if (!isNumber(value)) return MISSING;
	return toFixedHalfEven(value, 0);
}

// Uptime units. Mirrors format_seconds()
// (glances/outputs/curses_formatters_v5.py:66-80) exactly -- including its
// missing marker, "" rather than this module's "-": the Python function
// catches TypeError/ValueError and returns "", and the TUI renders nothing.
export function formatSeconds(value) {
	const parsed = parseSeconds(value);
	if (!Number.isFinite(parsed)) return "";
	let secs = Math.trunc(parsed); // int(float(value))
	if (secs < 60) return `${secs}s`;
	let minutes = Math.floor(secs / 60);
	secs %= 60;
	if (minutes < 60) return `${minutes}m${pad2(secs)}s`;
	let hours = Math.floor(minutes / 60);
	minutes %= 60;
	if (hours < 24) return `${hours}h${pad2(minutes)}m`;
	const days = Math.floor(hours / 24);
	hours %= 24;
	return `${days}d${pad2(hours)}h`;
}

// float() accepts a number or a numeric string. Number("") is 0 and
// Number(null) is 0, where float() raises -- hence the explicit cases.
function parseSeconds(value) {
	if (typeof value === "number") return value;
	if (typeof value === "string" && value.trim() !== "") return Number(value);
	return Number.NaN;
}

function pad2(n) {
	return String(n).padStart(2, "0");
}

// Mirrors processlist/render_curses_v5.py::_format_cpu_time() -- the TIME+
// column: `cpu_times.user + cpu_times.system`, NOT format_seconds() above
// (a different algorithm: MM:SS below an hour, Hh{MM:SS} between 1h and
// 99h, a bare `{hours}h` past that, and this module's own "-" for a missing
// value rather than format_seconds()'s ""). Added here, not kept private to
// PluginProcesslist.vue, because `programlist` reuses this
// renderer's cell builders VERBATIM in Python
// (glances/plugins/programlist/render_curses_v5.py imports `_format_cpu_time`
// from processlist rather than redefining it) -- its WebUI component needs
// the identical formatter, and format.js is where every cross-plugin
// formatter already lives.
export function formatCpuTime(cpuTimes) {
	if (!cpuTimes || typeof cpuTimes !== "object") return MISSING;
	const user = Number(cpuTimes.user);
	const system = Number(cpuTimes.system);
	if (!Number.isFinite(user) || !Number.isFinite(system)) return MISSING;
	const total = user + system;
	if (total < 0) return MISSING;
	const totalInt = Math.trunc(total);
	const seconds = totalInt % 60;
	const totalMinutes = Math.floor(totalInt / 60);
	const minutes = totalMinutes % 60;
	const hours = Math.floor(totalMinutes / 60);
	if (hours > 99) return `${hours}h`;
	if (hours > 0) return `${hours}h${pad2(minutes)}:${pad2(seconds)}`;
	return `${minutes}:${pad2(seconds)}`;
}

// The processlist renderer's OWN byte formatter
// (glances/plugins/processlist/render_curses_v5.py:199-212), not the shared
// `formatBytes` above. It drops the decimal at 100 and over, which is what
// lets VIRT/RES fit the terminal's 5-column budget -- and this WebUI now uses
// that same budget, so it needs the same string. This is the THIRD byte
// formatter in this module: `formatBytes` mirrors the WebUI's own rule,
// `formatAutoUnit` mirrors globals.auto_unit, and this one mirrors one
// plugin's local renderer. Say which surface you mean before reaching for one.
//
// The terminal's `rjust(width)` is deliberately NOT ported: the <colgroup> and
// `text-align` do that job here, and copied padding would ship trailing spaces
// into the DOM and defeat the ellipsis.
//
// `null`/`undefined` must be checked explicitly, before `Number()`: Python's
// `float(None)` raises and is caught, returning "?" -- but `Number(null)` is
// `0`, a finite non-negative number that would silently render "0B". This
// formatter serves `_memory_info_field()` (render_curses_v5.py:217-221),
// which returns `None` whenever `memory_info` is missing or not a dict (an
// access-denied process, for one), so a false "0B" is a live, reachable case,
// not a defensive guard against input that cannot occur.
export function formatProcessBytes(value) {
	if (value === null || value === undefined) return "?";
	const n = Number(value);
	if (!Number.isFinite(n) || n < 0) return "?";
	for (const [suffix, scale] of [
		["T", 1024 ** 4],
		["G", 1024 ** 3],
		["M", 1024 ** 2],
		["K", 1024],
	]) {
		if (n >= scale) {
			const v = n / scale;
			// toFixedHalfEven, not toFixed: v = n / scale with scale a power of
			// two and n an integer byte count from psutil, so exact binary ties
			// (every multiple of scale / 4) are ordinary input, not an edge
			// case -- and toFixed() breaks a tie away from zero where Python's
			// f"{v:.1f}" breaks it to even.
			return v < 100 ? `${toFixedHalfEven(v, 1)}${suffix}` : `${Math.trunc(v)}${suffix}`;
		}
	}
	return `${Math.trunc(n)}B`;
}

// `_format_username` (processlist/render_curses_v5.py:158-162). The boundary is
// off by one from the obvious reading: the crop fires only when the name is
// LONGER than the column, so a 10-character name is shown whole and an
// 11-character one becomes its first 9 plus `+`. The terminal's trailing
// `ljust` is not ported, for the same reason as above.
export function formatUsername(value) {
	const text = value === null || value === undefined ? "?" : String(value);
	return text.length > USER_WIDTH ? `${text.slice(0, USER_WIDTH - 1)}+` : text;
}

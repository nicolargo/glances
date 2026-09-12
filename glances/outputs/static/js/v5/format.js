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

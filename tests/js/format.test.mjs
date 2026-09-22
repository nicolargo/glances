import { test } from "node:test";
import assert from "node:assert/strict";
import {
	formatAutoHz,
	formatAutoUnit,
	formatBytes,
	formatCount,
	formatFixed0,
	formatIops,
	formatNetworkRate,
	formatPercent,
	formatProcessBytes,
	formatRate,
	formatSeconds,
	formatUsername,
	toFahrenheit,
	toFixedHalfEven
} from "../../glances/outputs/static/js/v5/format.js";

test("formatBytes uses binary units", () => {
	assert.equal(formatBytes(0), "0B");
	assert.equal(formatBytes(1023), "1023B");
	assert.equal(formatBytes(1024), "1.0K");
	assert.equal(formatBytes(16417853440), "15.3G");
});

test("formatBytes survives what the API can actually send", () => {
	// A rate field is null until its second cycle -- see the v5 base plugin.
	assert.equal(formatBytes(null), "-");
	assert.equal(formatBytes(undefined), "-");
});

test("formatRate marks per-second values", () => {
	assert.equal(formatRate(1024), "1.0K/s");
	assert.equal(formatRate(null), "-");
});

test("formatPercent keeps one decimal", () => {
	assert.equal(formatPercent(52.5), "52.5%");
	assert.equal(formatPercent(0), "0.0%");
	assert.equal(formatPercent(null), "-");
});

test("formatCount is a plain integer below 1024 and K-scaled at or above it", () => {
	// The TUI is the authority here: _ctx_sw_value_cell()
	// (glances/plugins/cpu/render_curses_v5.py:52-70) scales at >= 1024, not
	// >= 1000, matching v4's auto_unit. Counting in powers of two is odd, but
	// the two outputs agreeing matters more than either being tidy.
	assert.equal(formatCount(0), "0");
	assert.equal(formatCount(42), "42");
	assert.equal(formatCount(1023), "1023");
	assert.equal(formatCount(1024), "1.0K");
	assert.equal(formatCount(6860), "6.7K");
	assert.equal(formatCount(1048576), "1.0M");
});

test("formatCount truncates below 1024, like the TUI's int()", () => {
	// These fields are `rate`s, so the values are floats, and an idle
	// machine's interrupts/s is routinely under 1024 -- i.e. this is the
	// common path, not an edge case. `_ctx_sw_value_cell()`
	// (glances/plugins/cpu/render_curses_v5.py) formats an unscaled counter
	// with `f"{int(value)}"`, which truncates: 855.6 reads 855 there, so
	// Math.round would have shown 856 in the browser for the same tick.
	assert.equal(formatCount(855.6), "855");
	assert.equal(formatCount(1023.9), "1023");
	// At or above 1024 both sides go through one decimal and already agree.
	assert.equal(formatCount(1024.9), "1.0K");
});

test("formatCount returns the missing marker for a non-number", () => {
	// `rate` fields are null until their second cycle -- null IS a value the
	// API sends, so this is a live path, not defensive padding.
	assert.equal(formatCount(null), "-");
	assert.equal(formatCount(undefined), "-");
	assert.equal(formatCount("12"), "-");
});

test("toFahrenheit mirrors glances.globals.to_fahrenheit", () => {
	// celsius * 1.8 + 32, and nothing else -- no rounding, no unit. The
	// caller decides how to render, because gpu's missing marker is "N/A"
	// while every other v5 formatter uses "-".
	assert.equal(toFahrenheit(0), 32);
	assert.equal(toFahrenheit(100), 212);
	assert.equal(toFahrenheit(55), 131);
});

test("formatSeconds mirrors the TUI's format_seconds exactly", () => {
	// glances/outputs/curses_formatters_v5.py:66-80. Each boundary on both
	// sides: the unit changes at 60, 3600 and 86400.
	assert.equal(formatSeconds(0), "0s");
	assert.equal(formatSeconds(59), "59s");
	assert.equal(formatSeconds(60), "1m00s");
	assert.equal(formatSeconds(3599), "59m59s");
	assert.equal(formatSeconds(3600), "1h00m");
	assert.equal(formatSeconds(86399), "23h59m");
	assert.equal(formatSeconds(86400), "1d00h");
	assert.equal(formatSeconds(273600), "3d04h");
});

test("formatSeconds truncates like int(float(value))", () => {
	assert.equal(formatSeconds(61.9), "1m01s");
	assert.equal(formatSeconds("61.9"), "1m01s");
});

test("formatSeconds returns the TUI's empty string for what it cannot parse", () => {
	// NOT this module's "-": format_seconds() catches TypeError/ValueError and
	// returns "", and the TUI then renders nothing.
	assert.equal(formatSeconds(null), "");
	assert.equal(formatSeconds(undefined), "");
	assert.equal(formatSeconds(""), "");
	assert.equal(formatSeconds("abc"), "");
});

test("toFixedHalfEven matches CPython's float formatting, exact ties included", () => {
	// Expected strings are CPython's f"{value:.{digits}f}". JS toFixed agrees
	// everywhere except on an EXACT tie, which it rounds away from zero.
	const cases = [
		[0.15, 1, "0.1"], // stored as 0.1499999..., no tie -- a detector using value * 10 would call it one
		[1.25, 1, "1.2"],
		[1.35, 1, "1.4"], // stored above 1.35, no tie
		[0.75, 1, "0.8"],
		[42.5, 0, "42"],
		[43.5, 0, "44"],
		[0.5, 0, "0"],
		[-54.5, 0, "-54"],
		[-54.4, 0, "-54"],
		[108.5, 0, "108"], // 42.5 C in Fahrenheit: 42.5 * 1.8 + 32 is exactly 108.5
	];
	for (const [value, digits, expected] of cases) {
		assert.equal(toFixedHalfEven(value, digits), expected, `${value} at ${digits} digit(s)`);
	}
});

test("formatBytes truncates below 1K like the TUI's int()", () => {
	// _auto_unit() in curses_formatters_v5.py prints int(value) below 1024.
	assert.equal(formatBytes(855.6), "855B");
	assert.equal(formatBytes(1023.9), "1023B");
});

test("formatBytes breaks an exact one-decimal tie to even, like the TUI", () => {
	assert.equal(formatBytes(1280), "1.2K"); // 1.25K exactly
	assert.equal(formatBytes(1792), "1.8K"); // 1.75K exactly
});

test("formatRate inherits the TUI's sub-K truncation", () => {
	assert.equal(formatRate(855.6), "855B/s"); // format_bytespers(855.6)
});

test("formatNetworkRate mirrors network's _format_rate: bits, or bytes under --byte", () => {
	assert.equal(formatNetworkRate(100, false), "800b");
	assert.equal(formatNetworkRate(1048576, false), "8.0Mb");
	assert.equal(formatNetworkRate(524288, false), "4.0Mb");
	assert.equal(formatNetworkRate(100, true), "100");
	assert.equal(formatNetworkRate(1048576, true), "1.0M");
	assert.equal(formatNetworkRate(524288, true), "512.0K");
	assert.equal(formatNetworkRate(null, false), "-");
	assert.equal(formatNetworkRate(null, true), "-");
});

test("formatFixed0 is Python's :.0f, and the usual missing marker", () => {
	assert.equal(formatFixed0(42.5), "42");
	assert.equal(formatFixed0(-71.2), "-71");
	assert.equal(formatFixed0(1200), "1200");
	assert.equal(formatFixed0(null), "-");
	assert.equal(formatFixed0("ERR"), "-");
});

// The cases are auto_unit()'s own docstring (glances/globals.py:431-447) --
// the one place the v4 algorithm is specified by example.
test("formatAutoUnit mirrors v4 auto_unit", () => {
	assert.equal(formatAutoUnit(613421788), "585M");
	assert.equal(formatAutoUnit(5307033647), "4.94G");
	assert.equal(formatAutoUnit(44968414685), "41.9G");
	assert.equal(formatAutoUnit(838471403472), "781G");
	assert.equal(formatAutoUnit(9683209690677), "8.81T");
	// A quotient of exactly 1024 stays in the smaller unit: the loop takes the
	// largest prefix whose quotient is > 1, so 1G is "1024M", not "1.0G".
	assert.equal(formatAutoUnit(1073741824), "1024M");
	// The trailing zero is part of the contract: a fixed-decimal string, never
	// a Number round-trip that would print "1.1G".
	assert.equal(formatAutoUnit(1181116006), "1.10G");
});

test("formatAutoUnit below 1K, at zero and on a missing value", () => {
	// Python: `if number == 0: return '0'` -- before any division.
	assert.equal(formatAutoUnit(0), "0");
	// No prefix quotient is > 1, so the fallthrough formats the number itself:
	// 0 decimals for an integer, 2 for a float (Python's isinstance check).
	assert.equal(formatAutoUnit(500), "500");
	assert.equal(formatAutoUnit(500.5), "500.50");
	assert.equal(formatAutoUnit(1024), "1024");
	assert.equal(formatAutoUnit(null), "-");
	assert.equal(formatAutoUnit(undefined), "-");
});

// Mirrors npu/render_curses_v5.py::_auto_hz() -- base 1000, one decimal once
// scaled, a plain truncated integer below 1K.
test("formatAutoHz mirrors npu's _auto_hz: base 1000, one decimal", () => {
	assert.equal(formatAutoHz(1000000000), "1.0G");
	assert.equal(formatAutoHz(2000000000), "2.0G");
	assert.equal(formatAutoHz(1500000000), "1.5G");
	assert.equal(formatAutoHz(1000000), "1.0M");
	assert.equal(formatAutoHz(1000), "1.0K");
	assert.equal(formatAutoHz(999), "999");
	assert.equal(formatAutoHz(0), "0");
});

// Mirrors processlist/render_curses_v5.py::_format_username() -- the boundary
// is off by one from the obvious reading: the crop fires only when the name
// is LONGER than the column, so a name AT the width is shown whole.
test("a name at the width is shown whole; one past it crops", () => {
	assert.equal(formatUsername("0123456789"), "0123456789");
	assert.equal(formatUsername("01234567890"), "012345678+");
	assert.equal(formatUsername(null), "?");
});

// Mirrors processlist/render_curses_v5.py::_format_bytes() -- the terminal's
// OWN byte formatter (distinct from formatBytes/formatAutoUnit above).
test("formatProcessBytes keeps the decimal below 100 and drops it at 100", () => {
	assert.equal(formatProcessBytes(99.4 * 1024 ** 3), "99.4G");
	assert.equal(formatProcessBytes(100 * 1024 ** 3), "100G");
});

test("formatProcessBytes: sub-kilobyte values are plain bytes, bad values are a question mark", () => {
	assert.equal(formatProcessBytes(512), "512B");
	assert.equal(formatProcessBytes(-1), "?");
	assert.equal(formatProcessBytes("nope"), "?");
});

// _memory_info_field() (render_curses_v5.py:217-221) returns None whenever
// memory_info is missing or not a dict -- an access-denied process, for one
// -- and that None reaches _format_bytes directly. Python's float(None)
// raises and is caught, returning "?"; Number(null) is 0, so an unguarded
// port would render a false "0B" for an unreadable process instead of the
// terminal's honest "unknown".
test("formatProcessBytes treats null/undefined as unreadable, not zero", () => {
	assert.equal(formatProcessBytes(null), "?");
	assert.equal(formatProcessBytes(undefined), "?");
});

// v = n / scale with scale a power of two and n an integer byte count from
// psutil, so an exact one-decimal tie (v * 4 an odd integer, i.e. v's
// fractional part is exactly .25 or .75) is ordinary input. toFixed() breaks
// such a tie away from zero; Python's f"{v:.1f}" breaks it to even -- see
// toFixedHalfEven's own tests above for the general rule.
//
// Both values below were run through the real
// processlist._format_bytes()/_memory_info_field() path, not derived by
// reasoning: 1280 -> ' 1.2K' (a K-scale tie), and 8858370048 (= 8.25 *
// 1024**3, confirmed exact via `int(8.25 * 1024**3) == 8.25 * 1024**3`) ->
// ' 8.2G' (a G-scale tie, chosen at a different magnitude than the K case).
// Node's `(1280/1024).toFixed(1)` gives "1.3" and
// `(8858370048/1024**3).toFixed(1)` gives "8.3" -- both wrong without the
// half-even fix.
test("formatProcessBytes breaks an exact one-decimal tie to even, like the terminal", () => {
	assert.equal(formatProcessBytes(1280), "1.2K");
	assert.equal(formatProcessBytes(8858370048), "8.2G");
});

test("neither formatter pads -- the colgroup does that job", () => {
	assert.equal(formatProcessBytes(512), formatProcessBytes(512).trim());
	assert.equal(formatUsername("ab"), "ab");
});

test("formatAutoHz accepts a numeric string, like Python's float()", () => {
	assert.equal(formatAutoHz("1"), "1");
	assert.equal(formatAutoHz("2000000000"), "2.0G");
});

test('formatAutoHz returns "?" for whatever it cannot parse', () => {
	// _auto_hz() catches TypeError/ValueError from float(hz) and returns "?" --
	// NOT this module's usual "-" missing marker.
	assert.equal(formatAutoHz(null), "?");
	assert.equal(formatAutoHz(undefined), "?");
	assert.equal(formatAutoHz("abc"), "?");
	assert.equal(formatAutoHz(""), "?");
	assert.equal(formatAutoHz(NaN), "?");
});

test("formatIops mirrors the TUI's _format_count_rate: 1000-step, unitless", () => {
	// Deliberately NOT formatCount's 1024 step -- the two surfaces must print
	// the same string for the same number.
	assert.equal(formatIops(0), "0");
	assert.equal(formatIops(7.4), "7");
	assert.equal(formatIops(999), "999");
	assert.equal(formatIops(1000), "1.0K");
	assert.equal(formatIops(2500), "2.5K");
	assert.equal(formatIops(1e6), "1.0M");
	assert.equal(formatIops(1e9), "1.0G");
	assert.equal(formatIops(null), "-");
	assert.equal(formatIops(undefined), "-");
});

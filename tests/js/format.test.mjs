import { test } from "node:test";
import assert from "node:assert/strict";
import { formatBytes, formatRate, formatPercent, formatCount, toFahrenheit } from "../../glances/outputs/static/js/v5/format.js";

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

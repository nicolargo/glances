import { test } from "node:test";
import assert from "node:assert/strict";
import { formatBytes, formatRate, formatPercent } from "../../glances/outputs/static/js/v5/format.js";

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

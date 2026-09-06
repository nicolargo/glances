import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { resolveLabels, labelFor } from "../../glances/outputs/static/js/v5/labels.js";

beforeEach(() => {
	delete globalThis.fetch;
});

function stubInfo(body, ok = true) {
	globalThis.fetch = async () => ({ ok, status: ok ? 200 : 500, json: async () => body });
}

test("short_name wins over label, which wins over the field name", () => {
	const labels = { a: "SN", b: "Label", c: undefined };
	assert.equal(labelFor(labels, "a"), "SN");
	assert.equal(labelFor(labels, "b"), "Label");
	assert.equal(labelFor(labels, "c"), "c");
	assert.equal(labelFor(labels, "missing"), "missing");
});

test("resolveLabels applies the field_label precedence", async () => {
	// Mirrors glances/outputs/curses_renderer_v5.py:243 field_label():
	// short_name -> label -> field name. Reproducing it means a label improved
	// in the schema improves the TUI and the WebUI at once.
	stubInfo({
		total: { short_name: "total", label: "Total memory" },
		available: { label: "avail" },
		buffers: {},
	});
	const labels = await resolveLabels("mem");
	assert.equal(labels.total, "total");
	assert.equal(labels.available, "avail");
	assert.equal(labelFor(labels, "buffers"), "buffers");
});

test("an unreachable /info degrades to field names, never to blank", async () => {
	// A distinct plugin name from the precedence test above: resolveLabels
	// caches by name, so reusing "mem" here would return the previous
	// test's cached (successful) result instead of exercising this stub.
	globalThis.fetch = async () => {
		throw new TypeError("network error");
	};
	const labels = await resolveLabels("unreachable");
	assert.deepEqual(labels, {});
	assert.equal(labelFor(labels, "total"), "total");
});

test("resolveLabels fetches once per plugin and caches", async () => {
	let calls = 0;
	globalThis.fetch = async () => {
		calls += 1;
		return { ok: true, status: 200, json: async () => ({ x: { label: "X" } }) };
	};
	await resolveLabels("cachetest");
	await resolveLabels("cachetest");
	assert.equal(calls, 1);
});

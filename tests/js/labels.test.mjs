import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { resolveAllLabels, labelFor } from "../../glances/outputs/static/js/v5/labels.js";

beforeEach(() => {
	delete globalThis.fetch;
});

test("short_name wins over label, which wins over the field name", () => {
	const labels = { a: "SN", b: "Label", c: undefined };
	assert.equal(labelFor(labels, "a"), "SN");
	assert.equal(labelFor(labels, "b"), "Label");
	assert.equal(labelFor(labels, "c"), "c");
	assert.equal(labelFor(labels, "missing"), "missing");
});

test("resolveAllLabels applies the field_label precedence per plugin, in one fetch", async () => {
	const paths = [];
	globalThis.fetch = async (path) => {
		paths.push(path);
		return {
			ok: true,
			status: 200,
			json: async () => ({
				mem: { total: { short_name: "total", label: "Total memory" }, available: { label: "avail" }, buffers: {} },
				network: { bytes_recv: { short_name: "Rx/s" } },
			}),
		};
	};
	const labels = await resolveAllLabels();
	// ONE request whatever the number of plugins -- the point of the batch.
	assert.deepEqual(paths, ["api/5/all/info"]);
	assert.equal(labels.mem.total, "total");
	assert.equal(labels.mem.available, "avail");
	assert.equal(labelFor(labels.mem, "buffers"), "buffers");
	assert.equal(labels.network.bytes_recv, "Rx/s");
});

test("an unreachable /all/info degrades to field names for every plugin", async () => {
	globalThis.fetch = async () => ({ ok: false, status: 500, json: async () => ({ detail: "boom" }) });
	const labels = await resolveAllLabels();
	assert.deepEqual(labels, {});
	assert.equal(labelFor(labels.mem, "total"), "total");
});

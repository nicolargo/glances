import { test } from "node:test";
import assert from "node:assert/strict";
import { cellClassFor } from "../../glances/outputs/static/js/v5/columns.js";

const PAYLOAD = {
	_key: "interface_name",
	data: [{ interface_name: "eth0", bytes_recv: 10 }],
	_levels: { eth0: { bytes_recv: { level: "warning", prominent: true } } },
};

test("the tier class is resolved through the payload's _key", () => {
	const item = PAYLOAD.data[0];
	assert.equal(cellClassFor(PAYLOAD, item, "bytes_recv"), "gl-level-warning gl-prominent");
	assert.equal(cellClassFor(PAYLOAD, item, "interface_name"), "");
});

test("a payload without _key yields no class rather than throwing", () => {
	// An older server does not publish _key. A component must still render.
	const legacy = { data: PAYLOAD.data, _levels: PAYLOAD._levels };
	assert.equal(cellClassFor(legacy, legacy.data[0], "bytes_recv"), "");
});

test("an item whose key value has no _levels entry yields no class", () => {
	const item = { interface_name: "lo", bytes_recv: 0 };
	assert.equal(cellClassFor(PAYLOAD, item, "bytes_recv"), "");
});

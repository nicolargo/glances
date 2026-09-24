import { test } from "node:test";
import assert from "node:assert/strict";
import { levelClass, scalarLevel, itemLevel, computeLevel } from "../../glances/outputs/static/js/v5/levels.js";

const SCALAR = { percent: 52.5, _levels: { percent: { level: "careful", prominent: true } } };
const COLLECTION = {
	data: [{ interface_name: "eth0", errors_in: 0 }],
	_levels: { eth0: { errors_in: { level: "ok", prominent: false } } },
};

test("each tier maps to its class", () => {
	for (const tier of ["ok", "careful", "warning", "critical"]) {
		assert.equal(levelClass({ level: tier }), `gl-level-${tier}`);
	}
});

test("prominent adds a background class, not a different colour", () => {
	assert.equal(levelClass({ level: "critical", prominent: true }), "gl-level-critical gl-prominent");
});

test("an unknown or missing tier yields no class", () => {
	assert.equal(levelClass(null), "");
	assert.equal(levelClass(undefined), "");
	assert.equal(levelClass({ level: "bogus" }), "");
	assert.equal(levelClass({}), "");
});

test("scalarLevel reads _levels[field]", () => {
	assert.deepEqual(scalarLevel(SCALAR, "percent"), { level: "careful", prominent: true });
	assert.equal(scalarLevel(SCALAR, "total"), null);
	assert.equal(scalarLevel({}, "percent"), null);
});

test("itemLevel reads _levels[primaryKeyValue][field]", () => {
	assert.deepEqual(itemLevel(COLLECTION, "eth0", "errors_in"), { level: "ok", prominent: false });
	assert.equal(itemLevel(COLLECTION, "eth0", "bytes_recv"), null);
	assert.equal(itemLevel(COLLECTION, "lo", "errors_in"), null);
});

test("levels.js exports exactly its intended surface", async () => {
	// The TUI signals an alert on the VALUE only
	// (glances/outputs/curses_renderer_v5.py:126-129). The rule is enforced by
	// there being no API to break it -- so the export surface is asserted, not
	// asserted-about. A previous version of this test checked globalThis,
	// which ES module exports never populate: it passed even with a real
	// `export function headerClass` present.
	const mod = await import("../../glances/outputs/static/js/v5/levels.js");
	assert.deepEqual(Object.keys(mod).sort(), ["computeLevel", "itemLevel", "levelClass", "scalarLevel"]);
});

test("computeLevel grades most severe first, `>=` inclusive (compute_level port)", () => {
	const limits = { careful: 50, warning: 70, critical: 90 };
	assert.deepEqual(computeLevel(10, limits), { level: "ok", prominent: false });
	assert.deepEqual(computeLevel(50, limits), { level: "careful", prominent: false });
	assert.deepEqual(computeLevel(75, limits), { level: "warning", prominent: false });
	assert.deepEqual(computeLevel(95, limits), { level: "critical", prominent: false });
	// A partial ladder grades on what is configured.
	assert.deepEqual(computeLevel(25, { critical: 20 }), { level: "critical", prominent: false });
	assert.deepEqual(computeLevel(5, { critical: 20 }), { level: "ok", prominent: false });
});

test("computeLevel has nothing to grade without limits or a number", () => {
	assert.equal(computeLevel(80, undefined), null);
	assert.equal(computeLevel(80, {}), null);
	assert.equal(computeLevel(undefined, { careful: 50 }), null);
});

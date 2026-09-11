import { test } from "node:test";
import assert from "node:assert/strict";
import { visiblePlugins, groupBySlot } from "../../glances/outputs/static/js/v5/layout.js";

const REGISTRY = [
	{ name: "system", slot: "header-left" },
	{ name: "uptime", slot: "header-right" },
	{ name: "cloud", slot: "header-right" },
	{ name: "now", slot: "header-right" },
	{ name: "cpu", slot: "top" },
	{ name: "network", slot: "left" },
];

test("visiblePlugins keeps only what the server instantiated, in registry order", () => {
	// pluginslist is SORTED server-side; the registry order must win, or the
	// page would lay out alphabetically.
	const names = ["cloud", "cpu", "network", "now", "system", "uptime"].filter((n) => n !== "cloud");
	assert.deepEqual(
		visiblePlugins(REGISTRY, names).map((e) => e.name),
		["system", "uptime", "now", "cpu", "network"],
	);
});

test("visiblePlugins ignores a server plugin the registry has no component for", () => {
	assert.deepEqual(
		visiblePlugins(REGISTRY, ["cpu", "processlist"]).map((e) => e.name),
		["cpu"],
	);
});

test("an unreadable pluginslist renders the whole registry", () => {
	// null is what resolvePluginNames() returns on failure. Falling back to
	// the full registry is exactly the behaviour before visibility existed.
	assert.equal(visiblePlugins(REGISTRY, null), REGISTRY);
	assert.equal(visiblePlugins(REGISTRY, { detail: "nope" }), REGISTRY);
});

test("groupBySlot keeps registry order inside a slot and omits unused slots", () => {
	const slots = groupBySlot(REGISTRY);
	assert.deepEqual(Object.keys(slots).sort(), ["header-left", "header-right", "left", "top"]);
	assert.deepEqual(slots["header-right"].map((e) => e.name), ["uptime", "cloud", "now"]);
	assert.equal(slots.right, undefined);
});

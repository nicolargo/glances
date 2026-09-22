import assert from "node:assert/strict";
import test from "node:test";

import { HIDE_KEYS, HIDE_SLOT_KEYS, hideTargets, toggleHidden, helpRows } from "../../glances/outputs/static/js/v5/hotkeys.js";

// A registry shaped like `AppShell.plugins`: name + slot is all hideTargets reads.
const REGISTRY = [
	{ name: "system", slot: "header-left" },
	{ name: "quicklook", slot: "top" },
	{ name: "cpu", slot: "top" },
	{ name: "network", slot: "left" },
	{ name: "diskio", slot: "left" },
	{ name: "processlist", slot: "right" },
];

test("a plain key names its own plugin", () => {
	assert.deepEqual(hideTargets("n", REGISTRY), ["network"]);
	assert.deepEqual(hideTargets("G", REGISTRY), ["gpu"]);
});

test("a compound key names every plugin it reaches", () => {
	assert.deepEqual(hideTargets("f", REGISTRY), ["fs", "folders"]);
	assert.deepEqual(hideTargets("z", REGISTRY), ["processlist", "programlist", "processcount"]);
});

test("a slot key resolves against the live registry, not a second list", () => {
	assert.deepEqual(hideTargets("2", REGISTRY), ["network", "diskio"]);
	assert.deepEqual(hideTargets("5", REGISTRY), ["quicklook", "cpu"]);
});

test("a slot key covers only registered plugins", () => {
	// A server that disables the whole sidebar leaves `2` with nothing to do --
	// it must not name plugins the page never renders.
	assert.deepEqual(hideTargets("2", [{ name: "cpu", slot: "top" }]), []);
});

test("an unbound key is null, not an empty list", () => {
	// The caller distinguishes them: null means "not ours, let the browser have
	// it", [] means "ours, but nothing to hide".
	assert.equal(hideTargets("y", REGISTRY), null);
	assert.equal(hideTargets("h", REGISTRY), null, "help is handled before hideTargets");
});

test("toggling adds then removes the same names", () => {
	let hidden = new Set();
	hidden = toggleHidden(hidden, ["network"]);
	assert.deepEqual([...hidden], ["network"]);
	hidden = toggleHidden(hidden, ["network"]);
	assert.deepEqual([...hidden], []);
});

test("a compound key never lands half-hidden", () => {
	// Start from a half state: folders hidden on its own, fs visible. The tuple
	// flips as a unit, keyed on its FIRST member -- the TUI's rule
	// (glances_curses_v5._handle_key).
	let hidden = new Set(["folders"]);
	hidden = toggleHidden(hidden, ["fs", "folders"]);
	assert.deepEqual([...hidden].sort(), ["folders", "fs"]);
	hidden = toggleHidden(hidden, ["fs", "folders"]);
	assert.deepEqual([...hidden], []);
});

test("toggling returns a new Set and leaves the input alone", () => {
	// Vue re-renders on reassignment; mutating in place would not repaint.
	const before = new Set(["network"]);
	const after = toggleHidden(before, ["diskio"]);
	assert.notEqual(before, after);
	assert.deepEqual([...before], ["network"]);
});

test("an empty target list is a no-op", () => {
	const hidden = new Set(["network"]);
	assert.deepEqual([...toggleHidden(hidden, [])], ["network"]);
});

test("every bound key is documented, and nothing else is", () => {
	const documented = helpRows().map((row) => row.key).sort();
	const bound = [...Object.keys(HIDE_KEYS), ...Object.keys(HIDE_SLOT_KEYS)].sort();
	assert.deepEqual(documented, bound);
	assert.equal(bound.length, 24);
	for (const row of helpRows()) assert.ok(row.desc, `${row.key} has no description`);
});

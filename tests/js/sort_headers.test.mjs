import assert from "node:assert/strict";
import test from "node:test";

import {
	CONTAINERS_HEADER_SORT_KEY,
	sortHeaderAttrs,
} from "../../glances/outputs/static/js/v5/sort_headers.js";
import { HEADER_SORT_KEY } from "../../glances/outputs/static/js/v5/process_shared.js";

test("the live sort column is underlined, and only it", () => {
	assert.equal(sortHeaderAttrs(HEADER_SORT_KEY, "cpu_percent", "CPU%").class["gl-sorted"], true);
	assert.equal(sortHeaderAttrs(HEADER_SORT_KEY, "cpu_percent", "MEM%").class["gl-sorted"], false);
	assert.equal(sortHeaderAttrs(HEADER_SORT_KEY, null, "CPU%").class["gl-sorted"], false);
});

test("a header with an engine key is clickable and titled", () => {
	const attrs = sortHeaderAttrs(CONTAINERS_HEADER_SORT_KEY, "cpu_percent", "MEM");
	assert.equal(attrs.class["gl-sortable"], true);
	assert.equal(attrs.title, "Sort by MEM");
	assert.equal(typeof attrs.onClick, "function");
});

test("a header with no engine key stays inert", () => {
	const attrs = sortHeaderAttrs(HEADER_SORT_KEY, "cpu_percent", "VIRT");
	assert.deepEqual(attrs, { class: { "gl-sorted": false, "gl-sortable": false } });
});

test("a hint is kept, after the sort title", () => {
	const attrs = sortHeaderAttrs(HEADER_SORT_KEY, "name", "Command", "Click a process to pin it.");
	assert.equal(attrs.title, "Sort by Command. Click a process to pin it.");
	assert.equal(attrs.class["gl-sorted"], true);
});

test("a click POSTs the column's engine key to the sort route", async () => {
	const calls = [];
	globalThis.fetch = async (path, init) => {
		calls.push([path, init && init.method]);
		return { ok: true, status: 200, json: async () => true };
	};
	try {
		await sortHeaderAttrs(CONTAINERS_HEADER_SORT_KEY, null, "CONTAINER").onClick();
	} finally {
		delete globalThis.fetch;
	}
	assert.deepEqual(calls, [["api/5/processes/sort/name", "POST"]]);
});

test("a refused sort does not throw into the click handler", async () => {
	globalThis.fetch = async () => ({ ok: false, status: 400, json: async () => ({}) });
	try {
		await sortHeaderAttrs(HEADER_SORT_KEY, null, "CPU%").onClick();
	} finally {
		delete globalThis.fetch;
	}
});

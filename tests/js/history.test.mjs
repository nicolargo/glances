import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { fetchSeries, resolveHistoryFields } from "../../glances/outputs/static/js/history.js";

const ok = (body) => ({ ok: true, status: 200, json: async () => body });

beforeEach(() => {
	delete globalThis.fetch;
});

test("only the fields flagged history in the schema are resolved, with their unit", async () => {
	globalThis.fetch = async (path) =>
		ok(
			path === "status"
				? { history: true }
				: { cpu: { user: { history: true, unit: "percent" }, total: { unit: "percent" } }, ip: { address: {} } },
		);
	assert.deepEqual(await resolveHistoryFields(), { cpu: { user: "percent" } });
});

test("no field is clickable when the server keeps no history", async () => {
	globalThis.fetch = async (path) => ok(path === "status" ? { history: false } : { cpu: { user: { history: true } } });
	assert.deepEqual(await resolveHistoryFields(), {});
});

test("an unreachable /status means no history, not an error", async () => {
	globalThis.fetch = async () => ({ ok: false, status: 500, json: async () => ({}) });
	assert.deepEqual(await resolveHistoryFields(), {});
});

test("a scalar series is zipped with the time axis, gaps kept", async () => {
	let url;
	globalThis.fetch = async (path) => {
		url = path;
		return ok({ timestamps: [1, 2, 3], series: { user: [null, 4, 5] } });
	};
	assert.deepEqual(await fetchSeries({ plugin: "cpu", field: "user" }), [
		{ t: 1, v: null },
		{ t: 2, v: 4 },
		{ t: 3, v: 5 },
	]);
	assert.equal(url, "api/5/cpu/history?field=user");
});

test("a collection series is read under its item, which may be a path", async () => {
	let url;
	globalThis.fetch = async (path) => {
		url = path;
		return ok({ timestamps: [1], series: { percent: { "/home": [42] } } });
	};
	assert.deepEqual(await fetchSeries({ plugin: "fs", field: "percent", item: "/home" }), [{ t: 1, v: 42 }]);
	assert.equal(url, "api/5/fs/history?field=percent&item=%2Fhome");
});

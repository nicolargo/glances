import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
	getJson,
	validate,
	resolveConfig,
	resolveArgs,
	resolvePluginNames,
	resolveVersion,
	fetchAll,
	DEFAULT_REFRESH_SECONDS,
	DEFAULT_THEME,
	DEFAULT_API_DOC,
} from "../../glances/outputs/static/js/v5/api.js";

function stubFetch(routes) {
	globalThis.fetch = async (path) => {
		const r = routes[path];
		if (!r) throw new TypeError("network error");
		return {
			ok: r.status === undefined || (r.status >= 200 && r.status < 300),
			status: r.status ?? 200,
			json: async () => r.body,
		};
	};
}

beforeEach(() => {
	delete globalThis.fetch;
});

test("getJson returns the parsed body on 200", async () => {
	stubFetch({ "api/5/mem": { body: { percent: 1 } } });
	assert.deepEqual(await getJson("api/5/mem"), { percent: 1 });
});

test("getJson throws with the path and status on a non-OK response", async () => {
	stubFetch({ "api/5/mem": { status: 500, body: { detail: "boom" } } });
	await assert.rejects(() => getJson("api/5/mem"), /api\/5\/mem: HTTP 500/);
});

test("validate rejects a 200 carrying the wrong shape", () => {
	// The failure that started this: fetch does not reject on 4xx/5xx, and a
	// FastAPI error body is valid JSON. Without a shape check it renders as
	// data -- G9-1's page reported a plausible, wrong plugin count.
	const spec = { shape: "scalar", required: ["percent", "total"] };
	assert.throws(() => validate({ detail: "boom" }, spec), /missing|shape/i);
});

test("validate accepts a well-formed scalar payload", () => {
	const spec = { shape: "scalar", required: ["percent"] };
	const payload = { percent: 52.5, _levels: {} };
	assert.equal(validate(payload, spec), payload);
});

test("validate requires a data array for a collection", () => {
	const spec = { shape: "collection", required: ["interface_name"] };
	assert.throws(() => validate({ detail: "boom" }, spec), /shape/i);
	assert.throws(() => validate({ data: {} }, spec), /shape/i);
	const ok = { data: [{ interface_name: "eth0" }] };
	assert.equal(validate(ok, spec), ok);
});

test("validate accepts an empty collection", () => {
	// A plugin with nothing to show (no container running) is not an error.
	const spec = { shape: "collection", required: ["interface_name"] };
	const ok = { data: [] };
	assert.equal(validate(ok, spec), ok);
});

test("validate passes a cycle-0 null through untouched", () => {
	// /api/5/<plugin> answers `200 null` before the first cycle (G9-1
	// contract). That is a loading state, not a shape error.
	const spec = { shape: "scalar", required: ["percent"] };
	assert.equal(validate(null, spec), null);
});




test("resolveConfig reads [global] refresh and [outputs] theme from one fetch", async () => {
	stubFetch({ "api/5/config": { body: { global: { refresh: 5 }, outputs: { theme: "light" } } } });
	assert.deepEqual(await resolveConfig(), {
		refreshSeconds: 5,
		theme: "light",
		maxProcessesDisplay: null,
		apiDoc: DEFAULT_API_DOC,
	});
});

test("resolveConfig falls back to defaults when config is unreachable", async () => {
	stubFetch({});
	assert.deepEqual(await resolveConfig(), {
		refreshSeconds: DEFAULT_REFRESH_SECONDS,
		theme: DEFAULT_THEME,
		maxProcessesDisplay: null,
		apiDoc: DEFAULT_API_DOC,
	});
});

// Fix round 1, IMPORTANT 1: `[outputs] max_processes_display` is resolved
// from this SAME /api/5/config fetch (not a second one from
// PluginProcesslist.vue), the same way refresh/theme already are, and
// handed down through AppShell's provide()/inject.
test("resolveConfig reads [outputs] max_processes_display", async () => {
	stubFetch({ "api/5/config": { body: { outputs: { max_processes_display: 25 } } } });
	assert.equal((await resolveConfig()).maxProcessesDisplay, 25);
});

test("resolveConfig truncates a non-integer max_processes_display", async () => {
	stubFetch({ "api/5/config": { body: { outputs: { max_processes_display: "25.9" } } } });
	assert.equal((await resolveConfig()).maxProcessesDisplay, 25);
});

test("resolveConfig treats an absent, zero or negative max_processes_display as no cap", async () => {
	stubFetch({ "api/5/config": { body: {} } });
	assert.equal((await resolveConfig()).maxProcessesDisplay, null);
	stubFetch({ "api/5/config": { body: { outputs: { max_processes_display: 0 } } } });
	assert.equal((await resolveConfig()).maxProcessesDisplay, null);
	stubFetch({ "api/5/config": { body: { outputs: { max_processes_display: -5 } } } });
	assert.equal((await resolveConfig()).maxProcessesDisplay, null);
	stubFetch({ "api/5/config": { body: { outputs: { max_processes_display: "not-a-number" } } } });
	assert.equal((await resolveConfig()).maxProcessesDisplay, null);
});

test("resolveConfig falls back to the default theme when config has no theme key", async () => {
	stubFetch({ "api/5/config": { body: { global: { refresh: 5 } } } });
	assert.equal((await resolveConfig()).theme, DEFAULT_THEME);
});

test("resolveConfig falls back to the default theme on an unrecognised value", async () => {
	// A config typo must not be written through to data-theme -- fall back
	// rather than ship an unstyled page.
	stubFetch({ "api/5/config": { body: { outputs: { theme: "solarized" } } } });
	assert.equal((await resolveConfig()).theme, DEFAULT_THEME);
});

test("fetchAll issues exactly one request", async () => {
	let calls = 0;
	globalThis.fetch = async () => {
		calls += 1;
		return { ok: true, status: 200, json: async () => ({ mem: { percent: 1 }, network: { data: [] } }) };
	};
	await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	]);
	assert.equal(calls, 1);
});

test("a plugin absent from /all is loading, not an error", async () => {
	// /api/5/all omits a plugin that has not published yet (scheduler cycle 0).
	// That is the same state the per-plugin `200 null` used to signal.
	globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ mem: { percent: 1 } }) });
	const { results, errors } = await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	]);
	assert.deepEqual(results.mem, { percent: 1 });
	assert.equal(results.network, null);
	assert.equal(errors.network, undefined);
});

test("a wrong-shaped slice errors only its own plugin", async () => {
	globalThis.fetch = async () => ({
		ok: true,
		status: 200,
		json: async () => ({ mem: { percent: 1 }, network: { detail: "boom" } }),
	});
	const { results, errors } = await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	]);
	assert.deepEqual(results.mem, { percent: 1 });
	assert.match(errors.network, /shape/i);
	assert.equal(errors.mem, undefined);
});

test("an unreachable /all errors every plugin", async () => {
	// The honest cost of one request: one failure blanks the page. Pinned so
	// the trade is visible rather than discovered.
	globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({}) });
	const { results, errors } = await fetchAll([
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
	]);
	assert.equal(results.mem, undefined);
	assert.match(errors.mem, /HTTP 503/);
});

test("resolveArgs returns the args object and fetches once", async () => {
	let calls = 0;
	globalThis.fetch = async () => {
		calls += 1;
		return { ok: true, status: 200, json: async () => ({ meangpu: true, fahrenheit: false }) };
	};
	assert.deepEqual(await resolveArgs(), { meangpu: true, fahrenheit: false });
	// CLI arguments cannot change while the server runs, so a second call
	// must not hit the network.
	await resolveArgs();
	assert.equal(calls, 1);
});

test("a non-object /all envelope errors every plugin instead of rejecting", async () => {
	// getJson guarantees only "HTTP 2xx and parseable JSON". `null`, a number,
	// a string and an array are all parseable JSON -- and `"mem" in null`
	// throws a TypeError that escapes fetchAll, breaking its documented
	// {results, errors} contract. AppShell's tick() has a `finally` but no
	// `catch`, so that rejection propagates out of mounted() and the poll
	// interval is never scheduled: the page freezes on "loading…" forever.
	const specs = [
		{ name: "mem", spec: { shape: "scalar", required: ["percent"] } },
		{ name: "network", spec: { shape: "collection", required: [] } },
	];
	for (const body of [null, [{ mem: 1 }], "boom", 42]) {
		globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => body });
		const { results, errors } = await fetchAll(specs);
		assert.deepEqual(results, {}, `body ${JSON.stringify(body)} should yield no results`);
		assert.match(errors.mem, /shape/i);
		assert.match(errors.network, /shape/i);
	}
});

test("resolvePluginNames returns the server's plugin list", async () => {
	stubFetch({ "api/5/pluginslist": { body: ["cpu", "mem"] } });
	assert.deepEqual(await resolvePluginNames(), ["cpu", "mem"]);
});

test("resolvePluginNames returns null when the list cannot be read", async () => {
	stubFetch({ "api/5/pluginslist": { status: 500, body: { detail: "boom" } } });
	assert.equal(await resolvePluginNames(), null);
	// A 200 carrying the wrong shape is not a list either.
	stubFetch({ "api/5/pluginslist": { body: { detail: "nope" } } });
	assert.equal(await resolvePluginNames(), null);
	// Network failure: stubFetch throws for an unknown route.
	stubFetch({});
	assert.equal(await resolvePluginNames(), null);
});

// The footer links /docs only when the server mounts it -- the same
// `[outputs] api_doc` gate webserver_v5.build_app() reads.
test("resolveConfig reads [outputs] api_doc, in either of the types the merged config serves", async () => {
	// GlancesConfigV5.DEFAULTS and the CLI overlay hold a real boolean ...
	stubFetch({ "api/5/config": { body: { outputs: { api_doc: false } } } });
	assert.equal((await resolveConfig()).apiDoc, false);
	// ... while a value read from glances.conf arrives as a raw string.
	stubFetch({ "api/5/config": { body: { outputs: { api_doc: "False" } } } });
	assert.equal((await resolveConfig()).apiDoc, false);
	stubFetch({ "api/5/config": { body: { outputs: { api_doc: "on" } } } });
	assert.equal((await resolveConfig()).apiDoc, true);
});

test("resolveConfig keeps the default api_doc when the key is absent or unreadable", async () => {
	stubFetch({ "api/5/config": { body: { outputs: {} } } });
	assert.equal((await resolveConfig()).apiDoc, DEFAULT_API_DOC);
	stubFetch({ "api/5/config": { body: { outputs: { api_doc: "maybe" } } } });
	assert.equal((await resolveConfig()).apiDoc, DEFAULT_API_DOC);
});

test("resolveVersion reads the release from the health probe", async () => {
	stubFetch({ status: { body: { status: "ok", version: "5", glances_version: "5.0.0" } } });
	assert.equal(await resolveVersion(), "5.0.0");
});

test("resolveVersion returns null rather than failing the page", async () => {
	// The footer then names no version. Nothing else depends on it.
	stubFetch({});
	assert.equal(await resolveVersion(), null);
	// A 200 whose body does not carry the key is the same non-answer.
	stubFetch({ status: { body: { status: "ok", version: "5" } } });
	assert.equal(await resolveVersion(), null);
});

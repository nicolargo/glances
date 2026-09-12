import { test } from "node:test";
import assert from "node:assert/strict";
import { TOP_CASCADE, HEADER_CASCADE, fits, resolveDegrade } from "../../glances/outputs/static/js/v5/degrade.js";

test("fits compares the zone's content with its available width", () => {
	assert.equal(fits({ content: 300, available: 400 }), true);
	assert.equal(fits({ content: 400, available: 400 }), true); // exactly full still fits
	assert.equal(fits({ content: 401, available: 400 }), false);
});

test("fits never degrades on an unusable measurement", () => {
	// A detached node, a hidden tab, a DOM without layout (the render probe):
	// reading 0 or NaN must not hide the user's stats.
	for (const available of [0, NaN, undefined, null]) {
		assert.equal(fits({ content: 5000, available }), true, `available=${available}`);
	}
	assert.equal(fits({ content: NaN, available: 400 }), true);
});

test("resolveDegrade applies nothing when the zone already fits", async () => {
	const seen = [];
	const flags = await resolveDegrade(TOP_CASCADE, (f) => {
		seen.push(f);
		return { content: 100, available: 400 };
	});
	assert.deepEqual(flags, {});
	assert.equal(seen.length, 1, "measures once, applies no notch");
});

test("resolveDegrade stops at the first notch that fits", async () => {
	// Fits only from the second measurement on: one notch applied.
	let call = 0;
	const flags = await resolveDegrade(TOP_CASCADE, () => ({ content: call++ === 0 ? 500 : 300, available: 400 }));
	assert.deepEqual(flags, { mem_cols: 1 });
});

test("resolveDegrade walks the cascade in the TUI's order", async () => {
	const applied = [];
	await resolveDegrade(TOP_CASCADE, (f) => {
		applied.push({ ...f });
		return { content: 5000, available: 400 }; // never fits: the whole cascade runs
	});
	// applied[0] is the measurement before any notch.
	assert.deepEqual(applied[1], { mem_cols: 1 });
	assert.deepEqual(applied[2], { mem_cols: 1, cpu_cols: 2 });
	assert.deepEqual(applied[3], { mem_cols: 1, cpu_cols: 1 });
	assert.deepEqual(applied[7], {
		mem_cols: 1,
		cpu_cols: 1,
		quicklook_freq_only: true,
		hide_quicklook: true,
		hide_memswap: true,
		hide_gpu: true,
	});
});

test("resolveDegrade returns every flag when the cascade is exhausted", async () => {
	const flags = await resolveDegrade(HEADER_CASCADE, () => ({ content: 5000, available: 100 }));
	assert.deepEqual(flags, {
		hide_cloud: true,
		hide_ip_location: true,
		hide_os_info: true,
		hide_now: true,
		hide_ip: true,
		hide_uptime: true,
	});
});

test("resolveDegrade starts from no flag every time, so widening restores stats", async () => {
	const measure = (widths) => (f) => ({ content: Object.keys(f).length ? 300 : 500, available: widths });
	const narrow = await resolveDegrade(TOP_CASCADE, measure(400));
	assert.deepEqual(narrow, { mem_cols: 1 });
	const wide = await resolveDegrade(TOP_CASCADE, () => ({ content: 300, available: 4000 }));
	assert.deepEqual(wide, {}, "a second run does not inherit the first run's flags");
});

test("resolveDegrade awaits an async measure", async () => {
	const flags = await resolveDegrade(TOP_CASCADE, async () => ({ content: 300, available: 400 }));
	assert.deepEqual(flags, {});
});

test("the cascades carry the TUI's steps, quicklook included", () => {
	assert.deepEqual(
		TOP_CASCADE.map((s) => [s.key, s.value]),
		[
			["mem_cols", 1],
			["cpu_cols", 2],
			["cpu_cols", 1],
			["quicklook_freq_only", true],
			["hide_quicklook", true],
			["hide_memswap", true],
			["hide_gpu", true],
		],
	);
	// Declared, not omitted: quicklook is not ported, so these two change
	// nothing today -- but the order and the count must match the TUI.
	assert.deepEqual(
		TOP_CASCADE.filter((s) => s.notApplicable).map((s) => s.key),
		["quicklook_freq_only", "hide_quicklook"],
	);
	assert.deepEqual(
		HEADER_CASCADE.map((s) => [s.key, s.value]),
		[
			["hide_cloud", true],
			["hide_ip_location", true],
			["hide_os_info", true],
			["hide_now", true],
			["hide_ip", true],
			["hide_uptime", true],
		],
	);
});

test("the two cascades share no key, which is what makes merging their flags safe", () => {
	// AppShell.slots() spreads {...degrade.header, ...degrade.top} before
	// deciding which blocks to hide: a shared key would resolve in favour of
	// `top` with no diagnostic.
	const shared = TOP_CASCADE.filter((step) => HEADER_CASCADE.some((h) => h.key === step.key));
	assert.deepEqual(shared, []);
});

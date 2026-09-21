import assert from "node:assert/strict";
import { test } from "node:test";

import {
	dataDrivenHidden,
	hiddenColumns,
	nameWidth,
	rowWidth,
	visibleCells,
} from "../../glances/outputs/static/js/v5/containers_columns.js";
import {
	COL_SEPARATOR,
	CONTAINER_COL_KEYS,
	CONTAINER_COL_WIDTHS,
	WEBUI_CONTAINER_COL_WIDTHS,
} from "../../glances/outputs/static/js/v5/process_widths.js";
import { formatAutoUnit, formatNetworkRate, formatPercent } from "../../glances/outputs/static/js/v5/format.js";

const ONE_ENGINE = [{ engine: "docker", pod_name: null, memory_limit: null }];
const TWO_ENGINES = [
	{ engine: "docker", pod_name: "frontend", memory_limit: 2147483648 },
	{ engine: "podman", pod_name: null, memory_limit: null },
];

test("a single engine hides the Engine column", () => {
	assert.ok(dataDrivenHidden(ONE_ENGINE, []).has("engine"));
	assert.ok(!dataDrivenHidden(TWO_ENGINES, []).has("engine"));
});

test("no pod hides the Pod column, one pod shows it", () => {
	assert.ok(dataDrivenHidden(ONE_ENGINE, []).has("pod"));
	assert.ok(!dataDrivenHidden(TWO_ENGINES, []).has("pod"));
});

test("disable_stats hides its columns whatever the data says", () => {
	const hidden = dataDrivenHidden(TWO_ENGINES, ["ports", "command"]);
	assert.ok(hidden.has("ports"));
	assert.ok(hidden.has("command"));
});

test("disable_stats mem takes memory_max with it", () => {
	const hidden = dataDrivenHidden(TWO_ENGINES, ["mem"]);
	assert.ok(hidden.has("mem"));
	assert.ok(hidden.has("memory_max"));
});

test("no memory_limit anywhere does NOT hide the /MAX column -- render_curses_v5.py has no such rule", () => {
	const allNullLimits = [
		{ engine: "docker", pod_name: "frontend", memory_limit: null },
		{ engine: "podman", pod_name: null, memory_limit: null },
	];
	assert.ok(!dataDrivenHidden(allNullLimits, []).has("memory_max"));
});

test("an empty collection hides every conditional column", () => {
	const hidden = dataDrivenHidden([], []);
	for (const column of ["engine", "pod"]) assert.ok(hidden.has(column));
	assert.ok(!hidden.has("memory_max"));
});

test("cascade flags add to the data-driven set, never remove from it", () => {
	const hidden = hiddenColumns(TWO_ENGINES, [], { drop_command: true, drop_ports: true });
	assert.ok(hidden.has("command"));
	assert.ok(hidden.has("ports"));
	assert.ok(!hidden.has("engine"), "two engines: Engine must survive the cascade");
});

test("a flag that is not a drop_ flag is ignored", () => {
	assert.ok(!hiddenColumns(TWO_ENGINES, [], { hide_gpu: true }).has("gpu"));
});

test("the never-dropped columns survive every flag", () => {
	const every = {};
	for (const column of ["command", "ports", "memory_max", "pod", "engine", "diskio", "networkio", "uptime", "status"]) {
		every[`drop_${column}`] = true;
	}
	const hidden = hiddenColumns(TWO_ENGINES, [], every);
	for (const column of ["name", "cpu", "mem"]) assert.ok(!hidden.has(column), `${column} must survive`);
});

// ---------------------------------------------------------------- geometry
//
// The <colgroup> the block renders, and the `min-width` that makes its width
// cascade fire where the terminal's own row_width() stops fitting.

test("every visible column is a cell, and the rate pairs are two", () => {
	const cells = visibleCells(new Set(), 20);
	assert.deepEqual(
		cells.map((cell) => cell.key),
		[
			"engine",
			"pod",
			"name",
			"status",
			"uptime",
			"cpu",
			"mem",
			"memory_max",
			"diskio",
			"diskio",
			"networkio",
			"networkio",
			"ports",
			"command",
		],
	);
	// The pair's 14 characters are split evenly, as the TUI's two 7-wide
	// headers are (render_curses_v5.py:157-162).
	assert.deepEqual(
		cells.filter((cell) => cell.key === "diskio").map((cell) => cell.width),
		[7, 7],
	);
});

test("a hidden column contributes no cell at all", () => {
	const cells = visibleCells(new Set(["command", "diskio"]), 20);
	const keys = cells.map((cell) => cell.key);
	assert.ok(!keys.includes("command"));
	assert.ok(!keys.includes("diskio"), "a half-pair can never be shown");
	assert.equal(cells[cells.length - 1].key, "ports", "the tail moves down the drop order");
});

test("the name cell carries the width it was given, never a constant", () => {
	assert.equal(visibleCells(new Set(), 13).find((cell) => cell.key === "name").width, 13);
});

test("the row width is the cells plus one separator between two of them", () => {
	// The terminal's row_width(), in the browser's own separator width.
	assert.equal(rowWidth([]), 0);
	assert.equal(rowWidth([{ width: 6 }]), 6, "no separator after the last cell");
	assert.equal(rowWidth([{ width: 6 }, { width: 7 }]), 13 + COL_SEPARATOR);
	const cells = visibleCells(new Set(), 20);
	const widths = cells.reduce((sum, cell) => sum + cell.width, 0);
	assert.equal(rowWidth(cells), widths + COL_SEPARATOR * (cells.length - 1));
});

test("the name column is the longest name, capped by the config", () => {
	const rows = [{ name: "web" }, { name: "database-primary" }];
	assert.equal(nameWidth(rows, 20, "CONTAINER"), "database-primary".length);
	assert.equal(nameWidth(rows, 8, "CONTAINER"), 9, "the cap never takes it below the header label");
	assert.equal(nameWidth(rows, 12, "CONTAINER"), 12);
});

test("the name column is sized on the alias the browser paints", () => {
	const rows = [{ name: "db", alias: "database-primary" }];
	assert.equal(nameWidth(rows, 20, "CONTAINER"), "database-primary".length);
});

test("a missing max_name_size falls back to the TUI's own default", () => {
	const rows = [{ name: "a-very-long-container-name-indeed" }];
	assert.equal(nameWidth(rows, undefined, "CONTAINER"), 20);
	assert.equal(nameWidth(rows, 0, "CONTAINER"), 20, "0 is not a usable cap");
});

test("an empty collection still leaves room for the header label", () => {
	assert.equal(nameWidth([], 20, "CONTAINER"), 9);
});

// The same two-sided check tests/js/process_widths.test.mjs runs on
// WEBUI_COL_WIDTHS: a browser width must cover the longest string its own
// formatter can produce, and must not diverge from the terminal's without a
// documented reason.
const CONTAINER_WORST_CASE = {
	// The engine name, and the `Engine` header, are both 6.
	engine: () => "docker",
	// `pod_id` is unbounded; the terminal budgets 12 and the browser matches
	// it rather than spending a character every host pays for.
	pod: () => "x".repeat(12),
	// `restarting`, the longest status `_STATUS_ROLE` maps.
	status: () => "restarting",
	// The TUI's own budget for a humanised uptime.
	uptime: () => "x".repeat(10),
	// A container spread over many cores genuinely passes 1000%, and the
	// browser appends the `%` the terminal's `{cpu:>6.1f}` does not print.
	cpu: () => formatPercent(9999.9),
	mem: () => formatAutoUnit(1023 * 1024 ** 3),
	// `/` plus the limit.
	memory_max: () => `/${formatAutoUnit(1023 * 1024 ** 3)}`,
	// Two cells: `1023GB` in each.
	diskio: () => `${formatAutoUnit(1023 * 1024 ** 3)}B`,
	networkio: () => formatNetworkRate(1023 * 1024 ** 3, false),
	// A published port list is unbounded; 16 is the terminal's budget, and
	// the full list stays on the cell's `title`.
	ports: () => "x".repeat(16),
	// The elastic tail: 8 is a FLOOR, not a worst case.
	command: () => "x".repeat(8),
};

test("every WebUI container column is wide enough for its own worst case", () => {
	for (const key of CONTAINER_COL_KEYS) {
		if (key === "name") continue; // sized from the data, not from a constant
		const worst = CONTAINER_WORST_CASE[key]();
		const cells = key === "diskio" || key === "networkio" ? 2 : 1;
		const perCell = WEBUI_CONTAINER_COL_WIDTHS[key] / cells;
		assert.ok(perCell >= worst.length, `${key}: ${perCell} character(s) cannot hold "${worst}"`);
	}
});

test("the WebUI container widths only ever diverge from the terminal's for the `%` suffix", () => {
	// CONTAINER_COL_WIDTHS is drift-tested against the curses renderer 1:1
	// (tests/test_webui_v5_width_drift.py); WEBUI_CONTAINER_COL_WIDTHS is not,
	// so this is what keeps the second map from quietly wandering off. `cpu`
	// is the ONE documented divergence.
	for (const key of CONTAINER_COL_KEYS) {
		if (key === "name") continue;
		const expected = key === "cpu" ? CONTAINER_COL_WIDTHS[key] + 1 : CONTAINER_COL_WIDTHS[key];
		assert.equal(WEBUI_CONTAINER_COL_WIDTHS[key], expected, `${key} diverges from the terminal with no reason given`);
	}
});

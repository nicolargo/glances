import assert from "node:assert/strict";
import { test } from "node:test";

import { PROCESSLIST_DROP_ORDER, hiddenColumns } from "../../glances/outputs/static/js/v5/processlist_columns.js";

test("the drop order is the TUI's, in the TUI's order", () => {
	assert.deepEqual(PROCESSLIST_DROP_ORDER, ["VIRT", "TIME+", "RES", "USER", "PID", "THR", "S", "NI"]);
});

test("the columns the TUI never drops are absent from the order", () => {
	for (const column of ["CPU%", "MEM%", "R/s", "W/s", "Command"]) {
		assert.ok(!PROCESSLIST_DROP_ORDER.includes(column), `${column} must never be droppable`);
	}
});

test("no flags hides nothing", () => {
	assert.deepEqual(hiddenColumns({}), new Set());
	assert.deepEqual(hiddenColumns(undefined), new Set());
});

test("a drop_ flag hides its column", () => {
	const hidden = hiddenColumns({ "drop_VIRT": true, "drop_TIME+": true });
	assert.ok(hidden.has("VIRT"));
	assert.ok(hidden.has("TIME+"));
	assert.equal(hidden.size, 2);
});

test("a false-valued flag does not hide its column", () => {
	assert.ok(!hiddenColumns({ drop_VIRT: false }).has("VIRT"));
});

test("a flag that is not a drop_ flag is ignored", () => {
	assert.ok(!hiddenColumns({ hide_gpu: true }).has("gpu"));
});

test("the never-dropped columns survive every flag", () => {
	const every = {};
	for (const column of PROCESSLIST_DROP_ORDER) every[`drop_${column}`] = true;
	const hidden = hiddenColumns(every);
	for (const column of ["CPU%", "MEM%", "R/s", "W/s", "Command"]) {
		assert.ok(!hidden.has(column), `${column} must survive`);
	}
	assert.equal(hidden.size, PROCESSLIST_DROP_ORDER.length);
});

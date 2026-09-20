import { test } from "node:test";
import assert from "node:assert/strict";
import { planRightColumn, splitWorkloads, alertBlockHeight } from "../../glances/outputs/static/js/v5/row_budget.js";

const BASE = {
	bodyHeight: 40,
	staticHeights: { processcount: 1 },
	ampsHeight: 0,
	nVms: 0,
	nContainers: 0,
	nProcesses: 200,
	nAlerts: 0,
	nOngoing: 0,
};

test("a sparse block beside a crowded one keeps its rows (max-min fairness)", () => {
	assert.deepEqual(splitWorkloads(10, 2, 30), [2, 8]);
});

test("an odd leftover goes to vms first", () => {
	assert.deepEqual(splitWorkloads(5, 10, 10), [3, 2]);
});

test("an empty alert block costs one row, a populated one costs two plus its rows", () => {
	assert.equal(alertBlockHeight(0, 10), 1);
	assert.equal(alertBlockHeight(5, 0), 1);
	assert.equal(alertBlockHeight(5, 3), 5);
});

test("processes absorb the slack on a tall viewport", () => {
	const budget = planRightColumn({ ...BASE, bodyHeight: 60 });
	assert.ok(budget.processlist > 20, "the nominal 20 is a floor to grow from, not a cap");
	assert.equal(budget.processlist, budget.programlist);
});

test("an active alert holds its floor while everything else gives way", () => {
	const budget = planRightColumn({ ...BASE, bodyHeight: 8, nAlerts: 6, nOngoing: 3 });
	assert.ok(budget.alert >= 3, "three ongoing incidents must stay visible");
	assert.equal(budget.processlist, 0, "step l drops the process block for them");
});

test("with no active alert the floor never fires and the historical cascade holds", () => {
	const budget = planRightColumn({ ...BASE, bodyHeight: 8, nAlerts: 6, nOngoing: 0 });
	assert.equal(budget.alert, 0, "step h leaves the header only");
});

test("amps is reported only when the ladder truncated it", () => {
	assert.equal("amps" in planRightColumn({ ...BASE, bodyHeight: 60, ampsHeight: 3 }), false);
	assert.equal("amps" in planRightColumn({ ...BASE, bodyHeight: 6, ampsHeight: 9 }), true);
});

import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTAINERS_DROP_ORDER, dropCascade } from "../../glances/outputs/static/js/v5/drop_order.js";

test("the drop order is the TUI's, in the TUI's order", () => {
	assert.deepEqual(CONTAINERS_DROP_ORDER, [
		"command",
		"ports",
		"memory_max",
		"pod",
		"engine",
		"diskio",
		"networkio",
		"uptime",
		"status",
	]);
});

test("the columns the TUI never drops are absent from the order", () => {
	for (const column of ["name", "cpu", "mem"]) {
		assert.ok(!CONTAINERS_DROP_ORDER.includes(column), `${column} must never be droppable`);
	}
});

test("dropCascade produces one resolveDegrade step per column, in order", () => {
	assert.deepEqual(dropCascade(["command", "ports"]), [
		{ key: "drop_command", value: true },
		{ key: "drop_ports", value: true },
	]);
});

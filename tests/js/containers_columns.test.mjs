import assert from "node:assert/strict";
import { test } from "node:test";

import { dataDrivenHidden, hiddenColumns } from "../../glances/outputs/static/js/v5/containers_columns.js";

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

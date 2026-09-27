import { test } from "node:test";
import assert from "node:assert/strict";
import {
	cellClass,
	columnLabels,
	displayName,
	formatCell,
	headerRows,
	serverHref,
	statusClass,
	statusCounts,
	title,
} from "../../glances/outputs/static/js/v5/browser.js";

test("a status is coloured like the TUI browser colours it", () => {
	assert.equal(statusClass("ONLINE"), "gl-level-ok");
	assert.equal(statusClass("UNSUPPORTED"), "gl-level-careful");
	assert.equal(statusClass("PROTECTED"), "gl-level-warning");
	assert.equal(statusClass("OFFLINE"), "gl-level-critical");
	assert.equal(statusClass("UNKNOWN"), "");
});

test("the name cell shows the alias, else the name", () => {
	assert.equal(displayName({ name: "10.0.0.1", alias: "nas" }), "nas");
	assert.equal(displayName({ name: "10.0.0.1", alias: null }), "10.0.0.1");
});

test("a server links to its own Web UI", () => {
	assert.equal(serverHref({ name: "alpha", port: 61208 }), "http://alpha:61208/");
	assert.equal(serverHref({ name: "192.168.1.10", port: 61237 }), "http://192.168.1.10:61237/");
	assert.equal(serverHref({ name: "https://glances.example/", port: 61208 }), "https://glances.example/");
});

test("a name that is not a plain host or an http(s) URL gets no link", () => {
	for (const name of [
		"javascript:alert(1)",
		"javascript://%0aalert(1)",
		"data://text/html,x",
		"user:pw@evil.example",
		"http://user:pw@evil.example/",
		"evil.example/phish",
		"evil.example?x=1",
		"",
	]) {
		assert.equal(serverHref({ name, port: 61208 }), null, name);
	}
});

test("the headers are every server's labels, in first-seen order", () => {
	const servers = [
		{ columns: {} },
		{ columns: { "cpu:total": {}, "mem:percent": {} } },
		{ columns: { "mem:percent": {}, "sensors:value:Ambient": {} } },
	];
	assert.deepEqual(columnLabels(servers), ["cpu:total", "mem:percent", "sensors:value:Ambient"]);
	assert.deepEqual(headerRows("sensors:value:Ambient"), ["SENSORS", "VALUE AMBIENT"]);
	assert.deepEqual(headerRows("load:min5"), ["LOAD", "MIN5"]);
});

test("a cell reads as in the TUI browser", () => {
	assert.equal(formatCell({ value: 92.34, level: "critical" }), "92.3");
	assert.equal(formatCell({ value: 4, level: null }), "4");
	assert.equal(formatCell({ value: "Ubuntu 24.04" }), "Ubuntu 24.04");
	assert.equal(formatCell(undefined), "?");
	assert.equal(cellClass({ value: 1, level: "warning" }), "gl-level-warning");
	assert.equal(cellClass(undefined), "");
});

test("title and counts", () => {
	assert.equal(title(0), "No Glances server available");
	assert.equal(title(1), "1 Glances server available");
	assert.equal(title(3), "3 Glances servers available");
	assert.deepEqual(statusCounts([{ status: "ONLINE" }, { status: "OFFLINE" }, { status: "ONLINE" }]), [
		{ status: "ONLINE", count: 2 },
		{ status: "OFFLINE", count: 1 },
	]);
});

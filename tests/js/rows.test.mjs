import { test } from "node:test";
import assert from "node:assert/strict";
import { displayName, byText } from "../../glances/outputs/static/js/v5/rows.js";

test("displayName shows the configured alias", () => {
	assert.equal(displayName({ interface_name: "lo", alias: "Loopback" }, "interface_name"), "Loopback");
});

test("displayName falls back to the raw key when there is no usable alias", () => {
	assert.equal(displayName({ disk_name: "sda" }, "disk_name"), "sda");
	assert.equal(displayName({ disk_name: "sda", alias: "" }, "disk_name"), "sda");
	assert.equal(displayName({ disk_name: "sda", alias: null }, "disk_name"), "sda");
});

test("displayName never renders undefined", () => {
	assert.equal(displayName({}, "disk_name"), "");
	assert.equal(displayName({ disk_name: null }, "disk_name"), "");
});

test("byText sorts like Python's sorted(key=str): code units, not locale", () => {
	// Python: sorted(["a", "B"]) == ["B", "a"]; localeCompare would give ["a", "B"].
	const rows = [{ ssid: "a" }, { ssid: "B" }, { ssid: "wlp0s20f3" }, { ssid: "wlan0" }];
	assert.deepEqual(rows.slice().sort(byText("ssid")).map((r) => r.ssid), ["B", "a", "wlan0", "wlp0s20f3"]);
});

test("byText keeps equal keys in their original order, like sorted()", () => {
	const rows = [
		{ mnt_point: "/", n: 1 },
		{ mnt_point: "/", n: 2 },
	];
	assert.deepEqual(rows.slice().sort(byText("mnt_point")).map((r) => r.n), [1, 2]);
});

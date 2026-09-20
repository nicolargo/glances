import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
	REFRESH_STEPS,
	stepRefresh,
	loadRefresh,
	saveRefresh,
} from "../../glances/outputs/static/js/v5/refresh.js";

function stubStorage(initial) {
	const store = { ...initial };
	globalThis.localStorage = {
		getItem: (key) => (key in store ? store[key] : null),
		setItem: (key, value) => {
			store[key] = value;
		},
	};
	return store;
}

beforeEach(() => {
	delete globalThis.localStorage;
});

test("the ladder spans the whole 1..60 s range the footer advertises", () => {
	assert.equal(REFRESH_STEPS[0], 1);
	assert.equal(REFRESH_STEPS[REFRESH_STEPS.length - 1], 60);
	const sorted = [...REFRESH_STEPS].sort((a, b) => a - b);
	assert.deepEqual(REFRESH_STEPS, sorted, "stepRefresh scans the ladder in order");
});

test("stepping moves one rung in the asked direction", () => {
	assert.equal(stepRefresh(2, 1), 3);
	assert.equal(stepRefresh(2, -1), 1);
	assert.equal(stepRefresh(15, 1), 30);
	assert.equal(stepRefresh(15, -1), 10);
});

test("stepping clamps at both ends instead of wrapping", () => {
	// A "+" that jumped back to 1 s would silently make the page poll 60x
	// faster -- the opposite of what the click asked for.
	assert.equal(stepRefresh(60, 1), 60);
	assert.equal(stepRefresh(1, -1), 1);
});

test("stepping from an off-ladder cadence lands on the nearest rung", () => {
	// `[global] refresh=4` is legal and is not a rung.
	assert.equal(stepRefresh(4, 1), 5);
	assert.equal(stepRefresh(4, -1), 3);
	// A config value past the top of the ladder is pulled back onto it.
	assert.equal(stepRefresh(120, -1), 60);
	assert.equal(stepRefresh(120, 1), 60);
});

test("loadRefresh returns null when nothing was ever saved", () => {
	stubStorage({});
	assert.equal(loadRefresh(), null);
});

test("loadRefresh returns null rather than repairing an unusable value", () => {
	stubStorage({ "glances.refresh": "not a number" });
	assert.equal(loadRefresh(), null);
	stubStorage({ "glances.refresh": "0" });
	assert.equal(loadRefresh(), null);
});

test("a saved cadence survives the reload", () => {
	stubStorage({});
	saveRefresh(15);
	assert.equal(loadRefresh(), 15);
});

test("no localStorage at all degrades to 'not remembered', never to a throw", () => {
	// Private browsing, blocked site data, and the render probe's DOM stub all
	// look like this.
	assert.equal(loadRefresh(), null);
	assert.doesNotThrow(() => saveRefresh(5));
});

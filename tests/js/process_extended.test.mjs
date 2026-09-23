import assert from "node:assert/strict";
import test from "node:test";

import {
	IONICE_CLASSES,
	extendedLines,
	ioniceText,
	pinnedTitle,
} from "../../glances/outputs/static/js/v5/process_extended.js";

// The shape the live engine publishes (verified in
// tests/test_processes_extended.py), trimmed to what this module reads.
const PAYLOAD = {
	pid: 1,
	name: "hot",
	cmdline: ["/bin/hot", "--go"],
	cpu_min: 0.5,
	cpu_max: 78.4,
	cpu_mean: 12.25,
	memory_min: 1.0,
	memory_max: 12.5,
	memory_mean: 6.0,
	cpu_affinity: [0, 1, 2, 3],
	ionice: { ioclass: 2, value: 4 },
	memory_info: { rss: 33554432, vms: 125829120 },
	memory_swap: 4194304,
	num_threads: 20,
	num_fds: 45,
	tcp: 3,
	udp: 1,
};

const flat = (payload) => extendedLines(payload).map((line) => line.map((s) => s.text).join(" "));

test("nothing is rendered without a pinned process", () => {
	assert.deepEqual(extendedLines(null), []);
	assert.deepEqual(extendedLines({}), []);
	assert.deepEqual(extendedLines(undefined), []);
});

test("three lines, in the terminal's order", () => {
	const lines = flat(PAYLOAD);
	assert.equal(lines.length, 3);
	assert.match(lines[0], /^CPU Min\/Max\/Mean:/);
	assert.match(lines[1], /^MEM Min\/Max\/Mean:/);
	assert.match(lines[2], /^Open:/);
});

test("min/max/mean carry one decimal", () => {
	assert.match(flat(PAYLOAD)[0], /0\.5% \/ 78\.4% \/ 12\.3%/);
});

test("a missing min/max/mean reads zero rather than NaN", () => {
	// The engine publishes nothing until it has grabbed once; `undefined`
	// through `toFixed` would render "NaN%" on the first frame after a pin.
	assert.match(flat({ pid: 1, name: "x" })[0], /0\.0% \/ 0\.0% \/ 0\.0%/);
});

test("affinity counts the cores, it does not list them", () => {
	assert.match(flat(PAYLOAD)[0], /Affinity: 4 cores/);
});

test("the memory breakdown keeps the engine's own field names", () => {
	assert.match(flat(PAYLOAD)[1], /32\.0M rss 120M vms/);
});

test("swap is shown even at zero, because zero swap is information", () => {
	assert.match(flat({ ...PAYLOAD, memory_swap: 0 })[1], /0B swap/);
});

test("a platform that reports no swap shows no swap segment", () => {
	// `memory_swap` is None off Linux (`__get_extended_memory_swap`).
	assert.doesNotMatch(flat({ ...PAYLOAD, memory_swap: null })[1], /swap/);
});

test("the Open line names only the counters the platform reported", () => {
	const line = flat({ ...PAYLOAD, num_fds: null })[2];
	assert.match(line, /20 threads/);
	assert.doesNotMatch(line, /fds/);
	assert.match(line, /3 tcp 1 udp/);
});

test("a zero counter is still a counter", () => {
	assert.match(flat({ ...PAYLOAD, tcp: 0 })[2], /0 tcp/);
});

test("values are marked so the browser can emphasise what the terminal colours", () => {
	const [cpu] = extendedLines(PAYLOAD);
	assert.equal(cpu[0].value, undefined); // the label
	assert.equal(cpu[1].value, true); // the number
});

test("ionice reads the DICT the engine actually publishes", () => {
	// v4 tests `hasattr(ionice, 'ioclass')` on a value the engine has already
	// converted to a dict, so v4 never renders this line at all.
	assert.equal(ioniceText({ ioclass: 2, value: 4 }), "Class is Best Effort (value 4/7)");
	assert.equal(ioniceText({ ioclass: 0, value: 0 }), IONICE_CLASSES[0]);
	assert.equal(ioniceText({ ioclass: 9 }), "Class is 9");
	assert.equal(ioniceText(null), null);
	assert.equal(ioniceText({ value: 3 }), null);
});

test("Windows reads its own class table", () => {
	assert.equal(ioniceText({ ioclass: 2 }, true), "No specific I/O priority");
	assert.equal(ioniceText({ ioclass: 0 }, true), "Class is Very Low");
});

test("the title is the process name, as the terminal titles it", () => {
	// Not the command line: the engine's accumulator carries no `cmdline`
	// (it is added after the extended grab), so preferring it would render
	// the fallback every time while pretending not to.
	assert.equal(pinnedTitle(PAYLOAD), "hot");
	assert.equal(pinnedTitle({ name: "kthreadd" }), "kthreadd");
	assert.equal(pinnedTitle({}), "?");
	assert.equal(pinnedTitle(null), "?");
});

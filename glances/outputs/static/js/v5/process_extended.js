// The `e` block — the pinned process' extended stats (2.X-b3-web).
//
// Mirrors `_extended_rows` (processlist/render_curses_v5.py) segment for
// segment, so the terminal and the browser describe a pinned process with the
// SAME labels in the SAME order. That equality is not left to care: a Python
// test runs this module under node and compares the two
// (tests/test_webui_v5_extended_drift.py), the way `hotkeys.js`,
// `full_quicklook.js` and `degrade.js` are already held to their sources.
//
// A segment is `{ text, value }`. `value: true` marks the cells the terminal
// renders in the OK colour -- the numbers -- and the browser emphasises the
// same ones. The labels are the `value: false` segments, and those are what
// the drift test compares.
//
// v4's web UI shows three lines and omits IO nice and the Open counters
// (plugin-processlist.vue:5-30). v5's browser follows v5's OWN terminal
// instead: the two surfaces of one version agreeing is worth more than the
// browser agreeing with the previous version's browser.

import { formatProcessBytes } from "./format.js";

// `get_headers` (v4 processlist/__init__.py:719-726), labels included.
export const IONICE_CLASSES = {
	0: "No specific I/O priority",
	1: "Class is Real Time",
	2: "Class is Best Effort",
	3: "Class is IDLE",
};
export const IONICE_CLASSES_WINDOWS = {
	0: "Class is Very Low",
	1: "Class is Low",
	2: "No specific I/O priority",
};

// The counters the terminal's " Open:" line walks, in its order.
const OPEN_KEYS = ["num_threads", "num_fds", "num_handles", "tcp", "udp"];

export function ioniceText(ionice, windows = false) {
	// The engine stores `namedtuple_to_dict(proc)`, so psutil's `pionice`
	// namedtuple is a plain object by the time anyone reads it. v4 guards on
	// `hasattr(prog['ionice'], 'ioclass')` and therefore never renders this
	// line at all -- see the Python twin's docstring.
	if (!ionice || typeof ionice !== "object") return null;
	const ioclass = ionice.ioclass;
	if (ioclass === null || ioclass === undefined) return null;
	const table = windows ? IONICE_CLASSES_WINDOWS : IONICE_CLASSES;
	const n = Number(ioclass);
	let label = Object.prototype.hasOwnProperty.call(table, n) ? table[n] : `Class is ${n}`;
	const value = ionice.value;
	if (Number.isInteger(value) && value !== 0) label += ` (value ${value}/7)`;
	return label;
}

function mmm(payload, prefix) {
	// `_mmm`: the terminal's `{: >7.1f}` triple. The padding is the terminal's
	// column arithmetic and does not survive into HTML, so only the one
	// decimal does.
	const at = (suffix) => Number(payload[`${prefix}_${suffix}`] || 0).toFixed(1);
	return `${at("min")}% / ${at("max")}% / ${at("mean")}%`;
}

export function extendedLines(payload) {
	if (!payload || typeof payload !== "object" || !Object.keys(payload).length) return [];

	const cpu = [
		{ text: "CPU Min/Max/Mean:" },
		{ text: mmm(payload, "cpu"), value: true },
	];
	if (Array.isArray(payload.cpu_affinity)) {
		cpu.push({ text: "Affinity:" }, { text: `${payload.cpu_affinity.length} cores`, value: true });
	}
	const ionice = ioniceText(payload.ionice);
	if (ionice) cpu.push({ text: "IO nice:" }, { text: ionice, value: true });

	const mem = [
		{ text: "MEM Min/Max/Mean:" },
		{ text: mmm(payload, "memory"), value: true },
	];
	const info = payload.memory_info;
	if (info && typeof info === "object" && Object.keys(info).length) {
		mem.push({ text: "Memory info:" });
		for (const [key, val] of Object.entries(info)) {
			mem.push({ text: formatProcessBytes(val), value: true }, { text: String(key) });
		}
	}
	if (Number.isInteger(payload.memory_swap)) {
		mem.push({ text: formatProcessBytes(payload.memory_swap), value: true }, { text: "swap" });
	}

	const open = [{ text: "Open:" }];
	for (const key of OPEN_KEYS) {
		const val = payload[key];
		if (val !== null && val !== undefined) {
			open.push({ text: String(val), value: true }, { text: key.replace("num_", "") });
		}
	}

	return [cpu, mem, open];
}

export function pinnedTitle(payload) {
	// `name`, as the terminal titles it. NOT the command line, which v4's web
	// UI uses (plugin-processlist.vue:8): v4 reads the published LIST ITEM,
	// which carries one, while this block is built from the engine's
	// accumulator -- and that has no `cmdline` at all, because the engine adds
	// it after the extended grab. Measured, not assumed. The pinned ROW is
	// underlined in the table below, so the full command is a glance away.
	if (!payload) return "?";
	return String(payload.name || "?");
}

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

function mmmBytes(payload, prefix) {
	// `_mmm_bytes`: the RES triple, a byte count.
	const at = (suffix) => formatProcessBytes(payload[`${prefix}_${suffix}`] || 0);
	return `${at("min")} / ${at("max")} / ${at("mean")}`;
}

export function extendedLines(payload) {
	if (!payload || typeof payload !== "object" || !Object.keys(payload).length) return [];

	// `sep: true` marks the first segment of a group (a `Label:` and its
	// value, or a value and its unit), which the browser spaces out more than
	// the segments inside a group.
	const cpu = [
		{ text: "CPU Min/Max/Mean:" },
		{ text: mmm(payload, "cpu"), value: true },
	];
	if (Array.isArray(payload.cpu_affinity)) {
		cpu.push({ text: "Affinity:", sep: true }, { text: `${payload.cpu_affinity.length} cores`, value: true });
	}
	const ionice = ioniceText(payload.ionice);
	if (ionice) cpu.push({ text: "IO nice:", sep: true }, { text: ionice, value: true });

	const mem = [
		{ text: "RES Min/Max/Mean:" },
		{ text: mmmBytes(payload, "memory"), value: true },
	];
	const info = payload.memory_info;
	if (info && typeof info === "object" && Object.keys(info).length) {
		mem.push({ text: "Memory info:", sep: true });
		Object.entries(info).forEach(([key, val], i) => {
			mem.push({ text: formatProcessBytes(val), value: true, sep: i > 0 }, { text: String(key) });
		});
	}
	if (Number.isInteger(payload.memory_swap)) {
		mem.push({ text: formatProcessBytes(payload.memory_swap), value: true, sep: true }, { text: "swap" });
	}

	const open = [{ text: "Open:" }];
	for (const key of OPEN_KEYS) {
		const val = payload[key];
		if (val !== null && val !== undefined) {
			open.push({ text: String(val), value: true, sep: open.length > 1 }, { text: key.replace("num_", "") });
		}
	}

	return [cpu, mem, open];
}

export function pinnedTitle(payload) {
	// `_pinned_title`: the command line with its arguments, else `name`.
	if (!payload) return "?";
	if (Array.isArray(payload.cmdline) && payload.cmdline.length) return payload.cmdline.join(" ");
	return String(payload.name || "?");
}

/**
 * A pin the browser has asked for but the server has not published yet, or
 * null once it no longer needs showing: the payload's `extended` names it
 * (confirmed), or the process left the list (it will never be).
 *
 * The pending pin is what lets the "Pinned task:" line appear on the click
 * itself, before the server's next cycle carries the extended stats.
 */
export function settlePendingPin(pending, payload) {
	if (!pending) return null;
	if (payload?.extended?.pid === pending.pid) return null;
	if (Array.isArray(payload?.data) && !payload.data.some((item) => item?.pid === pending.pid)) return null;
	return pending;
}

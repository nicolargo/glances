// Glances v5 WebUI -- horizontal degradation: the TUI's cascades, in the TUI's
// order.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it. The caller
// owns measurement; this module owns the ORDER and the fit test. That split is
// what makes the behaviour testable at all -- the render probe has no layout
// engine, and a browser is not available under `node --test`.
//
// The two cascades mirror glances/outputs/glances_curses_v5.py
// (_DEGRADE_STEPS:62, _HEADER_DEGRADE_STEPS:87) entry by entry;
// tests/test_webui_v5_degrade_drift.py compares them. Never reorder, drop or
// edit one side alone.

// TOP row (a->g). Least useful detail first, whole blocks last.
export const TOP_CASCADE = [
	{ key: "mem_cols", value: 1 }, // (a) hide MEM's 2nd column
	{ key: "cpu_cols", value: 2 }, // (b) hide CPU's 3rd column
	{ key: "cpu_cols", value: 1 }, // (c) hide CPU's 2nd column
	// (d) and (e) act on `quicklook`, which the v5 WebUI does not render yet.
	// They are declared so the order and the count stay identical to the TUI's
	// and applying them is a no-op today; the drift test fails if quicklook is
	// ported without revisiting this file.
	{ key: "quicklook_freq_only", value: true, notApplicable: true },
	{ key: "hide_quicklook", value: true, notApplicable: true },
	{ key: "hide_memswap", value: true }, // (f) hide the swap block
	{ key: "hide_gpu", value: true }, // (g) hide the gpu block (last resort)
];

// Header line (0->5). `cloud` is opt-in, so it goes first: enabling it must
// never cost information that was on screen before it was turned on.
export const HEADER_CASCADE = [
	{ key: "hide_cloud", value: true },
	{ key: "hide_ip_location", value: true },
	{ key: "hide_os_info", value: true },
	{ key: "hide_now", value: true },
	{ key: "hide_ip", value: true },
	{ key: "hide_uptime", value: true },
];

// The TUI computes `sum(widths) + (n - 1) * gap <= max_x` because curses has no
// layout engine. The browser has one: `content` is the zone's scrollWidth and
// `available` its clientWidth, so the rule is measured rather than recomputed
// and no gap constant can drift from the CSS.
//
// An unusable reading means "cannot measure", and the answer is always `true`:
// a DOM without layout (the render probe), a hidden tab or a detached node must
// never hide the user's stats.
export function fits({ content, available }) {
	if (!Number.isFinite(content) || !Number.isFinite(available) || available <= 0) return true;
	return content <= available;
}

// Mirrors _build_fitted_frame / _fit_header: start with NO flag, apply one
// cascade entry at a time, re-measure, stop as soon as it fits. Starting from
// zero on every call is what makes a widening window give the stats back.
//
// `measure(flags)` may be async: applying a flag re-renders the view, and the
// caller awaits that before reading the DOM.
export async function resolveDegrade(cascade, measure) {
	let flags = {};
	if (fits(await measure(flags))) return flags;
	for (const step of cascade) {
		flags = { ...flags, [step.key]: step.value };
		if (fits(await measure(flags))) break;
	}
	return flags;
}

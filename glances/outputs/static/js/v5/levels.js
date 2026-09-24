// Glances v5 WebUI — the `_levels` payload field to a CSS class.
//
// The ONLY place tier semantics live. Components ask this module; they never
// test `level === "critical"` themselves, or the redesign drifts from the TUI
// one component at a time across 32 ports.
//
// Ported from the TUI contract (glances/outputs/curses_renderer_v5.py):
//   - four tiers: ok, careful, warning, critical
//   - `prominent` turns the value into a filled badge (tier colour as the
//     background, see css/v5.css), the TUI's reverse pairs; the tier itself
//     is unchanged
//   - an alert is signalled on the VALUE only; titles and column headers are
//     never given a tier colour. This module therefore exposes no function
//     that could colour a header -- the rule is enforced by omission.

const TIERS = new Set(["ok", "careful", "warning", "critical"]);

export function levelClass(entry) {
	if (!entry || !TIERS.has(entry.level)) return "";
	return entry.prominent ? `gl-level-${entry.level} gl-prominent` : `gl-level-${entry.level}`;
}

export function scalarLevel(payload, field) {
	const levels = payload && payload._levels;
	return (levels && levels[field]) || null;
}

export function itemLevel(payload, key, field) {
	const levels = payload && payload._levels;
	const item = levels && levels[key];
	return (item && item[field]) || null;
}

// Grade a value the server computed no `_levels` for (percpu's synthetic
// `CPU*` mean row) against published `{careful, warning, critical}` limits.
// Port of `thresholds_v5.compute_level`, "high" direction: most severe first,
// `value >= limit` wins. Returns a `levelClass`-ready entry, or null when
// there is nothing to grade against -- no colour, as the TUI.
export function computeLevel(value, thresholds) {
	if (!thresholds || typeof value !== "number" || Number.isNaN(value)) return null;
	let graded = false;
	for (const tier of ["critical", "warning", "careful"]) {
		const limit = thresholds[tier];
		if (typeof limit !== "number") continue;
		graded = true;
		if (value >= limit) return { level: tier, prominent: false };
	}
	return graded ? { level: "ok", prominent: false } : null;
}

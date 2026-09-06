// Glances v5 WebUI — the `_levels` payload field to a CSS class.
//
// The ONLY place tier semantics live. Components ask this module; they never
// test `level === "critical"` themselves, or the redesign drifts from the TUI
// one component at a time across 32 ports.
//
// Ported from the TUI contract (glances/outputs/curses_renderer_v5.py):
//   - four tiers: ok, careful, warning, critical
//   - `prominent` means a BACKGROUND highlight, not a different hue
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

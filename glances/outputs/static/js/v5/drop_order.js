// Glances v5 WebUI -- the container table's column drop order, the TUI's.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it.
//
// A copy of `_DROP_ORDER` (glances/plugins/containers/render_curses_v5.py:60):
// the browser cannot import Python. `name`, `cpu` and `mem` are deliberately
// absent -- they are what the block is for, and the TUI never drops them.
// tests/test_webui_v5_containers_drop_order_drift.py compares the two copies;
// never edit one side alone.
export const CONTAINERS_DROP_ORDER = [
	"command",
	"ports",
	"memory_max",
	"pod",
	"engine",
	"diskio",
	"networkio",
	"uptime",
	"status",
];

// The shape resolveDegrade() (degrade.js) consumes: one cumulative flag per
// step, applied in order, until the block fits. Keyed `drop_<column>` so a
// block's flag set never collides with the shell's own zone flags.
export function dropCascade(order) {
	return order.map((column) => ({ key: `drop_${column}`, value: true }));
}

// The inverse: the column names a resolved flag set hides. Every block with a
// width cascade needs this (containers, processlist, alert), so the `drop_`
// prefix convention is decoded here once rather than in each of them.
// Non-`drop_` keys are ignored, so a flag set mixing in a zone-level flag is
// harmless.
export function droppedColumns(flags) {
	const dropped = new Set();
	for (const [key, value] of Object.entries(flags || {})) {
		if (value && key.startsWith("drop_")) dropped.add(key.slice("drop_".length));
	}
	return dropped;
}

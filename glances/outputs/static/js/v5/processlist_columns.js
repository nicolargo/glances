// Glances v5 WebUI -- which processlist columns are visible.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it.
//
// Unlike `containers_columns.js`, processlist has no DATA-driven hiding --
// every one of its 12 fixed columns is always present in the payload
// (processlist/render_curses_v5.py has no `disable_stats`-style config
// knob). Only the WIDTH-driven cascade in `drop_order.js` ever hides one.

// A copy of `_DROP_ORDER` (glances/plugins/processlist/render_curses_v5.py:89):
// the browser cannot import Python. `CPU%`, `MEM%`, `R/s`, `W/s` and
// `Command` are deliberately absent -- they are never dropped.
// `Command` is the protected TAIL here, the opposite of `containers`, whose
// own `command` column is the FIRST one dropped -- both mirror their own
// terminal renderer, and this is not an inconsistency to "fix".
// tests/test_webui_v5_processlist_drop_order_drift.py compares the two
// copies; never edit one side alone.
export const PROCESSLIST_DROP_ORDER = ["VIRT", "TIME+", "RES", "USER", "PID", "THR", "S", "NI"];

// The shape resolveDegrade() (degrade.js) consumes, via dropCascade() in
// drop_order.js: one cumulative `drop_<column>` flag per step. This plugin
// has no data-driven hiding to union in (see the module comment above), so
// this is the whole story -- unlike containers_columns.js's hiddenColumns(),
// which also takes `rows`/`disableStats`.
export function hiddenColumns(flags) {
	const hidden = new Set();
	for (const [key, value] of Object.entries(flags || {})) {
		if (value && key.startsWith("drop_")) hidden.add(key.slice("drop_".length));
	}
	return hidden;
}

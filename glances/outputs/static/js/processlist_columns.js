// Glances v5 WebUI -- which processlist columns are visible.
//
// Pure: no DOM and no fetch, so `node --test` can load it.
//
// Two families, as in `containers_columns.js`: DATA-driven (the one config
// knob, `[processlist] disable_virtual_memory`, published in the payload as
// `disable_virtual_memory`) and WIDTH-driven (the cascade in `drop_order.js`).

import { droppedColumns } from "./drop_order.js";

// A copy of `_DROP_ORDER` (glances/plugins/processlist/render_curses.py:89):
// the browser cannot import Python. `CPU%`, `MEM%`, `R/s`, `W/s` and
// `Command` are deliberately absent -- they are never dropped.
// `Command` is the protected TAIL here, the opposite of `containers`, whose
// own `command` column is the FIRST one dropped -- both mirror their own
// terminal renderer, and this is not an inconsistency to "fix".
// tests/test_webui_processlist_drop_order_drift.py compares the two
// copies; never edit one side alone.
export const PROCESSLIST_DROP_ORDER = ["CPU", "VIRT", "TIME+", "RES", "USER", "PID", "THR", "S", "NI"];

// The union of both families: a column the config hides cannot come back when
// the window widens.
export function hiddenColumns(flags, disableVirtualMemory = false) {
	const hidden = droppedColumns(flags);
	if (disableVirtualMemory) hidden.add("VIRT");
	return hidden;
}

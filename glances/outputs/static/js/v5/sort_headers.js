// Glances v5 WebUI -- clickable sort headers (shared sort design, 2026-09-30).
//
// Clicking a header asks the server to sort by that column's engine key
// (`requestSort`). The sort is ONE server-wide key: processes, programs,
// containers and VMs all follow it, as they do in the TUI.
//
// The maps below are copies of the TUI's own header maps -- the browser
// cannot import Python -- held to them by tests/test_webui_v5_sort_drift.py.
// The process/program map lives in process_shared.js (`HEADER_SORT_KEY`).

import { requestSort } from "./api.js";

// containers/render_curses_v5.py `_HEADER_SORT_KEY`.
export const CONTAINERS_HEADER_SORT_KEY = {
	CONTAINER: "name",
	"CPU%": "cpu_percent",
	MEM: "memory_percent",
};

// vms/render_curses_v5.py `_HEADER_SORT_FIELD`.
export const VMS_HEADER_SORT_KEY = {
	Name: "name",
	"CPU%": "cpu_percent",
	"MEM/MAX": "memory_percent",
};

/**
 * The attributes of one header cell: the underline when `label` is the live
 * sort column, and -- when `label` has an engine key at all -- the pointer,
 * a title and the click. A header with no key (VIRT, PID, Status...) gets the
 * underline flag only, always false, and stays inert.
 *
 * `hint` is appended to the title, for a header that already explains
 * another gesture (processlist's Command: click a ROW to pin).
 */
export function sortHeaderAttrs(map, liveKey, label, hint = null) {
	const key = map[label];
	const attrs = { class: { "gl-sorted": !!liveKey && key === liveKey, "gl-sortable": !!key } };
	if (!key) {
		if (hint) attrs.title = hint;
		return attrs;
	}
	attrs.title = hint ? `Sort by ${label}. ${hint}` : `Sort by ${label}`;
	attrs.onClick = () => requestSort(key);
	return attrs;
}

/** A mixin giving a block `sortAttrs(label, hint)` over `map`. */
export function sortHeadersMixin(map) {
	return {
		methods: {
			sortAttrs(label, hint = null) {
				return sortHeaderAttrs(map, this.serverArgs?.sort_processes_key, label, hint);
			},
		},
	};
}

// Glances v5 WebUI -- which container columns are visible.
//
// Pure: no DOM, no fetch, so `node --test` can load it. Logic inside a .vue
// file cannot be unit-tested, and these rules are the ones most likely to
// drift from the TUI, so they live here.
//
// Two unrelated families, kept apart on purpose (spec §5):
//   - DATA-DRIVEN: the data (or the config) makes a column irrelevant. No
//     measurement, no window size -- containers/render_curses_v5.py:286-292
//     and the `disable_stats` seed at :259.
//   - WIDTH-DRIVEN: the row does not fit, so the cascade in drop_order.js
//     hides the least useful column first. That is `flags` below.

// containers/render_curses_v5.py:286-292 plus the config's own list.
export function dataDrivenHidden(rows, disableStats) {
	const hidden = new Set(disableStats || []);
	const items = rows || [];
	// render_curses_v5.py:287-288 -- disabling `mem` takes `/MAX` with it:
	// a limit column with no value column would be meaningless.
	if (hidden.has("mem")) hidden.add("memory_max");
	// `show_engine`: strictly MORE than one distinct engine. An empty
	// collection has none, so the column is hidden -- as the TUI's `len({...})
	// > 1` also resolves to false.
	if (new Set(items.map((item) => String(item.engine ?? ""))).size <= 1) hidden.add("engine");
	// `show_pod`: any item with a pod name.
	if (!items.some((item) => item.pod_name)) hidden.add("pod");
	return hidden;
}

// The union of both families. Never the difference: a cascade flag can only
// ADD to what the data already made irrelevant, so a column the config
// disabled cannot come back when the window widens.
export function hiddenColumns(rows, disableStats, flags) {
	const hidden = dataDrivenHidden(rows, disableStats);
	for (const [key, value] of Object.entries(flags || {})) {
		if (value && key.startsWith("drop_")) hidden.add(key.slice("drop_".length));
	}
	return hidden;
}

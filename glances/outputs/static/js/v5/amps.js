// Glances v5 WebUI -- which amps rows exist, and how many lines they cost.
//
// amps/render_curses_v5.py:67-71 skips an AMP whose `result` is still `None`
// entirely, rather than rendering an empty row. AppShell.vue's row budget
// (ampsHeight(), row_budget.js's `ampsHeight` input) and PluginAmps.vue's own
// `rows` must agree on exactly which items that leaves -- sharing this
// predicate is what makes them agree by construction instead of by
// coincidence. Kept in its own module, not part of either `.vue` file: a
// `.vue` file cannot be imported under node (see full_quicklook.js), and
// AppShell.vue is one.
export function ampsVisibleRows(data) {
	return (data || []).filter((item) => item.result !== null && item.result !== undefined);
}

// amps/render_curses_v5.py builds one Row per RESULT LINE and no header row
// (module docstring: "NO TITLE ROW and no column header") -- the natural
// height row_budget.js's `planRightColumn()` must be told about is the total
// line count over the visible rows above, not the item count and not +1 for
// a header this block never paints.
export function ampsLineCount(data) {
	return ampsVisibleRows(data).reduce((total, item) => total + String(item.result).split("\n").length, 0);
}

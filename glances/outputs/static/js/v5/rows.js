// Glances v5 WebUI -- row helpers shared by the collection components.
//
// Pure: no DOM, no fetch, no imports, so `node --test` can load it; logic in
// a .vue file cannot be unit-tested. Only what at least two components use
// lives here -- a skip rule used by one component stays in that component.

// The name a row displays: the configured alias when there is one, otherwise
// the raw primary key. Display only: `_levels` and the row key stay on the
// RAW key (base_v5.py `_apply_alias()`), exactly as in the TUI renderers.
export function displayName(item, keyField) {
	const alias = item && item.alias;
	if (typeof alias === "string" && alias !== "") return alias;
	const key = item ? item[keyField] : undefined;
	return key === undefined || key === null ? "" : String(key);
}

// Comparator for the TUI renderers' `sorted(items, key=lambda it:
// str(it.get(field, "")))`: plain code-unit order ("B" before "a"), never
// localeCompare(), whose collation would order rows differently from the
// terminal. Array.prototype.sort is stable, like sorted().
export function byText(field) {
	return (a, b) => {
		const x = String(a[field] ?? "");
		const y = String(b[field] ?? "");
		return x < y ? -1 : x > y ? 1 : 0;
	};
}

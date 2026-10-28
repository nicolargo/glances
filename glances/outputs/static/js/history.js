// Glances v5 WebUI -- the history of a field, shown in a popup on click.
//
// Three parts, none of which a plugin component has to know about:
//
// 1. `historyState`: which plugin fields are clickable (`history: True` in
//    the schema, and only when the server keeps a history at all), and the
//    field whose curve is currently open.
// 2. `v-history`, a directive a plugin puts on the cell showing a value. It
//    makes the cell a link when its field is historised and does nothing
//    otherwise, so a plugin declares WHAT a cell is, never whether history is
//    available.
// 3. HistoryModal.vue (mounted once by AppShell) reads `historyState.target`.

import { reactive } from "vue";
import { getJson } from "./api.js";
import { fetchSchemas } from "./labels.js";

export const historyState = reactive({
	// plugin name -> {historised field: schema unit}. {} when history is off.
	fields: {},
	// {plugin, field, item?, title} while a popup is open, null otherwise.
	target: null,
});

export function isHistoryField(plugin, field) {
	return !!historyState.fields[plugin] && field in historyState.fields[plugin];
}

export function openHistory(target) {
	historyState.target = target;
}

export function closeHistory() {
	historyState.target = null;
}

/**
 * Plugin name -> {historised field: unit}, or {} when nothing can be shown.
 *
 * `/status` says whether the server keeps a history at all (`history_size=0`
 * and `--disable-history` leave no store): the fields are only clickable when
 * it does. Any failure means "no history" -- the page is merely not clickable.
 */
export async function resolveHistoryFields() {
	try {
		const [status, schemas] = await Promise.all([getJson("status"), fetchSchemas()]);
		if (!status || status.history !== true) return {};
		const fields = {};
		for (const [plugin, schema] of Object.entries(schemas || {})) {
			const historised = Object.entries(schema || {}).filter(([, desc]) => desc && desc.history === true);
			if (historised.length) fields[plugin] = Object.fromEntries(historised.map(([name, desc]) => [name, desc.unit]));
		}
		return fields;
	} catch {
		return {};
	}
}

/**
 * `GET /api/5/<plugin>/history` narrowed to one series, as `[{t, v}]` with
 * the gaps (`null`) kept: the chart breaks the line there.
 */
export async function fetchSeries({ plugin, field, item }) {
	const query = new URLSearchParams({ field });
	if (item !== undefined && item !== null) query.set("item", item);
	const data = await getJson(`api/5/${encodeURIComponent(plugin)}/history?${query}`);
	let values = data.series?.[field];
	// A collection nests its series by item; a scalar plugin does not.
	if (values && !Array.isArray(values)) values = values[item];
	if (!Array.isArray(values)) return [];
	return data.timestamps.map((t, i) => ({ t, v: values[i] }));
}

function sync(el, binding) {
	const spec = binding.value;
	const on = !!spec && isHistoryField(spec.plugin, spec.field);
	if (on === !!el._glHistory) {
		el._glHistory = on ? spec : null;
		return;
	}
	if (on) {
		el.classList.add("gl-history-link");
		el.setAttribute("tabindex", "0");
		el.setAttribute("role", "button");
		el.setAttribute("aria-haspopup", "dialog");
		el._glClick = () => openHistory({ ...el._glHistory });
		el._glKey = (event) => {
			if (event.key === "Enter" || event.key === " ") {
				event.preventDefault();
				el._glClick();
			}
		};
		el.addEventListener("click", el._glClick);
		el.addEventListener("keydown", el._glKey);
	} else {
		el.classList.remove("gl-history-link");
		el.removeAttribute("tabindex");
		el.removeAttribute("role");
		el.removeAttribute("aria-haspopup");
		el.removeEventListener("click", el._glClick);
		el.removeEventListener("keydown", el._glKey);
	}
	el._glHistory = on ? spec : null;
}

// `updated` re-reads the binding: a collection row keeps its element while
// its item changes, and the fields arrive after the first paint.
export const vHistory = {
	mounted: sync,
	updated: sync,
	beforeUnmount(el) {
		sync(el, { value: null });
	},
};

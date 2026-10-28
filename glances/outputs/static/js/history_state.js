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
//
// The API calls are in history.js, which stays free of Vue.

import { reactive } from "vue";

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

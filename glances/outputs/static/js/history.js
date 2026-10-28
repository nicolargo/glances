// Glances v5 WebUI -- the API side of the history popups.
//
// Kept free of Vue so it runs under `node --test` (the reactive state and the
// `v-history` directive live in history_state.js).

import { getJson } from "./api.js";
import { fetchSchemas } from "./labels.js";

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

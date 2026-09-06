// Glances v5 WebUI -- field labels, resolved from the plugin schema.
//
// `/api/5/<plugin>/info` serves `fields_description`. The schema does not
// change at runtime, so it is fetched once per plugin and cached.
//
// The precedence mirrors field_label() in
// glances/outputs/curses_renderer_v5.py:243 exactly: short_name -> label ->
// field name. Reproducing it is the point: a label improved in the schema
// then improves the TUI and the WebUI together, and a plugin component
// writes no labels at all.

import { getJson } from "./api.js";

const cache = new Map();

export async function resolveLabels(pluginName) {
	if (cache.has(pluginName)) return cache.get(pluginName);

	let schema;
	try {
		schema = await getJson(`api/5/${pluginName}/info`);
	} catch {
		// A missing label must never blank a value: fall back to field names.
		// The empty result is cached like any other, i.e. a transient failure at
		// boot pins field-name labels for the tab's life -- acceptable only
		// while resolveLabels() is called once per page load (AppShell.mounted).
		cache.set(pluginName, {});
		return {};
	}

	const labels = {};
	for (const [field, desc] of Object.entries(schema || {})) {
		const label = (desc && (desc.short_name || desc.label)) || undefined;
		if (label) labels[field] = label;
	}
	cache.set(pluginName, labels);
	return labels;
}

export function labelFor(labels, field) {
	return (labels && labels[field]) || field;
}

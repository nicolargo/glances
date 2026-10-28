// Glances v5 WebUI -- field labels, resolved from the plugin schema.
//
// `/api/5/all/info` serves every plugin's `fields_description` in one
// request. The schema does not change at runtime, so it is fetched once per
// page load (AppShell.mounted).
//
// The precedence mirrors field_label() in
// glances/outputs/curses_renderer.py:243 exactly: short_name -> label ->
// field name. Reproducing it is the point: a label improved in the schema
// then improves the TUI and the WebUI together, and a plugin component
// writes no labels at all.

import { getJson } from "./api.js";

function labelsFromSchema(schema) {
	const labels = {};
	for (const [field, desc] of Object.entries(schema || {})) {
		const label = (desc && (desc.short_name || desc.label)) || undefined;
		if (label) labels[field] = label;
	}
	return labels;
}

// Concurrent callers (the labels and the history fields, resolved together at
// mount) share ONE request; it is not cached past the response, so a later
// call still re-fetches.
let inflight = null;
export function fetchSchemas() {
	if (!inflight) {
		inflight = getJson("api/5/all/info").finally(() => {
			inflight = null;
		});
	}
	return inflight;
}

export async function resolveAllLabels() {
	let schemas;
	try {
		schemas = await fetchSchemas();
	} catch {
		// A missing label must never blank a value: fall back to field names.
		// A transient failure here pins field-name labels for the tab's life --
		// acceptable because this is ONE request per page load, where an
		// earlier version made one per plugin.
		return {};
	}
	const labels = {};
	for (const [plugin, schema] of Object.entries(schemas || {})) {
		labels[plugin] = labelsFromSchema(schema);
	}
	return labels;
}

export function labelFor(labels, field) {
	return (labels && labels[field]) || field;
}

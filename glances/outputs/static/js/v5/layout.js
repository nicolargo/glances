// Glances v5 WebUI -- page layout: which registered plugins render, and where.
//
// Pure: no DOM, no fetch, no imports. It is not in plugins/index.js because
// that module imports .vue files, which `node --test` cannot load -- logic
// placed there could never be unit-tested.

export function visiblePlugins(registry, names) {
	// `names` is /api/5/pluginslist: the plugins the server instantiated. A
	// disabled plugin is never instantiated (glances/main_v5.py:372), so it is
	// never in /api/5/all either, and fetchAll() would read its absence as
	// "loading" forever -- `cloud` is disabled by default.
	//
	// Anything but an array means the list could not be read: render the whole
	// registry, which is exactly the behaviour before this function existed.
	if (!Array.isArray(names)) return registry;
	const enabled = new Set(names);
	// Filter the REGISTRY, not the names: pluginslist is sorted server-side,
	// and the registry order is the layout order.
	return registry.filter((entry) => enabled.has(entry.name));
}

export function groupBySlot(entries) {
	const slots = {};
	for (const entry of entries) {
		if (!slots[entry.slot]) slots[entry.slot] = [];
		slots[entry.slot].push(entry);
	}
	return slots;
}

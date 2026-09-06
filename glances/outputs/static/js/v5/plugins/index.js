// Glances v5 WebUI -- the plugin registry.
//
// Adding a plugin is ONE new .vue file plus ONE entry here. Before this,
// AppShell named every plugin in four places (import, components map, spec
// list, template): 32 ports x 4 edits to one file is 32 merge-conflict
// surfaces, and it contradicts the project's rule to prefer discovery
// mechanisms over hardcoded lists that require touching a central file.
//
// `spec` is what the service layer validates the payload against. `shape` is
// "scalar" or "collection" -- the only two payload shapes v5 has.

import PluginMem from "../PluginMem.vue";
import PluginNetwork from "../PluginNetwork.vue";

export const PLUGINS = [
	{
		name: "mem",
		component: PluginMem,
		spec: { shape: "scalar", required: ["percent", "total"] },
	},
	{
		name: "network",
		component: PluginNetwork,
		spec: { shape: "collection", required: ["interface_name"] },
	},
];

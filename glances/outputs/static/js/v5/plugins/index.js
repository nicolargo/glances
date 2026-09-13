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
//
// `slot` is where the page puts the component: "header-left",
// "header-right", "top", "left" or "right" -- the TUI's HEADER_SLOT_LEFT,
// HEADER_SLOT_RIGHT, TOP_SLOT, LEFT_SLOT and RIGHT_SLOT
// (glances/outputs/curses_renderer_v5.py). Order within a slot is THIS
// list's order, so keep entries in the TUI's order.
//
// This is a second copy of those tuples (G9-5 decision D4). Two tests keep it
// honest: test_every_slot_orders_its_plugins_like_the_tui fails on a plugin
// in the wrong slot or out of order, and
// test_the_registry_renders_every_registered_plugin fails on a missing or
// misspelled slot (such an entry renders in no zone at all). There is no
// fallback slot, unlike the TUI's slot_for().

import PluginMem from "../PluginMem.vue";
import PluginNetwork from "../PluginNetwork.vue";
import PluginLoad from "../PluginLoad.vue";
import PluginMemswap from "../PluginMemswap.vue";
import PluginQuicklook from "../PluginQuicklook.vue";
import PluginCpu from "../PluginCpu.vue";
import PluginPercpu from "../PluginPercpu.vue";
import PluginNpu from "../PluginNpu.vue";
import PluginMpp from "../PluginMpp.vue";
import PluginGpu from "../PluginGpu.vue";
import PluginSystem from "../PluginSystem.vue";
import PluginUptime from "../PluginUptime.vue";
import PluginNow from "../PluginNow.vue";
import PluginIp from "../PluginIp.vue";
import PluginCloud from "../PluginCloud.vue";
import PluginDiskio from "../PluginDiskio.vue";
import PluginFs from "../PluginFs.vue";
import PluginFolders from "../PluginFolders.vue";
import PluginWifi from "../PluginWifi.vue";
import PluginConnections from "../PluginConnections.vue";
import PluginIrq from "../PluginIrq.vue";
import PluginRaid from "../PluginRaid.vue";
import PluginSmart from "../PluginSmart.vue";
import PluginSensors from "../PluginSensors.vue";
import PluginPorts from "../PluginPorts.vue";

export const PLUGINS = [
	// The header plugins declare `required: []`: a missing guard field
	// (hostname, seconds, custom) is the component's hide rule -- the TUI
	// renders nothing -- not a shape error for validate() to display.
	{
		name: "system",
		component: PluginSystem,
		slot: "header-left",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "ip",
		component: PluginIp,
		slot: "header-left",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "uptime",
		component: PluginUptime,
		slot: "header-right",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "cloud",
		component: PluginCloud,
		slot: "header-right",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "now",
		component: PluginNow,
		slot: "header-right",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "quicklook",
		component: PluginQuicklook,
		slot: "top",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "cpu",
		component: PluginCpu,
		slot: "top",
		spec: { shape: "scalar", required: ["total"] },
	},
	{
		name: "percpu",
		component: PluginPercpu,
		slot: "top",
		spec: { shape: "collection", required: ["cpu_number"] },
	},
	{
		name: "npu",
		component: PluginNpu,
		slot: "top",
		spec: { shape: "collection", required: ["npu_id"] },
	},
	{
		name: "mpp",
		component: PluginMpp,
		slot: "top",
		spec: { shape: "collection", required: ["engine_id"] },
	},
	{
		name: "gpu",
		component: PluginGpu,
		slot: "top",
		spec: { shape: "collection", required: ["gpu_id"] },
	},
	{
		name: "mem",
		component: PluginMem,
		slot: "top",
		spec: { shape: "scalar", required: ["percent", "total"] },
	},
	{
		name: "memswap",
		component: PluginMemswap,
		slot: "top",
		spec: { shape: "scalar", required: ["total"] },
	},
	{
		name: "load",
		component: PluginLoad,
		slot: "top",
		spec: { shape: "scalar", required: ["min1"] },
	},
	{
		name: "network",
		component: PluginNetwork,
		slot: "left",
		spec: { shape: "collection", required: ["interface_name"] },
	},
	{
		name: "ports",
		component: PluginPorts,
		slot: "left",
		spec: { shape: "collection", required: ["indice"] },
	},
	{
		name: "wifi",
		component: PluginWifi,
		slot: "left",
		spec: { shape: "collection", required: ["ssid"] },
	},
	{
		name: "connections",
		component: PluginConnections,
		slot: "left",
		spec: { shape: "scalar", required: [] },
	},
	{
		name: "diskio",
		component: PluginDiskio,
		slot: "left",
		spec: { shape: "collection", required: ["disk_name"] },
	},
	{
		name: "fs",
		component: PluginFs,
		slot: "left",
		spec: { shape: "collection", required: ["mnt_point"] },
	},
	{
		name: "irq",
		component: PluginIrq,
		slot: "left",
		spec: { shape: "collection", required: ["irq_line"] },
	},
	{
		name: "folders",
		component: PluginFolders,
		slot: "left",
		spec: { shape: "collection", required: ["path"] },
	},
	{
		name: "raid",
		component: PluginRaid,
		slot: "left",
		spec: { shape: "collection", required: ["name"] },
	},
	{
		name: "smart",
		component: PluginSmart,
		slot: "left",
		spec: { shape: "collection", required: ["name"] },
	},
	{
		name: "sensors",
		component: PluginSensors,
		slot: "left",
		spec: { shape: "collection", required: ["label"] },
	},
];

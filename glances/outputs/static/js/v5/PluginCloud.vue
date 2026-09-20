<template>
	<span v-show="error || (platform && name)" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<!-- .gl-header is already bold: the TUI's HEADER role + bold=True. -->
			<span class="gl-header">{{ platform }}</span>
			<span>{{ summary }}</span>
		</template>
	</span>
</template>

<script>
import { PLUGIN_PROPS } from "./plugin_props.js";
const UNKNOWN = "Unknown";

export default {
	name: "PluginCloud",
	props: { ...PLUGIN_PROPS },
	computed: {
		// glances/plugins/cloud/render_curses_v5.py: platform AND name are
		// mandatory (#2485), or nothing renders.
		platform() {
			return this.payload?.platform || "";
		},
		name() {
			return this.payload?.name || "";
		},
		// `payload.get(key, "Unknown")` falls back on an ABSENT key only, hence
		// `in` rather than a null check. The TUI's summary opens with a space
		// because its painter adds another between cells; here .gl-inline's
		// gap does that, so the leading space is dropped.
		summary() {
			const p = this.payload || {};
			const part = (key) => (key in p ? String(p[key]) : UNKNOWN);
			return `${part("type")} instance ${part("name")} (${part("region")})`;
		},
	},
};
</script>

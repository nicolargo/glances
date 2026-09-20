<template>
	<span v-show="error || text" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<span>Uptime:</span>
			<span>{{ text }}</span>
		</template>
	</span>
</template>

<script>
import { formatSeconds } from "./format.js";
import { PLUGIN_PROPS } from "./plugin_props.js";

export default {
	name: "PluginUptime",
	props: { ...PLUGIN_PROPS },
	computed: {
		// glances/plugins/uptime/render_curses_v5.py: `seconds is None` -> no
		// block. "Uptime:" is a block tag, not a field label, and the TUI does
		// not read it from the schema either (spec §7.3).
		text() {
			const seconds = this.payload?.seconds;
			return seconds === null || seconds === undefined ? "" : formatSeconds(seconds);
		},
	},
};
</script>

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

export default {
	name: "PluginUptime",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the root.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// glances/plugins/uptime/render_curses_v5.py: `seconds is None` -> no
		// block. "Uptime:" is a block tag, not a field label, and the TUI does
		// not read it from the schema either (G9-5 spec §7.3).
		text() {
			const seconds = this.payload?.seconds;
			return seconds === null || seconds === undefined ? "" : formatSeconds(seconds);
		},
	},
};
</script>

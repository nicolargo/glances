<template>
	<span v-show="error || hostname" class="gl-inline">
		<!--
			v-show, not v-if, on the root: a hidden block stays in the DOM, so it
			keeps its data-plugin (the probe finds it) and takes no header gap.
			The TUI renders [] under the same condition. This comment sits INSIDE
			the root on purpose: the build keeps template comments, and one
			placed before the <span> would make a second root node, which stops
			Vue from putting data-plugin on the component at all.
		-->
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<template v-else>
			<span class="gl-header">{{ hostname }}</span>
			<span v-if="hrName" class="gl-truncate" :title="hrName">{{ hrName }}</span>
		</template>
	</span>
</template>

<script>
export default {
	name: "PluginSystem",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the root.
		serverArgs: { type: Object, default: () => ({}) },
		// `hide_os_info` (glances_curses_v5.py:87) is read below, in `hrName`.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// glances/plugins/system/render_curses_v5.py: no hostname, no block.
		// `hr_name` already carries `[system] system_info_msg`, applied by the
		// model.
		hostname() {
			return this.payload?.hostname || "";
		},
		// `hide_os_info` is the TUI's header step (2)
		// (glances_curses_v5.py:87): static host metadata is worth less under
		// width pressure than any live metric. G9-5 D3 said the browser would
		// not reproduce this; the 2026-09-12 spec reverses that.
		hrName() {
			if (this.degrade.hide_os_info) return "";
			return this.payload?.hr_name || "";
		},
	},
};
</script>

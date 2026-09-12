<template>
	<span v-show="error || custom" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<span v-else>{{ custom }}</span>
	</span>
</template>

<script>
export default {
	name: "PluginNow",
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
		// glances/plugins/now/render_curses_v5.py: the `custom` string only
		// (`[global] strftime_format` is applied by the model); `iso` is
		// REST-only.
		custom() {
			return this.payload?.custom || "";
		},
	},
};
</script>

<template>
	<span v-show="error || custom" class="gl-inline">
		<span v-if="error" class="gl-level-critical">{{ error }}</span>
		<span v-else>{{ custom }}</span>
	</span>
</template>

<script>
import { PLUGIN_PROPS } from "./plugin_props.js";
export default {
	name: "PluginNow",
	props: { ...PLUGIN_PROPS },
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

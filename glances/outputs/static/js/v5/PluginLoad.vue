<template>
	<article class="gl-plugin" aria-label="LOAD">
		<!-- aria-label: once loaded the title is a <dt>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<!--
			The title stands alone only until the first payload. Once data exists
			it is the first (label, value) pair of the grid, as on the TUI's line
			1 (`LOAD 4core`): the core count shares the right-aligned value
			column, in the default colour like the TUI's plain cell.
		-->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">LOAD</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<dt class="gl-header">LOAD</dt>
				<dd>{{ coreLabel }}</dd>
				<template v-for="(stat, i) in rows" :key="i">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";
import { PLUGIN_PROPS } from "./plugin_props.js";

const FIELDS = ["min1", "min5", "min15"];

export default {
	name: "PluginLoad",
	props: { ...PLUGIN_PROPS },
	computed: {
		// `cpucore` is internal: true in the schema -- the TUI shows it as the
		// header's "{N}core" suffix and never as a row. Same here.
		coreLabel() {
			const cores = this.payload?.cpucore;
			return typeof cores === "number" && cores > 0 ? `${Math.trunc(cores)}core` : "";
		},
		rows() {
			return FIELDS.map((field) => {
				const value = this.payload?.[field];
				return { field, value: typeof value === "number" ? value.toFixed(2) : "-" };
			});
		},
	},
	methods: { levelClass, scalarLevel, labelFor },
};
</script>

<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">LOAD</h2>
			<span v-if="coreLabel" class="gl-muted">{{ coreLabel }}</span>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
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

const FIELDS = ["min1", "min5", "min15"];

export default {
	name: "PluginLoad",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
	},
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

<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">MEM</h2>
			<span v-if="payload" :class="levelClass(scalarLevel(payload, 'percent'))">{{
				formatPercent(payload.percent)
			}}</span>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<template v-for="(stat, i) in col1" :key="i">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
			<dl>
				<template v-for="(stat, i) in col2" :key="i">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { formatBytes, formatPercent } from "./format.js";
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";

const COL2_FIELDS = ["active", "inactive", "buffers", "cached"];

export default {
	name: "PluginMem",
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
		// Mirrors glances/plugins/mem/render_curses_v5.py: `available` (Linux,
		// macOS) is preferred over `used`; `used` is the fallback for
		// platforms that don't publish `available` (e.g. some BSDs).
		availOrUsedField() {
			return this.payload && this.payload.available != null ? "available" : "used";
		},
		col1() {
			return ["total", this.availOrUsedField, "free"].map((field) => this.statFor(field));
		},
		col2() {
			return COL2_FIELDS.map((field) => this.statFor(field));
		},
	},
	methods: {
		levelClass,
		scalarLevel,
		labelFor,
		formatPercent,
		statFor(field) {
			// Optional chaining: Vue devtools evaluates computeds eagerly when
			// inspecting, outside the template's `v-else` payload guard.
			// formatBytes(undefined) already renders "-".
			return { field, value: formatBytes(this.payload?.[field]) };
		},
	},
};
</script>

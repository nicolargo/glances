<template>
	<article class="gl-plugin" aria-label="MEM">
		<!-- aria-label: once loaded the title is a <dt>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<!--
			The title stands alone only until the first payload. Once data exists
			it is the first (label, value) pair of column 1, as on the TUI's line
			1 (`MEM 53.2% | active 5.8G`): the percent shares the right-aligned
			value column and both columns have four lines.
		-->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">MEM</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<dt class="gl-header">MEM</dt>
				<dd :class="levelClass(scalarLevel(payload, 'percent'))">{{ formatPercent(payload.percent) }}</dd>
				<template v-for="(stat, i) in col1" :key="i">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
			<dl v-if="col2.length">
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
		// `mem_cols` (1 or 2) -- the TUI's first degradation notch
		// (glances_curses_v5.py:62). Anything else means "no degradation".
		degrade: { type: Object, default: () => ({}) },
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
		// mem_cols=1 (TUI step a) drops the whole 2nd column. In the TUI that
		// also drops the line-1 `active` pair; in the WebUI `active` IS the
		// first pair of this column (G9-5 A1), so one rule covers both.
		col2() {
			if (this.degrade.mem_cols === 1) return [];
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

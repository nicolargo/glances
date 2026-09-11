<template>
	<article class="gl-plugin" aria-label="SWAP">
		<!-- aria-label: once loaded the title is a <dt>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<!--
			The title stands alone only until the first payload. Once data exists
			it is the first (label, value) pair of the grid, as on the TUI's line
			1 (`SWAP 25.0%`): the percent shares the right-aligned value column.
		-->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">SWAP</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<!-- `gl-col-rate`: sin/sout are formatRate() values, up to 9 characters. -->
			<dl class="gl-col-rate">
				<dt class="gl-header">SWAP</dt>
				<dd :class="levelClass(scalarLevel(payload, 'percent'))">{{ formatPercent(payload.percent) }}</dd>
				<template v-for="(stat, i) in rows" :key="i">
					<dt class="gl-header">{{ labelFor(labels, stat.field) }}</dt>
					<dd :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { formatBytes, formatPercent, formatRate } from "./format.js";
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";

export default {
	name: "PluginMemswap",
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
		// `used` and `free` are deliberately absent -- see
		// glances/plugins/memswap/render_curses_v5.py: v5 trades that
		// redundant pair for the live paging rates. Adding them back here
		// would diverge from v5, not return to v4.
		rows() {
			return [
				{ field: "total", value: formatBytes(this.payload?.total) },
				{ field: "sin", value: formatRate(this.payload?.sin) },
				{ field: "sout", value: formatRate(this.payload?.sout) },
			];
		},
	},
	methods: { levelClass, scalarLevel, labelFor, formatPercent },
};
</script>

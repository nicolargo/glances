<template>
	<article class="gl-plugin" aria-label="WIFI">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">WIFI</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- The TUI's header row: block title, then the schema's label. -->
				<tr>
					<th class="gl-header">WIFI</th>
					<th class="gl-header gl-num">{{ labelFor(labels, "quality_level") }}</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in rows" :key="item.ssid">
					<td>
						<span class="gl-name gl-truncate" :title="item.ssid">{{ item.ssid }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'quality_level')">{{ formatFixed0(item.quality_level) }}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatFixed0 } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { byText } from "./rows.js";

export default {
	name: "PluginWifi",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Mirrors wifi/render_curses_v5.py:82-94: sorted by ssid; skip an empty
		// ssid (v4 #1151) and a signal that is not a number (#1973).
		rows() {
			return (this.payload?.data || [])
				.filter((item) => item.ssid != null && item.ssid !== "" && Number.isFinite(item.quality_level))
				.sort(byText("ssid"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatFixed0,
	},
};
</script>

<style scoped>
/* One width budget for the whole left column (maintainer's aesthetic call,
 * 2026-09-12): the three-column blocks' name cap (18ch) plus the value column
 * wifi does not have (.gl-num's 9ch floor) and its cell gap. It replaces G9-6
 * D3's TUI width here (26ch, wifi/render_curses_v5.py _NAME_MAX_WIDTH).
 * A table column still shrinks to its content, so this equalises the MAXIMUM
 * width: a block whose names are all short renders narrower. */
.gl-plugin {
	--gl-name-width: calc(27ch + var(--gl-gap));
}
</style>

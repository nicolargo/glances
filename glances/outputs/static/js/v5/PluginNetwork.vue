<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">NETWORK</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<p v-else-if="!payload.data.length" class="gl-muted">no interface</p>
		<table v-else>
			<thead>
				<tr>
					<th
						v-for="column in COLUMNS"
						:key="column.field"
						class="gl-header"
						:class="{ 'gl-num': column.numeric }"
					>
						{{ labelFor(labels, column.field) }}
					</th>
				</tr>
			</thead>
			<tbody>
				<!-- The row key hardcodes `interface_name` on purpose: deriving it
				from `payload._key` yields `item[undefined]` against a server that
				does not publish `_key`, i.e. one duplicate key per row. -->
				<tr v-for="item in payload.data" :key="item.interface_name">
					<td
						v-for="column in COLUMNS"
						:key="column.field"
						:class="[cellClassFor(payload, item, column.field), { 'gl-num': column.numeric }]"
					>
						{{ column.format(item[column.field]) }}
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { formatRate } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";

// `numeric` puts the column under .gl-num: right-aligned, tabular digits and
// a 9ch floor, so a rate growing from "1.2K/s" to "10.2M/s" between two ticks
// does not resize the column under the reader's eyes.
const COLUMNS = [
	{ field: "interface_name", format: (v) => v },
	{ field: "bytes_recv", format: formatRate, numeric: true },
	{ field: "bytes_sent", format: formatRate, numeric: true },
];

export default {
	name: "PluginNetwork",
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
		// A computed, not data(): data() is made deeply reactive, so anything
		// returned from it reaches the template as a Proxy. Inert for this
		// descriptor (functions are not proxied), but this is the shape the
		// next collection components copy -- and there it matters, see
		// AppShell's `plugins`.
		COLUMNS: () => COLUMNS,
	},
	methods: {
		labelFor,
		cellClassFor,
	},
};
</script>

<style scoped>
.gl-plugin table {
	border-collapse: collapse;
}
.gl-plugin th,
.gl-plugin td {
	padding: 0 var(--gl-gap) 0 0;
}
/* `:not(.gl-num)` is load-bearing, not decoration. Scoped styles compile to
   `.gl-plugin th[data-v-xxxx]` -- specificity (0,2,1) -- which beats the
   global `.gl-num` (0,1,0), so a plain `text-align: left` here would silently
   win and the numeric columns would never right-align. */
.gl-plugin th:not(.gl-num),
.gl-plugin td:not(.gl-num) {
	text-align: left;
}
</style>

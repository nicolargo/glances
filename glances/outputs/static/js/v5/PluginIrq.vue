<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's label. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "irq_rate") }}</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.irq_line">
					<td>
						<span class="gl-name gl-truncate" :title="item.irq_line">{{ item.irq_line }}</span>
					</td>
					<td class="gl-num">
						<span>{{ formatFixed0(item.irq_rate) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { labelFor } from "./labels.js";
import { formatFixed0 } from "./format.js";

const TITLE = "IRQ";

// The TUI keeps the five busiest lines (irq/render_curses_v5.py _TOP_N).
const TOP_N = 5;

export default {
	name: "PluginIrq",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// Ranking lives HERE, as it does in the TUI renderer: model_v5
		// publishes every IRQ line so exporters get the complete series, and
		// the display keeps the busiest five. A null rate (an item's first
		// cycle) sorts last rather than throwing. Copy the array first --
		// sort() mutates, and the payload is shared with every other consumer.
		rows() {
			return [...(this.payload?.data || [])]
				.sort((a, b) => (b.irq_rate || 0) - (a.irq_rate || 0))
				.slice(0, TOP_N);
		},
	},
	methods: { labelFor, formatFixed0 },
};
</script>

<style scoped>
/* The TUI's IRQ-line width (irq/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 24ch;
}
</style>

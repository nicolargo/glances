<template>
	<CollectionBlock title="MPP" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<!-- No #head slot: the TUI's first line is the title alone, with no
		column labels (mpp/render_curses_v5.py) -- same shape as `ports`
		(G9-7 D4). CollectionBlock renders no <thead> when the slot is absent. -->
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.engine_id">
					<td>{{ item.name }} {{ item.type }}</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'load')">{{ loadText(item) }}</span>
					</td>
					<!-- v4 omits the session cell entirely at zero -- not an empty
					string, a MISSING cell (mpp/render_curses_v5.py:52-55). -->
					<td v-if="item.sessions" class="gl-num">{{ item.sessions }} sess</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { formatPercent } from "./format.js";

export default {
	name: "PluginMpp",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: the TUI's first line is the title alone, with no
		// column labels to resolve through the schema.
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
		// Payload order -- the TUI does not sort (mpp/render_curses_v5.py).
		rows() {
			return (this.payload?.data || []).filter((item) => item && typeof item === "object");
		},
	},
	methods: {
		cellClassFor,
		// v4 parity: a null load renders "N/A" (mpp/render_curses_v5.py:47-48).
		// formatPercent's own missing marker is "-", so the null case is
		// resolved here rather than in the shared formatter.
		loadText(item) {
			return item.load == null ? "N/A" : formatPercent(item.load);
		},
	},
};
</script>

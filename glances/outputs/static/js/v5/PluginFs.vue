<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th class="gl-header gl-num">{{ labelFor(labels, valueField) }}</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "size") }}</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<!-- Keyed and coloured by the RAW mnt_point: the alias is display only. -->
				<tr v-for="item in rows" :key="item.mnt_point">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="nameOf(item)"><bdi>{{ nameOf(item) }}</bdi></span>
					</td>
					<!-- v4 parity: the used/free cell takes the `percent` tier, whatever
					free_space selects; Total is never coloured. -->
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'percent')">{{ formatBytes(item[valueField]) }}</span>
					</td>
					<td class="gl-num">
						<span>{{ formatBytes(item.size) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatBytes } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { byText, displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";

const TITLE = "FILE SYS";

export default {
	name: "PluginFs",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: `free_space` is read from the payload, not from
		// here -- /api/5/args misses a `[fs] free_space` set in the
		// configuration, which the model has already merged (fs/model_v5.py).
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// fs/render_curses_v5.py:75-76.
		valueField() {
			return this.payload?.free_space ? "free" : "used";
		},
		// fs/render_curses_v5.py:101-106: sorted by raw mount point, a row with
		// no mount point skipped.
		rows() {
			return (this.payload?.data || []).filter((item) => item.mnt_point).sort(byText("mnt_point"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatBytes,
		nameOf(item) {
			return displayName(item, "mnt_point");
		},
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (fs/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 18ch;
}
</style>

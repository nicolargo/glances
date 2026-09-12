<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th v-for="field in RATE_FIELDS" :key="field" class="gl-header gl-num">
					{{ labelFor(labels, field) }}
				</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<!-- Keyed and coloured by the RAW disk_name: the alias is display only. -->
				<tr v-for="item in rows" :key="item.disk_name">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="nameOf(item)"><bdi>{{ nameOf(item) }}</bdi></span>
					</td>
					<td v-for="field in RATE_FIELDS" :key="field" class="gl-num">
						<span :class="cellClassFor(payload, item, field)">{{ formatBytes(item[field]) }}</span>
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

const RATE_FIELDS = ["read_bytes", "write_bytes"];

const TITLE = "DISK I/O";

export default {
	name: "PluginDiskio",
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
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// A computed, not data(): data() would hand the template a deeply
		// reactive Proxy of the array.
		RATE_FIELDS: () => RATE_FIELDS,
		// Mirrors diskio/render_curses_v5.py:109-122: sorted by raw disk_name;
		// skip a row hide_zero still hides, a disk with no rate yet (cycle 1),
		// and a nameless one. Byte rates without "/s", the header carries it.
		rows() {
			return (this.payload?.data || [])
				.filter((item) => item.hidden !== true && item.read_bytes != null && item.write_bytes != null && item.disk_name)
				.sort(byText("disk_name"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatBytes,
		nameOf(item) {
			return displayName(item, "disk_name");
		},
	},
};
</script>

<style scoped>
/* G9-6 D3: the TUI's name width (diskio/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 18ch;
}
</style>

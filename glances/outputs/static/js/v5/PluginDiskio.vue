<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th v-for="field in rateFields" :key="field" class="gl-header gl-num">
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
					<td v-for="field in rateFields" :key="field" class="gl-num">
						<span :class="cellClassFor(payload, item, field)">{{ formatCell(item[field]) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatBytes, formatIops } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { byText, displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";
import { PLUGIN_PROPS } from "./plugin_props.js";

const RATE_FIELDS = ["read_bytes", "write_bytes"];
// The `B` key (v4 `_handle_diskio_iops`): operations per second instead of
// byte rates. Same two columns, a different pair of fields -- and the labels
// come from the schema, so swapping the pair swaps the header too.
const IOPS_FIELDS = ["read_count", "write_count"];

const TITLE = "DISK I/O";

export default {
	name: "PluginDiskio",
	components: { CollectionBlock },
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// A computed, not data(): data() would hand the template a deeply
		// reactive Proxy of the array.
		RATE_FIELDS: () => RATE_FIELDS,
		// The `B` key, through AppShell's `effectiveArgs`.
		iops() {
			return !!this.serverArgs.diskio_iops;
		},
		rateFields() {
			return this.iops ? IOPS_FIELDS : RATE_FIELDS;
		},
		// Mirrors diskio/render_curses_v5.py:109-122: sorted by raw disk_name;
		// skip a row hide_zero still hides, a disk with no rate yet (cycle 1),
		// and a nameless one. Byte rates without "/s", the header carries it.
		rows() {
			return (this.payload?.data || [])
				.filter(
					(item) =>
						item.hidden !== true &&
						this.rateFields.every((field) => item[field] != null) &&
						item.disk_name
				)
				.sort(byText("disk_name"));
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		// Byte rates and operation counts scale differently (1024 vs 1000) and
		// only one carries a unit -- see formatIops in format.js.
		formatCell(value) {
			return this.iops ? formatIops(value) : formatBytes(value);
		},
		formatBytes,
		nameOf(item) {
			return displayName(item, "disk_name");
		},
	},
};
</script>

<style scoped>
/* spec D3: the TUI's name width (diskio/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: calc(18 * var(--gl-col));
}
</style>

<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th v-if="combined" class="gl-header gl-num" colspan="2">{{ iops ? "IOR+W/s" : "R+W/s" }}</th>
				<th v-for="field in combined ? [] : rateFields" :key="field" class="gl-header gl-num">
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
					<!-- `T`: one summed column. No tier class -- each field has its
					own level and a sum belongs to neither (TUI twin: combined cell). -->
					<td v-if="combined" class="gl-num" colspan="2">
						<span>{{ formatCell(Number(item[rateFields[0]]) + Number(item[rateFields[1]])) }}</span>
					</td>
					<td v-for="field in combined ? [] : rateFields" :key="field" class="gl-num">
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
// The `L` key / --diskio-latency: mean ms per operation (v4 `diskio_latency`).
// `B` wins when both are on, v4's if/elif order (diskio/render_curses_v5.py).
const LATENCY_FIELDS = ["read_latency", "write_latency"];

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
		latency() {
			return !this.iops && !!this.serverArgs.diskio_latency;
		},
		rateFields() {
			if (this.iops) return IOPS_FIELDS;
			return this.latency ? LATENCY_FIELDS : RATE_FIELDS;
		},
		// The `T` key -- network's flag, so one key folds both blocks. Not in
		// latency mode: the sum of two per-operation means is not a latency.
		combined() {
			return !this.latency && !!this.serverArgs.network_sum;
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
		// only one carries a unit -- see formatIops in format.js. Latencies are
		// unitless ms counts, formatted the same way (v4 `auto_unit`).
		formatCell(value) {
			return this.iops || this.latency ? formatIops(value) : formatBytes(value);
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

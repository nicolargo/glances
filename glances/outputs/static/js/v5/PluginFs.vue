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
import { PLUGIN_PROPS } from "./plugin_props.js";

const TITLE = "FILE SYS";

export default {
	name: "PluginFs",
	components: { CollectionBlock },
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// fs/render_curses_v5.py:75-76.
		valueField() {
			// `serverArgs` here is AppShell's `effectiveArgs`, which seeds this
			// from the same payload metadata and lets the `F` key override it.
			return this.serverArgs.fs_free_space ? "free" : "used";
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
/* spec D3: the TUI's name width (fs/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: calc(18 * var(--gl-col));
}
</style>

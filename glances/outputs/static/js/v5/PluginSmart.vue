<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header row is ONE cell, the title; the empty <th> keeps
			the header aligned column by column with the body (the sensors and
			folders precedent). -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th class="gl-header gl-num"></th>
			</tr>
		</template>
		<template #body>
			<!-- One <tbody> per device (G9-7 D3). -->
			<tbody v-for="device in rows" :key="device.name">
				<tr>
					<!-- The device line spans both columns: it has no value. Its
					own cap is the block's full width, so it is set inline rather
					than through the component's --gl-name-width. -->
					<td colspan="2">
						<span class="gl-name gl-truncate" style="--gl-name-width: 34ch" :title="device.name">{{ device.name }}</span>
					</td>
				</tr>
				<!-- Keyed by position: an attribute name is not guaranteed unique
				across a device's list, and these rows are plain text with no
				component state. -->
				<tr v-for="(attr, index) in device.attributes" :key="index">
					<td>
						<span class="gl-name gl-truncate gl-subline" :title="attr.name">{{ attr.name }}</span>
					</td>
					<td class="gl-num"><span>{{ attr.value }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { formatAutoUnit } from "./format.js";
import { LARGE_VALUE_KEYS } from "./smart_keys.js";

const TITLE = "SMART disks";

export default {
	name: "PluginSmart",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: `smart` has no column label (no value header).
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
		// Payload order -- the plugin sorts the attributes itself (v4's own
		// order) and the TUI renderer does not re-sort.
		rows() {
			return (this.payload?.data || []).map((device) => ({
				name: String(device.name || ""),
				attributes: (device.attributes || []).map((attr) => ({
					// The leading space is the TUI's indent; .gl-subline keeps it.
					name: ` ${String(attr.name ?? "").replace(/_/g, " ")}`,
					value: this.attrValue(attr),
				})),
			}));
		},
	},
	methods: {
		// v4 `_attr_value_text`: auto_unit() for the six large-value keys, the
		// raw value otherwise, and an empty cell when there is none. NOT
		// formatBytes: auto_unit() is a different algorithm (see format.js).
		attrValue(attr) {
			if (attr.raw === null || attr.raw === undefined) return "";
			return LARGE_VALUE_KEYS.has(attr.key) ? formatAutoUnit(attr.raw) : String(attr.raw);
		},
	},
};
</script>

<style scoped>
/* The TUI's attribute-name width (smart/render_curses_v5.py _NAME_COL_WIDTH).
 * The device line overrides it inline: its own cap is the block's width. */
.gl-plugin {
	--gl-name-width: 25ch;
}
</style>

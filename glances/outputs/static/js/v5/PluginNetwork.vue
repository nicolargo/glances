<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- spec D6: the TUI's header row -- the block title, then the rate
			labels from the schema. An empty collection keeps this row and
			shows no line, as the TUI paints its header. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th v-for="field in RATE_FIELDS" :key="field" class="gl-header gl-num">
					{{ labelFor(labels, field) }}
				</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<!-- The row key hardcodes `interface_name` on purpose: deriving it
				from `payload._key` yields `item[undefined]` against a server that
				does not publish `_key`, i.e. one duplicate key per row. -->
				<tr v-for="item in rows" :key="item.interface_name">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="nameOf(item)"><bdi>{{ nameOf(item) }}</bdi></span>
					</td>
					<!-- The tier goes on the <span>, not the <td>: a prominent badge's
					background would otherwise fill the whole cell. -->
					<td v-for="field in RATE_FIELDS" :key="field" class="gl-num">
						<span :class="cellClassFor(payload, item, field)">{{
							formatNetworkRate(item[field], !!serverArgs.byte)
						}}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatNetworkRate } from "./format.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";
import { displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";
import { PLUGIN_PROPS } from "./plugin_props.js";

const RATE_FIELDS = ["bytes_recv", "bytes_sent"];

const TITLE = "NETWORK";

export default {
	name: "PluginNetwork",
	components: { CollectionBlock },
	// Reads `serverArgs.byte` (--byte): rates in bytes instead of bits.
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// A computed, not data(): data() would hand the template a deeply
		// reactive Proxy of the array.
		RATE_FIELDS: () => RATE_FIELDS,
		// Mirrors network/render_curses_v5.py:129-142: skip a down interface
		// (v4 #765), one hide_zero still hides, and one with no rate yet (cycle
		// 1). Payload order -- the TUI does not sort this block.
		rows() {
			return (this.payload?.data || []).filter(
				(item) =>
					item.is_up !== false && item.hidden !== true && item.bytes_recv != null && item.bytes_sent != null,
			);
		},
	},
	methods: {
		labelFor,
		cellClassFor,
		formatNetworkRate,
		nameOf(item) {
			return displayName(item, "interface_name");
		},
	},
};
</script>

<style scoped>
/* spec D3: the TUI's name width (network/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: calc(18 * var(--gl-col));
}
</style>

<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- spec D6: the TUI's header row -- the block title, then the rate
			labels from the schema. An empty collection keeps this row and
			shows no line, as the TUI paints its header. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th v-if="combined" class="gl-header gl-num" colspan="2">{{ combinedLabel }}</th>
				<th v-for="field in combined ? [] : valueFields" :key="field" class="gl-header gl-num">
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
					<!-- `T` (v4 `network_sum`): one combined column. No tier class --
					the two fields carry their own levels and a sum belongs to
					neither, which is why the TUI paints its combined cell plain
					too. -->
					<td v-if="combined" class="gl-num" colspan="2">
						<span>{{ formatNetworkRate(rxPlusTx(item), !!serverArgs.byte) }}</span>
					</td>
					<!-- Coloured by the RATE field's level in both modes, as v4 reads
					the same `bytes_recv` decoration for its cumulative cells. -->
					<td v-for="(field, index) in combined ? [] : valueFields" :key="field" class="gl-num">
						<span :class="cellClassFor(payload, item, RATE_FIELDS[index])">{{
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
// The `U` key (v4 `network_cumul`): the counters since the interface came up,
// kept by the model beside the rates that replaced them.
const CUMUL_FIELDS = ["bytes_recv_cumul", "bytes_sent_cumul"];

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
		// The `T` key, through AppShell's `effectiveArgs`.
		combined() {
			return !!this.serverArgs.network_sum;
		},
		// v4's own label for the mode (`network/__init__.py:246-254`): the
		// "/s" is dropped under --byte there too.
		// Cumulative mode drops it as well: a total is not a rate.
		combinedLabel() {
			return this.serverArgs.byte || this.cumul ? "Rx+Tx" : "Rx+Tx/s";
		},
		// The `U` key, through AppShell's `effectiveArgs`.
		cumul() {
			return !!this.serverArgs.network_cumul;
		},
		valueFields() {
			return this.cumul ? CUMUL_FIELDS : RATE_FIELDS;
		},
		// Mirrors network/render_curses_v5.py:129-142: skip a down interface
		// (v4 #765), one hide_zero still hides, and one with no rate yet (cycle
		// 1). Payload order -- the TUI does not sort this block.
		// A counter exists from cycle 1, so `U` shows a row the rate mode skips.
		rows() {
			const [rx, tx] = this.valueFields;
			return (this.payload?.data || []).filter(
				(item) => item.is_up !== false && item.hidden !== true && item[rx] != null && item[tx] != null,
			);
		},
	},
	methods: {
		// v5 has no `bytes_all` field (v4's model computes one); summing the
		// two rates the payload already carries gives the same number over the
		// same interval. Mirrors network/render_curses_v5.py.
		rxPlusTx(item) {
			const [rx, tx] = this.valueFields;
			return Number(item[rx]) + Number(item[tx]);
		},
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

<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<!-- The TUI's header row is ONE cell, the title. The empty <th> keeps
			the header aligned column by column with the body. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th class="gl-header gl-num"></th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<!-- Keyed by position, NOT by label: the payload repeats labels (v4 names
				rows chip + " " + index per sub-type, so a chip's first temperature and
				first fan are both "dell_smm 0"), and duplicate keys make Vue's keyed diff
				leave stale rows behind when the list changes. The rows are plain text
				with no component state, so an index key is safe -- v4's
				plugin-sensors.vue keys by index too. -->
				<tr v-for="(row, index) in rows" :key="index">
					<td>
						<span class="gl-name gl-truncate" :title="row.item.label">{{ row.item.label }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, row.item, 'value')">{{ row.text }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatFixed0, toFahrenheit } from "./format.js";
import { cellClassFor } from "./columns.js";
import CollectionBlock from "./CollectionBlock.vue";
import { PLUGIN_PROPS } from "./plugin_props.js";

// sensors/render_curses_v5.py:48-49.
const SENTINELS = new Set(["ERR", "SLP", "UNK", "NOS"]);
const NO_FAHRENHEIT_TYPES = new Set(["battery", "fan_speed"]);

const TITLE = "SENSORS";

// _battery_trend(). Always the unicode glyphs: v4 and the TUI both call
// unicode_message() without args, so --disable-unicode never reaches them.
function batteryTrend(item) {
	const status = String(item.status ?? "");
	if (status.startsWith("Charg")) return "↑";
	if (status.startsWith("Discharg")) return "↓";
	if (status.startsWith("Full")) return "✓";
	return "";
}

// _value_text(). "" means the TUI skips the row. That also covers the
// renderer's separate empty-battery guard (value [], None or ""): none of
// those is a number or a sentinel, so both rules skip the same rows.
function valueText(item, fahrenheit) {
	const value = item.value;
	if (typeof value === "string" && SENTINELS.has(value)) return value;
	if (!Number.isFinite(value)) return "";
	const type = String(item.type ?? "");
	if (fahrenheit && !NO_FAHRENHEIT_TYPES.has(type)) return `${formatFixed0(toFahrenheit(value))}F`;
	const trend = type === "battery" ? batteryTrend(item) : "";
	return `${formatFixed0(value)}${item.unit ?? ""}${trend}`;
}

export default {
	name: "PluginSensors",
	components: { CollectionBlock },
	// Reads `serverArgs.fahrenheit` (--fahrenheit) for the temperatures.
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// Payload order: the server already sorts with natural keys
		// (sensors/model_v5.py:198) and the renderer does not re-sort.
		rows() {
			const fahrenheit = !!this.serverArgs.fahrenheit;
			return (this.payload?.data || [])
				.map((item) => ({ item, text: valueText(item, fahrenheit) }))
				.filter((row) => row.text !== "");
		},
	},
	methods: {
		cellClassFor,
	},
};
</script>

<style scoped>
/* One width budget for the whole left column (maintainer's aesthetic call,
 * 2026-09-12): the three-column blocks' name cap (18ch) plus the value column
 * sensors does not have (.gl-num's 9ch floor) and its cell gap. It replaces
 * spec D3's TUI width here (19ch, sensors/render_curses_v5.py
 * _NAME_MAX_WIDTH). A table column still shrinks to its content, so this
 * equalises the MAXIMUM width: a block whose names are all short renders
 * narrower. */
.gl-plugin {
	--gl-name-width: calc(27ch + var(--gl-gap));
}
</style>

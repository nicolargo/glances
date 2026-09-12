<template>
	<article class="gl-plugin" aria-label="SENSORS">
		<!-- aria-label: once loaded the title is a <th>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">SENSORS</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<table v-else class="gl-table">
			<thead>
				<!-- The TUI's header row is ONE cell, the title. The empty <th> keeps
				the header aligned column by column with the body. -->
				<tr>
					<th class="gl-header">SENSORS</th>
					<th class="gl-header gl-num"></th>
				</tr>
			</thead>
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
		</table>
	</article>
</template>

<script>
import { formatFixed0, toFahrenheit } from "./format.js";
import { cellClassFor } from "./columns.js";

// sensors/render_curses_v5.py:48-49.
const SENTINELS = new Set(["ERR", "SLP", "UNK", "NOS"]);
const NO_FAHRENHEIT_TYPES = new Set(["battery", "fan_speed"]);

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
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: the TUI's value column has no label.
		labels: { type: Object, default: () => ({}) },
		// `fahrenheit` (--fahrenheit) converts temperatures, as in the TUI.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
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
 * G9-6 D3's TUI width here (19ch, sensors/render_curses_v5.py
 * _NAME_MAX_WIDTH). A table column still shrinks to its content, so this
 * equalises the MAXIMUM width: a block whose names are all short renders
 * narrower. */
.gl-plugin {
	--gl-name-width: calc(27ch + var(--gl-gap));
}
</style>

<template>
	<CollectionBlock
		:title="TITLE"
		:payload="payload"
		:error="error"
		table-class="gl-process-table"
		:style="fixedColsStyle"
		:hidden="quotaHidden"
	>
		<template #cols>
			<colgroup>
				<!-- Command: no <col> at all, deliberately -- not a `<col />` with
				no `:style`. The fixed table-layout algorithm (CSS 2.1 17.5.2.1)
				gives any column past the <colgroup>'s specified count an equal
				share of the remaining space once every other column is pinned;
				with only the 12 fixed columns listed, Command (alone past that
				count) gets the whole remainder -- the TUI's elastic last column.
				A bare trailing `<col />` renders identically in a browser but adds
				a 13th, width-less entry to `pluginColWidths` (the render probe reads
				every <col> in the table) that no consumer of this list wants. -->
				<col v-for="key in visibleFixedColumns" :key="key" :style="colStyle(key)" />
			</colgroup>
		</template>
		<template #head>
			<tr>
				<!-- The TUI's header literals (programlist/render_curses_v5.py:99-113):
				identical to processlist's except NPROCS replaces PID -- the per-program
				aggregation has no single pid (glances/plugins/programlist/model_v5.py:
				the engine sets `pid='_'`). No width cascade here: programlist's own
				renderer never imports processlist's `_DROP_ORDER`/`_MIN_COMMAND_WIDTH`,
				so every column below is unconditional -- no `shows()`/`v-if` per
				column, unlike processlist's own template. -->
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('CPU%') }">{{ cpuLabel }}</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('MEM%') }">MEM%</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('VIRT') }">VIRT</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('RES') }">RES</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('NPROCS') }">NPROCS</th>
				<th class="gl-header" :class="{ 'gl-sorted': isSorted('USER') }">USER</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('THR') }">THR</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('NI') }">NI</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('S') }">S</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('TIME+') }">TIME+</th>
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('R/s') }">R/s</th>
				<!-- gl-num-left: a deliberate WebUI-only divergence, not TUI parity,
				shared with PluginProcesslist.vue's identical rule (see its own
				comment for the full reasoning). The maintainer asked for W/s
				left-aligned in the browser even though the terminal right-aligns
				it like every other numeric column -- do not "fix" this back. -->
				<th class="gl-header gl-num gl-num-left" :class="{ 'gl-sorted': isSorted('W/s') }">W/s</th>
				<th class="gl-header" :class="{ 'gl-sorted': isSorted('Command') }">Command</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_percent')">{{ formatCpu(item.cpu_percent) }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{
							formatPercent(item.memory_percent)
						}}</span>
					</td>
					<td class="gl-num"><span>{{ formatProcessBytes(memField(item, 'vms')) }}</span></td>
					<td class="gl-num"><span>{{ formatProcessBytes(memField(item, 'rss')) }}</span></td>
					<td class="gl-num"><span>{{ fmt(item.nprocs) }}</span></td>
					<td><span>{{ formatUsername(item.username) }}</span></td>
					<td class="gl-num"><span>{{ fmt(item.num_threads) }}</span></td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'nice')">{{ fmt(item.nice) }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'status')">{{ fmt(item.status) }}</span>
					</td>
					<td class="gl-num"><span>{{ formatCpuTime(item.cpu_times) }}</span></td>
					<td class="gl-num"><span>{{ formatProcessBytes(ioRate(item, true)) }}</span></td>
					<td class="gl-num gl-num-left"><span>{{ formatProcessBytes(ioRate(item, false)) }}</span></td>
					<td>
						<span class="gl-truncate" :title="fmt(commandText(item))">{{
							fmt(commandText(item))
						}}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { PLUGIN_PROPS } from "./plugin_props.js";
import { processBlockMixin } from "./process_block.js";
// The character-column widths (process_widths.js), so the <colgroup> and CSS
// derive from the same numbers the terminal renderer uses -- never a literal
// copied by hand.
import { NPROCS_WIDTH, PROGRAM_FIXED_COL_KEYS, WEBUI_COL_WIDTHS } from "./process_widths.js";

const TITLE = "PROGRAMS";

// WEBUI_COL_WIDTHS has no NPROCS entry (it is processlist's own map) --
// NPROCS_WIDTH is the one column this block does not share with processlist's
// width map.
function columnWidth(key) {
	return key === "NPROCS" ? NPROCS_WIDTH : WEBUI_COL_WIDTHS[key];
}

export default {
	name: "PluginProgramlist",
	components: { CollectionBlock },
	// No fitBlockMixin, unlike processlist: programlist's own renderer never
	// imports processlist's `_DROP_ORDER`, so this block has no width cascade
	// and every column is unconditional.
	mixins: [processBlockMixin({ budgetKey: "programlist", columnWidth, wideIrixLabel: "CPU%/C" })],
	// Reads `serverArgs.sort_processes_key` for the sort underline (isSorted()).
	// `degrade` is declared and left unused: this block has no width cascade to
	// feed it to.
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// Constant, unlike processlist's own `visibleFixedColumns`: there is no
		// cascade to filter it. Command is not one of them -- it is the elastic
		// tail, sized by the <colgroup>'s implicit column.
		visibleFixedColumns: () => PROGRAM_FIXED_COL_KEYS,
	},
};
</script>

<style scoped>
/* Same reasoning as PluginProcesslist.vue's own scoped rule: no existing
 * global class underlines a sorted header, and this is a single consumer. */
.gl-table th.gl-sorted {
	text-decoration: underline;
}
/* W/s is left-aligned in the browser, a DELIBERATE divergence from the
 * terminal -- see PluginProcesslist.vue's identical rule for the full
 * reasoning (confirmed by the maintainer knowing the two disagree). Do not
 * "fix" this back to match the TUI. The element is part of the selector on
 * purpose, for the same specificity reason processlist's own rule gives. */
.gl-table th.gl-num-left,
.gl-table td.gl-num-left {
	text-align: left;
}
</style>

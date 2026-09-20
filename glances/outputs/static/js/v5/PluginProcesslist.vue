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
				<!-- The TUI's header literals (processlist/render_curses_v5.py:91,
				`_FIXED_COL_KEYS` + `Command`) -- no separate title cell, unlike
				`containers`: this renderer never puts one in its header row. -->
				<th v-if="shows('CPU%')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('CPU%') }">CPU%</th>
				<th v-if="shows('MEM%')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('MEM%') }">MEM%</th>
				<th v-if="shows('VIRT')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('VIRT') }">VIRT</th>
				<th v-if="shows('RES')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('RES') }">RES</th>
				<th v-if="shows('PID')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('PID') }">PID</th>
				<th v-if="shows('USER')" class="gl-header" :class="{ 'gl-sorted': isSorted('USER') }">USER</th>
				<th v-if="shows('THR')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('THR') }">THR</th>
				<th v-if="shows('NI')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('NI') }">NI</th>
				<th v-if="shows('S')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('S') }">S</th>
				<th v-if="shows('TIME+')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('TIME+') }">TIME+</th>
				<th v-if="shows('R/s')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('R/s') }">R/s</th>
				<!-- gl-num-left: a deliberate WebUI-only divergence, not TUI parity
				(unlike `containers`' own use of this class, which mirrors its
				renderer). The terminal right-aligns W/s exactly like every other
				numeric column (render_curses_v5.py:435-445 gives every header
				`ljust=False`; USER is the TUI's only `ljust=True` column). The
				maintainer asked for W/s left-aligned in the browser anyway --
				confirmed knowing the terminal disagrees. Do not "fix" this back to
				match the TUI. -->
				<th v-if="shows('W/s')" class="gl-header gl-num gl-num-left" :class="{ 'gl-sorted': isSorted('W/s') }">W/s</th>
				<th class="gl-header" :class="{ 'gl-sorted': isSorted('Command') }">Command</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.pid">
					<td v-if="shows('CPU%')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_percent')">{{ formatPercent(item.cpu_percent) }}</span>
					</td>
					<td v-if="shows('MEM%')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{
							formatPercent(item.memory_percent)
						}}</span>
					</td>
					<td v-if="shows('VIRT')" class="gl-num"><span>{{ formatProcessBytes(memField(item, 'vms')) }}</span></td>
					<td v-if="shows('RES')" class="gl-num"><span>{{ formatProcessBytes(memField(item, 'rss')) }}</span></td>
					<td v-if="shows('PID')" class="gl-num"><span>{{ fmt(item.pid) }}</span></td>
					<td v-if="shows('USER')"><span>{{ formatUsername(item.username) }}</span></td>
					<td v-if="shows('THR')" class="gl-num"><span>{{ fmt(item.num_threads) }}</span></td>
					<td v-if="shows('NI')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'nice')">{{ fmt(item.nice) }}</span>
					</td>
					<td v-if="shows('S')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'status')">{{ fmt(item.status) }}</span>
					</td>
					<td v-if="shows('TIME+')" class="gl-num"><span>{{ formatCpuTime(item.cpu_times) }}</span></td>
					<td v-if="shows('R/s')" class="gl-num"><span>{{ formatProcessBytes(ioRate(item, true)) }}</span></td>
					<td v-if="shows('W/s')" class="gl-num gl-num-left"><span>{{ formatProcessBytes(ioRate(item, false)) }}</span></td>
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
import { PROCESSLIST_DROP_ORDER, hiddenColumns as resolveHiddenColumns } from "./processlist_columns.js";
import { dropCascade } from "./drop_order.js";
import { fitBlockMixin } from "./fit_block.js";
import { processBlockMixin } from "./process_block.js";
// The character-column widths (process_widths.js), so the <colgroup> and CSS
// derive from the same numbers the terminal renderer uses -- never a literal
// copied by hand. `WEBUI_COL_WIDTHS`, not `PROCESS_COL_WIDTHS`: the browser
// renders one column (MEM%) one character wider than the terminal, because
// `formatPercent()` appends a `%` curses never prints -- see that module.
import { FIXED_COL_KEYS, WEBUI_COL_WIDTHS } from "./process_widths.js";

const TITLE = "PROCESSES";

export default {
	name: "PluginProcesslist",
	components: { CollectionBlock },
	// fitBlockMixin owns the WIDTH cascade (`dropFlags`, the columns this block
	// drops as it narrows); processBlockMixin owns everything this block shares
	// with `programlist` (row ceilings, <colgroup> arithmetic, cell formatters).
	mixins: [fitBlockMixin, processBlockMixin({ budgetKey: "processlist", columnWidth: (key) => WEBUI_COL_WIDTHS[key] })],
	// Reads `serverArgs.sort_processes_key` for the sort underline (isSorted()).
	// `degrade` is declared and left unused: this block owns its own width
	// cascade, not the shell's zone-level one.
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// The cascade the fit mixin resolves: the TUI's drop order, as steps. A
		// computed so the array reaching resolveDegrade() is not a reactive Proxy
		// of component data.
		dropCascadeSteps: () => dropCascade(PROCESSLIST_DROP_ORDER),
		hiddenColumns() {
			return resolveHiddenColumns(this.dropFlags);
		},
		// The fixed columns still on screen, in display order. Command is not one
		// of them -- it is the elastic tail, sized by the <colgroup>'s implicit
		// column.
		visibleFixedColumns() {
			return FIXED_COL_KEYS.filter((key) => this.shows(key));
		},
	},
	watch: {
		// A new process, a longer command line or a wider PID changes the natural
		// width, so the cascade must be re-resolved -- the ResizeObserver does not
		// fire when only the CONTENT changes.
		payload() {
			this.fitBlock().catch(() => {});
		},
	},
	methods: {
		shows(column) {
			return !this.hiddenColumns.has(column);
		},
	},
};
</script>

<style scoped>
/* The active sort column's header, underlined -- the TUI's 'SORT' decoration
 * (processlist/render_curses_v5.py `_header`, `underline=...`). No existing
 * global class does this (no WebUI collection before this one underlines a
 * header), so it is scoped here rather than added to css/v5.css for a single
 * consumer. */
.gl-table th.gl-sorted {
	text-decoration: underline;
}
/* W/s is left-aligned in the browser, a DELIBERATE divergence from the
 * terminal, not parity -- the terminal right-aligns W/s like every other
 * numeric column (render_curses_v5.py:435-445 gives every header
 * `ljust=False`; USER is its only `ljust=True` column). Confirmed by the
 * maintainer knowing the two disagree; do not "fix" this back to match the
 * TUI. Same selector shape as `containers`'s
 * own `.gl-num-left` (PluginContainers.vue), for the opposite reason there
 * (that one IS TUI parity) -- the element is part of the selector on
 * purpose: a bare `.gl-num-left` (0,1,0) only ties with the global
 * `.gl-num` (0,1,0), and the winner would be decided by source order, which
 * nothing guarantees between a scoped style and the token file. */
.gl-table th.gl-num-left,
.gl-table td.gl-num-left {
	text-align: left;
}
</style>

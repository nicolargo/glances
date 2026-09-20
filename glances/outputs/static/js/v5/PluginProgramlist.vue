<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
		<template #head>
			<tr>
				<!-- The TUI's header literals (programlist/render_curses_v5.py:99-113):
				identical to processlist's except NPROCS replaces PID -- the per-program
				aggregation has no single pid (glances/plugins/programlist/model_v5.py:
				the engine sets `pid='_'`). No width cascade here: unlike processlist,
				programlist/render_curses_v5.py never imports processlist's
				`_visible_fixed_keys`/`_DROP_ORDER` -- its `render()` always emits all
				thirteen cells, so this template has no `shows()`/`v-if` per column
				either (verified by reading the file in full; a "share the cascade"
				assumption would have been wrong here). -->
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('CPU%') }">CPU%</th>
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
				<th class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('W/s') }">W/s</th>
				<th class="gl-header" :class="{ 'gl-sorted': isSorted('Command') }">Command</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_percent')">{{ formatPercent(item.cpu_percent) }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{
							formatPercent(item.memory_percent)
						}}</span>
					</td>
					<td class="gl-num"><span>{{ formatBytes(memField(item, 'vms')) }}</span></td>
					<td class="gl-num"><span>{{ formatBytes(memField(item, 'rss')) }}</span></td>
					<td class="gl-num"><span>{{ fmt(item.nprocs) }}</span></td>
					<td><span>{{ fmt(item.username) }}</span></td>
					<td class="gl-num"><span>{{ fmt(item.num_threads) }}</span></td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'nice')">{{ fmt(item.nice) }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'status')">{{ fmt(item.status) }}</span>
					</td>
					<td class="gl-num"><span>{{ formatCpuTime(item.cpu_times) }}</span></td>
					<td class="gl-num"><span>{{ formatBytes(ioRate(item, true)) }}</span></td>
					<td class="gl-num"><span>{{ formatBytes(ioRate(item, false)) }}</span></td>
					<td>
						<span class="gl-command gl-truncate" :title="fmt(commandText(item))">{{
							fmt(commandText(item))
						}}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatBytes, formatCpuTime, formatPercent } from "./format.js";
import { cellClassFor } from "./columns.js";
import CollectionBlock from "./CollectionBlock.vue";
// G9-9B Task 8 fix round 1: these three were byte-identical duplicates of
// PluginProcesslist.vue's own local copies -- both blocks now import the
// single copy in process_shared.js (its docstring covers why NPROCS/PID have
// no HEADER_SORT_KEY entry either).
import { HEADER_SORT_KEY, ioRate, commandText } from "./process_shared.js";

const TITLE = "PROGRAMS";

export default {
	name: "PluginProgramlist",
	components: { CollectionBlock },
	// `[outputs] max_processes_display` -- the same config key and the same
	// AppShell provide() as processlist's (there is no separate
	// `max_programs_display` key; task 8 brief's "share the same cap" holds
	// here, unlike the cascade mixin).
	inject: {
		maxProcessesDisplay: { default: null },
	},
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: every programlist header is a literal, like
		// processlist's.
		labels: { type: Object, default: () => ({}) },
		// `serverArgs.sort_processes_key` drives the sort underline (isSorted()
		// below) -- the only server flag this block reads.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared and left unused: no width cascade applies to this block (see
		// the template comment) -- there is no `dropFlags`/zone-level `degrade`
		// for it to consume, so this mirrors processlist's own reasoning for a
		// different reason (that one owns its OWN cascade instead of the
		// shell's; this one owns none at all).
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// The full payload, in ENGINE order -- the sort is server-side, and
		// this component must not re-sort.
		allRows() {
			return this.payload?.data || [];
		},
		// The cap applies to that same payload order: the first N rows, never
		// the top N by any column value.
		rows() {
			const rows = this.allRows;
			const cap = this.maxProcessesDisplay;
			return Number.isInteger(cap) && cap > 0 ? rows.slice(0, cap) : rows;
		},
	},
	methods: {
		cellClassFor,
		formatBytes,
		formatCpuTime,
		formatPercent,
		ioRate,
		commandText,
		isSorted(label) {
			const key = this.serverArgs && this.serverArgs.sort_processes_key;
			return !!key && HEADER_SORT_KEY[label] === key;
		},
		memField(item, field) {
			return item && item.memory_info ? item.memory_info[field] : undefined;
		},
		fmt(value) {
			return value === null || value === undefined || value === "" ? "-" : String(value);
		},
	},
};
</script>

<style scoped>
/* Same reasoning as PluginProcesslist.vue's own scoped rule: no existing
 * global class underlines a sorted header, and this is a single consumer. */
.gl-table th.gl-sorted {
	text-decoration: underline;
}
</style>

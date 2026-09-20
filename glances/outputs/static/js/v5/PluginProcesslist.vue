<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error">
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
				<th v-if="shows('W/s')" class="gl-header gl-num" :class="{ 'gl-sorted': isSorted('W/s') }">W/s</th>
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
					<td v-if="shows('VIRT')" class="gl-num"><span>{{ formatBytes(memField(item, 'vms')) }}</span></td>
					<td v-if="shows('RES')" class="gl-num"><span>{{ formatBytes(memField(item, 'rss')) }}</span></td>
					<td v-if="shows('PID')" class="gl-num"><span>{{ fmt(item.pid) }}</span></td>
					<td v-if="shows('USER')"><span>{{ fmt(item.username) }}</span></td>
					<td v-if="shows('THR')" class="gl-num"><span>{{ fmt(item.num_threads) }}</span></td>
					<td v-if="shows('NI')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'nice')">{{ fmt(item.nice) }}</span>
					</td>
					<td v-if="shows('S')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'status')">{{ fmt(item.status) }}</span>
					</td>
					<td v-if="shows('TIME+')" class="gl-num"><span>{{ formatCpuTime(item.cpu_times) }}</span></td>
					<td v-if="shows('R/s')" class="gl-num"><span>{{ formatBytes(ioRate(item, true)) }}</span></td>
					<td v-if="shows('W/s')" class="gl-num"><span>{{ formatBytes(ioRate(item, false)) }}</span></td>
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
import { PROCESSLIST_DROP_ORDER, hiddenColumns as resolveHiddenColumns } from "./processlist_columns.js";
import { dropCascade } from "./drop_order.js";
import { fitBlockMixin } from "./fit_block.js";
// G9-9B Task 8 fix round 1: HEADER_SORT_KEY/ioRate/commandText were
// byte-identical duplicates of PluginProgramlist.vue's own copies -- both
// blocks now import the single copy in process_shared.js.
import { HEADER_SORT_KEY, ioRate, commandText } from "./process_shared.js";

const TITLE = "PROCESSES";

export default {
	name: "PluginProcesslist",
	components: { CollectionBlock },
	mixins: [fitBlockMixin],
	// `[outputs] max_processes_display`, resolved once by AppShell (its
	// mounted(), reusing the SAME /api/5/config fetch as refresh/theme) and
	// handed down via its `provide()` -- deliberately `inject`, not a prop
	// like `serverArgs`/`degrade`: it has (today) exactly one consumer, so a
	// prop on the shared `<component>` binding would either leave 29 dead
	// declarations on every other plugin or leak a `max-processes-display`
	// DOM attribute on all of them, the same tradeoff `serverPlugins` already
	// made in PluginPercpu.vue. Fix round 1, IMPORTANT 1: this component used
	// to fetch `/api/5/config` itself, a genuine second round-trip per page
	// load to a credentials-bearing endpoint, arriving AFTER mount (one
	// uncapped paint on a large host) and bypassing the "AppShell resolves
	// shared endpoints once" layering every other cross-cutting value
	// follows. The default is `null` ("no cap") for a component mounted
	// outside AppShell (the render probe mounts AppShell itself, so this only
	// matters for a future isolated unit test).
	inject: {
		maxProcessesDisplay: { default: null },
	},
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: every processlist header is a literal (the TUI
		// renderer hardcodes them too, same as `vms`/`containers`), not a
		// schema-derived label.
		labels: { type: Object, default: () => ({}) },
		// `serverArgs.sort_processes_key` drives the sort underline (isSorted()
		// below) -- the only server flag this block reads.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared and left unused: the shell binds `degrade` to every
		// component in a slot from one shared expression (AppShell.vue). This
		// component owns its own width cascade (fit_block.js's `dropFlags`),
		// not the shell's zone-level one.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// The full payload, in ENGINE order -- the sort is server-side
		// (glances_processes.sort_key), and this component must not re-sort.
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
		// The cascade the mixin resolves: the TUI's drop order, as steps. A
		// computed so the array reaching resolveDegrade() is not a reactive
		// Proxy of component data.
		dropCascadeSteps: () => dropCascade(PROCESSLIST_DROP_ORDER),
		hiddenColumns() {
			return resolveHiddenColumns(this.dropFlags);
		},
	},
	watch: {
		// A new process, a longer command line or a wider PID changes the
		// natural width, so the cascade must be re-resolved -- the
		// ResizeObserver does not fire when only the CONTENT changes.
		payload() {
			this.fitBlock().catch(() => {});
		},
	},
	methods: {
		cellClassFor,
		formatBytes,
		formatCpuTime,
		formatPercent,
		ioRate,
		commandText,
		shows(column) {
			return !this.hiddenColumns.has(column);
		},
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
/* The active sort column's header, underlined -- the TUI's 'SORT' decoration
 * (processlist/render_curses_v5.py `_header`, `underline=...`). No existing
 * global class does this (no WebUI collection before this one underlines a
 * header), so it is scoped here rather than added to css/v5.css for a single
 * consumer. */
.gl-table th.gl-sorted {
	text-decoration: underline;
}
</style>

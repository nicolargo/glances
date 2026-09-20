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
						<span :class="cellClassFor(payload, item, 'cpu_percent')">{{ formatPercent(item.cpu_percent) }}</span>
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
import { formatCpuTime, formatPercent, formatProcessBytes, formatUsername } from "./format.js";
import { cellClassFor } from "./columns.js";
import CollectionBlock from "./CollectionBlock.vue";
// G9-9B Task 8 fix round 1: these three were byte-identical duplicates of
// PluginProcesslist.vue's own local copies -- both blocks now import the
// single copy in process_shared.js (its docstring covers why NPROCS/PID have
// no HEADER_SORT_KEY entry either).
import { HEADER_SORT_KEY, ioRate, commandText } from "./process_shared.js";
// The TUI's own character-column widths (render_curses_v5.py:55-65, :91;
// programlist/render_curses_v5.py:58), so the <colgroup> and CSS derive from
// the same numbers the terminal renderer uses -- never a literal copied by
// hand.
import { MIN_COMMAND_WIDTH, NPROCS_WIDTH, PROCESS_COL_WIDTHS, PROGRAM_FIXED_COL_KEYS } from "./process_widths.js";

const TITLE = "PROGRAMS";

// PROCESS_COL_WIDTHS has no NPROCS entry (it is processlist's own map, drift-
// tested against the terminal 1:1) -- NPROCS_WIDTH is the one column this
// block does not share with processlist's width map.
function contentWidth(key) {
	return key === "NPROCS" ? NPROCS_WIDTH : PROCESS_COL_WIDTHS[key];
}

export default {
	name: "PluginProgramlist",
	components: { CollectionBlock },
	// `[outputs] max_processes_display` -- the same config key and the same
	// AppShell provide() as processlist's (there is no separate
	// `max_programs_display` key). `rowBudget` is the vertical row quota
	// AppShell's refitVertical() pass allots this block (row_budget.js),
	// handed down the same way -- `inject`, never a prop, for the same reason
	// PluginProcesslist.vue gives (a prop on the shared `<component>` binding
	// would leak a DOM attribute onto every other plugin, AppShell.vue:89-110).
	inject: {
		maxProcessesDisplay: { default: null },
		rowBudget: { default: () => ({}) },
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
		// Two ceilings, composed like processlist's own `rows()`: the height-
		// driven budget and the config key. `min()` because `[outputs]
		// max_processes_display` is a hard cap that available height may never
		// raise (design 4.7). The cap applies to the payload's own order: the
		// first N rows, never the top N by any column value.
		//
		// The two predicates differ on purpose, exactly as processlist's own
		// do not merge: `maxProcessesDisplay` keeps `> 0` (its `0` means "no
		// cap"); `rowBudget.programlist` uses `>= 0` (its `0` means "hide the
		// block entirely", the browser's counterpart of the TUI's own
		// `row_budget(...) <= 0` early return, programlist/render_curses_v5.py
		// :91-94).
		rows() {
			const caps = [];
			if (Number.isInteger(this.maxProcessesDisplay) && this.maxProcessesDisplay > 0) {
				caps.push(this.maxProcessesDisplay);
			}
			if (Number.isInteger(this.rowBudget?.programlist) && this.rowBudget.programlist >= 0) {
				caps.push(this.rowBudget.programlist);
			}
			if (!caps.length) return this.allRows;
			return this.allRows.slice(0, Math.min(...caps));
		},
		// Ladder steps g and l make a block vanish entirely, header included
		// (curses_renderer_v5.py:1035-1044, row_budget.js's `cost()`) --
		// `rows` above already renders nothing at a zero quota, but
		// CollectionBlock still paints the loading/title header on an empty
		// table (G9-6 D6) unless told to hide the whole block. Tied to the
		// EXPLICIT quota, never to `rows.length === 0`, exactly as
		// PluginProcesslist.vue's own identical rule (design 4.8).
		quotaHidden() {
			return Number.isInteger(this.rowBudget?.programlist) && this.rowBudget.programlist === 0;
		},
		// The fixed columns, in display order -- constant per render: there is
		// no cascade to filter it (unlike processlist's own `visibleFixedColumns`,
		// which drops entries as `dropFlags` grows). Command is not one of them
		// -- it is the elastic tail, sized by the <colgroup>'s implicit column.
		visibleFixedColumns: () => PROGRAM_FIXED_COL_KEYS,
		// The integer the stylesheet turns into a width -- same formula as
		// processlist's own `fixedColsStyle`, constant here since the column
		// set never shrinks. Below this width the table overflows its
		// container and the block scrolls: the browser's floor, with no JS
		// cascade to soften it (programlist has none).
		fixedColsStyle() {
			const keys = this.visibleFixedColumns;
			const fixed = keys.reduce((total, key) => total + contentWidth(key), 0);
			const separators = keys.length; // one after each fixed column, before Command
			return { "--gl-fixed-cols": String(fixed + separators + MIN_COMMAND_WIDTH) };
		},
	},
	methods: {
		cellClassFor,
		formatCpuTime,
		formatPercent,
		formatProcessBytes,
		formatUsername,
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
		// `contentWidth(key)` alone under-sizes every column by one character --
		// same reasoning as processlist's own `colStyle()` (see its comment):
		// under `table-layout: fixed` the <col> is the column's WHOLE box, and
		// the separator's `padding-right: var(--gl-col)` comes out of that same
		// box, so a <col> of exactly N characters leaves only N-1 for content.
		// `+1` reserves the separator's own character inside the box.
		colStyle(key) {
			return { width: `calc(${contentWidth(key) + 1} * var(--gl-col))` };
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

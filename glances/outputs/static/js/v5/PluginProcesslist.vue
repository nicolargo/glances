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
				a 13th, width-less entry to `pluginColWidths` (Task 7's probe reads
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
import { formatCpuTime, formatPercent, formatProcessBytes, formatUsername } from "./format.js";
import { cellClassFor } from "./columns.js";
import CollectionBlock from "./CollectionBlock.vue";
import { PROCESSLIST_DROP_ORDER, hiddenColumns as resolveHiddenColumns } from "./processlist_columns.js";
import { dropCascade } from "./drop_order.js";
import { fitBlockMixin } from "./fit_block.js";
// G9-9B Task 8 fix round 1: HEADER_SORT_KEY/ioRate/commandText were
// byte-identical duplicates of PluginProgramlist.vue's own copies -- both
// blocks now import the single copy in process_shared.js.
import { HEADER_SORT_KEY, ioRate, commandText } from "./process_shared.js";
// The character-column widths (process_widths.js), so the <colgroup> and CSS
// derive from the same numbers the terminal renderer uses -- never a literal
// copied by hand. `WEBUI_COL_WIDTHS`, not `PROCESS_COL_WIDTHS`: the browser
// renders one column (MEM%) one character wider than the terminal, because
// `formatPercent()` appends a `%` curses never prints -- see that module.
import { COL_SEPARATOR, FIXED_COL_KEYS, MIN_COMMAND_WIDTH, WEBUI_COL_WIDTHS } from "./process_widths.js";

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
		// The vertical row quota AppShell's refitVertical() pass allots this
		// block (row_budget.js), handed down via provide() the same way
		// as `maxProcessesDisplay` right above -- AppShell.vue never binds it as
		// an attribute on the shared `<component>` (that would leak a
		// `row-budget` DOM attribute on the other 31 plugins, the same
		// reasoning documented at AppShell.vue:114-126). `{}` means no budget --
		// an environment without measurement must never hide stats (design 4.8).
		rowBudget: { default: () => ({}) },
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
		// Two ceilings, composed: the height-driven budget and the config key.
		// `min()` because `[outputs] max_processes_display` is a hard cap that
		// available height may never raise (design 4.7) -- the browser's
		// counterpart of the TUI's row_budget(view, "processlist", _MAX_ROWS)
		// fallback chain (processlist/render_curses_v5.py:414). The cap applies
		// to the payload's own order: the first N rows, never the top N by any
		// column value.
		//
		// The two ceilings do NOT share one predicate, deliberately: their `0`
		// means opposite things. `maxProcessesDisplay` keeps `> 0` -- `[outputs]
		// max_processes_display = 0` must keep meaning "no cap", not start
		// hiding the block, which would be an unannounced change to what an
		// explicit configuration value does. `rowBudget.processlist` uses
		// `>= 0`: its `0` legitimately means "hide the block entirely", the
		// browser's counterpart of the TUI's own `row_budget(...) <= 0` early
		// return (processlist/render_curses_v5.py:413-416) -- step l of the
		// vertical cascade, an active alert needing the room. Do not merge
		// these back into one filter; a reader would otherwise assume one of
		// the two comparisons is a typo.
		rows() {
			const caps = [];
			if (Number.isInteger(this.maxProcessesDisplay) && this.maxProcessesDisplay > 0) {
				caps.push(this.maxProcessesDisplay);
			}
			if (Number.isInteger(this.rowBudget?.processlist) && this.rowBudget.processlist >= 0) {
				caps.push(this.rowBudget.processlist);
			}
			if (!caps.length) return this.allRows;
			return this.allRows.slice(0, Math.min(...caps));
		},
		// Ladder steps g and l make a block vanish entirely, header included
		// (curses_renderer_v5.py:1035-1044, row_budget.js's `cost()`) --
		// `rows` above already renders nothing at a zero quota, but
		// CollectionBlock still paints the loading/title header on an empty
		// table (G9-6 D6) unless told to hide the whole block. Tied to the
		// EXPLICIT quota, never to `rows.length === 0`: an environment
		// without measurement (`rowBudget` = `{}`, design 4.8) must keep
		// showing a host with zero running processes, not hide it.
		quotaHidden() {
			return Number.isInteger(this.rowBudget?.processlist) && this.rowBudget.processlist === 0;
		},
		// The cascade the mixin resolves: the TUI's drop order, as steps. A
		// computed so the array reaching resolveDegrade() is not a reactive
		// Proxy of component data.
		dropCascadeSteps: () => dropCascade(PROCESSLIST_DROP_ORDER),
		hiddenColumns() {
			return resolveHiddenColumns(this.dropFlags);
		},
		// The fixed columns still on screen, in display order. Command is not
		// one of them -- it is the elastic tail.
		visibleFixedColumns() {
			return FIXED_COL_KEYS.filter((key) => this.shows(key));
		},
		// The integer the stylesheet turns into a width. CSS does the
		// character->pixel conversion, so no JS ever measures `--gl-col`
		// (design D7): the sum is the visible fixed widths, plus one separator
		// column between cells, plus Command's floor. The table's min-width is
		// built from it, so the table overflows its container exactly when
		// Command would fall below the floor -- which is what keeps the
		// existing measure-driven cascade firing at the TUI's own threshold.
		fixedColsStyle() {
			const keys = this.visibleFixedColumns;
			const fixed = keys.reduce((total, key) => total + WEBUI_COL_WIDTHS[key], 0);
			// One separator after each fixed column, before Command.
			const separators = COL_SEPARATOR * keys.length;
			return { "--gl-fixed-cols": String(fixed + separators + MIN_COMMAND_WIDTH) };
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
		formatCpuTime,
		formatPercent,
		formatProcessBytes,
		formatUsername,
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
		// `WEBUI_COL_WIDTHS[key]` alone under-sizes every column by the
		// separator. Under `table-layout: fixed` the <col> width is the
		// column's WHOLE box, and `.gl-process-table td:not(:last-child)`'s
		// `padding-right` separator comes out of that same box -- so a `<col>`
		// of exactly N characters leaves only N - COL_SEPARATOR for content
		// (every fixed column crops early; invisibly so for "S", whose N=1
		// makes it disappear rather than merely narrow). Adding COL_SEPARATOR
		// reserves the separator's own characters inside the box, leaving the
		// full N for content. `fixedColsStyle` does NOT add it per column: it
		// already charges one separator per visible fixed column via its own
		// `separators` term, so Σ(N + COL_SEPARATOR) there and
		// Σ(N) + separators here agree by construction.
		colStyle(key) {
			return { width: `calc(${WEBUI_COL_WIDTHS[key] + COL_SEPARATOR} * var(--gl-col))` };
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

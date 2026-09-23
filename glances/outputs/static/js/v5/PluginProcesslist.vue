<template>
	<CollectionBlock
		:title="TITLE"
		:payload="payload"
		:error="error"
		table-class="gl-process-table"
		:style="fixedColsStyle"
		:hidden="quotaHidden"
	>
		<template #prepend>
			<!-- The `e` block (2.X-b3-web). v4's web UI offers the same thing
			by clicking a row (plugin-processlist.vue:59, :720, :726); the
			LINES are v5's terminal's, not v4's browser's, so the two surfaces
			of this version describe a pinned process identically
			(process_extended.js, held to the Python by
			tests/test_webui_v5_extended_drift.py). -->
			<div v-if="extended" class="gl-pinned">
				<div class="gl-pinned-head">
					<span class="gl-header">Pinned task:</span>
					<span class="gl-truncate" :title="pinnedTitle(extended)">{{ pinnedTitle(extended) }}</span>
					<button type="button" class="gl-pin-button" @click="unpin">Unpin</button>
				</div>
				<div v-for="(line, i) in extendedLines(extended)" :key="i" class="gl-pinned-line">
					<span v-for="(seg, j) in line" :key="j" :class="{ 'gl-level-ok': seg.value }">{{ seg.text }}</span>
				</div>
			</div>
		</template>
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
				<!-- "Command", like the terminal and like `programlist` -- NOT
				v4's "Command (click to pin)" (plugin-processlist.vue:59).
				Measured in Chromium: this column is the elastic remainder and
				lands at 72-161px across 640/900/1280px viewports, while that
				wording needs 186px, so it would wrap the header row at almost
				every width. The click affordance is carried by the row's
				`cursor: pointer` and by this cell's `title` instead, neither
				of which costs a pixel of layout. -->
				<th
					class="gl-header"
					:class="{ 'gl-sorted': isSorted('Command') }"
					title="Click a process to pin its extended stats"
				>Command</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr
					v-for="item in rows"
					:key="item.pid"
					class="gl-pinnable"
					:class="{ 'gl-pinned-row': isPinned(item) }"
					@click="pin(item)"
				>
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
// The `e` block's segments, shared with the terminal renderer through a drift
// test rather than through a second hand-written copy.
import { extendedLines, pinnedTitle } from "./process_extended.js";
import { postJson } from "./api.js";

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
		// The pinned process, straight from the payload metadata the server
		// publishes while a pin is live (processlist/model_v5.py
		// `_add_metadata`). No local copy: the pin is GLOBAL server state --
		// the TUI's `e` sets the same one -- so the payload is the truth and
		// a component-level mirror could only go stale against it.
		extended() {
			const payload = this.payload;
			return payload && payload.extended ? payload.extended : null;
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
		extendedLines,
		pinnedTitle,
		isPinned(item) {
			return !!this.extended && this.extended.pid === item.pid;
		},
		// Clicking the pinned row again unpins it: the affordance is one
		// gesture, and a row you cannot un-click is a trap.
		pin(item) {
			const path = this.isPinned(item)
				? "api/5/processes/extended/disable"
				: `api/5/processes/extended/${item.pid}`;
			// No optimistic update and no `$forceUpdate` (v4 does both): the
			// next tick re-reads the payload from the server, which is where
			// the pin actually lives. A failed POST therefore leaves the UI
			// showing the truth rather than a pin that was never set.
			postJson(path).catch(() => {});
		},
		unpin() {
			postJson("api/5/processes/extended/disable").catch(() => {});
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

/* The `e` block (2.X-b3-web). Scoped here for the same reason `.gl-sorted`
 * is: one consumer, and nothing in css/v5.css describes a pinned process. */
.gl-pinned {
	margin-bottom: 0.35rem;
}
.gl-pinned-head,
.gl-pinned-line {
	display: flex;
	gap: 0.5ch;
	align-items: baseline;
	flex-wrap: wrap;
}
/* The command line can be arbitrarily long; it must not push the Unpin
 * button off the row. */
.gl-pinned-head > .gl-truncate {
	flex: 1 1 auto;
	min-width: 0;
}
.gl-pin-button {
	flex: 0 0 auto;
	font: inherit;
	color: inherit;
	background: transparent;
	border: 1px solid currentColor;
	border-radius: 3px;
	padding: 0 0.5ch;
	cursor: pointer;
	opacity: 0.8;
}
.gl-pin-button:hover {
	opacity: 1;
}
/* Every row is clickable, so every row says so on hover: the pointer AND a
 * raised background, which is what v4 gets from Bootstrap's `table-hover`
 * (plugin-processlist.vue:38). v5 ships no Bootstrap, so the rule lives here.
 *
 * `.gl-pinnable` and not `.gl-table tr`: `programlist`, `containers` and the
 * left-column blocks are not clickable, and a row that lights up under the
 * cursor but does nothing when clicked is a lie about what a click will do.
 *
 * The colour is `--gl-row-hover`, a token of its own in css/v5.css rather
 * than `--gl-surface` (the overlays' raised background, which must not
 * retune this) and never a literal, which
 * test_no_colour_literal_outside_the_token_file forbids here anyway. */
.gl-table tr.gl-pinnable {
	cursor: pointer;
}
.gl-table tr.gl-pinnable:hover {
	background: var(--gl-row-hover);
}
/* The pinned row, marked the way the terminal marks its selection: the
 * command underlined, not the whole row inverted
 * (processlist/render_curses_v5.py `_select`). */
.gl-table tr.gl-pinned-row td:last-child span {
	text-decoration: underline;
}
</style>

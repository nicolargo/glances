<template>
	<CollectionBlock
		:title="TITLE"
		:payload="payload"
		:error="error"
		table-class="gl-process-table"
		:style="fixedColsStyle"
		:hidden="!!payload && rows.length === 0"
	>
		<template #cols>
			<colgroup>
				<!-- One <col> per painted cell EXCEPT the last, deliberately.
				Under `table-layout: fixed` (CSS 2.1 17.5.2.1) a column past the
				<colgroup>'s specified count takes the whole remaining space once
				every other column is pinned, so the tail column is the elastic
				one -- the browser's equivalent of the TUI's unbounded trailing
				Command cell (containers/render_curses_v5.py:213), and the same
				mechanism PluginProcesslist.vue uses for its own Command column.
				Which column that is depends on the cascade: `command` normally,
				`ports` once `command` is dropped, and so on down `_DROP_ORDER`. -->
				<col v-for="(cell, index) in fixedCells" :key="index" :style="colStyle(cell)" />
			</colgroup>
		</template>
		<template #head>
			<tr>
				<!-- The TUI's header literals (containers/render_curses_v5.py:124-165).
				`CONTAINER` is the block title -- no separate title row, as `fs` does
				in spec D6. -->
				<th v-if="shows('engine')" class="gl-header">Engine</th>
				<th v-if="shows('pod')" class="gl-header">Pod</th>
				<th v-if="shows('name')" class="gl-header">{{ TITLE }}</th>
				<th v-if="shows('status')" class="gl-header gl-num">Status</th>
				<th v-if="shows('uptime')" class="gl-header gl-num">Uptime</th>
				<th v-if="shows('cpu')" class="gl-header gl-num">CPU%</th>
				<th v-if="shows('mem')" class="gl-header gl-num">MEM</th>
				<th v-if="shows('memory_max')" class="gl-header">/MAX</th>
				<template v-if="shows('diskio')">
					<th class="gl-header gl-num">IOR/s</th>
					<th class="gl-header gl-num gl-num-left">IOW/s</th>
				</template>
				<template v-if="shows('networkio')">
					<th class="gl-header gl-num">Rx/s</th>
					<th class="gl-header gl-num gl-num-left">Tx/s</th>
				</template>
				<th v-if="shows('ports')" class="gl-header">Ports</th>
				<th v-if="shows('command')" class="gl-header">Command</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td v-if="shows('engine')"><span>{{ fmt(item.engine) }}</span></td>
					<!-- The column's VISIBILITY is gated on `pod_name` (:265 in the
					renderer), but the CELL renders `pod_id` (:235) -- they are two
					distinct payload fields. -->
					<td v-if="shows('pod')"><span>{{ fmt(item.pod_id) }}</span></td>
					<!-- `.gl-truncate` and a `title`, but no `.gl-name` cap: the
					<col> above already holds this column to the terminal's own
					`name_w`, and `.gl-process-table td` crops what overflows. -->
					<td v-if="shows('name')">
						<span class="gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
					</td>
					<!-- The TUI colours `status` from its own mapping, never from
					`_levels` (containers/render_curses_v5.py `_status_role`). -->
					<td v-if="shows('status')" class="gl-num">
						<span :class="statusClass(item.status)">{{ fmt(item.status) }}</span>
					</td>
					<td v-if="shows('uptime')" class="gl-num"><span>{{ fmt(item.uptime) }}</span></td>
					<td v-if="shows('cpu')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_percent')">{{
							formatPercent(item.cpu_percent)
						}}</span>
					</td>
					<!-- The displayed MEM is the no-cache value (the v4 MEM column);
					`memory_usage` is the export value and is NOT shown. -->
					<td v-if="shows('mem')" class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{
							formatAutoUnit(item.memory_usage_no_cache)
						}}</span>
					</td>
					<!-- The limit is never coloured. -->
					<td v-if="shows('memory_max')"><span>/{{ formatAutoUnit(item.memory_limit) }}</span></td>
					<template v-if="shows('diskio')">
						<td class="gl-num"><span>{{ ioText(item.io_rx) }}</span></td>
						<td class="gl-num gl-num-left"><span>{{ ioText(item.io_wx) }}</span></td>
					</template>
					<template v-if="shows('networkio')">
						<td class="gl-num"><span>{{ netText(item.network_rx) }}</span></td>
						<td class="gl-num gl-num-left"><span>{{ netText(item.network_tx) }}</span></td>
					</template>
					<td v-if="shows('ports')">
						<span class="gl-truncate" :title="fmt(item.ports)">{{ fmt(item.ports) }}</span>
					</td>
					<td v-if="shows('command')">
						<span class="gl-truncate" :title="fmt(item.command)">{{ fmt(item.command) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { dashIfBlank, formatAutoUnit, formatNetworkRate, formatPercent } from "./format.js";
import { cellClassFor } from "./columns.js";
import { levelClass } from "./levels.js";
import { displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";
import { CONTAINERS_DROP_ORDER, dropCascade } from "./drop_order.js";
import {
	hiddenColumns as resolveHiddenColumns,
	nameWidth as resolveNameWidth,
	rowWidth,
	visibleCells,
} from "./containers_columns.js";
import { fitBlockMixin } from "./fit_block.js";
import { PLUGIN_PROPS } from "./plugin_props.js";
import { COL_SEPARATOR } from "./process_widths.js";

const TITLE = "CONTAINER";

// containers/render_curses_v5.py `_STATUS_ROLE`: this plugin's OWN status ->
// tier map, mirroring that renderer (not v4 WebUI's `getStatusClass`, whose
// dead/unhealthy -> "error" has no v5 equivalent -- v5 folds them to
// CRITICAL, same as the TUI comment explains). A status absent from this
// map gets no class, exactly like the TUI's ColorRole.DEFAULT paints
// nothing.
const STATUS_TIER = {
	running: "ok",
	healthy: "ok",
	dead: "critical",
	unhealthy: "critical",
	created: "warning",
	exited: "warning",
	paused: "careful",
	restarting: "careful",
};

export default {
	name: "PluginContainers",
	components: { CollectionBlock },
	mixins: [fitBlockMixin],
	// The vertical row quota AppShell's refitVertical() pass allots this
	// block (row_budget.js), handed down via provide()/inject -- same
	// reasoning as PluginProcesslist.vue's own `rowBudget` inject
	// (AppShell.vue:114-127): a prop on the shared `<component>` binding
	// would leak a `row-budget` DOM attribute on the other 31 plugins. `{}`
	// means no budget -- an environment without measurement must never hide
	// stats (design 4.8).
	inject: {
		rowBudget: { default: () => ({}) },
	},
	// Reads `serverArgs.byte` (--byte): network rates in bytes instead of bits,
	// as the TUI does (containers/render_curses_v5.py).
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// Payload order: the sort is server-side (containers/model_v5.py
		// `_sort`, aligned on the process sort). UNBUDGETED -- `hiddenColumns`
		// below reads this, not `rows`: containers/render_curses_v5.py:264-265
		// decides `show_engine`/`show_pod` from the full item list, BEFORE its
		// own `items[:budget]` slice (:273), so a container a cramped
		// viewport pushes past the quota must still count toward "is there a
		// pod here".
		allRows() {
			return this.payload?.data || [];
		},
		// containers has no config cap to compose with (unlike processlist's
		// `maxProcessesDisplay`) -- the row budget is its only ceiling, so its
		// `0` legitimately means "hide the block entirely" (`>= 0`), the
		// browser's counterpart of the TUI's own `budget <= 0` early return
		// (containers/render_curses_v5.py:269-270).
		rows() {
			const budget = this.rowBudget?.containers;
			if (Number.isInteger(budget) && budget >= 0) {
				return this.allRows.slice(0, budget);
			}
			return this.allRows;
		},
		// The cascade the mixin resolves: the TUI's drop order, as steps.
		// A computed so the array reaching resolveDegrade() is not a reactive
		// Proxy of component data.
		dropCascadeSteps: () => dropCascade(CONTAINERS_DROP_ORDER),
		// Both families, unioned (containers_columns.js): the data-driven set
		// plus whatever the width cascade dropped this pass. `allRows`, not
		// `rows` -- see `allRows`' own comment above.
		hiddenColumns() {
			return resolveHiddenColumns(this.allRows, this.payload?.disable_stats, this.dropFlags);
		},
		// The name column's width, in characters: the terminal's own `name_w`
		// (containers/render_curses_v5.py:261-262). `allRows`, not `rows` --
		// the TUI computes it BEFORE slicing to the row budget (:273), so a
		// container a short viewport hides does not change the column width.
		nameWidth() {
			return resolveNameWidth(this.allRows, this.payload?.max_name_size, TITLE);
		},
		// Every cell still on screen, in display order.
		cells() {
			return visibleCells(this.hiddenColumns, this.nameWidth);
		},
		// The same list minus the LAST cell: that one is the elastic tail, and
		// giving it a <col> would pin it (see the <colgroup> comment in the
		// template).
		fixedCells() {
			return this.cells.slice(0, -1);
		},
		// The integer the stylesheet turns into the table's `min-width`, same
		// contract as processBlockMixin's own `fixedColsStyle`: CSS does the
		// character->pixel conversion, so no JS ever measures `--gl-col`. The
		// sum covers EVERY cell, the elastic tail included -- at its floor,
		// which is the width `_COL_GEOMETRY` already budgets it at (8 for
		// `command`, its own width for any other tail). So the table overflows
		// its container at the same point the TUI's row_width() stops fitting,
		// and the cascade fires there.
		fixedColsStyle() {
			return { "--gl-fixed-cols": String(rowWidth(this.cells)) };
		},
	},
	watch: {
		// A new container, a longer command or a wider port list changes the
		// natural width, so the cascade must be re-resolved -- the
		// ResizeObserver does not fire when only the CONTENT changes.
		payload() {
			this.fitBlock().catch(() => {});
		},
	},
	methods: {
		cellClassFor,
		formatAutoUnit,
		formatPercent,
		shows(column) {
			return !this.hiddenColumns.has(column);
		},
		nameOf(item) {
			return displayName(item, "name");
		},
		statusClass(status) {
			return levelClass({ level: STATUS_TIER[String(status || "").toLowerCase()] });
		},
		fmt: dashIfBlank,
		// containers/render_curses_v5.py `_io_cell`: auto_unit() plus a "B".
		ioText(value) {
			return typeof value === "number" ? `${formatAutoUnit(value)}B` : "-";
		},
		// `_net_cell` is `network`'s rule: bits by default, bytes under --byte.
		netText(value) {
			return formatNetworkRate(value, !!this.serverArgs.byte);
		},
		// `+ COL_SEPARATOR`, not the bare width: under table-layout:fixed the
		// <col> is the column's WHOLE box and
		// `.gl-process-table td:not(:last-child)`'s `padding-right` separator
		// comes out of that same box, so a <col> of exactly N characters would
		// leave only N - COL_SEPARATOR for content. Same reasoning, same
		// constant, as processBlockMixin's own colStyle(); `fixedColsStyle`
		// needs no counterpart because rowWidth() charges the separators
		// itself, one per inter-cell boundary.
		colStyle(cell) {
			return { width: `calc(${cell.width + COL_SEPARATOR} * var(--gl-col))` };
		},
	},
};
</script>

<style scoped>
/* The TUI right-aligns `IOR/s`/`Rx/s` and LEFT-aligns `IOW/s`/`Tx/s`
 * (containers/render_curses_v5.py:158-162 for the headers, :205-209 for the
 * cells), so each rate pair hugs in the middle instead of drifting apart.
 * The element is part of the selector on purpose: a bare `.gl-num-left`
 * (0,1,0) only ties with the global `.gl-num` (0,1,0) and the winner would
 * be decided by source order, which nothing guarantees between a scoped
 * style and the token file. */
.gl-table th.gl-num-left,
.gl-table td.gl-num-left {
	text-align: left;
}
</style>

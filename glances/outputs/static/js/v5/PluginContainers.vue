<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<tr>
				<!-- The TUI's header literals (containers/render_curses_v5.py:124-165).
				`CONTAINER` is the block title -- no separate title row, as `fs` does
				in G9-6 D6. -->
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
					<td v-if="shows('name')">
						<span class="gl-name gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
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
						<span class="gl-ports gl-truncate" :title="fmt(item.ports)">{{ fmt(item.ports) }}</span>
					</td>
					<td v-if="shows('command')">
						<span class="gl-command gl-truncate" :title="fmt(item.command)">{{ fmt(item.command) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { formatAutoUnit, formatNetworkRate, formatPercent } from "./format.js";
import { cellClassFor } from "./columns.js";
import { levelClass } from "./levels.js";
import { displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";
import { CONTAINERS_DROP_ORDER, dropCascade } from "./drop_order.js";
import { hiddenColumns as resolveHiddenColumns } from "./containers_columns.js";
import { fitBlockMixin } from "./fit_block.js";

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
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// `byte` (--byte) switches the network rates from bits to bytes, as the
		// TUI reads `view["byte"]` (containers/render_curses_v5.py:208).
		serverArgs: { type: Object, default: () => ({}) },
		// Declared and left unused: the shell binds `degrade` to every
		// component in a slot from one shared expression (AppShell.vue), and
		// an undeclared object prop would fall through as a stringified DOM
		// attribute on the root element. This component owns its own width
		// cascade (fit_block.js's `dropFlags`), not the shell's zone-level one.
		degrade: { type: Object, default: () => ({}) },
	},
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
		fmt(value) {
			return value === null || value === undefined || value === "" ? "-" : String(value);
		},
		// containers/render_curses_v5.py `_io_cell`: auto_unit() plus a "B".
		ioText(value) {
			return typeof value === "number" ? `${formatAutoUnit(value)}B` : "-";
		},
		// `_net_cell` is `network`'s rule: bits by default, bytes under --byte.
		netText(value) {
			return formatNetworkRate(value, !!this.serverArgs.byte);
		},
	},
};
</script>

<style scoped>
/* The TUI's name column (containers/render_curses_v5.py `max_name_size`,
 * default 20 -- published in the payload, capped here at the same value). */
.gl-plugin {
	--gl-name-width: calc(20 * var(--gl-col));
}
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

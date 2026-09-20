<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<tr>
				<!-- The TUI's header literals (vms/render_curses_v5.py:83-107), not
				schema labels: the renderer hardcodes them too, and the vms schema
				declares no short_name. -->
				<th v-if="showEngine" class="gl-header">Engine</th>
				<th class="gl-header">Name</th>
				<th class="gl-header gl-num">Status</th>
				<th class="gl-header gl-num">Core</th>
				<th class="gl-header gl-num">CPU%</th>
				<th class="gl-header gl-num">MEM/MAX</th>
				<th v-if="showLoad" class="gl-header gl-num">LOAD 1/5/15min</th>
				<th class="gl-header">Release</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td v-if="showEngine"><span>{{ item.engine }}</span></td>
					<td>
						<span class="gl-name gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
					</td>
					<!-- `status` keeps the TUI's own mapping (`_status_role`) and is
					never coloured from `_levels` -- see `statusClass()` below. -->
					<td class="gl-num"><span :class="statusClass(item.status)">{{ item.status || "-" }}</span></td>
					<td class="gl-num"><span>{{ fmt(item.cpu_count) }}</span></td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'cpu_time')">{{ formatPercent(item.cpu_time) }}</span>
					</td>
					<!-- ONE cell for MEM and MAX, both carrying the memory_percent
					tier: the TUI glues them deliberately (renderer docstring). -->
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'memory_percent')">{{ memText(item) }}</span>
					</td>
					<td v-if="showLoad" class="gl-num">
						<span :class="cellClassFor(payload, item, 'load_1min')">{{ loadText(item) }}</span>
					</td>
					<td><span>{{ fmt(item.release) }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { dashIfMissing, formatAutoUnit, formatPercent } from "./format.js";
import { cellClassFor } from "./columns.js";
import { levelClass } from "./levels.js";
import { displayName } from "./rows.js";
import CollectionBlock from "./CollectionBlock.vue";
import { PLUGIN_PROPS } from "./plugin_props.js";

const TITLE = "VMS";

// vms/render_curses_v5.py `_STATUS_ROLE`: this plugin's OWN status -> tier
// map, mirroring that renderer (not v4 WebUI's `getStatusClass`, whose
// unmapped default is "info", a role v5 does not have -- v5 leaves an
// unmapped status uncoloured, same as the TUI's ColorRole.DEFAULT).
const STATUS_TIER = {
	running: "ok",
	starting: "warning",
	restarting: "warning",
	"delayed shutdown": "warning",
};

export default {
	name: "PluginVms",
	components: { CollectionBlock },
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
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// Payload order: the sort is server-side (vms/model_v5.py
		// `sort_vm_stats`, aligned on the process sort), and the renderer does
		// not re-sort. UNBUDGETED -- `showEngine`/`showLoad` below read this,
		// not `rows`: vms/render_curses_v5.py:157-162 decides both from the
		// full item list, BEFORE its own `items = items[:budget]` slice
		// (:169), so a VM that a cramped viewport pushes past the quota must
		// still count toward "is there more than one engine here".
		allRows() {
			return this.payload?.data || [];
		},
		// vms has no config cap to compose with (unlike processlist's
		// `maxProcessesDisplay`) -- the row budget is its only ceiling, so its
		// `0` legitimately means "hide the block entirely" (`>= 0`), the
		// browser's counterpart of the TUI's own `budget <= 0` early return
		// (vms/render_curses_v5.py:167-168).
		rows() {
			const budget = this.rowBudget?.vms;
			if (Number.isInteger(budget) && budget >= 0) {
				return this.allRows.slice(0, budget);
			}
			return this.allRows;
		},
		// vms/render_curses_v5.py:157 -- more than one DISTINCT engine.
		showEngine() {
			return new Set(this.allRows.map((item) => String(item.engine ?? ""))).size > 1;
		},
		// :162 -- the FIRST item decides, exactly as the TUI does: the engine
		// either publishes load for all its VMs or for none.
		showLoad() {
			return this.allRows.length > 0 && this.allRows[0].load_1min !== null && this.allRows[0].load_1min !== undefined;
		},
	},
	methods: {
		cellClassFor,
		formatPercent,
		nameOf(item) {
			return displayName(item, "name");
		},
		statusClass(status) {
			return levelClass({ level: STATUS_TIER[String(status || "").toLowerCase()] });
		},
		// vms/render_curses_v5.py `_fmt`: a null renders as the placeholder.
		fmt: dashIfMissing,
		memText(item) {
			return `${formatAutoUnit(item.memory_usage)}/${formatAutoUnit(item.memory_total)}`;
		},
		// The TUI formats the three averages at one decimal and drops the whole
		// cell if any is missing (`except (KeyError, TypeError)`); showLoad has
		// already established that the engine publishes them.
		loadText(item) {
			const parts = [item.load_1min, item.load_5min, item.load_15min];
			if (parts.some((value) => typeof value !== "number")) return "-";
			return parts.map((value) => value.toFixed(1)).join("/");
		},
	},
};
</script>

<style scoped>
/* The TUI's name column (vms/render_curses_v5.py max_name_size default 20). */
.gl-plugin {
	--gl-name-width: calc(20 * var(--gl-col));
	/* Spec divergence 4: vms has no width cascade (unlike `containers`), so a
	 * too-wide table scrolls horizontally WITHIN the block instead of
	 * cropping columns or letting the whole page scroll -- the other
	 * overflow-x: auto containers (AppShell.vue's header/top zones, the
	 * footer) do not cover this block. */
	overflow-x: auto;
}
</style>

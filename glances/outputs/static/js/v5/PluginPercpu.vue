<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- v4/TUI parity (percpu/render_curses_v5.py): quicklook already shows
			the per-core totals once it is on screen, so this block drops its `CPU`
			title cell AND its `total` column -- not just the row labels below. -->
			<tr>
				<th v-if="standalone" class="gl-header">{{ TITLE }}</th>
				<th v-if="standalone" class="gl-header gl-num">total</th>
				<th v-for="field in statFields" :key="field" class="gl-header gl-num">{{ field }}</th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<tr v-for="row in displayRows" :key="row.key">
					<!-- Row labels vanish with the title and the `total` column
					(same `standalone` gate, same TUI reason). -->
					<td v-if="standalone">
						<span class="gl-name">{{ row.label }}</span>
					</td>
					<td v-if="standalone" class="gl-num">{{ formatPercent(row.stats.total) }}</td>
					<td v-for="field in statFields" :key="field" class="gl-num">{{ formatPercent(row.stats[field]) }}</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { computed } from "vue";
import CollectionBlock from "./CollectionBlock.vue";
import { formatPercent } from "./format.js";
import { PLUGIN_PROPS } from "./plugin_props.js";

const TITLE = "CPU";

// v4 fidelity fallback (percpu/render_curses_v5.py _DEFAULT_MAX_CPU_DISPLAY):
// used only when the payload predates `max_cpu_display` (an older server).
const DEFAULT_MAX_CPU_DISPLAY = 4;

export default {
	name: "PluginPercpu",
	components: { CollectionBlock },
	// The instantiated-plugin list AppShell provides -- see AppShell.vue's
	// `provide()`. This is `inject`, deliberately NOT a prop like `serverArgs`
	// or `degrade`: it has exactly one consumer (this component), so
	// declaring it as a prop on all 24 registered components would leave 23
	// dead declarations, and leaving it undeclared everywhere else would leak
	// a `server-plugins` DOM attribute on every other block. Do not "fix"
	// this back into a prop. The default
	// is a reactive empty list for a component mounted outside AppShell (the
	// render probe, a future unit test) -- empty means "quicklook not
	// instantiated", i.e. the standalone shape.
	inject: {
		serverPlugins: { default: () => computed(() => []) },
	},
	// Reads `serverArgs.percpu` and `degrade.hide_quicklook`, both in
	// `standalone` below.
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// v4/TUI parity, deliberately narrowed: v4 gates
		// this on ONE flag (`args.percpu`) that governs both "percpu is on
		// screen" and "quicklook draws per-core bars" at once
		// (percpu/render_curses_v5.py module docstring). v5 split that into
		// two independent facts -- quicklook merely being INSTANTIATED is not
		// enough, quicklook must actually be drawing the per-core bars
		// (`serverArgs.percpu`, the same flag quicklook itself reads) -- or a
		// quicklook showing only the aggregate `cpu` bar silently strips this
		// block's title, `total` column and row labels for no reason.
		standalone() {
			// `inject` auto-unwraps a Ref/ComputedRef onto `this` in the Options
			// API (Vue's `resolveInjections`), so this is the plain array, not
			// the ref -- no `.value` here, unlike inside AppShell's `provide()`.
			// A quicklook the width cascade hid is not on screen either (TUI twin:
			// curses_renderer_v5.build_frame `quicklook_on_screen`).
			const quicklookOnScreen = this.serverPlugins.includes("quicklook") && !this.degrade.hide_quicklook;
			return !(quicklookOnScreen && this.serverArgs.percpu);
		},
		rows() {
			return (this.payload?.data || []).filter((item) => item && typeof item === "object");
		},
		// The columns the TUI resolves from `sys.platform` cannot be resolved
		// in the browser, but the SERVER can: the model publishes the resolved
		// order as `stat_fields` -- the same treatment `max_cpu_display`
		// already gets. The first core's own numeric
		// keys are only the fallback for a payload from an older server that
		// predates the field.
		statFields() {
			const published = this.payload?.stat_fields;
			if (Array.isArray(published) && published.length && published.every((f) => typeof f === "string")) {
				return published;
			}
			const first = this.rows[0];
			if (!first) return [];
			return Object.keys(first).filter((key) => key !== "cpu_number" && key !== "total" && typeof first[key] === "number");
		},
		// Cores sorted by `total` descending, the first `max_cpu_display` of
		// them, then -- when some did not fit -- a `CPU*` row averaging ONLY
		// the cores that did NOT fit (issue #3687, percpu/render_curses_v5.py).
		displayRows() {
			const sorted = [...this.rows].sort((a, b) => (Number(b.total) || 0) - (Number(a.total) || 0));
			const maxDisplay = Number.isInteger(this.payload?.max_cpu_display)
				? this.payload.max_cpu_display
				: DEFAULT_MAX_CPU_DISPLAY;
			const displayed = sorted.slice(0, maxDisplay);
			const overflow = sorted.slice(maxDisplay);

			const rows = displayed.map((item) => ({
				key: `cpu-${item.cpu_number}`,
				label: `CPU${item.cpu_number}`,
				stats: item,
			}));

			if (overflow.length) {
				const fields = this.standalone ? ["total", ...this.statFields] : this.statFields;
				const means = {};
				for (const field of fields) {
					const values = overflow.map((item) => Number(item[field]) || 0);
					means[field] = values.reduce((a, b) => a + b, 0) / values.length;
				}
				rows.push({ key: "cpu-mean", label: "CPU*", stats: means });
			}
			return rows;
		},
	},
	methods: {
		formatPercent,
	},
};
</script>

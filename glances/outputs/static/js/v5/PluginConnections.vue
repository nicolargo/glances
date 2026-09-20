<template>
	<article v-show="!hidden" class="gl-plugin" :aria-label="TITLE">
		<!-- aria-label: once loaded the title is a <dt>, not a heading. Keep this
		comment INSIDE the root: the build keeps template comments, and one
		before <article> would make a second root node and drop data-plugin. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">{{ TITLE }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl>
				<!-- The TUI's title line carries no value, so the pair that opens
				the grid has an empty <dd> -- the shape PluginLoad.vue established,
				where the core count fills that slot. -->
				<dt class="gl-header">{{ TITLE }}</dt>
				<dd></dd>
				<template v-for="row in rows" :key="row.field">
					<dt class="gl-header">{{ labelFor(labels, row.field) }}</dt>
					<dd :class="row.className">{{ row.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";
import { formatFixed0 } from "./format.js";
import { PLUGIN_PROPS } from "./plugin_props.js";

const TITLE = "TCP CONNECTIONS";

// The TUI's fixed display order (connections/render_curses_v5.py:48-53). Each
// row is skipped when its key is ABSENT from the payload -- absent, not null.
const STATE_FIELDS = ["LISTEN", "initiated", "ESTABLISHED", "terminated"];

export default {
	name: "PluginConnections",
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// Neither probe enabled -> the TUI returns [] and the block is not
		// painted. Before the first payload the block still says "loading…",
		// like every other left-column block.
		hidden() {
			if (!this.payload || this.error) return false;
			return !this.payload.net_connections_enabled && !this.payload.nf_conntrack_enabled;
		},
		rows() {
			const payload = this.payload || {};
			const rows = [];
			if (payload.net_connections_enabled) {
				for (const field of STATE_FIELDS) {
					if (field in payload) rows.push({ field, value: String(payload[field]), className: "" });
				}
			}
			// Both values must be present: conntrack can be enabled and still
			// have nothing to report (connections/render_curses_v5.py:95).
			if (
				payload.nf_conntrack_enabled &&
				payload.nf_conntrack_count !== null && payload.nf_conntrack_count !== undefined &&
				payload.nf_conntrack_max !== null && payload.nf_conntrack_max !== undefined
			) {
				rows.push({
					field: "nf_conntrack_count",
					value: `${formatFixed0(payload.nf_conntrack_count)}/${formatFixed0(payload.nf_conntrack_max)}`,
					className: levelClass(scalarLevel(payload, "nf_conntrack_percent")),
				});
			}
			return rows;
		},
	},
	methods: { labelFor },
};
</script>

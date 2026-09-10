<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">CPU</h2>
			<span v-if="payload" :class="levelClass(scalarLevel(payload, 'total'))">{{
				formatPercent(payload.total)
			}}</span>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else class="gl-stat-grid">
			<dl v-for="(column, i) in columns" :key="i">
				<template v-for="(stat, j) in column" :key="j">
					<dt class="gl-header">{{ stat.field ? labelFor(labels, stat.field) : "" }}</dt>
					<dd :class="levelClass(scalarLevel(payload, stat.field))">{{ stat.value }}</dd>
				</template>
			</dl>
		</div>
	</article>
</template>

<script>
import { formatCount, formatPercent } from "./format.js";
import { levelClass, scalarLevel } from "./levels.js";
import { labelFor } from "./labels.js";

// Column 3 holds counters, not percentages -- see formatCount.
const COUNTER_FIELDS = new Set(["interrupts", "soft_interrupts", "ctx_switches", "syscalls"]);
// `cpucore` is a core COUNT. Its schema unit is "number", which the TUI
// renders through format_number() (curses_formatters_v5.py:83) as a bare
// integer -- formatPercent would print "4.0%" and formatCount would K-scale
// a 1024-core machine to "1.0K".
const PLAIN_FIELDS = new Set(["cpucore"]);

export default {
	name: "PluginCpu",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
	},
	computed: {
		// Mirrors glances/plugins/cpu/render_curses_v5.py:145-200. The TUI
		// branches on payload CONTENT, never on the operating system, which
		// is why a browser can reproduce it without knowing the server's OS.
		columns() {
			const p = this.payload || {};
			const col1 = !("user" in p)
				? // The TUI writes `core` here (cpu/render_curses_v5.py:183) but
					// no such field exists -- the schema and v4 both call it
					// `cpucore`. Ported against the real field on purpose; see §10
					// of the G9-4 design spec, which owns fixing the TUI side.
					["idle", "cpucore", "dpc"]
				: ["user", "system", "iowait"];

			// `idle` (maintainer-requested Task 6b move: first row of column 2,
			// above `irq`). Same TUI condition as before
			// (render_curses_v5.py:157): shown only outside the idle-tag branch,
			// where `idle` already opens column 1 above.
			const col2 = [];
			if ("user" in p && p.idle != null) col2.push("idle");
			col2.push("irq", "nice", "steal");

			// `ctx_switches` (maintainer-requested Task 6b move: first row of
			// column 3, above `interrupts`). Same TUI condition as before
			// (render_curses_v5.py:167), gated on the value only, never on
			// `idle_tag`. In the idle-tag branch this can place `ctx_switches`
			// directly above ITSELF at the col-3 fallback below -- the TUI does
			// the same (line 1 shows ctx_sw whenever present; the grid's col-3
			// second row falls back to ctx_switches whenever `soft_interrupts`
			// is null), so the duplication is reproduced faithfully, not
			// deduplicated.
			const col3 = [];
			if (p.ctx_switches != null) col3.push("ctx_switches");
			col3.push("interrupts");
			// Key presence for `guest`, value for the rates: a `rate` field is
			// null BUT PRESENT until its second cycle, so `in` and `!= null`
			// select different columns and are not interchangeable.
			col3.push(p.soft_interrupts != null ? "soft_interrupts" : "ctx_switches");
			if ("guest" in p) col3.push("guest");
			else if (p.syscalls != null) col3.push("syscalls");
			else col3.push("");

			return [col1, col2, col3].map((fields) => fields.map((f) => this.statFor(f)));
		},
	},
	methods: {
		levelClass,
		scalarLevel,
		labelFor,
		formatPercent,
		statFor(field) {
			if (!field) return { field: "", value: "" };
			const value = this.payload?.[field];
			if (PLAIN_FIELDS.has(field)) {
				return { field, value: typeof value === "number" ? String(Math.trunc(value)) : "-" };
			}
			return { field, value: COUNTER_FIELDS.has(field) ? formatCount(value) : formatPercent(value) };
		},
	},
};
</script>

<template>
	<article class="gl-plugin" :aria-label="TITLE">
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else class="gl-tasks">
			<span class="gl-header">{{ TITLE }}</span>
			<template v-if="total !== null">{{ counts }}</template>
		</p>
	</article>
</template>

<script>
import { PLUGIN_PROPS } from "./plugin_props.js";
const TITLE = "TASKS";

// processes.py `sort_for_human` -- the same object the TUI's
// `_sort_indicator_cell` (processcount/render_curses_v5.py:65) reads via
// `sort_for_human.get(key, key)`. "processs name" is not a typo introduced
// here: it is copied verbatim from the Python dict (glances/processes.py:43),
// so a byte-for-byte parity check on the rendered indicator would not need a
// special case for it.
const SORT_FOR_HUMAN = {
	io_counters: "disk IO",
	cpu_percent: "CPU consumption",
	memory_percent: "memory consumption",
	cpu_times: "process time",
	username: "user name",
	name: "processs name",
	cpu_num: "CPU core number",
};

export default {
	name: "PluginProcesscount",
	// `[outputs] max_processes_display` -- the same config key and the same
	// AppShell provide() as processlist/programlist's own inject (task 8):
	// this is the browser's substitute for the TUI's vertical `row_budget`
	// (processcount/render_curses_v5.py `_count_text`, :37) -- the WebUI has
	// no vertical fit pass, so the configured cap is the only bound it knows.
	inject: {
		maxProcessesDisplay: { default: null },
	},
	// Reads `serverArgs.programs` (truncation counter) and
	// `serverArgs.sort_processes_key` / `.auto_sort` (sort indicator).
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// processcount/render_curses_v5.py:82-86: no aggregate yet -> the title
		// alone, never `TASKS 0`.
		total() {
			const total = this.payload?.total;
			return typeof total === "number" ? total : null;
		},
		// `_count_text` (processcount/render_curses_v5.py:37-55), browser
		// equivalent: `total` alone, or `N/total` when the cap actually cuts the
		// list below. Never in the programs view -- `total` counts PROCESSES
		// while `programlist` shows PROGRAMS, so the ratio would compare two
		// different things (the same guard the TUI function itself states).
		countText() {
			const total = this.total;
			if (this.serverArgs && this.serverArgs.programs) return String(total);
			const cap = this.maxProcessesDisplay;
			if (!Number.isInteger(cap) || cap <= 0 || cap >= total) return String(total);
			return `${cap}/${total}`;
		},
		// `_sort_indicator_cell` (processcount/render_curses_v5.py:58-70),
		// browser equivalent. `serverArgs` is AppShell's `effectiveArgs`, whose
		// `sort_processes_key` / `auto_sort` are the LIVE engine values
		// `processcount` publishes (shared sort design, 2026-09-30). A server
		// that predates them only gives the `--sort-processes` startup key, and
		// no `auto_sort`: "sorted by X" is still true then, because that flag
		// is always applied with auto off (main_v5.py `apply_process_flags`).
		sortIndicatorText() {
			const key = this.serverArgs && this.serverArgs.sort_processes_key;
			if (!key) return null;
			const prefix = this.serverArgs.programs ? "Programs" : "Threads";
			const sortHuman = Object.prototype.hasOwnProperty.call(SORT_FOR_HUMAN, key) ? SORT_FOR_HUMAN[key] : key;
			return this.serverArgs.auto_sort
				? `${prefix} sorted automatically by ${sortHuman}`
				: `${prefix} sorted by ${sortHuman}`;
		},
		// One string, built exactly as the TUI concatenates its cells
		// (:88-110), plus the indicator appended as its own trailing cell --
		// the curses painter inserts one space between every cell (see
		// MEMORY project_v5_g7_done), which the previous plain concatenation
		// here had no equivalent of, so it is added explicitly below.
		// Rendered as text rather than as cells because nothing in this line
		// is individually coloured or aligned.
		counts() {
			const total = this.total;
			const thread = this.payload?.thread;
			const running = this.payload?.running;
			const sleeping = this.payload?.sleeping;
			// The TUI writes ` (N thr),` when the count is known and a bare `,`
			// when it is not -- the comma belongs to the total either way.
			let text = ` ${this.countText}${typeof thread === "number" ? ` (${thread} thr)` : ""},`;
			if (typeof running === "number") text += ` ${running} run,`;
			if (typeof sleeping === "number") text += ` ${sleeping} slp,`;
			// "oth" is computed, not published: total - running - sleeping.
			text += ` ${total - (running || 0) - (sleeping || 0)} oth`;
			if (this.sortIndicatorText) text += ` ${this.sortIndicatorText}`;
			return text;
		},
	},
};
</script>

<style scoped>
.gl-tasks {
	margin: 0;
}
</style>

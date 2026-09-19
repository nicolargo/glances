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
const TITLE = "TASKS";

export default {
	name: "PluginProcesscount",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: the TUI's sort indicator reads TUI view state
		// (sort_key / auto_sort / programs), which has no server mirror --
		// spec D7 defers it to G9-9B with `--programs`.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this block never shrinks, it is one line.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// processcount/render_curses_v5.py:82-86: no aggregate yet -> the title
		// alone, never `TASKS 0`.
		total() {
			const total = this.payload?.total;
			return typeof total === "number" ? total : null;
		},
		// One string, built exactly as the TUI concatenates its cells
		// (:88-110). Rendered as text rather than as cells because nothing in
		// this line is individually coloured or aligned.
		counts() {
			const total = this.total;
			const thread = this.payload?.thread;
			const running = this.payload?.running;
			const sleeping = this.payload?.sleeping;
			// The TUI writes ` (N thr),` when the count is known and a bare `,`
			// when it is not -- the comma belongs to the total either way.
			let text = ` ${total}${typeof thread === "number" ? ` (${thread} thr)` : ""},`;
			if (typeof running === "number") text += ` ${running} run,`;
			if (typeof sleeping === "number") text += ` ${sleeping} slp,`;
			// "oth" is computed, not published: total - running - sleeping.
			text += ` ${total - (running || 0) - (sleeping || 0)} oth`;
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

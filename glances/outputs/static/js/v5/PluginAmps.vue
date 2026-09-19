<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<!-- No #head slot: the TUI paints no title and no column header
		(amps/render_curses_v5.py module docstring, v4 parity), so
		CollectionBlock renders no <thead> -- the `ports` case from G9-7 D4.
		`title` is still required by the shell: it names the block for assistive
		technology and shows while loading or erroring. A comment placed BEFORE
		<CollectionBlock> instead of inside it makes this component a two-root
		fragment, which silently drops the `data-plugin`/`aria-label`
		fallthrough attributes AppShell relies on (CollectionBlock.vue's own
		root-comment warning) -- the plugin then vanishes from the page with no
		error anywhere. Keep every comment INSIDE this root. -->
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.name">
					<td>
						<!-- The tier comes from the item's `count` level and lands on the
						NAME, as the TUI does (amps/render_curses_v5.py:78-79). -->
						<span class="gl-name gl-truncate" :class="cellClassFor(payload, item, 'count')" :title="item.name">{{
							item.name
						}}</span>
					</td>
					<td class="gl-num gl-amp-count">
						<span>{{ countOf(item) }}</span>
					</td>
					<!-- Spec D6: the whole result, newlines included, in ONE cell.
					The TUI emits one row per line with the name and count blanked
					after the first; `pre-line` paints the same thing. -->
					<td><span class="gl-amp-result">{{ item.result }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import { cellClassFor } from "./columns.js";
import CollectionBlock from "./CollectionBlock.vue";

const TITLE = "AMPS";

export default {
	name: "PluginAmps",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: nothing in this block depends on a CLI flag.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: hidden as a whole, never shrunk.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		// amps/render_curses_v5.py:70-73: an AMP that has produced nothing yet
		// renders no row at all -- v4 skips it rather than painting an empty
		// one. Payload order: the TUI does not sort this block.
		rows() {
			return (this.payload?.data || []).filter((item) => item.result !== null && item.result !== undefined);
		},
	},
	methods: {
		cellClassFor,
		// amps/render_curses_v5.py:76: a regex-less AMP has nothing to count,
		// so the cell stays empty even when `count` is set.
		countOf(item) {
			return !item.regex || item.count === null || item.count === undefined ? "" : String(item.count);
		},
	},
};
</script>

<style scoped>
/* The TUI's name column (amps/render_curses_v5.py _NAME_COL_WIDTH = 16). */
.gl-plugin {
	--gl-name-width: calc(16 * var(--gl-col));
}
/* `.gl-num` floors a column at 9ch (css/v5.css), a width sized for a rate
 * cell's worst case ("1023.9G/s"). An AMP count is one to four digits, so it
 * can never use that floor and the column rendered far wider than the TUI's.
 * 4ch is the TUI's own column (amps/render_curses_v5.py `_COUNT_COL_WIDTH`);
 * the content sizes the column from there, and a count cannot outgrow it. */
.gl-amp-count {
	min-width: calc(4 * var(--gl-col));
}
/* Spec D6: a multi-line AMP result keeps its newlines in one cell. */
.gl-amp-result {
	white-space: pre-line;
}
</style>

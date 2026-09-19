<template>
	<CollectionBlock title="PORTS" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<!-- No #head slot: `ports` has NO title and NO column header in the TUI
		(ports/render_curses_v5.py, test_no_title_row_deliberate_do_not_fix). It
		sits under `network` and the two read as one block; the missing header is
		that continuity, not an oversight. CollectionBlock renders no <thead>
		when the slot is absent, and the title reaches the page as the
		aria-label only (G9-7 D4). -->
		<template #body>
			<tbody>
				<tr v-for="item in rows" :key="item.indice">
					<td>
						<span class="gl-name gl-truncate" :title="nameOf(item)">{{ nameOf(item) }}</span>
					</td>
					<td class="gl-num">
						<span :class="cellClassFor(payload, item, 'status')">{{ statusText(item) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { formatFixed0 } from "./format.js";

export default {
	name: "PluginPorts",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: `ports` shows no schema label (no column header).
		labels: { type: Object, default: () => ({}) },
		// Declared but unused. An undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk. An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		// Payload order -- the TUI does not sort. An item with neither `url`
		// nor `host` cannot be scanned and is skipped, never rendered with a
		// blank status (ports/render_curses_v5.py:107-114).
		rows() {
			return (this.payload?.data || []).filter((item) => "url" in item || "host" in item);
		},
	},
	methods: {
		cellClassFor,
		nameOf(item) {
			return String(item.description || "");
		},
		statusText(item) {
			return "url" in item ? this.webStatus(item) : this.hostStatus(item);
		},
		// v4 `set_status_if_url` (ports/render_curses_v5.py:70-78).
		webStatus(item) {
			const status = item.status;
			if (typeof status === "number") return `Code ${status}`;
			if (status === null || status === undefined) return "Scanning";
			// The scanner writes the literal string "Error" when requests raises.
			return String(status);
		},
		// v4 `set_status_if_host` (ports/render_curses_v5.py:57-67). The order
		// matters: `true` is checked before the number branch, and `status === 0
		// || status === false` reproduces Python's `status == 0`, which is true
		// for both.
		hostStatus(item) {
			if (item.host === null || item.host === undefined) return "None";
			const status = item.status;
			if (status === null || status === undefined) return "Scanning";
			if (status === true) return "Open";
			if (status === 0 || status === false) return "Timeout";
			// The RTT is stored in seconds and displayed in milliseconds.
			return `${formatFixed0(status * 1000)}ms`;
		},
	},
};
</script>

<style scoped>
/* The TUI's description width (ports/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: calc(25 * var(--gl-col));
}
</style>

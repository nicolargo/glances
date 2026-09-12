<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's FOLDERS line carries no size label; the empty <th>
			keeps the header aligned column by column with the body (the sensors
			precedent). G9-7 D4. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th class="gl-header gl-num"></th>
			</tr>
		</template>
		<template #body>
			<tbody>
				<!-- Keyed by index, not `item.path`: a missing/empty path is
				coalesced to "" (below), and Vue would then collide two such rows
				on the same key. The rows are plain text with no component state,
				so an index key is safe -- PluginSensors.vue keys the same way for
				its own duplicate-key case. -->
				<tr v-for="(item, index) in rows" :key="index">
					<td>
						<span class="gl-name gl-truncate gl-truncate-start" :title="pathOf(item)"><bdi>{{ pathOf(item) }}</bdi></span>
					</td>
					<td class="gl-num">
						<span :class="sizeClass(item)">{{ sizeText(item) }}</span>
					</td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { formatBytes } from "./format.js";

const TITLE = "FOLDERS";

export default {
	name: "PluginFolders",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: the size column has no header to label.
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
		TITLE: () => TITLE,
		// Payload order -- the TUI does not sort (folders/render_curses_v5.py).
		// Every dict item, as the TUI does (folders/render_curses_v5.py:93-94):
		// a missing path is coalesced to "" there, never a dropped row.
		rows() {
			return (this.payload?.data || []).filter((item) => item && typeof item === "object");
		},
	},
	methods: {
		// v4 parity: `str(item.get("path") or "")` (folders/render_curses_v5.py:103)
		// -- a missing/falsy path renders an empty name cell, not "undefined".
		pathOf(item) {
			return item.path || "";
		},
		// The "?" is a rendering decision, not a formatting one: it marks a
		// folder the plugin could not read (errno != 0), and the formatter
		// must stay the plain byte formatter.
		sizeText(item) {
			return `${item.errno ? "?" : ""}${formatBytes(item.size)}`;
		},
		// v4 parity: a broken folder short-circuits the size ladder and gets no
		// `_levels` entry, so it is bold with no colour -- never alert-coloured.
		sizeClass(item) {
			return item.errno ? "gl-strong" : cellClassFor(this.payload, item, "size");
		},
	},
};
</script>

<style scoped>
/* The TUI's path width (folders/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: 24ch;
}
</style>

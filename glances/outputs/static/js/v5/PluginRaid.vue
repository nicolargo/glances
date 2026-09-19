<template>
	<CollectionBlock :title="TITLE" :payload="payload" :error="error" :hidden="!!payload && rows.length === 0">
		<template #head>
			<!-- The TUI's header row: block title, then the schema's labels. -->
			<tr>
				<th class="gl-header">{{ TITLE }}</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "used") }}</th>
				<th class="gl-header gl-num">{{ labelFor(labels, "available") }}</th>
			</tr>
		</template>
		<template #body>
			<!-- One <tbody> per array (G9-7 D3): the sub-lines belong to their
			array, and grouping is what lets a test - and a stylesheet - tell
			them apart from a flat table. -->
			<tbody v-for="array in rows" :key="array.name">
				<tr>
					<td>
						<span class="gl-name gl-truncate" :title="array.title">{{ array.title }}</span>
					</td>
					<!-- An array that is neither raid0-active nor active renders a
					name-only row in the TUI. Here it keeps two EMPTY cells rather
					than a colspan: both look the same, but empty cells keep the
					three-column grid a colspan would let the name spread under. -->
					<td class="gl-num"><span :class="array.className">{{ array.used }}</span></td>
					<td class="gl-num"><span :class="array.className">{{ array.avail }}</span></td>
				</tr>
				<tr v-for="(line, index) in array.subLines" :key="index">
					<td colspan="3"><span class="gl-subline" :class="line.className">{{ line.text }}</span></td>
				</tr>
			</tbody>
		</template>
	</CollectionBlock>
</template>

<script>
import CollectionBlock from "./CollectionBlock.vue";
import { cellClassFor } from "./columns.js";
import { labelFor } from "./labels.js";
import { byText } from "./rows.js";

const TITLE = "RAID disks";

export default {
	name: "PluginRaid",
	components: { CollectionBlock },
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
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
		// sorted(items, key=lambda it: str(it.get("name", ""))) -- code-unit
		// order, so "md12" comes before "md4". A nameless array is skipped.
		rows() {
			return [...(this.payload?.data || [])].filter((item) => item.name).sort(byText("name")).map((item) => this.describe(item));
		},
	},
	methods: {
		labelFor,
		describe(item) {
			// `type` null renders UNKNOWN -- v4 parity.
			const type = item.type === null || item.type === undefined ? "UNKNOWN" : String(item.type).toUpperCase();
			const className = cellClassFor(this.payload, item, "status");
			const components = item.components || {};
			let used = "";
			let avail = "";
			if (item.type === "raid0" && item.status === "active") {
				// raid0 has no redundancy: the TUI shows the component count and
				// a dash.
				used = String(Object.keys(components).length);
				avail = "-";
			} else if (item.status === "active") {
				used = String(item.used);
				avail = String(item.available);
			}
			return { name: item.name, title: `${type} ${item.name}`, used, avail, className, subLines: this.subLines(item, className) };
		},
		subLines(item, className) {
			const lines = [];
			const components = item.components || {};
			if (item.status === "inactive") {
				lines.push({ text: `└─ Status ${item.status}`, className });
				const names = Object.keys(components).sort();
				names.forEach((component, index) => {
					const tree = index === names.length - 1 ? "└─" : "├─";
					lines.push({ text: `   ${tree} disk ${components[component]}: ${component}`, className: "" });
				});
			}
			// NOT an else: an inactive array can also be degraded, and the TUI
			// emits both groups, in this order.
			if (
				item.type !== "raid0" &&
				item.used !== null && item.used !== undefined &&
				item.available !== null && item.available !== undefined &&
				item.used < item.available
			) {
				lines.push({ text: "└─ Degraded mode", className });
				const config = String(item.config || "");
				// The layout line is dropped when it is too wide for the block --
				// v4's `len(config) < 17`. "_" marks a missing disk and is shown
				// as "A", as v4 does.
				if (config.length < 17) lines.push({ text: `   └─ ${config.replace(/_/g, "A")}`, className: "" });
			}
			return lines;
		},
	},
};
</script>

<style scoped>
/* The TUI's array-name width (raid/render_curses_v5.py _NAME_MAX_WIDTH). */
.gl-plugin {
	--gl-name-width: calc(18 * var(--gl-col));
}
</style>

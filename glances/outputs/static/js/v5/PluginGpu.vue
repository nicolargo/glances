<template>
	<article class="gl-plugin">
		<div class="gl-plugin-title">
			<h2 class="gl-header">{{ title }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<div v-else-if="cards.length && isSummary" class="gl-stat-grid">
			<dl>
				<template v-for="row in summaryRows" :key="row.field">
					<dt class="gl-header">{{ row.label }}</dt>
					<dd :class="levelClass(itemLevel(payload, firstId, row.field))">
						{{ row.value }}
					</dd>
				</template>
			</dl>
		</div>
		<table v-else-if="cards.length">
			<tbody>
				<tr v-for="card in cards" :key="card.gpu_id">
					<!-- The tier goes on the <span>, not the <td>: a prominent badge's
					background would otherwise fill the whole cell, 9ch floor and
					padding included, instead of the value's text. -->
					<td v-for="column in columns" :key="column.field" :class="{ 'gl-num': column.numeric }">
						<span :class="cellClassFor(payload, card, column.field)">{{
							column.format(card[column.field])
						}}</span>
					</td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { toFahrenheit } from "./format.js";
import { levelClass, itemLevel } from "./levels.js";
import { labelFor } from "./labels.js";
import { cellClassFor } from "./columns.js";

const HEADER_FALLBACK = "GPU";

function mean(cards, key) {
	const values = cards.map((c) => c && c[key]).filter((v) => typeof v === "number");
	return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

// Mirrors _format_value() in gpu/render_curses_v5.py. gpu's missing marker is
// "N/A", not the "-" every other v5 formatter uses, which is why this lives
// here rather than in format.js.
function gpuValue(value, unit = "%") {
	return typeof value === "number" ? `${Math.round(value)}${unit}` : "N/A";
}

export default {
	name: "PluginGpu",
	props: {
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		labels: { type: Object, default: () => ({}) },
		// The first component that actually READS this -- `meangpu` picks the
		// layout, `fahrenheit` the temperature unit. The declaration is
		// mandatory either way: an undeclared prop becomes a fallthrough
		// attribute, so without this line the DOM gets
		// server-args="[object Object]" on the article.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: this component is hidden as a whole rather than
		// shrunk (spec D7). An undeclared prop becomes a fallthrough attribute.
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		cards() {
			return this.payload?.data || [];
		},
		// Mirrors _build_header(): one card -> its name; several cards all
		// reporting the same name -> "{N} {name}"; otherwise "{N} GPUs". The
		// TUI's 17-character slice is NOT reproduced -- it is a terminal-width
		// constraint, and the browser truncates with the layout (design spec
		// §8.4).
		title() {
			const cards = this.cards;
			if (!cards.length) return HEADER_FALLBACK;
			const first = cards[0].name || HEADER_FALLBACK;
			if (cards.length === 1) return first;
			const same = cards.every((c) => (c.name || HEADER_FALLBACK) === first);
			return same ? `${cards.length} ${first}` : `${cards.length} GPUs`;
		},
		isSummary() {
			return this.cards.length === 1 || !!this.serverArgs.meangpu;
		},
		// v4 quirk, reproduced on purpose: summary mode averages ACROSS the
		// cards but takes its colour from the FIRST card's `_levels`, not from
		// the mean. Do not "fix" this without changing the TUI first.
		firstId() {
			return this.cards.length ? this.cards[0].gpu_id : undefined;
		},
		summaryRows() {
			const cards = this.cards;
			const isMulti = cards.length > 1;
			const rows = ["proc", "mem"].map((field) => ({
				field,
				// The schema holds ONE word per field; the colon and the " mean"
				// suffix are composed here, exactly as _summary_rows() does.
				label: `${labelFor(this.labels, field)}${isMulti ? " mean:" : ":"}`,
				value: gpuValue(mean(cards, field)),
			}));

			const fahrenheit = !!this.serverArgs.fahrenheit;
			let temp = mean(cards, "temperature");
			if (temp !== null && fahrenheit) temp = toFahrenheit(temp);
			rows.push({
				field: "temperature",
				// Only the non-mean form comes from the schema. v4 shortens the
				// word in the mean form ("temperature:" -> "temp mean:"), i.e.
				// the two forms use DIFFERENT words, and a schema holds one
				// string per field -- so the mean form stays a literal.
				label: isMulti ? "temp mean:" : `${labelFor(this.labels, "temperature")}:`,
				value: gpuValue(temp, fahrenheit ? "F" : "C"),
			});
			return rows;
		},
		// v4 quirk, reproduced on purpose: multi mode shows NO temperature at
		// all -- only the name, `proc` and the conditional `mem`. Summary mode
		// shows all three. Do not "fix" this without changing the TUI first.
		//
		// #3631: a card reporting nothing still shows N/A -- hiding the cell
		// per card would misalign heterogeneous rows. The whole column is
		// dropped only when NO card reports memory, which keeps every row
		// aligned and makes the plugin narrower.
		//
		// There is no header row, and the word "mem" is written INSIDE each
		// memory cell -- both exactly as _multi_rows() does (it emits no
		// header at all, and line 116 writes f" mem {value}"). A <thead> here
		// would show `name` and `proc`, two labels the terminal never
		// displays. The card-name column is NOT truncated to 9 characters
		// (design spec §8.4).
		columns() {
			const cols = [
				{ field: "name", format: (v) => v || "" },
				{ field: "proc", format: (v) => gpuValue(v), numeric: true },
			];
			if (this.cards.some((c) => c.mem != null)) {
				cols.push({ field: "mem", format: (v) => `mem ${gpuValue(v)}`, numeric: true });
			}
			return cols;
		},
	},
	methods: {
		levelClass,
		itemLevel,
		cellClassFor,
	},
};
</script>

<style scoped>
.gl-plugin table {
	border-collapse: collapse;
}
.gl-plugin td {
	padding: 0 var(--gl-gap) 0 0;
}
/* `:not(.gl-num)` is load-bearing, not decoration -- see PluginNetwork.vue:
   scoped styles out-specify the global `.gl-num`, so a plain
   `text-align: left` here would stop the numeric columns right-aligning. */
.gl-plugin td:not(.gl-num) {
	text-align: left;
}
</style>

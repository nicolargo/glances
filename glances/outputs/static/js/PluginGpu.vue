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
					<dd
						v-history="cards.length === 1 ? { plugin: 'gpu', field: row.field, item: firstId } : null"
						:class="levelClass(itemLevel(payload, firstId, row.field))"
					>
						{{ row.value }}
					</dd>
				</template>
			</dl>
		</div>
		<table v-else-if="cards.length">
			<tbody>
				<tr v-for="card in cards" :key="card.gpu_id">
					<!-- name: capped at the TUI's 9-character cut (render_curses.py:114
					`[0:9]`), full name on hover -- the established .gl-name/.gl-truncate
					pair (npu's header uses the same shape). Never coloured: the TUI
					never alert-colours the card name either. -->
					<td>
						<span class="gl-name gl-truncate" :title="card.name || ''">{{ card.name || "" }}</span>
					</td>
					<!-- The tier goes on the <span>, not the <td>: a prominent badge's
					background would otherwise fill the whole cell, 9ch floor and
					padding included, instead of the value's text. -->
					<td v-for="column in valueColumns" :key="column.field" class="gl-num" :style="{ '--gl-gpu-chars': column.chars }">
						<span v-history="{ plugin: 'gpu', field: column.field, item: card.gpu_id }" :class="cellClassFor(payload, card, column.field)">{{
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
import { PLUGIN_PROPS } from "./plugin_props.js";

const HEADER_FALLBACK = "GPU";
const HEADER_MAX = 17;

function mean(cards, key) {
	const values = cards.map((c) => c && c[key]).filter((v) => typeof v === "number");
	return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

// Mirrors _format_value() in gpu/render_curses.py. gpu's missing marker is
// "N/A", not the "-" every other v5 formatter uses, which is why this lives
// here rather than in format.js.
// Mirrors _shows_temperature() in gpu/render_curses.py: `hide_temperature`
// is set by the model when the sensors plugin already shows the card's
// temperature, or when `[gpu] hide_temperature` is on.
function showsTemperature(card) {
	return !card.hide_temperature;
}

function gpuValue(value, unit = "%") {
	return typeof value === "number" ? `${Math.round(value)}${unit}` : "N/A";
}

export default {
	name: "PluginGpu",
	// Reads `serverArgs.meangpu` (layout) and `serverArgs.fahrenheit` (unit).
	props: { ...PLUGIN_PROPS },
	computed: {
		cards() {
			return this.payload?.data || [];
		},
		// Mirrors _build_header(): one card -> its name; several cards all
		// reporting the same name -> "{N} {name}"; otherwise "{N} GPUs". The
		// TUI's 17-character cap is reproduced, cut on a word boundary so
		// the header never overflows the stat columns.
		title() {
			const cards = this.cards;
			if (!cards.length) return HEADER_FALLBACK;
			const first = cards[0].name || HEADER_FALLBACK;
			let header = first;
			if (cards.length > 1) {
				const same = cards.every((c) => (c.name || HEADER_FALLBACK) === first);
				header = same ? `${cards.length} ${first}` : `${cards.length} GPUs`;
			}
			if (header.length <= HEADER_MAX) return header;
			const head = header.slice(0, HEADER_MAX + 1);
			return head.includes(" ") ? head.slice(0, head.lastIndexOf(" ")) : header.slice(0, HEADER_MAX);
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
				// The schema holds ONE word per field; the " mean" suffix is
				// composed here, exactly as _summary_rows() does.
				label: `${labelFor(this.labels, field)}${isMulti ? " mean" : ""}`,
				value: gpuValue(mean(cards, field)),
			}));

			if (!cards.some(showsTemperature)) return rows;
			const fahrenheit = !!this.serverArgs.fahrenheit;
			let temp = mean(cards, "temperature");
			if (temp !== null && fahrenheit) temp = toFahrenheit(temp);
			rows.push({
				field: "temperature",
				// Only the non-mean form comes from the schema. v4 shortens the
				// word in the mean form ("temperature" -> "temp mean"), i.e.
				// the two forms use DIFFERENT words, and a schema holds one
				// string per field -- so the mean form stays a literal.
				label: isMulti ? "temp mean" : labelFor(this.labels, "temperature"),
				value: gpuValue(temp, fahrenheit ? "F" : "C"),
			});
			return rows;
		},
		// Multi mode shows the name, `proc`, the conditional `mem` and the
		// conditional temperature -- exactly as _multi_rows() does.
		//
		// #3631: a card reporting nothing still shows N/A -- hiding the cell
		// per card would misalign heterogeneous rows. The mem / temperature
		// column is dropped only when NO card reports it, which keeps every
		// row aligned and makes the plugin narrower.
		//
		// There is no header row, and the word "mem" is written INSIDE each
		// memory cell -- both exactly as _multi_rows() does (it emits no
		// header at all, and line 116 writes f" mem {value}"). A <thead> here
		// would show `name` and `proc`, two labels the terminal never
		// displays. The card-name column IS capped at 9 characters in the
		// template -- the TUI's own cut
		// (render_curses.py:114) -- reversing the earlier design-spec §8.4
		// call after the maintainer's smoke test found the uncapped name
		// pushed every value column to the far edge of its 9ch floor.
		valueColumns() {
			// `chars`: the column's widest possible value, its width floor.
			const cols = [{ field: "proc", format: (v) => gpuValue(v), numeric: true, chars: 4 }];
			if (this.cards.some((c) => c.mem != null)) {
				cols.push({ field: "mem", format: (v) => `mem ${gpuValue(v)}`, numeric: true, chars: 8 });
			}
			if (this.cards.some((c) => showsTemperature(c) && c.temperature != null)) {
				const fahrenheit = !!this.serverArgs.fahrenheit;
				cols.push({
					field: "temperature",
					format: (v) => gpuValue(typeof v === "number" && fahrenheit ? toFahrenheit(v) : v, fahrenheit ? "F" : "C"),
					numeric: true,
					chars: 4,
				});
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
/* : the TUI's name width (render_curses.py:114 `[0:9]`). */
.gl-plugin {
	--gl-name-width: calc(9 * var(--gl-col));
}
/* The global `.gl-num` 9ch floor is wrong for THIS table: it is wider than
   any value gpu ever renders and pushed every value to the far edge of its
   column. With no floor at all the column resizes with the text every tick
   ("9%" -> "100%"), so the numbers jitter. Each column is therefore floored
   at its own widest value, in TUI columns (`--gl-col`, never `ch`, whose
   font-fallback value is 0.5em): 4 for `proc` ("100%") and the temperature
   ("212F", "N/A"), 8 for `mem`, whose format writes the literal "mem "
   inside the cell ("mem 100%"). `--gl-gpu-chars` comes from
   `valueColumns()`. Right-alignment and tabular-nums are unchanged. */
.gl-plugin table td.gl-num {
	min-width: calc(var(--gl-gpu-chars) * var(--gl-col));
}
</style>

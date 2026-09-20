<template>
	<article class="gl-plugin" :aria-label="TITLE" :style="fixedColsStyle">
		<!-- Keep every comment INSIDE this root, like CollectionBlock.vue: one
		before <article> would make a second root node and drop the
		`data-plugin`/`aria-label` attributes AppShell passes down. -->
		<!-- The title is a full-width line of its OWN, above the grid -- the
		TUI's shape (curses_renderer_v5.py:806-816 emits the
		`ALERTS N ongoing · M resolved` row first, then the column-header row
		under it). It used to double as the grid's first <th>, which squeezed
		the whole sentence into the 1-character GLYPH column's box: under
		`table-layout: fixed` that cell cannot grow, so the counts spilled
		across the TIME and DURATION headers. `headerText` keeps the bare
		`ALERT` for every state that paints no grid. -->
		<div class="gl-plugin-title">
			<h2 class="gl-header">{{ headerText }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<!-- Warm-up is not an all-clear (an alert simply cannot have fired
		yet), so it stays neutral rather than claiming a healthy system --
		same rule and wording as the TUI's collapse
		(curses_renderer_v5.py:738-745, `is_initializing`). Checked BEFORE
		the empty-rows branch: with nothing ingested yet, `allRows` is also
		empty, and initializing must win. -->
		<p v-else-if="isInitializing" class="gl-muted">(initializing)</p>
		<!-- `allRows`, not the budget-capped `rows`: a tight vertical row
		budget can shrink `rows` to zero while incidents still exist
		(row_budget.js's "header only" step) -- that state renders the table
		with zero data rows, never this all-clear message. -->
		<!-- OK-coloured, mirroring the TUI (curses_renderer_v5.py:745): this
		was `gl-muted` before, which understated a genuine all-clear as if it
		were merely neutral like "loading"/"(initializing)". -->
		<p v-else-if="!allRows.length" class="gl-level-ok">(no alert detected)</p>
		<table v-else class="gl-table gl-process-table">
			<colgroup>
				<col :style="colStyle('GLYPH')" />
				<col :style="colStyle('TIME')" />
				<col v-if="shows('DURATION')" :style="colStyle('DURATION')" />
				<!-- TARGET gets an explicit width rather than being left width-less
				like TOP below: under table-layout:fixed, two width-less columns
				split the remainder 50/50 (CSS 2.1 17.5.2.1) -- not by floor, not
				by priority. The terminal gives TARGET its natural width and lets
				TOP absorb the slack (curses_renderer_v5.py:534-536); fixed layout
				cannot measure "natural", but `targetWidth` below computes it from
				the rendered strings the same way the terminal does, so the two
				agree. TOP is left as the sole auto column, so it is the one that
				grows. -->
				<col :style="colStyle('TARGET')" />
				<col v-if="shows('TOP')" />
				<col v-if="shows('LEVEL')" :style="colStyle('LEVEL')" />
			</colgroup>
			<thead>
				<tr>
					<!-- Blank, like the TUI's own glyph header
					(curses_renderer_v5.py:818, `Cell(text=" " * _ALERT_W_GLYPH)`):
					the ongoing/resolved dot has no label, and the block title now
					has its own line above the grid. -->
					<th class="gl-header"></th>
					<th class="gl-header">TIME</th>
					<th v-if="shows('DURATION')" class="gl-header">DURATION</th>
					<th class="gl-header">TARGET</th>
					<th v-if="shows('TOP')" class="gl-header">TOP PROCESSES</th>
					<th v-if="shows('LEVEL')" class="gl-header">LEVEL</th>
				</tr>
			</thead>
			<tbody>
				<!-- Payload order: incidents arrive already sorted ongoing-first,
				newest-first within each group (derive_incidents(), design §5.3) --
				this renderer never re-sorts, same rule as vms/containers. `rows`
				is `allRows` capped to the row budget, never a re-sort of it. -->
				<tr v-for="incident in rows" :key="incidentKey(incident)">
					<td><span :class="glyphClass(incident)">{{ glyphOf(incident) }}</span></td>
					<td>{{ timeOf(incident) }}</td>
					<td v-if="shows('DURATION')">{{ incident.duration || "-" }}</td>
					<td>{{ targetOf(incident) }}</td>
					<td v-if="shows('TOP')">{{ topOf(incident) }}</td>
					<td v-if="shows('LEVEL')"><span :class="levelClassOf(incident)">{{ levelTextOf(incident) }}</span></td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { levelClass } from "./levels.js";
import { fitBlockMixin } from "./fit_block.js";
import { droppedColumns } from "./drop_order.js";
// The TUI's own character-column widths (curses_renderer_v5.py:525-540), so
// the <colgroup> and CSS derive from the same numbers the terminal renderer
// uses -- never a literal copied by hand.
import { ALERT_COL_WIDTHS, ALERT_MIN_TARGET, ALERT_MIN_TOP, COL_SEPARATOR } from "./process_widths.js";
import { PLUGIN_PROPS } from "./plugin_props.js";

const TITLE = "ALERT";

// curses_renderer_v5.py `_ALERT_GENERIC_FIELDS`: a field whose whole name is
// in this set identifies nothing on its own -- the plugin (and its key)
// already say what the alert is about ("sensors[i915 0].value" reads better
// as "Sensors i915 0"). Closed list, grounded on the fields that can
// actually raise an alert -- do not widen it without redoing that check.
const GENERIC_FIELDS = new Set(["value", "percent"]);

export default {
	name: "PluginAlert",
	mixins: [fitBlockMixin],
	inject: {
		// The vertical row quota AppShell's refitVertical() pass allots this
		// block (row_budget.js's `budget.alert`), handed down via provide() the
		// same way as PluginProcesslist.vue's own `rowBudget` inject. `{}`
		// means no budget -- an environment without measurement must never
		// hide stats (design 4.8).
		rowBudget: { default: () => ({}) },
	},
	// `payload` is this block's own envelope ({isInitializing, incidents}),
	// not the `{ data: [...] }` every other collection plugin gets: it is fed
	// by /api/5/alert/incidents and validated against no registry `spec`.
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// The full incident list, unbudgeted. titleText's ongoing/resolved
		// counts and the empty/table branches above must read THIS, not the
		// budget-capped `rows` below -- otherwise a tight vertical budget would
		// make the header undercount incidents that are simply not all on
		// screen, or claim "no alert detected" while incidents exist.
		allRows() {
			return (this.payload && this.payload.incidents) || [];
		},
		// The row budget caps the payload's own order -- the first N
		// incidents, never a re-sort. No config key to compose with here,
		// unlike processlist's `maxProcessesDisplay`: `rowBudget.alert` is the
		// only ceiling. `>= 0`, exactly like `rowBudget.processlist`: its `0`
		// legitimately means "header only" (row_budget.js's `alertBlockHeight`
		// collapsing to the title + column-header rows alone), not "no
		// budget".
		rows() {
			if (Number.isInteger(this.rowBudget?.alert) && this.rowBudget.alert >= 0) {
				return this.allRows.slice(0, this.rowBudget.alert);
			}
			return this.allRows;
		},
		isInitializing() {
			return !!(this.payload && this.payload.isInitializing);
		},
		// Exactly the states the template's <table v-else> paints, so
		// `headerText` cannot disagree with what is rendered under it: every
		// earlier branch of that v-if chain (error, no payload, warm-up,
		// nothing to show) keeps the bare `ALERT` title instead of a count.
		hasGrid() {
			return !this.error && !!this.payload && !this.isInitializing && this.allRows.length > 0;
		},
		headerText() {
			return this.hasGrid ? this.titleText : TITLE;
		},
		// Mirrors `_build_alert_title_cells`'s populated text
		// (curses_renderer_v5.py:629-675), minus its own width shrink ladder --
		// the browser has the width, so it never needs to drop the `resolved`
		// clause. Counts are derived from `allRows`, not a server field or the
		// budget-capped `rows`: every incident the block has is the source of
		// truth for this count, regardless of how many rows fit on screen.
		titleText() {
			const nOngoing = this.allRows.filter((incident) => incident.ongoing).length;
			const nResolved = this.allRows.length - nOngoing;
			return `ALERTS  ${nOngoing} ongoing · ${nResolved} resolved`;
		},
		// The TUI's own drop order: TOP first, then LEVEL, then DURATION
		// (curses_renderer_v5.py:538-540). TARGET is never dropped -- it says
		// WHAT the alert is about, and the terminal sacrifices TOP to keep it.
		dropCascadeSteps: () => [
			{ key: "drop_TOP", value: true },
			{ key: "drop_LEVEL", value: true },
			{ key: "drop_DURATION", value: true },
		],
		// The mixin's cumulative `drop_<column>` flags, translated to column
		// names. Unlike containers, this block has no data-driven hiding to
		// union in -- the cascade's flags are the whole story.
		hiddenColumns() {
			return droppedColumns(this.dropFlags);
		},
		// The <col> elements actually rendered: GLYPH, TIME and TARGET always,
		// plus whichever of DURATION/TOP/LEVEL survive the cascade.
		columnCount() {
			return 3 + ["DURATION", "TOP", "LEVEL"].filter((key) => this.shows(key)).length;
		},
		// TARGET's width in characters: its NATURAL width -- the longest target
		// text on screen -- floored at the terminal's own `_ALERT_MIN_TARGET`,
		// which is exactly what the terminal does when it is not
		// width-constrained (curses_renderer_v5.py:781-784). Pinning the <col>
		// to that floor instead, as this block used to, cropped every target
		// past twelve characters -- `Sensors Composite`, `Fs /home percent` --
		// even with the whole right column free beside it.
		//
		// No ceiling, deliberately: when the natural width no longer fits, the
		// cascade above drops TOP first and LEVEL next, which IS the terminal's
		// priority (it sacrifices TOP to keep TARGET readable, :538-540).
		// Measured over `rows`, the budgeted set actually painted, never
		// `allRows` -- an incident scrolled off by the row budget must not widen
		// a column it does not appear in.
		targetWidth() {
			const natural = this.rows.reduce((widest, incident) => Math.max(widest, this.targetOf(incident).length), 0);
			return Math.max(ALERT_MIN_TARGET, natural);
		},
		// The integer the stylesheet turns into a width, same contract as
		// PluginProcesslist.vue's own `fixedColsStyle`: TARGET contributes the
		// `targetWidth` above (its natural width, floored), TOP only its floor
		// -- it is the auto column and takes whatever is left. The sum this
		// produces does NOT match `ALERT_W_WITH_TOP`/`_LEVEL`/`_DURATION`
		// (process_widths.js), and is not meant to: the terminal gives its TIME
		// and DURATION cells one trailing pad column each to land the spec's
		// curses offsets (curses_renderer_v5.py:814-829), which CSS already
		// reserves inside `COL_SEPARATOR`, and TARGET is natural here rather
		// than the floor those constants assume. Do not "correct" either side
		// to match the other: the cascade fires at the same RELATIVE points
		// (the deltas between thresholds agree exactly).
		fixedColsStyle() {
			let total = ALERT_COL_WIDTHS.GLYPH + ALERT_COL_WIDTHS.TIME + this.targetWidth;
			if (this.shows("DURATION")) total += ALERT_COL_WIDTHS.DURATION;
			if (this.shows("LEVEL")) total += ALERT_COL_WIDTHS.LEVEL;
			if (this.shows("TOP")) total += ALERT_MIN_TOP;
			// One separator between cells, never after the last.
			return { "--gl-fixed-cols": String(total + COL_SEPARATOR * (this.columnCount - 1)) };
		},
	},
	watch: {
		// A new incident changes the natural width (a longer TARGET or TOP
		// text), so the cascade must be re-resolved -- the ResizeObserver does
		// not fire when only the CONTENT changes (fit_block.js's documented
		// host contract).
		payload() {
			this.fitBlock().catch(() => {});
		},
	},
	methods: {
		// The engine's own incident identity: `(plugin, key, field)` opens and
		// closes an incident (alerts_incidents_v5.derive_incidents), and `begin`
		// separates two successive incidents on the same tuple. The list
		// re-sorts as incidents resolve (ongoing first, newest first), so an
		// INDEX key would make Vue patch each row into a different incident's
		// data on every tick instead of moving the row.
		incidentKey(incident) {
			return [incident.plugin, incident.key, incident.field, incident.begin].join("\u0000");
		},
		shows(column) {
			return !this.hiddenColumns.has(column);
		},
		glyphOf(incident) {
			return incident.ongoing ? "●" : "○";
		},
		// The glyph keeps the level colour regardless of ongoing/resolved, so
		// the severity an incident reached always stays readable
		// (curses_renderer_v5.py:840-843). Divergence from the TUI: there the
		// glyph carries `prominent` only once LEVEL is width-dropped: the
		// browser drops LEVEL too now, but `prominent` still belongs on LEVEL
		// alone here -- see levelClassOf().
		glyphClass(incident) {
			return levelClass({ level: incident.level });
		},
		// curses_renderer_v5.py:851-861 -- LEVEL is tier-COLOURED only while the
		// incident is ONGOING, so colour in this column means "still
		// happening". The BADGE is a separate axis, though: `:851-861` passes
		// `color=role if is_ongoing else DEFAULT, prominent=prominent` --
		// `prominent` reaches the Cell unconditionally, so a resolved incident
		// that was prominent still paints reverse-video, just without the
		// tier hue.
		levelClassOf(incident) {
			if (incident.ongoing) {
				return levelClass({ level: incident.level, prominent: incident.prominent });
			}
			// The shared `levelClass()` token helper cannot express "badge, no
			// tier hue": a lone `.gl-prominent` has no CSS rule at all
			// (css/v5.css:77-91), specifically so the badge can never appear
			// without SOME tier colour behind it. Matching the TUI here needs a
			// second, alert-local badge variant instead (scoped style below)
			// rather than widening levels.js's shared contract for this one
			// caller.
			return incident.prominent ? "gl-alert-resolved-prominent" : "";
		},
		levelTextOf(incident) {
			return incident.level ? String(incident.level).toUpperCase() : "-";
		},
		// Same-day: HH:MM:SS (local). Any other day: YY-MM-DD. Mirrors
		// _format_alert_time()'s two-form rule; unlike `duration`, this is not
		// server-computed (the server sends only the ISO `begin`), so the
		// browser renders it in the viewer's own local time.
		timeOf(incident) {
			if (!incident.begin) return "--:--:--";
			const begin = new Date(incident.begin);
			if (Number.isNaN(begin.getTime())) return "--:--:--";
			const now = new Date();
			const sameDay =
				begin.getFullYear() === now.getFullYear() &&
				begin.getMonth() === now.getMonth() &&
				begin.getDate() === now.getDate();
			if (sameDay) {
				return begin.toTimeString().slice(0, 8);
			}
			const yy = String(begin.getFullYear()).slice(-2);
			const mm = String(begin.getMonth() + 1).padStart(2, "0");
			const dd = String(begin.getDate()).padStart(2, "0");
			return `${yy}-${mm}-${dd}`;
		},
		// curses_renderer_v5.py `_humanise_target`: only the plugin name is
		// capitalised (its first letter only -- no acronym table, "gpu" stays
		// "Gpu"); the key is kept verbatim (device names, mountpoints and
		// container names are already human-readable); a generic field name
		// is dropped rather than rewritten.
		targetOf(incident) {
			const parts = [];
			const plugin = String(incident.plugin || "");
			if (plugin) parts.push(plugin.slice(0, 1).toUpperCase() + plugin.slice(1));
			if (incident.key !== null && incident.key !== undefined) {
				const key = String(incident.key).trim();
				if (key) parts.push(key);
			}
			const field = String(incident.field || "");
			if (field && !GENERIC_FIELDS.has(field)) parts.push(field.replace(/_/g, " "));
			return parts.join(" ");
		},
		topOf(incident) {
			return (incident.top || []).map((name) => String(name)).join(", ");
		},
		// `N + COL_SEPARATOR`, not `N`: under table-layout:fixed the <col> width
		// is the column's WHOLE box, and `.gl-process-table`'s `padding-right`
		// separator (css/v5.css) comes out of that same box -- a <col> of
		// exactly N characters leaves only N - COL_SEPARATOR for content. Same
		// offset as PluginProcesslist.vue's own colStyle(). TARGET has no entry
		// in ALERT_COL_WIDTHS (the terminal gives it no fixed width, only a
		// floor) -- `targetWidth` stands in for it here.
		colStyle(key) {
			const n = key === "TARGET" ? this.targetWidth : ALERT_COL_WIDTHS[key];
			return { width: `calc(${n + COL_SEPARATOR} * var(--gl-col))` };
		},
	},
};
</script>

<style scoped>
/* Resolved-but-was-prominent: the tier hue drops
 * (levelClassOf() above returns "" for the colour), but the badge does not
 * -- curses_renderer_v5.py:851-861 keeps `prominent` unconditional. Mirrors
 * `.gl-prominent.gl-level-*` (css/v5.css:88-91) but with the theme's muted
 * tone standing in for the tier hue a resolved incident no longer carries. */
.gl-alert-resolved-prominent {
	background: var(--gl-muted);
	color: var(--gl-prominent-fg);
}
</style>

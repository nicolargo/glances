<template>
	<article class="gl-plugin" :aria-label="TITLE" :style="fixedColsStyle">
		<!-- Keep every comment INSIDE this root, like CollectionBlock.vue: one
		before <article> would make a second root node and drop the
		`data-plugin`/`aria-label` attributes AppShell passes down. -->
		<div v-if="error || !payload || !allRows.length" class="gl-plugin-title">
			<h2 class="gl-header">{{ TITLE }}</h2>
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
				TOP absorb the slack (curses_renderer_v5.py:534-536), but "natural
				width" is content-dependent and fixed layout cannot measure that;
				the closest defensible browser equivalent is the same floor the
				terminal itself falls back to (_ALERT_MIN_TARGET, :529). TOP is
				left as the sole auto column, so it is the one that grows. -->
				<col :style="colStyle('TARGET')" />
				<col v-if="shows('TOP')" />
				<col v-if="shows('LEVEL')" :style="colStyle('LEVEL')" />
			</colgroup>
			<thead>
				<tr>
					<!-- The glyph column doubles as the title cell here, the same
					"title is the first <th>" convention CollectionBlock documents
					(CollectionBlock.vue:14): the TUI's own title row (`ALERTS N
					ongoing · M resolved`, curses_renderer_v5.py:806-807) is a
					full-width line above the grid, not a real column, so this is
					where it fits without an unconditional <h2> that would depart
					from every sibling block. -->
					<th class="gl-header">{{ titleText }}</th>
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
				<tr v-for="(incident, i) in rows" :key="i">
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
// The TUI's own character-column widths (curses_renderer_v5.py:525-540), so
// the <colgroup> and CSS derive from the same numbers the terminal renderer
// uses -- never a literal copied by hand.
import { ALERT_COL_WIDTHS, ALERT_MIN_TARGET, ALERT_MIN_TOP } from "./process_widths.js";

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
	props: {
		// Not `{ data: [...] }` like every other collection plugin: this block
		// is fed by its own endpoint (/api/5/alert/incidents), which answers an
		// envelope -- `{isInitializing, incidents}`, AppShell.vue's own shape
		// carried through unchanged, not the route's wire field names -- of
		// already-collapsed incidents, never validated against a registry
		// `spec` (it declares none).
		payload: { type: Object, default: null },
		error: { type: String, default: undefined },
		// Declared but unused: no alert cell depends on a field label.
		labels: { type: Object, default: () => ({}) },
		// Declared but unused: no alert column depends on a CLI flag.
		serverArgs: { type: Object, default: () => ({}) },
		// Declared but unused: the shell binds `degrade` to every component in
		// a slot from one shared expression (AppShell.vue). This block owns its
		// own width cascade via fitBlockMixin (`dropFlags` below), not the
		// shell's zone-level one -- same reasoning as PluginProcesslist.vue's
		// own `degrade` prop.
		degrade: { type: Object, default: () => ({}) },
	},
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
		// `hiddenColumns`/`shows()` did not exist on this component before --
		// it has never had a cascade. Same shape as processlist_columns.js's
		// `hiddenColumns`: the mixin's cumulative `drop_<column>` flags,
		// translated to column names -- no separate module to import it from,
		// unlike processlist, since this cascade has only three steps.
		hiddenColumns() {
			const hidden = new Set();
			for (const [key, value] of Object.entries(this.dropFlags || {})) {
				if (value && key.startsWith("drop_")) hidden.add(key.slice("drop_".length));
			}
			return hidden;
		},
		// The <col> elements actually rendered: GLYPH, TIME and TARGET always,
		// plus whichever of DURATION/TOP/LEVEL survive the cascade.
		columnCount() {
			return 3 + ["DURATION", "TOP", "LEVEL"].filter((key) => this.shows(key)).length;
		},
		// The integer the stylesheet turns into a width, same contract as
		// PluginProcesslist.vue's own `fixedColsStyle`: TARGET and TOP
		// contribute their FLOOR here, never a natural/content width -- CSS
		// cannot measure that under table-layout:fixed. The sum this produces
		// is INTENTIONALLY short of `ALERT_W_WITH_TOP`/`_LEVEL`/`_DURATION`
		// (process_widths.js) by the one trailing pad column the terminal
		// gives its TIME and DURATION cells to land the spec's curses
		// offsets (curses_renderer_v5.py:814-829) -- CSS already reserves
		// that same character as the `padding-right: var(--gl-col)`
		// separator (colStyle()'s `+1`), so adding the terminal's own pad on
		// top would double-count it. Do not "correct" either side to match
		// the other: the cascade fires at the same RELATIVE points (the
		// deltas between thresholds agree exactly), just anchored a few
		// characters earlier in absolute terms than the exported constants.
		fixedColsStyle() {
			let total = ALERT_COL_WIDTHS.GLYPH + ALERT_COL_WIDTHS.TIME + ALERT_MIN_TARGET;
			if (this.shows("DURATION")) total += ALERT_COL_WIDTHS.DURATION;
			if (this.shows("LEVEL")) total += ALERT_COL_WIDTHS.LEVEL;
			if (this.shows("TOP")) total += ALERT_MIN_TOP;
			// One separator between cells, never after the last.
			return { "--gl-fixed-cols": String(total + this.columnCount - 1) };
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
		// `N + 1`, not `N`: under table-layout:fixed the <col> width is the
		// column's WHOLE box, and `.gl-process-table`'s
		// `padding-right: var(--gl-col)` separator (css/v5.css) comes out of
		// that same box -- a <col> of exactly N characters leaves only N-1 for
		// content. Same `+1` as PluginProcesslist.vue's own colStyle(). TARGET
		// has no entry in ALERT_COL_WIDTHS (the terminal gives it no fixed
		// width, only a floor) -- ALERT_MIN_TARGET stands in for it here.
		colStyle(key) {
			const n = key === "TARGET" ? ALERT_MIN_TARGET : ALERT_COL_WIDTHS[key];
			return { width: `calc(${n + 1} * var(--gl-col))` };
		},
	},
};
</script>

<style scoped>
/* Resolved-but-was-prominent (fix round 1, IMPORTANT 2): the tier hue drops
 * (levelClassOf() above returns "" for the colour), but the badge does not
 * -- curses_renderer_v5.py:851-861 keeps `prominent` unconditional. Mirrors
 * `.gl-prominent.gl-level-*` (css/v5.css:88-91) but with the theme's muted
 * tone standing in for the tier hue a resolved incident no longer carries. */
.gl-alert-resolved-prominent {
	background: var(--gl-muted);
	color: var(--gl-prominent-fg);
}
</style>

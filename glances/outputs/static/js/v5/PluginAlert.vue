<template>
	<article class="gl-plugin" :aria-label="TITLE">
		<!-- Keep every comment INSIDE this root, like CollectionBlock.vue: one
		before <article> would make a second root node and drop the
		`data-plugin`/`aria-label` attributes AppShell passes down. -->
		<div v-if="error || !payload || !rows.length" class="gl-plugin-title">
			<h2 class="gl-header">{{ TITLE }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<!-- Warm-up is not an all-clear (an alert simply cannot have fired
		yet), so it stays neutral rather than claiming a healthy system --
		same rule and wording as the TUI's collapse
		(curses_renderer_v5.py:738-745, `is_initializing`). Checked BEFORE
		the empty-rows branch: with nothing ingested yet, `rows` is also
		empty, and initializing must win. -->
		<p v-else-if="isInitializing" class="gl-muted">(initializing)</p>
		<!-- OK-coloured, mirroring the TUI (curses_renderer_v5.py:745): this
		was `gl-muted` before, which understated a genuine all-clear as if it
		were merely neutral like "loading"/"(initializing)". -->
		<p v-else-if="!rows.length" class="gl-level-ok">(no alert detected)</p>
		<table v-else class="gl-table">
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
					<th class="gl-header">DURATION</th>
					<th class="gl-header">TARGET</th>
					<th class="gl-header">TOP PROCESSES</th>
					<th class="gl-header">LEVEL</th>
				</tr>
			</thead>
			<tbody>
				<!-- Payload order: incidents arrive already sorted ongoing-first,
				newest-first within each group (derive_incidents(), design §5.3) --
				this renderer never re-sorts, same rule as vms/containers. -->
				<tr v-for="(incident, i) in rows" :key="i">
					<td><span :class="glyphClass(incident)">{{ glyphOf(incident) }}</span></td>
					<td>{{ timeOf(incident) }}</td>
					<td>{{ incident.duration || "-" }}</td>
					<td>{{ targetOf(incident) }}</td>
					<td>{{ topOf(incident) }}</td>
					<td><span :class="levelClassOf(incident)">{{ levelTextOf(incident) }}</span></td>
				</tr>
			</tbody>
		</table>
	</article>
</template>

<script>
import { levelClass } from "./levels.js";

const TITLE = "ALERT";

// curses_renderer_v5.py `_ALERT_GENERIC_FIELDS`: a field whose whole name is
// in this set identifies nothing on its own -- the plugin (and its key)
// already say what the alert is about ("sensors[i915 0].value" reads better
// as "Sensors i915 0"). Closed list, grounded on the fields that can
// actually raise an alert -- do not widen it without redoing that check.
const GENERIC_FIELDS = new Set(["value", "percent"]);

export default {
	name: "PluginAlert",
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
		// Declared but unused: spec D5, this block has no width cascade --
		// like `vms`, it scrolls instead (see the scoped style below).
		degrade: { type: Object, default: () => ({}) },
	},
	computed: {
		TITLE: () => TITLE,
		rows() {
			return (this.payload && this.payload.incidents) || [];
		},
		isInitializing() {
			return !!(this.payload && this.payload.isInitializing);
		},
		// Mirrors `_build_alert_title_cells`'s populated text
		// (curses_renderer_v5.py:629-675), minus its own width shrink ladder --
		// the browser has the width, so it never needs to drop the `resolved`
		// clause. Counts are derived from `rows`, not a server field: the
		// incidents this block already has are the only source of truth.
		titleText() {
			const nOngoing = this.rows.filter((incident) => incident.ongoing).length;
			const nResolved = this.rows.length - nOngoing;
			return `ALERTS  ${nOngoing} ongoing · ${nResolved} resolved`;
		},
	},
	methods: {
		glyphOf(incident) {
			return incident.ongoing ? "●" : "○";
		},
		// The glyph keeps the level colour regardless of ongoing/resolved, so
		// the severity an incident reached always stays readable
		// (curses_renderer_v5.py:840-843). Divergence from the TUI: there the
		// glyph carries `prominent` only once LEVEL is width-dropped: the
		// browser never drops LEVEL (it scrolls instead), so `prominent`
		// belongs on LEVEL alone here -- see levelClassOf().
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
	},
};
</script>

<style scoped>
/* Spec divergence: the TUI width-gates DURATION, TOP PROCESSES and LEVEL
 * (curses_renderer_v5.py:771-798) -- LEVEL and DURATION on width alone, TOP
 * PROCESSES on width AND data (`show_top`, :777: a host whose only alerts
 * come from fs or sensors incidents, which carry no `top`, gets no TOP
 * PROCESSES column at all in the TUI). The browser has the width -- it
 * renders every column unconditionally, including an empty TOP PROCESSES
 * one on such a host, and like `vms` scrolls horizontally within the block
 * rather than cropping columns or letting the whole page scroll. */
.gl-plugin {
	overflow-x: auto;
}
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

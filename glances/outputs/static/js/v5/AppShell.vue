<template>
	<main class="gl-app">
		<!--
			Zones mirror the TUI's page: header line, top row, then the left and
			right columns. AppShell still never names a plugin -- the registry's
			`slot` decides where each one lands.
		-->
		<component :is="zone.tag" v-for="zone in zones" :key="zone.name" :class="['gl-zone', `gl-zone-${zone.name}`]">
			<!-- `slotName`, not `slot`: `slot` is a reserved attribute name in Vue templates. -->
			<template v-for="slotName in zone.slots" :key="slotName">
				<section v-if="slots[slotName]" :class="['gl-slot', `gl-slot-${slotName}`]" :data-slot="slotName">
					<component
						:is="plugin.component"
						v-for="plugin in slots[slotName]"
						:key="plugin.name"
						:data-plugin="plugin.name"
						:payload="results[plugin.name]"
						:error="errors[plugin.name]"
						:labels="labels[plugin.name] || {}"
						:server-args="serverArgs"
						:degrade="zone.name === 'header' ? degrade.header : degrade.top"
					/>
				</section>
			</template>
		</component>

		<footer class="gl-alerts">
			<span v-if="!alerts.length" class="gl-muted">No alert</span>
			<ul v-else>
				<!--
					The line keeps the tier text colour; only the level word carries
					the prominent badge, like the TUI's LEVEL cell. A badge on the
					whole <li> would paint a full-width coloured band.
				-->
				<li v-for="(alert, i) in alerts" :key="i" :class="levelClass({ level: alert.level })">
					{{ alertLabel(alert) }} — <span :class="levelClass(alert)">{{ alert.level }}</span>
				</li>
			</ul>
			<!-- G9-5 D5: moved here from the removed top bar. -->
			<span class="gl-muted gl-refresh">{{ refreshLabel }}</span>
		</footer>
	</main>
</template>

<script>
import { fetchAll, resolveConfig, resolveArgs, resolvePluginNames, getJson } from "./api.js";
import { levelClass } from "./levels.js";
import { resolveAllLabels } from "./labels.js";
import { visiblePlugins, groupBySlot } from "./layout.js";
import { PLUGINS } from "./plugins/index.js";
import { resolveDegrade, TOP_CASCADE, HEADER_CASCADE } from "./degrade.js";

// The page's zones, top to bottom, and the registry slots each one holds.
// `tag` is the element the zone renders as: the header zone stays a real
// <header>, which the render probe asserts.
const ZONES = [
	{ name: "header", tag: "header", slots: ["header-left", "header-right"] },
	{ name: "top", tag: "section", slots: ["top"] },
	{ name: "body", tag: "div", slots: ["left", "right"] },
];

// Which flag removes which block. The TUI does the same in
// _build_fitted_frame, by filtering frame.top -- a block that disappears is
// the shell's business; a block that merely shrinks is the component's
// (spec D7).
const HIDDEN_BY = {
	hide_cloud: "cloud",
	hide_now: "now",
	hide_ip: "ip",
	hide_uptime: "uptime",
	hide_memswap: "memswap",
	hide_gpu: "gpu",
};

// Both cascades resolve to a flat object of primitive values (booleans/
// numbers), never nested -- a plain key-by-key comparison is enough. Used by
// refit() to skip its final `degrade` assignment when nothing actually
// changed (spec section 6): `resolveDegrade` always returns a fresh object,
// so `===` on the two flag sets would never be true even when they agree.
function sameFlags(a, b) {
	const aKeys = Object.keys(a);
	const bKeys = Object.keys(b);
	return aKeys.length === bKeys.length && aKeys.every((key) => a[key] === b[key]);
}

export default {
	name: "AppShell",
	data() {
		return {
			results: {},
			errors: {},
			labels: {},
			serverArgs: {},
			// /api/5/pluginslist. null until read, and null if it cannot be read:
			// visiblePlugins() then renders the whole registry.
			pluginNames: null,
			alerts: [],
			refresh: null,
			timer: null,
			ticking: false,
			// The flags each zone resolved. {} = nothing degraded, which is also
			// what an environment without measurement keeps (spec section 9).
			degrade: { header: {}, top: {} },
			observers: [],
			// Same guard shape as `ticking`: refit() is triggered from three
			// independent async sources (mounted(), every tick(), every
			// ResizeObserver callback), and measureZone() mutates `degrade` (and
			// therefore the DOM) once per candidate notch -- a second call must
			// not interleave with one already mid-cascade (spec section 6).
			refitting: false,
		};
	},
	computed: {
		// NOT data(): Vue makes data()'s return value deeply reactive, so each
		// `plugin.component` would reach <component :is> as a Proxy of the
		// component options object -- which the dev build warns about
		// ("Vue received a Component that was made a reactive object") on
		// every vnode creation. A computed over the raw PLUGINS array returns
		// raw entries.
		plugins() {
			return visiblePlugins(PLUGINS, this.pluginNames);
		},
		slots() {
			const hidden = new Set(
				Object.entries({ ...this.degrade.header, ...this.degrade.top })
					.filter(([key, value]) => value && HIDDEN_BY[key])
					.map(([key]) => HIDDEN_BY[key]),
			);
			return groupBySlot(this.plugins.filter((plugin) => !hidden.has(plugin.name)));
		},
		// Always all three: design spec section 8 stacks header, top, body
		// unconditionally. A slot with no visible plugin renders no `<section>`
		// at all, via the `v-if="slots[slotName]"` below -- so a zone whose every
		// plugin is disabled server-side (e.g. every header plugin disabled)
		// shows as an empty separated band. Accepted as cosmetic: spec §6.4 only
		// requires empty slots to render nothing.
		zones() {
			return ZONES;
		},
		refreshLabel() {
			return this.refresh === null ? "…" : `refresh ${this.refresh}s`;
		},
	},
	async mounted() {
		const { refreshSeconds, theme } = await resolveConfig();
		this.refresh = refreshSeconds;
		// [outputs] theme, mapped straight to data-theme -- see the G9-2 design
		// spec, section 5. The static template hardcodes "dark" so the page
		// has a theme before this fetch resolves.
		document.documentElement.dataset.theme = theme;
		// The schema and the server's CLI arguments never change while the
		// server runs, so all three are resolved once here: three requests
		// whatever the number of plugins. The plugin list specifically is read
		// once per page load: a plugin enabled at runtime (#3548) only appears
		// after a reload -- see resolvePluginNames() in api.js.
		const [labels, serverArgs, pluginNames] = await Promise.all([
			resolveAllLabels(),
			resolveArgs(),
			resolvePluginNames(),
		]);
		this.labels = labels;
		this.serverArgs = serverArgs;
		this.pluginNames = pluginNames;
		await this.tick();
		await this.refit();
		if (typeof ResizeObserver === "function") {
			for (const slotName of ["header-left", "top"]) {
				const zone = this.$el?.querySelector?.(`[data-slot="${slotName}"]`);
				if (!zone) continue;
				const observer = new ResizeObserver(() => {
					// Not awaited: a rejection here would surface as an unhandled promise
					// rejection. The in-flight guard is cleared by refit()'s own `finally`,
					// so a failed pass simply retries on the next tick or resize.
					this.refit().catch(() => {});
				});
				observer.observe(zone);
				this.observers.push(observer);
			}
		}
		// The render probe drives the cascade through this hook: its fake DOM
		// has no ResizeObserver and no layout until the harness sets widths.
		// `this.degrade` is reassigned (not mutated) by refit(), so the hook
		// must republish it -- the ResizeObserver path above reads `degrade`
		// through Vue's reactivity instead and needs no such republish.
		if (typeof window !== "undefined") {
			window.__glancesRefit = async () => {
				await this.refit();
				window.__glancesDegrade = this.degrade;
			};
			window.__glancesDegrade = this.degrade;
		}
		this.timer = setInterval(() => this.tick(), this.refresh * 1000);
	},
	unmounted() {
		// The poll must stop with the component, or a hot reload leaves timers
		// stacking up against the API.
		if (this.timer) clearInterval(this.timer);
		for (const observer of this.observers) observer.disconnect();
	},
	methods: {
		levelClass,
		// `_build_event()` (glances/alerts_v5.py:706-716) is the only source of
		// this shape: {ts, plugin, key, field, level, previous_level, value,
		// prominent, is_initial, hostname}. There is no `description` field --
		// identify the alert from what actually exists: the plugin, the
		// collection item key when there is one, and the field. The level word
		// is rendered by the template on its own, so that it alone can carry
		// the prominent badge.
		alertLabel(alert) {
			const parts = [alert.plugin];
			if (alert.key) parts.push(alert.key);
			parts.push(alert.field);
			return parts.join(" ");
		},
		async tick() {
			// The interval fires unconditionally every `refresh` seconds
			// regardless of whether the previous tick's awaits have settled.
			// Without this guard, two overlapping ticks against a slow/loaded
			// server can resolve out of order and an older response clobbers
			// `results`/`errors`/`alerts` with stale data.
			if (this.ticking) return;
			this.ticking = true;
			try {
				// Visible plugins only: a disabled plugin is absent from /all by
				// construction, and asking for it would only produce a
				// permanent loading state nobody renders.
				const { results, errors } = await fetchAll(this.plugins);
				this.results = results;
				this.errors = errors;
				await this.refit();
				if (typeof window !== "undefined") window.__glancesDegrade = this.degrade;
				// The footer alert list is its own endpoint; its failure must not
				// disturb the plugins above it.
				try {
					const history = await getJson("api/5/alert");
					// get_history() (glances/alerts_v5.py:181) documents its return
					// as most-recent-LAST. `slice(0, 10)` would take the ten OLDEST
					// entries once history exceeds ten -- the footer would freeze on
					// stale alerts and never show a new one. Take the last ten, then
					// reverse so the newest alert reads first in the vertical list.
					this.alerts = Array.isArray(history) ? history.slice(-10).reverse() : [];
				} catch {
					this.alerts = [];
				}
			} finally {
				this.ticking = false;
			}
		},
		// Measure one zone, apply a candidate flag set, let Vue re-render, and
		// report what the browser says. `resolveDegrade` calls this once per
		// notch (spec section 6).
		async measureZone(slotName, zoneKey, flags) {
			if (!sameFlags(flags, this.degrade[zoneKey])) this.degrade = { ...this.degrade, [zoneKey]: flags };
			await this.$nextTick();
			const zone = this.$el?.querySelector?.(`[data-slot="${slotName}"]`);
			if (!zone) return { content: 0, available: 0 };
			// Harness hook: a real element ignores this expando property; the
			// render probe's FakeElement uses it to model scrollWidth shrinking
			// by one CONTENT_PER_NOTCH per flag in the candidate just applied.
			zone._notches = Object.keys(flags).length;
			return { content: zone.scrollWidth, available: zone.clientWidth };
		},
		// Re-run both cascades from scratch. Starting from no flag is what gives
		// the stats back when the window widens (spec section 6). Guarded like
		// `tick()`: refit() is triggered from mounted(), every tick(), and every
		// ResizeObserver callback, and measureZone() mutates `degrade` (and
		// therefore the DOM) once per candidate notch, so a second call must not
		// interleave with one already mid-cascade.
		async refit() {
			if (this.refitting) return;
			this.refitting = true;
			const previous = this.degrade;
			try {
				const header = await resolveDegrade(HEADER_CASCADE, (flags) =>
					this.measureZone("header-left", "header", flags),
				);
				const top = await resolveDegrade(TOP_CASCADE, (flags) => this.measureZone("top", "top", flags));
				// Only re-render the steady state when it actually differs from
				// what was in effect before this pass -- this is also what stops
				// an observer feedback loop (spec section 6).
				if (!sameFlags(header, previous.header) || !sameFlags(top, previous.top)) {
					this.degrade = { header, top };
				}
			} finally {
				this.refitting = false;
			}
		},
	},
};
</script>

<style scoped>
.gl-app {
	display: flex;
	flex-direction: column;
	gap: var(--gl-gap);
	padding: var(--gl-gap);
	/* At least the viewport, padding included, so the footer's margin-top:auto
	 * has room to push it to the bottom of a short page without adding a
	 * scrollbar. */
	min-height: 100vh;
	/* The small viewport where supported: on mobile, 100vh is measured with
	 * the browser toolbar hidden, so a short page would scroll by its height. */
	min-height: 100dvh;
	box-sizing: border-box;
}
/* Lightweight separators between zones, as the removed top bar had. */
.gl-zone {
	border-bottom: 1px solid var(--gl-border);
	padding-bottom: var(--gl-gap);
}
/* Header line. `3ch` is the TUI's _HEADER_GAP = 3 (glances_curses_v5.py): a
 * spacing, not a truncation, so the character unit is legitimate here. The
 * right group is pushed to the right edge, like _paint_header() does; when the
 * line wraps it stays right-aligned on its own row. */
/* The header never wraps: when it no longer fits, the cascade in this
 * component hides blocks in the TUI's order (degrade.js), then the blocks
 * crop, then this zone scrolls -- the browser's floor, where a terminal user
 * would have resized the window (spec D4). */
.gl-zone-header {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: 3ch;
	overflow-x: auto;
}
.gl-slot-header-left {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: 3ch;
	/* Lets the header's long strings shrink into their ellipsis. */
	min-width: 0;
}
.gl-slot-header-right {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: 3ch;
	min-width: 0;
	margin-left: auto;
}
/* Top row: first block flush left, last flush right, gaps distributed --
 * _paint_top_row()'s rule. Never wraps (spec goal 1): the cascade hides
 * blocks, then they crop, then this zone scrolls. */
.gl-slot-top {
	display: flex;
	flex-wrap: nowrap;
	justify-content: space-between;
	gap: calc(var(--gl-gap) * 2);
	flex: 1;
	overflow-x: auto;
}
.gl-zone-top {
	display: flex;
}
/* Left column sized by its content, right column takes the rest. */
.gl-zone-body {
	display: grid;
	grid-template-columns: max-content 1fr;
	gap: calc(var(--gl-gap) * 2);
}
.gl-slot-left,
.gl-slot-right {
	display: flex;
	flex-direction: column;
	gap: calc(var(--gl-gap) * 2);
	min-width: 0;
}
/* Pinned to the second column so it does not slide left when no plugin is in
 * the left slot. */
.gl-slot-right {
	grid-column: 2;
}
/* 48rem matches no TUI rule: it is the browser's own threshold (G9-5 D3),
 * kept in this single rule so it can be tuned. Below it the columns stack. */
@media (max-width: 48rem) {
	.gl-zone-body {
		grid-template-columns: 1fr;
	}
	.gl-slot-right {
		grid-column: auto;
	}
}
/* Footer at the bottom of the screen, always visible: pushed down on a short
 * page (margin-top: auto in the min-height column), stuck to the viewport's
 * bottom edge on a long one. Opaque background and a separator so scrolled
 * content passes under it rather than showing through. */
.gl-alerts {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: var(--gl-gap);
	margin-top: auto;
	position: sticky;
	bottom: 0;
	background: var(--gl-bg);
	border-top: 1px solid var(--gl-border);
	padding-block: var(--gl-gap);
}
.gl-alerts ul {
	margin: 0;
	padding-left: 1rem;
	/* A sticky footer taller than the viewport would slide off its TOP edge,
	 * and the list is newest-first, so the newest alerts would be the ones
	 * lost -- while the footer covered the page. Capped, the list scrolls
	 * inside the footer and its first (newest) line stays visible. */
	max-height: 40vh;
	overflow-y: auto;
}
</style>

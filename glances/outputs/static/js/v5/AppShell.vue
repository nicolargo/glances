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

// The page's zones, top to bottom, and the registry slots each one holds.
// `tag` is the element the zone renders as: the header zone stays a real
// <header>, which the render probe asserts.
const ZONES = [
	{ name: "header", tag: "header", slots: ["header-left", "header-right"] },
	{ name: "top", tag: "section", slots: ["top"] },
	{ name: "body", tag: "div", slots: ["left", "right"] },
];

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
			return groupBySlot(this.plugins);
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
		this.timer = setInterval(() => this.tick(), this.refresh * 1000);
	},
	unmounted() {
		// The poll must stop with the component, or a hot reload leaves timers
		// stacking up against the API.
		if (this.timer) clearInterval(this.timer);
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
.gl-zone-header {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	column-gap: 3ch;
}
.gl-slot-header-left,
.gl-slot-header-right {
	display: flex;
	flex-wrap: wrap;
	align-items: baseline;
	column-gap: 3ch;
	/* Lets the header's long strings shrink into their ellipsis. */
	min-width: 0;
}
.gl-slot-header-right {
	margin-left: auto;
}
/* Top row: first block flush left, last flush right, gaps distributed --
 * _paint_top_row()'s rule. */
.gl-slot-top {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: calc(var(--gl-gap) * 2);
	flex: 1;
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

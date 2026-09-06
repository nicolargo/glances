<template>
	<main class="gl-app">
		<header class="gl-topbar">
			<span class="gl-header">Glances</span>
			<span class="gl-muted">{{ refreshLabel }}</span>
		</header>

		<section class="gl-plugins">
			<component
				:is="plugin.component"
				v-for="plugin in plugins"
				:key="plugin.name"
				:payload="results[plugin.name]"
				:error="errors[plugin.name]"
				:labels="labels[plugin.name] || {}"
			/>
		</section>

		<footer class="gl-alerts">
			<span v-if="!alerts.length" class="gl-muted">No alert</span>
			<ul v-else>
				<li v-for="(alert, i) in alerts" :key="i" :class="levelClass(alert)">
					{{ alertLabel(alert) }}
				</li>
			</ul>
		</footer>
	</main>
</template>

<script>
import { fetchAll, resolveConfig, getJson } from "./api.js";
import { levelClass } from "./levels.js";
import { resolveLabels } from "./labels.js";
import { PLUGINS } from "./plugins/index.js";

export default {
	name: "AppShell",
	data() {
		return {
			results: {},
			errors: {},
			labels: {},
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
		// every vnode creation. A computed returns the raw array.
		plugins: () => PLUGINS,
		refreshLabel() {
			return this.refresh === null ? "…" : `refresh ${this.refresh}s`;
		},
	},
	async mounted() {
		const { refreshSeconds, theme } = await resolveConfig();
		this.refresh = refreshSeconds;
		// [outputs] theme, mapped straight to data-theme -- see the design
		// spec, section 5. The static template hardcodes "dark" so the page
		// has a theme before this fetch resolves.
		document.documentElement.dataset.theme = theme;
		// The schema never changes at runtime (see labels.js), so labels are
		// resolved once here rather than on every tick.
		const entries = await Promise.all(
			PLUGINS.map(async (p) => [p.name, await resolveLabels(p.name)]),
		);
		this.labels = Object.fromEntries(entries);
		await this.tick();
		this.timer = setInterval(() => this.tick(), this.refresh * 1000);
	},
	unmounted() {
		// The poll must stop with the component, or a hot reload during G9-3..N
		// leaves timers stacking up against the API.
		if (this.timer) clearInterval(this.timer);
	},
	methods: {
		levelClass,
		// `_build_event()` (glances/alerts_v5.py:706-716) is the only source of
		// this shape: {ts, plugin, key, field, level, previous_level, value,
		// prominent, is_initial, hostname}. There is no `description` field --
		// identify the alert from what actually exists: the plugin, the
		// collection item key when there is one, and the field.
		alertLabel(alert) {
			const parts = [alert.plugin];
			if (alert.key) parts.push(alert.key);
			parts.push(alert.field);
			return `${parts.join(" ")} — ${alert.level}`;
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
}
.gl-topbar {
	display: flex;
	justify-content: space-between;
	border-bottom: 1px solid var(--gl-border);
	padding-bottom: var(--gl-gap);
}
.gl-plugins {
	display: flex;
	flex-wrap: wrap;
	gap: calc(var(--gl-gap) * 2);
}
.gl-alerts ul {
	margin: 0;
	padding-left: 1rem;
}
</style>

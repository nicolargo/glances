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
			<!-- G9-5 D5: moved here from the removed top bar. The alert list that
			used to share this footer (raw history, newest-first) moved into
			PluginAlert.vue (G9-9B), fed by the collapsed /api/5/alert/incidents
			grid -- this footer keeps only the cadence. -->
			<span class="gl-muted gl-refresh">{{ refreshLabel }}</span>
		</footer>
	</main>
</template>

<script>
import { computed } from "vue";
import { fetchAll, resolveConfig, resolveArgs, resolvePluginNames, getJson } from "./api.js";
import { resolveAllLabels } from "./labels.js";
import { visiblePlugins, groupBySlot } from "./layout.js";
import { PLUGINS } from "./plugins/index.js";
import { resolveDegrade, TOP_CASCADE, HEADER_CASCADE } from "./degrade.js";
import { FULL_QUICKLOOK_HIDDEN } from "./full_quicklook.js";

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
	hide_quicklook: "quicklook",
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
	// `percpu` is the only component that needs the instantiated-plugin list
	// (it decides whether to render standalone or drop its title/total column
	// once quicklook is instantiated). A prop on the shared `<component>`
	// binding would fall through as a `server-plugins` DOM attribute on the
	// other 23 plugins, which never declare it -- provide/inject reaches the
	// one consumer without touching them (G9-8 Task 4 review). `computed()`
	// keeps this reactive: `pluginNames` is null until /api/5/pluginslist
	// resolves, and a plain `{ serverPlugins: this.pluginNames }` would
	// capture that null forever -- the computed getter re-reads
	// `this.pluginNames` on every access, so the injecting component sees the
	// resolved list once `mounted()` sets it.
	provide() {
		return {
			serverPlugins: computed(() => this.pluginNames || []),
			// `[outputs] max_processes_display` (resolveConfig(), api.js), for
			// PluginProcesslist.vue (and, next task, programlist): the same
			// reasoning as `serverPlugins` above applies verbatim -- a value read
			// by a small number of plugins, provided once here rather than each
			// one fetching `/api/5/config` itself (fix round 1, IMPORTANT 1: that
			// was a genuine second round-trip per page load to a
			// credentials-bearing endpoint, and it broke the "AppShell resolves
			// shared endpoints once" layering every other cross-cutting value
			// follows). `computed()` for the same reason as `pluginNames` above:
			// it re-reads `this.maxProcessesDisplay` on every access, so the
			// injecting component sees the resolved value once mounted() below
			// sets it, not the `null` it was created with.
			maxProcessesDisplay: computed(() => this.maxProcessesDisplay),
		};
	},
	data() {
		return {
			results: {},
			errors: {},
			labels: {},
			serverArgs: {},
			// /api/5/pluginslist. null until read, and null if it cannot be read:
			// visiblePlugins() then renders the whole registry.
			pluginNames: null,
			// `[outputs] max_processes_display`, resolved alongside refresh/theme
			// in mounted() below and handed down via provide() above. `null` means
			// "no cap", both before resolveConfig() resolves and when the key is
			// absent/unparsable.
			maxProcessesDisplay: null,
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
			// `--full-quicklook` gives the quicklook block the whole row: the TUI
			// hides the same six siblings (curses_renderer_v5.py:89
			// `_FULL_QUICKLOOK_HIDDEN`) and deliberately spares `load` and
			// `percpu`. Server state, not a viewport response, so it is unioned
			// with the cascade's own hidden set rather than being a cascade step.
			if (this.serverArgs.full_quicklook) {
				for (const name of FULL_QUICKLOOK_HIDDEN) hidden.add(name);
			}
			// `cpu` / `percpu` mutual exclusion (final review, Critical 1): the
			// v5 TUI shows exactly one of them -- glances_curses_v5.py:565-567
			// drops one from `frame.top` on EVERY frame:
			// `hidden_top = "cpu" if self._view.show_percpu else "percpu"`.
			// Without this the WebUI rendered both side by side, a duplicated
			// CPU surface. `show_percpu` is a TUI-only runtime toggle (hotkey
			// `1`) with no server-side representation, so the browser cannot
			// mirror it exactly (browser hotkeys are out of scope for this
			// group) -- the best available signal is `serverArgs.percpu`
			// (`--percpu`), which is also what gates quicklook's own per-core
			// view. This is NOT what the v4 WebUI does: its equivalent block is
			// commented out (glances/outputs/static/js/App.vue:43-52), so v4's
			// WebUI renders no `percpu` at all. The authority here is the v5 TUI.
			if (this.serverArgs.percpu) {
				hidden.add("cpu");
			} else {
				hidden.add("percpu");
			}
			// `processlist` / `programlist` mutual exclusion (task 8, same shape as
			// cpu/percpu above): the v5 TUI shows exactly one --
			// glances_curses_v5.py:578 `hidden_right = "processlist" if
			// self._view.programs else "programlist"`. `--programs` (Task 5) is
			// wired into both the TUI's own `_view.programs` (main_v5.assemble)
			// and `serverArgs.programs`, so the two agree -- unlike the TUI-only
			// `show_percpu` hotkey above, there is no browser/TUI gap to paper
			// over here.
			if (this.serverArgs.programs) {
				hidden.add("processlist");
			} else {
				hidden.add("programlist");
			}
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
		const { refreshSeconds, theme, maxProcessesDisplay } = await resolveConfig();
		this.refresh = refreshSeconds;
		// [outputs] theme, mapped straight to data-theme -- see the G9-2 design
		// spec, section 5. The static template hardcodes "dark" so the page
		// has a theme before this fetch resolves.
		document.documentElement.dataset.theme = theme;
		// Resolved from the SAME /api/5/config fetch as refresh/theme above --
		// no second round-trip. Provided to `processlist`/`programlist`
		// (provide() above) before the first tick(), so their very first paint
		// is already capped (fix round 1, IMPORTANT 1's third consequence: the
		// cap used to arrive after mount, one refresh tick too late).
		this.maxProcessesDisplay = maxProcessesDisplay;
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
		async tick() {
			// The interval fires unconditionally every `refresh` seconds
			// regardless of whether the previous tick's awaits have settled.
			// Without this guard, two overlapping ticks against a slow/loaded
			// server can resolve out of order and an older response clobbers
			// `results`/`errors` with stale data.
			if (this.ticking) return;
			this.ticking = true;
			try {
				// Visible plugins only: a disabled plugin is absent from /all by
				// construction, and asking for it would only produce a permanent
				// loading state nobody renders. `ownEndpoint` plugins (alert) are
				// excluded too -- they are never a key of the /api/5/all envelope
				// fetchAll() reads, so passing one through made fetchAll() write
				// results[name] = null (its "absent from /all" branch) on EVERY
				// tick, and errors[name] on every /all failure (api.js:134-138 sets
				// an error for EVERY requested spec) -- an unrelated /all outage
				// blanking a block fed by its own healthy endpoint, exactly the
				// coupling the brief forbade, just in the direction nobody thought
				// to look (fix round 1, IMPORTANT 1).
				const ownEndpointPlugins = this.plugins.filter((plugin) => plugin.ownEndpoint);
				const { results, errors } = await fetchAll(this.plugins.filter((plugin) => !plugin.ownEndpoint));
				// fetchAll() only ever returns entries for what it was asked for, so
				// the reassignment below would otherwise blank every ownEndpoint
				// slot for the length of the refit() await (the same "flashes back
				// to loading on every tick" bug excluding them from fetchAll() was
				// meant to remove) -- carry each one over from the previous tick,
				// generalised over the registry's `ownEndpoint` entries rather than
				// hardcoded to `alert` (fix round 2). A `{...this.results, ...results}`
				// spread over the WHOLE object looks simpler and was proposed in
				// review, but is wrong: spread only ADDS/overwrites keys, it can
				// never delete one merely absent from the newer object, so a
				// fetchAll()-covered plugin whose error clears next tick (present in
				// the new `results`, absent from the new `errors`) would keep
				// showing its stale error FOREVER under a blind spread -- a real
				// regression for every ordinary plugin's recovery path, not just
				// alert's. (A stale PAYLOAD under the same spread is harmless: every
				// component checks `error` before `payload`, so it never reaches the
				// DOM -- verified across every Plugin*.vue template and
				// CollectionBlock.vue -- but the error side is not harmless, hence
				// this loop instead of the spread.) Every fetchAll()-covered plugin
				// therefore still goes through fetchAll()'s fresh, complete
				// `results`/`errors` via a plain reassignment below; only the
				// own-endpoint slots are hand-carried here.
				for (const plugin of ownEndpointPlugins) {
					results[plugin.name] = this.results[plugin.name];
					errors[plugin.name] = this.errors[plugin.name];
				}
				this.results = results;
				this.errors = errors;
				await this.refit();
				if (typeof window !== "undefined") window.__glancesDegrade = this.degrade;
				// PluginAlert.vue's data comes from its own endpoint -- the already
				// collapsed incident grid, not a raw plugin stat block -- so it
				// cannot go through fetchAll()'s /api/5/all envelope. Kept in its
				// own try/catch, like the block it replaced: a failing alert
				// endpoint must not disturb the plugins fetchAll() just resolved.
				try {
					// Envelope, not a bare array (fix round 2, IMPORTANT 2):
					// `is_initializing` lets PluginAlert.vue tell "warm-up" from
					// "no alert detected" apart, the same distinction
					// `render_alert_block` makes (curses_renderer_v5.py:738-745).
					const envelope = await getJson("api/5/alert/incidents");
					const incidents = Array.isArray(envelope && envelope.incidents) ? envelope.incidents : [];
					const isInitializing = !!(envelope && envelope.is_initializing);
					// Clear a stale error from a previous failed round-trip now that
					// this one succeeded -- carried-over `errors.alert` above would
					// otherwise linger forever once the endpoint recovers.
					const nextErrors = { ...this.errors };
					delete nextErrors.alert;
					this.errors = nextErrors;
					this.results = { ...this.results, alert: { isInitializing, incidents } };
				} catch (e) {
					this.errors = { ...this.errors, alert: e.message };
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
			// Measure the text at its natural width (css/v5.css `.gl-measuring`):
			// shrunk into its ellipsis it never overflows, and the cascade would
			// never run. Added, read and removed synchronously -- never painted.
			zone.classList.add("gl-measuring");
			const reading = { content: zone.scrollWidth, available: zone.clientWidth };
			zone.classList.remove("gl-measuring");
			return reading;
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
/* Header line. The gap is the TUI's _HEADER_GAP = 3 (glances_curses_v5.py),
 * so it is three CHARACTERS and uses --gl-col, not `ch`: `ch` resolves to
 * 0.5em under the shipped font stack (see the token file), which made this
 * gap 2.5 characters wide. The
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
	column-gap: calc(3 * var(--gl-col));
	overflow-x: auto;
}
.gl-slot-header-left {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: calc(3 * var(--gl-col));
	/* Lets the header's long strings shrink into their ellipsis. */
	min-width: 0;
}
.gl-slot-header-right {
	display: flex;
	flex-wrap: nowrap;
	align-items: baseline;
	column-gap: calc(3 * var(--gl-col));
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
	/* G9-9B: the alert list that used to share this footer moved into
	 * PluginAlert.vue -- the cadence is the footer's only child now, so
	 * `space-between` (which needs two) would leave it flush left instead of
	 * at the right edge it always occupied. */
	justify-content: flex-end;
	align-items: flex-start;
	gap: var(--gl-gap);
	margin-top: auto;
	position: sticky;
	bottom: 0;
	background: var(--gl-bg);
	border-top: 1px solid var(--gl-border);
	padding-block: var(--gl-gap);
}
</style>

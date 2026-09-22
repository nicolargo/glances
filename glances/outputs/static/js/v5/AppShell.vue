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
						:server-args="effectiveArgs"
						:degrade="zone.name === 'header' ? degrade.header : degrade.top"
					/>
				</section>
			</template>
		</component>

		<footer class="gl-alerts">
			<!-- spec D5: moved here from the removed top bar. The alert list that
			used to share this footer (raw history, newest-first) moved into
			PluginAlert.vue, fed by the collapsed /api/5/alert/incidents
			grid -- this footer carries the server's identity on the left and the
			cadence on the right. The class name is the one the vertical budget
			and the render probe already look for; it outlived the alerts. -->
			<div class="gl-muted gl-about">
				<span>{{ versionLabel }}</span>
				<span class="gl-about-sep" aria-hidden="true">·</span>
				<!-- A <button>, styled as a link: it acts on this page rather than
				navigating, so an <a> would lie to assistive tech and offer a
				middle-click that goes nowhere. `aria-expanded` names the overlay's
				state, which is the part a sighted user reads off the screen. -->
				<button
					type="button"
					class="gl-about-action"
					:aria-expanded="showHelp ? 'true' : 'false'"
					@click="toggleHelp"
				>
					Hotkeys
				</button>
				<span class="gl-about-sep" aria-hidden="true">·</span>
				<a href="https://github.com/nicolargo/glances" target="_blank" rel="noopener noreferrer">GitHub</a>
				<!-- /docs only when [outputs] api_doc is on: that same key decides
				whether FastAPI mounts Swagger UI at all (webserver_v5.build_app),
				so linking it unconditionally would offer a 404. Absolute, not
				relative: the v5 server has no url_prefix and mounts /docs at the
				root, next to the page itself. -->
				<template v-if="apiDoc">
					<span class="gl-about-sep" aria-hidden="true">·</span>
					<a href="/docs" target="_blank" rel="noopener noreferrer">API</a>
				</template>
			</div>
			<div class="gl-muted gl-refresh">
				<span>Refresh:</span>
				<button
					type="button"
					class="gl-step"
					:disabled="!canSpeedUp"
					aria-label="Refresh faster"
					@click="changeRefresh(-1)"
				>
					−
				</button>
				<span class="gl-refresh-value">{{ refreshLabel }}</span>
				<button
					type="button"
					class="gl-step"
					:disabled="!canSlowDown"
					aria-label="Refresh slower"
					@click="changeRefresh(1)"
				>
					+
				</button>
			</div>
		</footer>

		<!-- `h`, mirroring the TUI's overlay. Rows come from hotkeys.js, the same
		table the dispatcher reads, so a bound key cannot go undocumented. -->
		<div
			v-if="showHelp"
			class="gl-help"
			role="dialog"
			aria-modal="true"
			aria-label="Keyboard shortcuts"
			@click="showHelp = false"
		>
			<div class="gl-help-panel" @click.stop>
				<div class="gl-help-title">
					<span>Keyboard shortcuts</span>
					<button type="button" class="gl-step" aria-label="Close" @click="showHelp = false">×</button>
				</div>
				<ul class="gl-help-list">
					<li v-for="row in helpKeys" :key="row.key" :data-group="row.group">
						<kbd>{{ row.key }}</kbd>
						<span>{{ row.desc }}</span>
					</li>
					<li data-group="MISCELLANEOUS">
						<kbd>h</kbd>
						<span>Show / hide this help</span>
					</li>
				</ul>
			</div>
		</div>
	</main>
</template>

<script>
import { computed, markRaw } from "vue";
import { fetchAll, resolveConfig, resolveArgs, resolvePluginNames, resolveVersion, getJson } from "./api.js";
import { REFRESH_STEPS, stepRefresh, loadRefresh, saveRefresh } from "./refresh.js";
import { resolveAllLabels } from "./labels.js";
import { visiblePlugins, groupBySlot } from "./layout.js";
import { PLUGINS } from "./plugins/index.js";
import { resolveDegrade, sameFlags, TOP_CASCADE, HEADER_CASCADE } from "./degrade.js";
import { FULL_QUICKLOOK_HIDDEN } from "./full_quicklook.js";
import { hideTargets, toggleHidden, helpRows, viewFlag, HELP_KEY } from "./hotkeys.js";
import { planRightColumn } from "./row_budget.js";
import { ampsLineCount } from "./amps.js";

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

// The browser's own stacking threshold, not a TUI rule (spec D3). Kept next to
// the media query that owns it -- test_webui_v5_tokens.py pins the two
// together so the constant cannot drift from the stylesheet.
const STACK_BREAKPOINT = "48rem";

// Every poll payload is REPLACED, never mutated in place: fetchAll() parses a
// fresh /api/5/all envelope each tick and the components only ever read it.
// Deep reactivity therefore buys nothing and costs a lot -- Vue would wrap
// every process, container and sensor object of every tick in its own Proxy,
// and route each cell's property read through a trap plus a dependency
// record. On a host with a few hundred processes that is thousands of proxy
// allocations per refresh, for values that are thrown away whole at the next
// one.
//
// markRaw() opts the CONTAINER out of that conversion, so `this.results` and
// everything under it stay plain objects. Reactivity is preserved exactly
// where it is needed: the `results`/`errors` data keys themselves still track
// their reassignment, so a tick still re-renders, and each plugin still sees
// a new `payload` prop identity.
//
// The flag markRaw() sets is non-enumerable, so it does NOT survive a spread:
// every freshly built container below has to be marked again.

export default {
	name: "AppShell",
	// `percpu` is the only component that needs the instantiated-plugin list
	// (it decides whether to render standalone or drop its title/total column
	// once quicklook is instantiated). A prop on the shared `<component>`
	// binding would fall through as a `server-plugins` DOM attribute on the
	// other 23 plugins, which never declare it -- provide/inject reaches the
	// one consumer without touching them. `computed()`
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
			// one fetching `/api/5/config` itself (: that
			// was a genuine second round-trip per page load to a
			// credentials-bearing endpoint, and it broke the "AppShell resolves
			// shared endpoints once" layering every other cross-cutting value
			// follows). `computed()` for the same reason as `pluginNames` above:
			// it re-reads `this.maxProcessesDisplay` on every access, so the
			// injecting component sees the resolved value once mounted() below
			// sets it, not the `null` it was created with.
			maxProcessesDisplay: computed(() => this.maxProcessesDisplay),
			// The vertical row budget (row_budget.js): six consumers out
			// of thirty-two (vms, containers, processlist, programlist, alert,
			// amps), the same "small number of plugins" case `maxProcessesDisplay`
			// above describes -- a prop on the shared `<component>` binding would
			// fall through as a `row-budget` DOM attribute on the other
			// twenty-six, which never declare it -- the same reasoning as
			// `serverPlugins` above. `computed()`
			// for the same reason as the two entries above: `refitVertical()`
			// reassigns `this.rowBudget` on every vertical pass, and a plain
			// `{ rowBudget: this.rowBudget }` would capture whatever it was at
			// provide()-time forever.
			rowBudget: computed(() => this.rowBudget),
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
			// The release the server runs, read once from /status. null until
			// read, and null if it cannot be read -- the footer then names no
			// version rather than an error.
			version: null,
			// `[outputs] api_doc`: whether the server mounts /docs at all.
			// Starts true, as the config default does.
			apiDoc: true,
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
			// The row quota each elastic right-column block may use. {} = no
			// budget, which is what an environment without measurement keeps --
			// degrade.js's rule on the vertical axis (design 4.8).
			rowBudget: {},
			// Same guard shape as `refitting`: the vertical pass mutates
			// rowBudget and therefore the DOM.
			refittingVertical: false,
			// A refit coalesced into the next animation frame (scheduleRefit).
			refitFrame: null,
			// Listeners this component owns and must remove on unmount.
			visibilityHandler: null,
			keydownHandler: null,
			// The plugins the viewer hid with the SHOW/HIDE keys. A plain Array
			// rather than a Set: Vue 3 does proxy Sets, but every read here goes
			// through `slots()`, which builds a Set anyway -- and an Array keeps
			// the render probe's JSON round-trip trivial.
			//
			// Deliberately NOT persisted. The TUI's `ViewState.hidden_plugins`
			// is not either, and `--disable-plugin` / `[<p>] disable` remain the
			// way to make a choice stick.
			userHidden: [],
			// The `h` overlay listing the keys, mirroring the TUI's.
			showHelp: false,
			// TOGGLE VIEW keys (`1`, `j`, `4`, `/`). Each entry is absent while
			// the viewer has not pressed its key, and the SERVER's value
			// (`serverArgs`) is what applies; pressing the key writes a boolean
			// here, which then wins.
			//
			// An override rather than a copy of `serverArgs` seeded at mount:
			// `/api/5/args` is re-read on every tick, so a copy would be
			// silently overwritten by the next poll, and a viewer who has NOT
			// pressed the key must keep following the server if it changes.
			viewOverrides: {},
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
			if (this.effectiveArgs.full_quicklook) {
				for (const name of FULL_QUICKLOOK_HIDDEN) hidden.add(name);
			}
			// `cpu` / `percpu` mutual exclusion : the
			// v5 TUI shows exactly one of them -- glances_curses_v5.py:565-567
			// drops one from `frame.top` on EVERY frame:
			// `hidden_top = "cpu" if self._view.show_percpu else "percpu"`.
			// Without this the WebUI rendered both side by side, a duplicated
			// CPU surface. `show_percpu` is a TUI-only runtime toggle (hotkey
			// `1`) with no server-side representation, so the browser cannot
			// mirror it exactly -- the best available signal is
			// `serverArgs.percpu` (`--percpu`), which is also what gates
			// quicklook's own per-core view. The browser DOES read keys now
			// (hotkeys.js), but only the SHOW/HIDE family; `1` and the rest of
			// the TOGGLE VIEW group would each have to settle this same
			// server-state-versus-local-override question first, so they are
			// deliberately still unbound here. This is NOT what the v4 WebUI does: its equivalent block is
			// commented out (glances/outputs/static/js/App.vue:43-52), so v4's
			// WebUI renders no `percpu` at all. The authority here is the v5 TUI.
			if (this.effectiveArgs.percpu) {
				hidden.add("cpu");
			} else {
				hidden.add("percpu");
			}
			// `processlist` / `programlist` mutual exclusion (same shape as
			// cpu/percpu above): the v5 TUI shows exactly one --
			// glances_curses_v5.py:578 `hidden_right = "processlist" if
			// self._view.programs else "programlist"`. `--programs` is
			// wired into both the TUI's own `_view.programs` (main_v5.assemble)
			// and `serverArgs.programs`, so the two agree -- unlike the TUI-only
			// `show_percpu` hotkey above, there is no browser/TUI gap to paper
			// over here.
			if (this.effectiveArgs.programs) {
				hidden.add("processlist");
			} else {
				hidden.add("programlist");
			}
			// The viewer's own SHOW/HIDE keys, unioned in last. Same rule as the
			// TUI (`build_frame`, curses_renderer_v5.py): a block is hidden when
			// EITHER authority says so, and this one cannot conjure width the
			// degradation cascade above has already taken away.
			for (const name of this.userHidden) hidden.add(name);
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
		helpKeys() {
			return helpRows();
		},
		// What the server reported, with this viewer's TOGGLE VIEW keys applied
		// on top. This -- not the raw `serverArgs` -- is what goes down to the
		// plugins as `server-args`, so `1`, `4` and `/` reach their consumers
		// (PluginPercpu, PluginQuicklook, the two process blocks) with no
		// change to any of them. The prop keeps its name because renaming it
		// would touch all 32 components for no behavioural gain; its meaning is
		// "the effective view flags", and it is documented as such here.
		//
		// `process_short_name` has no server default (no CLI option sets it),
		// so it is seeded true, matching `ViewState.process_short_name`.
		effectiveArgs() {
			return { process_short_name: true, ...this.serverArgs, ...this.viewOverrides };
		},
		refreshLabel() {
			return this.refresh === null ? "…" : `${this.refresh}s`;
		},
		versionLabel() {
			return this.version === null ? "Glances" : `Glances v${this.version}`;
		},
		// Both false while `refresh` is still null (before /api/5/config
		// resolves): there is no cadence to step yet.
		canSpeedUp() {
			return this.refresh !== null && this.refresh > REFRESH_STEPS[0];
		},
		canSlowDown() {
			return this.refresh !== null && this.refresh < REFRESH_STEPS[REFRESH_STEPS.length - 1];
		},
	},
	async mounted() {
		const { refreshSeconds, theme, maxProcessesDisplay, apiDoc } = await resolveConfig();
		// A cadence the viewer picked with the footer's -/+ buttons wins over
		// `[global] refresh`, which stays the value a first visit starts at.
		this.refresh = loadRefresh() ?? refreshSeconds;
		this.apiDoc = apiDoc;
		// [outputs] theme, mapped straight to data-theme -- see the design
		// spec, section 5. The static template hardcodes "dark" so the page
		// has a theme before this fetch resolves.
		document.documentElement.dataset.theme = theme;
		// Resolved from the SAME /api/5/config fetch as refresh/theme above --
		// no second round-trip. Provided to `processlist`/`programlist`
		// (provide() above) before the first tick(), so their very first paint
		// is already capped: the cap used to arrive after mount, one refresh
		// tick too late.
		this.maxProcessesDisplay = maxProcessesDisplay;
		// The schema and the server's CLI arguments never change while the
		// server runs, so all three are resolved once here: three requests
		// whatever the number of plugins. The plugin list specifically is read
		// once per page load: a plugin enabled at runtime (#3548) only appears
		// after a reload -- see resolvePluginNames() in api.js.
		const [labels, serverArgs, pluginNames, version] = await Promise.all([
			resolveAllLabels(),
			resolveArgs(),
			resolvePluginNames(),
			resolveVersion(),
		]);
		// markRaw for the same reason as the poll payloads -- see the note above
		// the component. The schema map is the larger of the two: one entry per
		// field of every plugin, read once per cell per render.
		this.labels = markRaw(labels);
		this.serverArgs = markRaw(serverArgs);
		this.pluginNames = pluginNames;
		this.version = version;
		await this.tick();
		await this.refit();
		await this.refitVertical();
		if (typeof ResizeObserver === "function") {
			for (const slotName of ["header-left", "top", "right"]) {
				const zone = this.$el?.querySelector?.(`[data-slot="${slotName}"]`);
				if (!zone) continue;
				// scheduleRefit(), never refit() directly: dragging a window edge
				// fires these observers on every frame, and a full pass costs one
				// forced layout per cascade notch.
				const observer = new ResizeObserver(() => this.scheduleRefit());
				observer.observe(zone);
				this.observers.push(observer);
			}
		}
		// A hidden tab paints nothing, so polling it only burns the viewer's CPU
		// and the server's. Stop while it is in the background (tick() returns
		// early) and catch up in one immediate poll when it comes back, so the
		// page is never shown holding data from minutes ago.
		if (typeof document !== "undefined" && typeof document.addEventListener === "function") {
			this.visibilityHandler = () => {
				if (!document.hidden) this.tick();
			};
			document.addEventListener("visibilitychange", this.visibilityHandler);
			// SHOW/HIDE keys, the TUI's own (hotkeys.js mirrors its table).
			// On `document`, not on the root element: the page has focusable
			// controls (the refresh steppers), and a listener on the component
			// would stop working the moment one of them took focus.
			this.keydownHandler = (event) => {
				if (!this.ownsKeystroke(event)) return;
				// Escape closes the overlay and nothing else -- what every modal
				// owes its user, and what the TUI does too (ESC closes the help
				// screen instead of quitting while it is open,
				// `glances_curses_v5._handle_help_key`). Handled here rather than
				// in `handleHotkey` because it is a dismissal, not a toggle:
				// Escape on a closed overlay must do nothing.
				if (event.key === "Escape") {
					if (this.showHelp) {
						this.showHelp = false;
						event.preventDefault();
					}
					return;
				}
				if (this.handleHotkey(event.key)) event.preventDefault();
			};
			document.addEventListener("keydown", this.keydownHandler);
		}
		// The render probe drives the cascade through this hook: its fake DOM
		// has no ResizeObserver and no layout until the harness sets widths.
		// `this.degrade` is reassigned (not mutated) by refit(), so the hook
		// must republish it -- the ResizeObserver path above reads `degrade`
		// through Vue's reactivity instead and needs no such republish.
		if (typeof window !== "undefined") {
			window.__glancesRefit = async () => {
				await this.refit();
				await this.refitVertical();
				window.__glancesDegrade = this.degrade;
				window.__glancesRowBudget = this.rowBudget;
			};
			window.__glancesDegrade = this.degrade;
			window.__glancesRowBudget = this.rowBudget;
			// Same shape as `__glancesRefit` above: the render probe has no
			// timer (`setInterval` is stubbed to a no-op below) and no other way
			// to fire a SECOND poll cycle, which is what the tick-ordering test
			// needs -- `tick()` itself calls refit()/refitVertical() internally,
			// so this hook only needs to republish afterwards.
			window.__glancesTick = async () => {
				await this.tick();
				window.__glancesDegrade = this.degrade;
				window.__glancesRowBudget = this.rowBudget;
			};
			// Same shape again: the probe's fake document has a no-op
			// addEventListener, so it cannot dispatch a real keydown. It drives
			// the behaviour through the method the listener itself calls.
			// The footer's Hotkeys button: the probe has no event dispatch, so it
			// drives the method the button's @click is bound to.
			window.__glancesToggleHelp = async () => {
				this.toggleHelp();
				await this.$nextTick();
				window.__glancesShowHelp = this.showHelp;
			};
			window.__glancesHotkey = async (key) => {
				this.handleHotkey(key);
				await this.$nextTick();
				window.__glancesUserHidden = [...this.userHidden];
				window.__glancesShowHelp = this.showHelp;
				window.__glancesEffectiveArgs = { ...this.effectiveArgs };
			};
		}
		this.startTimer();
	},
	unmounted() {
		// Everything this component attached outside itself has to come back
		// with it: a hot reload otherwise leaves timers stacking up against the
		// API, and the `window.__glances*` hooks below hold a closure over a
		// dead instance, keeping its whole payload graph alive.
		if (this.timer) clearInterval(this.timer);
		for (const observer of this.observers) observer.disconnect();
		if (this.refitFrame !== null && typeof cancelAnimationFrame === "function") {
			cancelAnimationFrame(this.refitFrame);
		}
		if (this.visibilityHandler && typeof document !== "undefined") {
			document.removeEventListener("visibilitychange", this.visibilityHandler);
		}
		if (this.keydownHandler && typeof document !== "undefined") {
			document.removeEventListener("keydown", this.keydownHandler);
		}
		if (typeof window !== "undefined") {
			delete window.__glancesRefit;
			delete window.__glancesTick;
			delete window.__glancesHotkey;
			delete window.__glancesUserHidden;
			delete window.__glancesShowHelp;
			delete window.__glancesToggleHelp;
			delete window.__glancesEffectiveArgs;
			delete window.__glancesDegrade;
			delete window.__glancesRowBudget;
		}
	},
	methods: {
		/**
		 * Act on one SHOW/HIDE key. Returns true when the key was handled, so
		 * the DOM listener knows whether to swallow it.
		 *
		 * Split from the listener because it is the whole behaviour: the
		 * listener only decides whether a keystroke is ours to read, and the
		 * render probe drives this directly (the probe's fake document has a
		 * no-op addEventListener and cannot dispatch events).
		 */
		// The overlay's one switch: the `h` key and the footer's Hotkeys button
		// both come through here, so the two can never drift apart.
		toggleHelp() {
			this.showHelp = !this.showHelp;
		},
		handleHotkey(key) {
			if (key === HELP_KEY) {
				this.toggleHelp();
				return true;
			}
			const flag = viewFlag(key);
			if (flag) {
				// Flip the EFFECTIVE value, so the first press always visibly
				// changes something: starting from the server's own value rather
				// than from `false` is what makes `4` turn full-quicklook OFF on
				// a server started with `--full-quicklook`.
				this.viewOverrides = { ...this.viewOverrides, [flag]: !this.effectiveArgs[flag] };
				this.scheduleRefit();
				return true;
			}
			const names = hideTargets(key, this.plugins);
			if (!names) return false;
			this.userHidden = [...toggleHidden(new Set(this.userHidden), names)];
			// The zones' ResizeObserver fires on its own when the layout moves,
			// but a toggle that leaves every zone the same size (a right-column
			// block among several) would otherwise keep a stale row budget.
			this.scheduleRefit();
			return true;
		},
		/**
		 * Whether a keystroke is ours to read.
		 *
		 * Ignores anything carrying a modifier, so the browser's own shortcuts
		 * (Ctrl-R, Cmd-L, Alt-Left...) keep working, and anything typed into a
		 * field, so a future filter box does not toggle plugins as it is typed.
		 * `isContentEditable` covers the editable-div case a tag check misses.
		 */
		ownsKeystroke(event) {
			if (event.ctrlKey || event.altKey || event.metaKey) return false;
			const target = event.target;
			if (!target) return true;
			if (target.isContentEditable) return false;
			const tag = typeof target.tagName === "string" ? target.tagName.toLowerCase() : "";
			return !["input", "textarea", "select"].includes(tag);
		},
		startTimer() {
			// Always replaces the running interval: changeRefresh() calls this to
			// re-arm at the new cadence, and a second interval left behind would
			// double the request rate for the life of the page.
			if (this.timer) clearInterval(this.timer);
			this.timer = setInterval(() => this.tick(), this.refresh * 1000);
		},
		changeRefresh(direction) {
			const next = stepRefresh(this.refresh, direction);
			// Already at either end of the ladder: the button is disabled, but a
			// keyboard repeat can still fire the handler.
			if (next === this.refresh) return;
			this.refresh = next;
			saveRefresh(next);
			this.startTimer();
		},
		async tick() {
			// The interval fires unconditionally every `refresh` seconds
			// regardless of whether the previous tick's awaits have settled.
			// Without this guard, two overlapping ticks against a slow/loaded
			// server can resolve out of order and an older response clobbers
			// `results`/`errors` with stale data.
			if (this.ticking) return;
			// A background tab renders nothing: polling it costs the viewer CPU
			// and the server a request per tab per cadence, for a frame nobody
			// sees. The visibilitychange listener in mounted() fires one catch-up
			// tick the moment the tab is shown again.
			if (typeof document !== "undefined" && document.hidden === true) return;
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
				// to look.
				const ownEndpointPlugins = this.plugins.filter((plugin) => plugin.ownEndpoint);
				const { results, errors } = await fetchAll(this.plugins.filter((plugin) => !plugin.ownEndpoint));
				// fetchAll() only ever returns entries for what it was asked for, so
				// the reassignment below would otherwise blank every ownEndpoint
				// slot for the length of the refit() await (the same "flashes back
				// to loading on every tick" bug excluding them from fetchAll() was
				// meant to remove) -- carry each one over from the previous tick,
				// generalised over the registry's `ownEndpoint` entries rather than
				// hardcoded to `alert`. A `{...this.results, ...results}`
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
				this.results = markRaw(results);
				this.errors = markRaw(errors);
				await this.refit();
				if (typeof window !== "undefined") window.__glancesDegrade = this.degrade;
				// PluginAlert.vue's data comes from its own endpoint -- the already
				// collapsed incident grid, not a raw plugin stat block -- so it
				// cannot go through fetchAll()'s /api/5/all envelope. Kept in its
				// own try/catch, like the block it replaced: a failing alert
				// endpoint must not disturb the plugins fetchAll() just resolved.
				try {
					// Envelope, not a bare array :
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
					this.errors = markRaw(nextErrors);
					this.results = markRaw({ ...this.results, alert: { isInitializing, incidents } });
				} catch (e) {
					this.errors = markRaw({ ...this.errors, alert: e.message });
				}
				// Runs AFTER the alert fetch above, not right after refit(): it
				// reads `this.results.alert` for `nAlerts`/`nOngoing` (`floorAlerts`),
				// and those feed the same shared row pool `vms`/`containers`/
				// `processlist`/`programlist` draw from -- reading it before the
				// fetch above resolves would budget every periodic tick against the
				// PREVIOUS cycle's alert state, forever, not just at startup.
				// `refit()` stays where it is: the horizontal
				// cascades operate on the header/top zones and never read alert
				// state.
				await this.refitVertical();
			} finally {
				this.ticking = false;
			}
		},
		// Coalesce refit requests into one animation frame. A ResizeObserver
		// fires on every frame of a window drag, and one pass costs a forced
		// layout per cascade notch -- running them all would make resizing the
		// window the most expensive thing this page ever does.
		//
		// Re-scheduling (rather than dropping) a request that arrives while a
		// pass is in flight is what keeps the LAST size of a drag fitted: the
		// in-flight guards in refit()/refitVertical() make such a call a no-op,
		// and nothing else would come back for it before the next tick.
		scheduleRefit() {
			if (this.refitFrame !== null) return;
			// No requestAnimationFrame means no layout engine either (the render
			// probe), so there is nothing to coalesce and no frame to come back
			// on: run it as the observer callback used to.
			if (typeof requestAnimationFrame !== "function") {
				this.refitNow();
				return;
			}
			this.refitFrame = requestAnimationFrame(() => {
				this.refitFrame = null;
				if (this.refitting || this.refittingVertical) {
					this.scheduleRefit();
					return;
				}
				this.refitNow();
			});
		},
		// Both axes, in the TUI's order. Not awaited by its callers: a rejection
		// would surface as an unhandled promise rejection, and the in-flight
		// guards are cleared by each pass's own `finally`, so a failed pass
		// simply retries on the next tick or resize.
		refitNow() {
			this.refit()
				.then(() => this.refitVertical())
				.catch(() => {});
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
		// Rows available below the right slot's top edge.
		//
		// Derived from the VIEWPORT, never from the slot's own height: the
		// slot's height is this pass's own output, so reading it would close a
		// feedback loop immediately. This is fit_block.js's documented
		// horizontal reasoning -- the right slot is the body grid's `1fr`
		// track, so its width never comes from its content -- transposed to the
		// vertical axis, where it is not free and has to be engineered
		// (design 4.4).
		//
		// `null` means "cannot measure", and the caller must then budget
		// nothing.
		measureBodyRows() {
			if (typeof window === "undefined") return null;
			const slot = this.$el?.querySelector?.('[data-slot="right"]');
			if (!slot || typeof slot.getBoundingClientRect !== "function") return null;
			const viewport = window.innerHeight || 0;
			// Harness hook, like `_notches`: a real element ignores this
			// expando and the computed line-height answers instead.
			const rowPx = slot._rowPx || this.computedRowPx(slot);
			if (!(viewport > 0) || !(rowPx > 0)) return null;
			const footer = this.$el?.querySelector?.(".gl-alerts");
			const footerHeight = footer?.getBoundingClientRect ? footer.getBoundingClientRect().height : 0;
			const top = slot.getBoundingClientRect().top;
			const rows = Math.floor((viewport - top - footerHeight) / rowPx);
			return rows > 0 ? rows : null;
		},
		computedRowPx(element) {
			if (typeof window.getComputedStyle !== "function") return 0;
			const value = parseFloat(window.getComputedStyle(element).lineHeight);
			return Number.isFinite(value) ? value : 0;
		},
		// The vertical pass. Runs LAST, after both horizontal cascades: the
		// TUI orders it the same way and says why -- the body height it budgets
		// against depends on the TOP row height, which the horizontal cascade
		// above is free to change (glances_curses_v5.py:617-619).
		async refitVertical() {
			if (this.refittingVertical) return;
			this.refittingVertical = true;
			try {
				// Stacked layout (css `@media (max-width: 48rem)`): the right
				// column sits BELOW the left one rather than beside it, so
				// budgeting it to viewport height would hide processes for no
				// reason. The TUI has no equivalent case (design 4.9).
				if (this.isStacked()) {
					this.rowBudget = {};
					return;
				}
				const bodyHeight = this.measureBodyRows();
				if (bodyHeight === null) {
					this.rowBudget = {};
					return;
				}
				const count = (name) => (this.results[name]?.data || []).length;
				// `tick()` fetches `this.plugins`, NOT the `slots()`-filtered
				// list (AppShell.vue:283), so BOTH process payloads are always
				// present even though only one is rendered. Summing them would
				// tell the solver there are twice as many processes as exist.
				// The visible one is chosen by the same flag `slots()` uses.
				const processes = this.effectiveArgs.programs ? count("programlist") : count("processlist");
				const alert = this.results.alert || {};
				const incidents = Array.isArray(alert.incidents) ? alert.incidents : [];
				const next = planRightColumn({
					bodyHeight,
					staticHeights: { processcount: 1 },
					ampsHeight: this.ampsHeight(),
					nVms: count("vms"),
					nContainers: count("containers"),
					nProcesses: processes,
					nAlerts: incidents.length,
					nOngoing: incidents.filter((incident) => incident.ongoing).length,
				});
				if (!sameFlags(next, this.rowBudget)) this.rowBudget = next;
			} finally {
				this.refittingVertical = false;
			}
		},
		isStacked() {
			if (typeof window.matchMedia !== "function") return false;
			return window.matchMedia(`(max-width: ${STACK_BREAKPOINT})`).matches;
		},
		// The TUI emits one row per result LINE, blanking the name and count
		// after the first, and paints no header row (amps/render_curses_v5.py
		// module docstring) -- this WebUI puts the whole multi-line result in
		// one `pre-line` cell instead (spec D6), but the LINE cost is the
		// same either way. `ampsLineCount` also drops an AMP whose result is
		// still `None`, the same predicate PluginAmps.vue's own `rows` filters
		// by (amps.js) -- so the two agree by construction, not by coincidence.
		ampsHeight() {
			return ampsLineCount(this.results.amps?.data);
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
	min-width: 0;
}
.gl-slot-left {
	gap: calc(var(--gl-gap) * 2);
}
/* Exactly one text row, because the vertical budget's cost() charges one
 * blank line between blocks (row_budget.js). Any other value makes the
 * ported arithmetic wrong by a fraction of a row per block boundary.
 * `grid-column: 2` pins the slot to the second column so it does not slide
 * left when no plugin is in the left slot. */
.gl-slot-right {
	gap: calc(var(--gl-row) * var(--gl-size-base));
	grid-column: 2;
}
/* 48rem matches no TUI rule: it is the browser's own threshold (spec D3),
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
	/* Server identity left, cadence right -- the two ends of one line. */
	justify-content: space-between;
	align-items: baseline;
	gap: var(--gl-gap);
	flex-wrap: wrap;
	margin-top: auto;
	position: sticky;
	bottom: 0;
	background: var(--gl-bg);
	border-top: 1px solid var(--gl-border);
	padding-block: var(--gl-gap);
}
/* The whole footer is chrome, not data: one notch below the body text and
 * muted, so neither end competes with a plugin for attention. */
.gl-about,
.gl-refresh {
	display: flex;
	align-items: baseline;
	gap: calc(2 * var(--gl-col));
	font-size: var(--gl-size-sm);
}
/* Clearance for the vertical scrollbar. `.gl-app`'s padding leaves the "+"
 * half a gap from the viewport edge, which a classic scrollbar crowds and an
 * overlay one (Firefox, macOS) draws straight over -- the button ends up hard
 * to hit, or unhittable. Two characters of padding on this end only: the
 * version and the links keep their place at the other. */
.gl-refresh {
	padding-right: calc(2 * var(--gl-col));
}
.gl-about-sep {
	/* The separators are quieter still than the items they part. */
	opacity: 0.5;
}
/* Links inherit the muted colour and carry a dotted underline instead of the
 * browser's solid blue: visibly a link on inspection, invisible at a glance.
 * They resolve on hover and on keyboard focus. */
.gl-about a {
	color: inherit;
	text-decoration: none;
	border-bottom: 1px dotted currentcolor;
}
.gl-about a:hover,
.gl-about a:focus-visible {
	color: var(--gl-fg);
}
/* The Hotkeys button, indistinguishable from the links beside it: a <button>
 * for semantics, a link for the eye. It has to reset the UA's button chrome
 * (background, border, font, padding) before the `.gl-about a` rules above can
 * be repeated here -- `:is()` on the two selectors would be shorter but would
 * still leave every one of those resets to write. */
.gl-about-action {
	appearance: none;
	background: none;
	border: none;
	padding: 0;
	font: inherit;
	line-height: inherit;
	cursor: pointer;
	color: inherit;
	text-decoration: none;
	border-bottom: 1px dotted currentcolor;
}
.gl-about-action:hover,
.gl-about-action:focus-visible {
	color: var(--gl-fg);
}
/* The `h` overlay. A centred panel over a scrim, not a sidebar: it is read
 * once and dismissed, and it must not reflow the page underneath -- the
 * degradation cascade measures that layout and a transient width change would
 * make it thrash. Every colour is a token; the stylesheet is the only place a
 * literal may appear (test_webui_v5_tokens.py). */
.gl-help {
	position: fixed;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	/* The scrim leans on the page background rather than a black literal, so it
	 * stays correct in the light theme too. */
	background: var(--gl-bg);
	opacity: 0.98;
	z-index: 10;
	padding: var(--gl-gap);
}
.gl-help-panel {
	background: var(--gl-surface);
	border: 1px solid var(--gl-border);
	padding: var(--gl-gap);
	max-height: 90vh;
	overflow-y: auto;
	min-width: 0;
}
.gl-help-title {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: var(--gl-gap);
	font-weight: var(--gl-weight-bold);
	margin-bottom: var(--gl-gap);
}
.gl-help-list {
	list-style: none;
	margin: 0;
	padding: 0;
	/* Two columns where there is room, one on a phone. The key column is sized
	 * in `--gl-col` like every other character-width in this UI. */
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
	column-gap: calc(2 * var(--gl-gap));
}
.gl-help-list li {
	display: grid;
	grid-template-columns: calc(3 * var(--gl-col)) 1fr;
	gap: var(--gl-gap);
	align-items: baseline;
	line-height: var(--gl-row);
}
.gl-help-list kbd {
	font: inherit;
	font-weight: var(--gl-weight-bold);
	text-align: center;
}
.gl-help-list span {
	color: var(--gl-muted);
}

/* The -/+ steppers: text, not chrome. No border, no background, the same
 * muted colour and size as the cadence they change -- the footer must not
 * grow a control bar. */
.gl-step {
	appearance: none;
	background: none;
	border: none;
	color: inherit;
	font: inherit;
	line-height: inherit;
	padding: 0;
	cursor: pointer;
}
.gl-step:hover:not(:disabled) {
	color: var(--gl-fg);
}
.gl-step:disabled {
	opacity: 0.4;
	cursor: default;
}
/* Three characters wide, centred: "1s" and "60s" then occupy the same box, so
 * stepping the cadence does not shift the "+" out from under the pointer. */
.gl-refresh-value {
	display: inline-block;
	min-width: calc(3 * var(--gl-col));
	text-align: center;
}
</style>

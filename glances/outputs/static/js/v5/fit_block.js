// Glances v5 WebUI -- per-BLOCK horizontal degradation.
//
// AppShell measures ZONES, because the top and header cascades hide whole
// blocks: that is the shell's business. A cascade that hides columns INSIDE
// one block is the component's business (AppShell.vue's spec D7: "a block
// that disappears is the shell's business; a block that merely shrinks is
// the component's"), so the state lives here, in a mixin the component adds.
//
// The ORDER and the fit test still come from degrade.js -- this module owns
// only the measurement, exactly as AppShell.measureZone() does for a zone.

import { resolveDegrade, sameFlags } from "./degrade.js";

// Host contract -- a component adding this mixin MUST provide:
//   - a `dropCascadeSteps` computed (its absence makes fitBlock() return
//     silently, doing nothing);
//   - a `payload` watcher that calls `this.fitBlock()`;
//   - `dropFlags` consumed in its template (to actually hide columns);
//   - a `<table>` descendant of its root element for measureBlock() to read.
export const fitBlockMixin = {
	data() {
		return {
			// {} = nothing dropped, which is also what an environment without
			// measurement keeps.
			dropFlags: {},
			// In-flight guard, like AppShell.refitting: fitBlock() is triggered
			// from the ResizeObserver's initial callback (mounted() itself never
			// calls it directly -- observe() fires once as soon as the element
			// is laid out), from the host's payload watcher, and from every
			// later ResizeObserver callback; measuring MUTATES dropFlags (and
			// therefore the DOM) once per candidate notch.
			fitting: false,
			blockObserver: null,
			// A pass coalesced into the next animation frame (scheduleFit).
			fitFrame: null,
		};
	},
	mounted() {
		// The render probe drives the pass through this hook: its fake DOM has
		// no ResizeObserver and no layout until the harness sets widths.
		if (typeof window !== "undefined") {
			if (!Array.isArray(window.__glancesBlockRefits)) window.__glancesBlockRefits = [];
			// Kept on the instance so unmounted() can remove exactly this
			// closure -- without that, a remounted block (runtime plugin
			// toggling, #3548) would leave a stale closure over a dead
			// component instance in the array on every remount.
			this._blockRefit = () => this.fitBlock();
			window.__glancesBlockRefits.push(this._blockRefit);
		}
		if (typeof ResizeObserver === "function" && this.$el?.nodeType === 1) {
			// scheduleFit(), never fitBlock() directly: dragging a window edge
			// fires this observer on every frame, and a pass costs one forced
			// layout per cascade step.
			this.blockObserver = new ResizeObserver(() => this.scheduleFit());
			this.blockObserver.observe(this.$el);
		}
	},
	unmounted() {
		if (this.blockObserver) this.blockObserver.disconnect();
		if (this.fitFrame !== null && typeof cancelAnimationFrame === "function") {
			cancelAnimationFrame(this.fitFrame);
		}
		if (typeof window !== "undefined" && Array.isArray(window.__glancesBlockRefits) && this._blockRefit) {
			const index = window.__glancesBlockRefits.indexOf(this._blockRefit);
			if (index !== -1) window.__glancesBlockRefits.splice(index, 1);
		}
	},
	methods: {
		// Coalesce fit requests into one animation frame, and re-schedule
		// (rather than drop) one that arrives mid-pass -- the same reasoning as
		// AppShell.scheduleRefit(), and the reason the LAST size of a window
		// drag still ends up fitted.
		scheduleFit() {
			if (this.fitFrame !== null) return;
			// No requestAnimationFrame means no layout engine either (the render
			// probe), so there is nothing to coalesce and no frame to come back
			// on: run it as the observer callback used to.
			if (typeof requestAnimationFrame !== "function") {
				this.fitBlock().catch(() => {});
				return;
			}
			this.fitFrame = requestAnimationFrame(() => {
				this.fitFrame = null;
				if (this.fitting) {
					this.scheduleFit();
					return;
				}
				this.fitBlock().catch(() => {});
			});
		},
		// Apply a candidate flag set, let Vue re-render, and report what the
		// browser says about the table inside this block.
		async measureBlock(flags) {
			if (!sameFlags(flags, this.dropFlags)) this.dropFlags = flags;
			await this.$nextTick();
			const block = this.$el;
			if (!block || block.nodeType !== 1) return { content: 0, available: 0 };
			// Measure the text at its natural width: shrunk into its ellipsis it
			// never overflows and the cascade would never run. `.gl-command` and
			// `.gl-name` keep their caps (css/v5.css) -- the TUI budgets Command
			// at _MIN_COMMAND_WIDTH for the same reason.
			block.classList.add("gl-measuring");
			const table = block.querySelector?.("table");
			// A table can overflow its container, so its scrollWidth (not the
			// block's own) is the content figure; the block's own scrollWidth is
			// the fallback for a component with no table at all.
			const measured = table || block;
			// Harness hook, as AppShell.measureZone() does: a real element
			// ignores this expando; the probe's FakeElement models scrollWidth
			// shrinking by one CONTENT_PER_NOTCH per applied flag. Set on
			// `measured` (not always `block`) -- the shrink must land on
			// whichever element's scrollWidth is actually read below.
			measured._notches = Object.keys(flags).length;
			const reading = {
				content: measured.scrollWidth,
				available: block.clientWidth,
			};
			block.classList.remove("gl-measuring");
			return reading;
		},
		// Re-run the cascade from scratch: starting from no flag is what gives
		// the columns back when the window widens.
		async fitBlock(cascade) {
			const steps = cascade || this.dropCascadeSteps;
			if (this.fitting || !steps) return;
			this.fitting = true;
			try {
				// measureBlock() already assigned every candidate it tried to
				// this.dropFlags along the way, and resolveDegrade() returns the
				// LAST candidate it measured -- so by the time this resolves,
				// this.dropFlags already equals the answer; nothing more to
				// assign. `measureBlock`'s `sameFlags` guard only skips a
				// redundant re-assignment when a candidate happens to match what
				// is already applied -- it does NOT stop dropFlags from being
				// reassigned mid-pass: every pass restarts from `{}`, so a block
				// whose prior steady state was non-empty is briefly widened back
				// out before the cascade re-drops the same columns. What actually
				// keeps a ResizeObserver from feeding back on itself is (1) the
				// `fitting` in-flight guard above, which makes any resize event
				// fired by this pass's OWN DOM writes a no-op re-entrant call, and
				// (2) that dropping/restoring COLUMNS does not change the block's
				// own box size (only its scrollWidth) -- the shell's grid still
				// gives it the same width, so hiding a column is not itself an
				// event this component's own ResizeObserver reacts to. WHY the box
				// is independent of its content: AppShell.vue's `.gl-zone-body` is
				// `grid-template-columns: max-content 1fr` and `.gl-slot-right`
				// (this block's ancestor) is `min-width: 0` -- the right slot IS the
				// `1fr` track, so its width comes from the remaining grid space,
				// never from what is inside it. A later layout change that makes the
				// right column content-sized (e.g. `max-content`) would reintroduce
				// this feedback loop -- and the next batch's process list lands in
				// this very slot.
				await resolveDegrade(steps, (candidate) => this.measureBlock(candidate));
			} finally {
				this.fitting = false;
			}
		},
	},
};

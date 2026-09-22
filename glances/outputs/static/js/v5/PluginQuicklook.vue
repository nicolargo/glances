<template>
	<article
		v-show="!isHidden"
		class="gl-plugin"
		:class="{ 'gl-quicklook-no-header': !header, 'gl-quicklook-full': fullQuicklook }"
		:aria-label="TITLE"
	>
		<!-- aria-label: once loaded the CPU name/frequency line is a plain row,
		not a heading, so the <article> keeps naming itself for assistive tech
		the whole time (PluginLoad.vue's pattern) -- quicklook has no per-payload
		identity the way gpu/npu do. -->
		<div v-if="error || !payload" class="gl-plugin-title">
			<h2 class="gl-header">{{ TITLE }}</h2>
		</div>
		<p v-if="error" class="gl-level-critical">{{ error }}</p>
		<p v-else-if="!payload" class="gl-muted">loading…</p>
		<template v-else>
			<!-- CPU name + frequency (render_curses_v5.py `_header_row`): absent
			entirely when there is no current frequency, not an empty row. Under
			`degrade.quicklook_freq_only` the name is replaced by the literal
			"Frequency" -- the TUI shrinks the header, it does not merely hide the
			name. -->
			<div v-if="header" class="gl-inline">
				<span class="gl-header">{{ header.name }}</span>
				<span>{{ header.freq }}</span>
			</div>
			<!-- One `.gl-bar` per `[quicklook] list` entry, in order. `bar_char`
			and `percent_char` are terminal concerns (how the TUI paints its
			`||||` characters) and are deliberately NOT read here -- the fill's
			CSS width IS the value; do not "restore" them. -->
			<div v-for="bar in bars" :key="bar.label" class="gl-bar">
				<span class="gl-bar-label">{{ bar.label }}</span>
				<div
					class="gl-bar-track"
					role="progressbar"
					:aria-valuenow="bar.valuenow"
					aria-valuemin="0"
					aria-valuemax="100"
					:aria-label="bar.label"
				>
					<div class="gl-bar-fill" :class="bar.cls" :style="{ width: bar.pct + '%' }"></div>
				</div>
				<span class="gl-bar-value gl-num" :class="bar.cls">{{ bar.text }}</span>
			</div>
		</template>
	</article>
</template>

<script>
import { levelClass, scalarLevel } from "./levels.js";
import { formatPercent, toFixedHalfEven } from "./format.js";
import { PLUGIN_PROPS } from "./plugin_props.js";

const TITLE = "QUICKLOOK";

// Fallback bar selection, used only when the payload carries no `stats_list`
// (quicklook/render_curses_v5.py `_BAR_KEYS`) -- an older server.
const FALLBACK_KEYS = ["cpu", "mem", "load", "gpu_mem", "gpu_proc"];

// 4-char display labels -- the raw upper-cased keys "GPU_MEM"/"GPU_PROC" are
// 7 characters and would break the TUI's grid (`_BAR_LABEL`).
const BAR_LABEL = { gpu_mem: "GMEM", gpu_proc: "GPU" };

// Per-core: top-N shown, the rest collapsed into a "CPU*" mean row. Fallback
// cut, used only when the payload carries no `max_cpu_display`
// (`_DEFAULT_MAX_CPU_DISPLAY`) -- an older server.
const DEFAULT_MAX_CPU_DISPLAY = 4;

const TIER_NAMES = new Set(["ok", "careful", "warning", "critical"]);

// A core's own level, or the aggregate `cpu` tier when it carries none/an
// unrecognised one -- mirrors `_LEVEL_TO_ROLE.get(core.get("level"),
// fallback_role)`, which falls through on both a missing key and an unknown
// value.
function pickLevel(level, fallback) {
	return TIER_NAMES.has(level) ? level : fallback;
}

function clampPct(value) {
	const n = Number(value);
	if (!Number.isFinite(n)) return 0;
	return Math.max(0, Math.min(100, n));
}

export default {
	name: "PluginQuicklook",
	// Reads `serverArgs.percpu` (per-core replacement of the `cpu` bar),
	// `serverArgs.full_quicklook` (the block takes the whole row) and
	// `degrade.quicklook_freq_only` (TOP_CASCADE step d).
	props: { ...PLUGIN_PROPS },
	computed: {
		TITLE: () => TITLE,
		// `--full-quicklook` / the `4` key. The TUI sizes the bars to the whole
		// terminal width in this mode (`_fit_full_quicklook`); the browser's
		// equivalent is letting the block grow into the row it now has to
		// itself, which the `.gl-quicklook-full` rule does. Without it the
		// article keeps its content width and the freed space is simply blank --
		// `.gl-slot-top` is `justify-content: space-between`, which does nothing
		// for a single child.
		fullQuicklook() {
			return !!this.serverArgs.full_quicklook;
		},
		freqOnly() {
			return !!this.degrade.quicklook_freq_only;
		},
		header() {
			if (!this.payload) return null;
			const cur = this.payload.cpu_hz_current;
			if (cur == null) return null;
			const max = this.payload.cpu_hz;
			const freq =
				max != null
					? `${toFixedHalfEven(cur / 1e9, 2)}/${toFixedHalfEven(max / 1e9, 2)}GHz`
					: `${toFixedHalfEven(cur / 1e9, 2)}GHz`;
			const name = this.freqOnly ? "Frequency" : this.payload.cpu_name || "Frequency";
			return { name, freq };
		},
		// The `cpu` bar is replaced by the per-core view only when the server ran
		// with --percpu AND the payload actually carries the `percpu` array
		// (render_curses_v5.py:168).
		percpuActive() {
			return !!this.serverArgs.percpu && Array.isArray(this.payload && this.payload.percpu);
		},
		perCoreBars() {
			if (!this.percpuActive) return [];
			const cores = this.payload.percpu.filter((c) => c && typeof c === "object");
			if (!cores.length) return [];
			const maxDisplay = Number.isInteger(this.payload.max_cpu_display)
				? this.payload.max_cpu_display
				: DEFAULT_MAX_CPU_DISPLAY;
			// Sorted by total descending ONLY when the cap actually bites -- the
			// TUI keeps payload order otherwise (_per_cpu_rows:198-201).
			const ordered =
				cores.length > maxDisplay
					? [...cores].sort((a, b) => (Number(b.total) || 0) - (Number(a.total) || 0))
					: cores;
			const displayed = ordered.slice(0, maxDisplay);
			const aggregateEntry = scalarLevel(this.payload, "cpu");
			const fallbackLevel = aggregateEntry ? aggregateEntry.level : null;

			const bars = displayed.map((core) => {
				const cid = core.cpu_number;
				// v4 parity: `f"CPU{cid}"` for a single digit, `f"{cid:>4}"`
				// otherwise -- the leading-space pad a JS `padStart` would add here
				// is inert in HTML (collapses), so the actual right-alignment comes
				// from `.gl-bar-label { text-align: right }` (css/v5.css) instead.
				const label = typeof cid === "number" && cid < 10 ? `CPU${cid}` : String(cid);
				return this.buildBar(label, core.total, {
					level: pickLevel(core.level, fallbackLevel),
					prominent: false,
				});
			});

			const other = this.payload.percpu_other;
			if (other && typeof other === "object") {
				bars.push(
					this.buildBar("CPU*", other.total, {
						level: pickLevel(other.level, fallbackLevel),
						prominent: false,
					}),
				);
			} else {
				// v4 parity: the "CPU*" row averages the HIDDEN (overflow) cores,
				// not the displayed ones, and takes the aggregate tier.
				const overflow = ordered.slice(maxDisplay);
				if (overflow.length) {
					const mean = overflow.reduce((sum, c) => sum + (Number(c.total) || 0), 0) / overflow.length;
					bars.push(this.buildBar("CPU*", mean, { level: fallbackLevel, prominent: false }));
				}
			}
			return bars;
		},
		bars() {
			if (!this.payload) return [];
			const keys =
				Array.isArray(this.payload.stats_list) && this.payload.stats_list.length
					? this.payload.stats_list
					: FALLBACK_KEYS;
			const bars = [];
			for (const key of keys) {
				if (key === "cpu" && this.percpuActive) {
					bars.push(...this.perCoreBars);
					continue;
				}
				const value = this.payload[key];
				if (value === null || value === undefined) continue;
				const label = BAR_LABEL[key] || key.toUpperCase();
				bars.push(this.buildBar(label, value, scalarLevel(this.payload, key)));
			}
			return bars;
		},
		isHidden() {
			return !!this.payload && !this.header && this.bars.length === 0;
		},
	},
	methods: {
		buildBar(label, value, entry) {
			const pct = clampPct(value);
			return {
				label,
				pct,
				valuenow: String(Math.round(pct)),
				text: formatPercent(value),
				cls: levelClass(entry),
			};
		},
	},
};
</script>

<template>
	<!-- Same overlay as the alerts' full list (PluginAlert.vue): the classes
	live in css/glances.css so both popups share one look. Teleported so no
	ancestor can clip a fixed box. -->
	<Teleport v-if="target" to="body">
		<div class="gl-alert-all" role="dialog" aria-modal="true" :aria-label="`${title} history`" @click="close">
			<div class="gl-alert-all-panel" @click.stop>
				<div class="gl-alert-all-title">
					<span class="gl-header">{{ title }}</span>
					<button type="button" class="gl-alert-link" aria-label="Close" @click="close">×</button>
				</div>
				<p v-if="error" class="gl-level-critical">{{ error }}</p>
				<p v-else-if="loading" class="gl-muted">loading…</p>
				<p v-else-if="!points.length" class="gl-muted">no history yet</p>
				<template v-else>
					<p class="gl-history-stats">
						<span class="gl-header">now</span> {{ fmt(stats.last) }}
						<span class="gl-header">min</span> {{ fmt(stats.min) }}
						<span class="gl-header">avg</span> {{ fmt(stats.avg) }}
						<span class="gl-header">max</span> {{ fmt(stats.max) }}
					</p>
					<div class="gl-history-plot">
						<!-- HTML, not SVG <text>: the SVG is stretched to the panel's
						width, which would squash the glyphs. -->
						<div class="gl-history-yaxis">
							<span v-for="tick in yTicks" :key="tick.text">{{ tick.text }}</span>
						</div>
						<div class="gl-history-canvas">
						<svg
							class="gl-history-chart"
							:viewBox="`0 0 ${W} ${H}`"
							preserveAspectRatio="none"
							role="img"
							:aria-label="`${title} over time`"
							@mousemove="onMove"
							@mouseleave="hover = null"
						>
							<line v-for="tick in yTicks" :key="tick.y" class="gl-history-grid" :x1="0" :x2="W" :y1="tick.y" :y2="tick.y" />
							<path class="gl-history-line" :d="path" />
							<line v-if="hoverPoint" class="gl-history-cursor" :x1="hoverPoint.x" :x2="hoverPoint.x" :y1="0" :y2="H" />
						</svg>
						<span v-if="hoverPoint" class="gl-history-dot" :style="dotStyle"></span>
						</div>
					</div>
					<p class="gl-history-axis">
						<span>{{ clock(points[0].t) }}</span>
						<span v-if="hoverPoint" class="gl-history-hover">{{ clock(hoverPoint.t) }} · {{ fmt(hoverPoint.v) }}</span>
						<span>{{ clock(points[points.length - 1].t) }}</span>
					</p>
				</template>
			</div>
		</div>
	</Teleport>
</template>

<script>
import { closeHistory, fetchSeries, historyState } from "./history.js";
import { formatBytes, formatNetworkRate, formatPercent, formatRate } from "./format.js";

// The SVG's own coordinate space, stretched to the panel by
// preserveAspectRatio="none"; strokes stay unscaled via vector-effect (CSS).
const W = 900;
const H = 260;
const PAD_L = 0;
const PAD_R = 0;
const PAD_T = 4;
const PAD_B = 4;

const FORMATTERS = {
	percent: formatPercent,
	byte: formatBytes,
	bytespers: formatRate,
	float: (v) => v.toFixed(2),
};

export default {
	name: "HistoryModal",
	// The live curve re-reads the series at the page's refresh cadence
	// (`refresh`, seconds) while the popup is open.
	props: { refresh: { type: Number, default: 2 } },
	data() {
		return { W, H, PAD_L, PAD_R, PAD_T, PAD_B, points: [], loading: false, error: "", hover: null, timer: null, listening: false };
	},
	computed: {
		target: () => historyState.target,
		unit() {
			return historyState.fields[this.target?.plugin]?.[this.target?.field];
		},
		// "CPU user", "NETWORK eth0 bytes_recv" -- plugin, then item, then field.
		title() {
			const { plugin, field, item } = this.target || {};
			return [plugin, item, field && field.replace(/_/g, " ")].filter((p) => p !== undefined && p !== null && p !== "").join(" ").toUpperCase();
		},
		values() {
			return this.points.map((p) => p.v).filter((v) => typeof v === "number");
		},
		stats() {
			const v = this.values;
			if (!v.length) return {};
			return { last: v[v.length - 1], min: Math.min(...v), max: Math.max(...v), avg: v.reduce((a, b) => a + b, 0) / v.length };
		},
		// Percent curves keep a 0-100 axis (their real range, comparable from
		// one popup to the next); anything else fits its own data, from 0.
		range() {
			const { min, max } = this.stats;
			if (this.unit === "percent") return [0, 100];
			return [Math.min(0, min), max > Math.min(0, min) ? max : Math.min(0, min) + 1];
		},
		coords() {
			const [lo, hi] = this.range;
			const n = this.points.length;
			return this.points.map((p, i) => ({
				...p,
				x: n > 1 ? PAD_L + (i / (n - 1)) * (W - PAD_L - PAD_R) : PAD_L,
				y: typeof p.v === "number" ? PAD_T + (1 - (p.v - lo) / (hi - lo)) * (H - PAD_T - PAD_B) : null,
			}));
		},
		// A gap (`null`, the series did not exist yet) breaks the line.
		path() {
			let d = "";
			let pen = false;
			for (const c of this.coords) {
				if (c.y === null) {
					pen = false;
					continue;
				}
				d += `${pen ? "L" : "M"}${c.x.toFixed(1)},${c.y.toFixed(1)}`;
				pen = true;
			}
			return d;
		},
		yTicks() {
			const [lo, hi] = this.range;
			return [1, 0.5, 0].map((f) => {
				const value = lo + (hi - lo) * f;
				return { y: PAD_T + (1 - f) * (H - PAD_T - PAD_B), text: this.fmt(value) };
			});
		},
		// The hovered point's marker is an HTML dot over the stretched SVG (a
		// circle in it would be squashed into an ellipse).
		dotStyle() {
			return { left: `${(this.hoverPoint.x / W) * 100}%`, top: `${(this.hoverPoint.y / H) * 100}%` };
		},
		hoverPoint() {
			return this.hover === null ? null : this.coords[this.hover]?.y === null ? null : this.coords[this.hover] || null;
		},
	},
	watch: {
		target: {
			immediate: true,
			handler(target) {
				this.stop();
				this.points = [];
				this.hover = null;
				if (!target) return;
				this.loading = true;
				this.error = "";
				document.addEventListener("keydown", this.onKeydown);
				this.listening = true;
				this.load();
				this.timer = setInterval(this.load, Math.max(1, this.refresh) * 1000);
			},
		},
	},
	beforeUnmount() {
		this.stop();
	},
	methods: {
		close: closeHistory,
		fmt(value) {
			if (typeof value !== "number") return "-";
			// Network rates follow the table: bits/s, or bytes/s under --byte.
			if (this.target.plugin === "network") return `${formatNetworkRate(value, !!this.target.byte)}/s`;
			return (FORMATTERS[this.unit] || ((v) => String(Math.round(v * 100) / 100)))(value);
		},
		clock(t) {
			return new Date(t * 1000).toTimeString().slice(0, 8);
		},
		async load() {
			const target = this.target;
			if (!target) return;
			try {
				const points = await fetchSeries(target);
				// The popup may have been closed or re-targeted meanwhile.
				if (this.target !== target) return;
				this.points = points;
				this.error = "";
			} catch (e) {
				if (this.target === target) this.error = e.message;
			} finally {
				if (this.target === target) this.loading = false;
			}
		},
		stop() {
			clearInterval(this.timer);
			this.timer = null;
			// Only once opened: the first call (the watcher's immediate run, with
			// no popup) has nothing to remove.
			if (this.listening) document.removeEventListener("keydown", this.onKeydown);
			this.listening = false;
		},
		onKeydown(event) {
			if (event.key === "Escape") {
				event.preventDefault();
				this.close();
			}
		},
		onMove(event) {
			const rect = event.currentTarget.getBoundingClientRect();
			const n = this.points.length;
			if (!rect.width || n < 2) return;
			const x = ((event.clientX - rect.left) / rect.width) * W;
			const i = Math.round(((x - PAD_L) / (W - PAD_L - PAD_R)) * (n - 1));
			this.hover = Math.min(n - 1, Math.max(0, i));
		},
	},
};
</script>

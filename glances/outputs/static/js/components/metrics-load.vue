<template>
	<div class="m-tile tile-load" style="--t-color:var(--green)">
		<div class="m-head">
			<span class="m-id">LOAD <span class="m-id-sub">{{ cpucore }}-core</span></span>
		</div>
		<div class="m-spark-row">
			<span class="m-val" :class="decoration">{{ min1Display }}</span>
			<sparkline :data="history" :max="cpucore" :color="sparkColor" :height="26" />
		</div>
		<div class="m-sub-rows">
			<div class="m-kv">1min  <span class="v" :class="min1Deco">{{ min1Display }}</span></div>
			<div class="m-kv">5min  <span class="v" :class="min5Deco">{{ min5Display }}</span></div>
			<div class="m-kv">15min <span class="v" :class="min15Deco">{{ min15Display }}</span></div>
		</div>
	</div>
</template>

<script>
import { store } from "../store.js";
import Sparkline from "./sparkline.vue";

function colorFor(pct) {
	if (pct >= 90) return '#ff3355';
	if (pct >= 75) return '#ffcc00';
	if (pct >= 50) return '#4488ff';
	return '#2ecc71';
}

function decoStr(v) {
	if (!v || !v.decoration) return '';
	const d = v.decoration.toLowerCase();
	if (d.endsWith('_log')) return d;
	if (d === 'ok') return 'ok';
	if (d === 'warning') return 'warn';
	if (d === 'critical') return 'crit';
	if (d === 'careful') return 'hi';
	if (d === 'default') return 'dim';
	return 'dim';
}

export default {
	components: { Sparkline },
	props: { data: { type: Object } },
	computed: {
		stats() { return this.data?.stats?.load || {}; },
		view() { return this.data?.views?.load || {}; },
		history() { return store.history.load; },
		cpucore() { return this.stats.cpucore || 1; },
		min1() { return this.stats.min1 ?? 0; },
		min5() { return this.stats.min5 ?? 0; },
		min15() { return this.stats.min15 ?? 0; },
		min1Display() { return this.min1.toFixed(2); },
		min5Display() { return this.min5.toFixed(2); },
		min15Display() { return this.min15.toFixed(2); },
		decoration() {
			if (!this.view.min1) return 'ok';
			return this.view.min1.decoration?.toLowerCase() || 'ok';
		},
		decorationLabel() {
			const d = this.decoration;
			if (d === 'ok') return 'OK';
			if (d === 'critical') return 'CRIT';
			if (d === 'warning') return 'WARN';
			return d.toUpperCase();
		},
		sparkColor() {
			const pct = this.cpucore > 0 ? (this.min1 / this.cpucore) * 100 : 0;
			return colorFor(pct);
		},
		min1Deco() { return decoStr(this.view.min1); },
		min5Deco() { return decoStr(this.view.min5); },
		min15Deco() { return decoStr(this.view.min15); },
	},
};
</script>

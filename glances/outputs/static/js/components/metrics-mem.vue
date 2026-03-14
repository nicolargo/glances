<template>
	<div class="m-tile tile-mem" style="--t-color:var(--yellow)">
		<!-- header: MEM left, SWAP value right -->
		<div class="m-head">
			<span class="m-id">MEM</span>
			<span class="ms-swap-hdr" v-if="hasSwap">
				<span class="ms-swap-label">SWAP</span>
				<span :class="swapDecoration">{{ swapPercent }}%</span>
			</span>
		</div>

		<!-- MEM sparkline row -->
		<div class="ms-sparks">
			<div class="m-spark-row">
				<span class="ms-val" :class="memDecoration">{{ memPercent }}<span class="unit">%</span></span>
				<sparkline :data="history" :max="100" :color="sparkColor" :height="22" />
			</div>
		</div>

		<!-- extended MEM stats in 2-column grid -->
		<div class="ms-stats">
			<div class="ms-stat-row"><span class="k">total:</span><span class="v">{{ total }}</span></div>
			<div class="ms-stat-row"><span class="k">active:</span><span class="v">{{ active }}</span></div>
			<div class="ms-stat-row"><span class="k">used:</span><span class="v" :class="usedDeco">{{ used }}</span></div>
			<div class="ms-stat-row"><span class="k">inactive:</span><span class="v">{{ inactive }}</span></div>
			<div class="ms-stat-row"><span class="k">free:</span><span class="v">{{ free }}</span></div>
			<div class="ms-stat-row"><span class="k">buffers:</span><span class="v">{{ buffers }}</span></div>
			<div class="ms-stat-row"><span class="k">avail:</span><span class="v">{{ available }}</span></div>
			<div class="ms-stat-row"><span class="k">cached:</span><span class="v">{{ cached }}</span></div>
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

export default {
	components: { Sparkline },
	props: { data: { type: Object } },
	computed: {
		memStats() { return this.data?.stats?.mem || {}; },
		memView() { return this.data?.views?.mem || {}; },
		swapStats() { return this.data?.stats?.memswap || {}; },
		swapView() { return this.data?.views?.memswap || {}; },
		history() { return store.history.mem; },

		memPercent() { return (this.memStats.percent ?? 0).toFixed(1); },
		memDecoration() {
			if (!this.memView.percent) return 'ok';
			return this.memView.percent.decoration?.toLowerCase() || 'ok';
		},

		hasSwap() { return this.swapStats.percent != null; },
		swapPercent() { return (this.swapStats.percent ?? 0).toFixed(1); },
		swapDecoration() {
			if (!this.swapView.percent) return 'ok';
			return this.swapView.percent.decoration?.toLowerCase() || 'ok';
		},

		sparkColor() { return colorFor(this.memStats.percent || 0); },

		total() { return this.$filters.bytes(this.memStats.total); },
		used() { return this.$filters.bytes(this.memStats.used); },
		available() { return this.$filters.bytes(this.memStats.available); },
		free() { return this.$filters.bytes(this.memStats.free); },
		active() { return this.$filters.bytes(this.memStats.active); },
		inactive() { return this.$filters.bytes(this.memStats.inactive); },
		buffers() { return this.$filters.bytes(this.memStats.buffers); },
		cached() { return this.$filters.bytes(this.memStats.cached); },

		usedDeco() {
			if (!this.memView.used) return '';
			const d = this.memView.used.decoration?.toLowerCase() || '';
			if (d.endsWith('_log')) return d;
			if (d === 'warning') return 'warn';
			if (d === 'critical') return 'crit';
			if (d === 'ok') return 'ok';
			if (d === 'careful') return 'ok';
			return '';
		},
	},
};
</script>

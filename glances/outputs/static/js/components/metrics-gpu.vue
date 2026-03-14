<template>
	<div class="m-tile tile-gpu" style="--t-color:var(--cyan)">
		<div class="m-head">
			<span class="m-id">GPU <template v-if="gpuCount > 1">&times;{{ gpuCount }}</template></span>
		</div>
		<div class="m-spark-row">
			<span class="m-val" :class="decoration">{{ meanProcDisplay }}<span class="unit">%</span></span>
			<sparkline :data="history" :max="100" :color="sparkColor" :height="26" />
		</div>
		<div class="m-sub-rows">
			<div class="m-kv" v-for="gpu in gpus" :key="gpu.gpu_id">
				{{ gpu.name }}
				<span class="v" :class="gpuProcDeco(gpu)">{{ (gpu.proc || 0).toFixed(0) }}%</span>
			</div>
			<div class="m-kv" v-if="meanMem != null">
				MEM <span class="v dim">{{ meanMem.toFixed(0) }}%</span>
			</div>
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
		stats() { return this.data?.stats?.gpu || []; },
		view() { return this.data?.views?.gpu || {}; },
		history() { return store.history.gpu; },
		gpus() { return this.stats; },
		gpuCount() { return this.stats.length; },
		meanProc() {
			if (this.stats.length === 0) return 0;
			return this.stats.reduce((s, g) => s + (g.proc || 0), 0) / this.stats.length;
		},
		meanProcDisplay() { return this.meanProc.toFixed(1); },
		meanMem() {
			if (this.stats.length === 0) return null;
			return this.stats.reduce((s, g) => s + (g.mem || 0), 0) / this.stats.length;
		},
		decoration() {
			// Use first GPU's decoration or derive from value
			const first = this.stats[0];
			if (first && this.view[first.gpu_id]?.proc?.decoration) {
				return this.view[first.gpu_id].proc.decoration.toLowerCase();
			}
			if (this.meanProc >= 90) return 'critical';
			if (this.meanProc >= 75) return 'warning';
			if (this.meanProc >= 50) return 'careful';
			return 'ok';
		},
		decorationLabel() {
			const d = this.decoration;
			if (d === 'ok') return 'OK';
			if (d === 'critical') return 'CRIT';
			if (d === 'warning') return 'WARN';
			return d.toUpperCase();
		},
		sparkColor() { return colorFor(this.meanProc); },
	},
	methods: {
		gpuProcDeco(gpu) {
			if (this.view[gpu.gpu_id]?.proc?.decoration) {
				const d = this.view[gpu.gpu_id].proc.decoration.toLowerCase();
				if (d.endsWith('_log')) return d;
				if (d === 'ok') return 'ok';
				if (d === 'warning') return 'warn';
				if (d === 'critical') return 'crit';
			}
			return 'ok';
		},
	},
};
</script>

<template>
	<div class="m-tile tile-npu" style="--t-color:var(--magenta)">
		<div class="m-head">
			<span class="m-id">NPU <template v-if="npuCount > 1">&times;{{ npuCount }}</template></span>
		</div>
		<div class="m-spark-row">
			<span class="m-val" :class="decoration">{{ meanProcDisplay }}<span class="unit">%</span></span>
			<sparkline :data="history" :max="100" :color="sparkColor" :height="26" />
		</div>
		<div class="m-sub-rows">
			<div class="m-kv" v-for="npu in npus" :key="npu.key">
				{{ npu.name }}
				<span class="v" :class="npuProcDeco(npu)">{{ (npu.proc || 0).toFixed(0) }}%</span>
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
		stats() { return this.data?.stats?.npu || []; },
		view() { return this.data?.views?.npu || {}; },
		history() { return store.history.npu; },
		npus() { return this.stats; },
		npuCount() { return this.stats.length; },
		meanProc() {
			if (this.stats.length === 0) return 0;
			return this.stats.reduce((s, n) => s + (n.proc || 0), 0) / this.stats.length;
		},
		meanProcDisplay() { return this.meanProc.toFixed(1); },
		meanMem() {
			if (this.stats.length === 0) return null;
			const mems = this.stats.filter(n => n.mem != null);
			if (mems.length === 0) return null;
			return mems.reduce((s, n) => s + (n.mem || 0), 0) / mems.length;
		},
		decoration() {
			const first = this.stats[0];
			if (first && this.view[first.key]?.proc?.decoration) {
				return this.view[first.key].proc.decoration.toLowerCase();
			}
			if (this.meanProc >= 90) return 'critical';
			if (this.meanProc >= 75) return 'warning';
			if (this.meanProc >= 50) return 'careful';
			return 'ok';
		},
		sparkColor() { return colorFor(this.meanProc); },
	},
	methods: {
		npuProcDeco(npu) {
			if (this.view[npu.key]?.proc?.decoration) {
				const d = this.view[npu.key].proc.decoration.toLowerCase();
				if (d === 'ok') return 'ok';
				if (d === 'warning') return 'warn';
				if (d === 'critical') return 'crit';
			}
			return 'ok';
		},
	},
};
</script>

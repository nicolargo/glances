<template>
	<div class="m-tile" style="--t-color:var(--green)">
		<div class="m-head">
			<span class="m-id">CPU <span class="m-id-sub" v-if="cpuName">{{ cpuName }} &middot; {{ coreCount }}-core</span></span>
		</div>
		<div class="m-spark-row">
			<span class="m-val" :class="decoration">{{ totalDisplay }}<span class="unit">%</span></span>
			<sparkline :data="history" :max="100" :color="sparkColor" :height="22" />
		</div>
		<!-- 3-column extended stats grid -->
		<div class="cpu-stats-grid">
			<!-- col 1 -->
			<div class="cpu-col">
				<div class="cpu-row"><span class="k">user:</span><span class="v" :class="userDeco">{{ user }}%</span></div>
				<div class="cpu-row"><span class="k">system:</span><span class="v" :class="systemDeco">{{ system }}%</span></div>
				<div class="cpu-row"><span class="k">iowait:</span><span class="v" :class="iowaitDeco">{{ iowait }}%</span></div>
				<div class="cpu-row" v-if="data.isLinux"><span class="k">steal:</span><span class="v dim">{{ steal }}%</span></div>
				<div class="cpu-row" v-if="data.isWindows"><span class="k">dpc:</span><span class="v" :class="dpcDeco">{{ dpc }}%</span></div>
			</div>
			<!-- col 2 -->
			<div class="cpu-col">
				<div class="cpu-row"><span class="k">idle:</span><span class="v hi">{{ idle }}%</span></div>
				<div class="cpu-row"><span class="k">irq:</span><span class="v dim">{{ irq }}%</span></div>
				<div class="cpu-row"><span class="k">nice:</span><span class="v dim">{{ nice }}%</span></div>
				<div class="cpu-row" v-if="data.isLinux"><span class="k">guest:</span><span class="v dim">{{ guest }}%</span></div>
			</div>
			<!-- col 3 -->
			<div class="cpu-col">
				<div class="cpu-row"><span class="k">ctx_sw:</span><span class="v" :class="ctxDeco">{{ ctxSwitches }}</span></div>
				<div class="cpu-row"><span class="k">inter:</span><span class="v dim">{{ interrupts }}</span></div>
				<div class="cpu-row" v-if="data.isLinux"><span class="k">sw_int:</span><span class="v dim">{{ softInterrupts }}</span></div>
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
	return '#00ff88';
}

function decoClass(v) {
	if (!v || !v.decoration) return 'dim';
	const d = v.decoration.toLowerCase();
	if (d === 'ok' || d === 'ok_log') return 'ok';
	if (d === 'warning' || d === 'warning_log') return 'warn';
	if (d === 'critical' || d === 'critical_log') return 'crit';
	if (d === 'careful' || d === 'careful_log') return 'hi';
	if (d === 'default') return 'dim';
	return 'dim';
}

export default {
	components: { Sparkline },
	props: { data: { type: Object } },
	computed: {
		stats() { return this.data?.stats?.cpu || {}; },
		view() { return this.data?.views?.cpu || {}; },
		history() { return store.history.cpu; },
		total() { return this.stats.total != null ? this.stats.total : 0; },
		totalDisplay() { return this.total.toFixed(1); },
		decoration() {
			if (!this.view.total) return 'ok';
			const d = this.view.total.decoration?.toLowerCase() || 'ok';
			return d.replace('_log', '');
		},
		decorationLabel() {
			const d = this.decoration;
			if (d === 'ok') return 'OK';
			if (d === 'critical') return 'CRIT';
			if (d === 'warning') return 'WARN';
			return d.toUpperCase();
		},
		sparkColor() { return colorFor(this.total); },
		cpuName() { return this.data?.stats?.quicklook?.cpu_name || ''; },
		coreCount() { return this.data?.stats?.core?.log || this.data?.stats?.core?.phys || '?'; },
		user() { return (this.stats.user ?? 0).toFixed(1); },
		system() { return (this.stats.system ?? 0).toFixed(1); },
		idle() { return (this.stats.idle ?? 0).toFixed(1); },
		nice() { return (this.stats.nice ?? 0).toFixed(1); },
		irq() { return (this.stats.irq ?? 0).toFixed(1); },
		iowait() { return (this.stats.iowait ?? 0).toFixed(1); },
		steal() { return (this.stats.steal ?? 0).toFixed(1); },
		guest() { return (this.stats.guest ?? 0).toFixed(1); },
		dpc() { return (this.stats.dpc ?? 0).toFixed(1); },
		ctxSwitches() {
			const v = this.stats.ctx_switches;
			if (v == null) return '0';
			const tsu = this.stats.time_since_update || 1;
			return Math.round(v / tsu).toLocaleString();
		},
		interrupts() {
			const v = this.stats.interrupts;
			if (v == null) return '0';
			const tsu = this.stats.time_since_update || 1;
			return Math.round(v / tsu).toLocaleString();
		},
		softInterrupts() {
			const v = this.stats.soft_interrupts;
			if (v == null) return '0';
			const tsu = this.stats.time_since_update || 1;
			return Math.round(v / tsu).toLocaleString();
		},
		userDeco() { return decoClass(this.view.user); },
		systemDeco() { return decoClass(this.view.system); },
		iowaitDeco() { return decoClass(this.view.iowait); },
		dpcDeco() { return decoClass(this.view.dpc); },
		ctxDeco() { return decoClass(this.view.ctx_switches); },
	},
};
</script>

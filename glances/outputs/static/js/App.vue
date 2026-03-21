<template>
	<div v-if="!dataLoaded" class="loading-page">
		Glances is loading...
	</div>
	<glances-help v-else-if="args.help_tag"></glances-help>
	<template v-else>
		<!-- HEADER -->
		<header-section :data="data"></header-section>

		<!-- METRICS STRIP -->
		<section id="metrics" :class="metricsClass">
			<metrics-cpu v-if="!args.disable_cpu" :data="data"></metrics-cpu>
			<metrics-mem v-if="!args.disable_mem" :data="data"></metrics-mem>
			<metrics-load v-if="!args.disable_load" :data="data"></metrics-load>
			<metrics-gpu v-if="!args.disable_gpu && hasGpu" :data="data"></metrics-gpu>
		</section>

		<!-- BODY: sidebar + main -->
		<div id="body" :class="{ 'no-sidebar': args.disable_left_sidebar }">
			<sidebar-section v-if="!args.disable_left_sidebar" :data="data"></sidebar-section>
			<main-process :data="data"></main-process>
		</div>

		<!-- FOOTER ALERTS -->
		<footer-alerts v-if="!args.disable_alert" :data="data"></footer-alerts>
	</template>
</template>

<script>
import hotkeys from "hotkeys-js";
import GlancesHelp from "./components/help.vue";
import HeaderSection from "./components/header-section.vue";
import MetricsCpu from "./components/metrics-cpu.vue";
import MetricsMem from "./components/metrics-mem.vue";
import MetricsLoad from "./components/metrics-load.vue";
import MetricsGpu from "./components/metrics-gpu.vue";
import SidebarSection from "./components/sidebar-section.vue";
import MainProcess from "./components/main-process.vue";
import FooterAlerts from "./components/footer-alerts.vue";
import { GlancesStats } from "./services.js";
import { store } from "./store.js";

export default {
	components: {
		GlancesHelp,
		HeaderSection,
		MetricsCpu,
		MetricsMem,
		MetricsLoad,
		MetricsGpu,
		SidebarSection,
		MainProcess,
		FooterAlerts,
	},
	data() {
		return { store };
	},
	computed: {
		args() { return this.store.args || {}; },
		config() { return this.store.config || {}; },
		data() { return this.store.data || {}; },
		dataLoaded() { return this.store.data !== undefined; },
		hasGpu() {
			return this.store.data?.stats?.gpu && this.store.data.stats.gpu.length > 0;
		},
		hasNpu() {
			return this.store.data?.stats?.npu && this.store.data.stats.npu.length > 0;
		},
		metricsClass() {
			const classes = [];
			if (this.args.disable_gpu || !this.hasGpu) classes.push('no-gpu');
			if (this.args.disable_load) classes.push('no-load');
			return classes.join(' ');
		},
		title() {
			const { data } = this;
			const title = (data.stats && data.stats.system && data.stats.system.hostname) || "";
			return title ? `${title} \u2014 Glances` : "Glances";
		},
	},
	watch: {
		title() {
			if (document) document.title = this.title;
		},
	},
	mounted() {
		const GLANCES = window.__GLANCES__ || {};
		const refreshTime = isFinite(GLANCES["refresh-time"])
			? parseInt(GLANCES["refresh-time"], 10)
			: undefined;
		GlancesStats.init(refreshTime);
		this.setupHotKeys();
	},
	beforeUnmount() {
		hotkeys.unbind();
	},
	methods: {
		setupHotKeys() {
			// Sort keys
			hotkeys("a", () => { this.store.args.sort_processes_key = null; });
			hotkeys("c", () => { this.store.args.sort_processes_key = "cpu_percent"; });
			hotkeys("m", () => { this.store.args.sort_processes_key = "memory_percent"; });
			hotkeys("u", () => { this.store.args.sort_processes_key = "username"; });
			hotkeys("p", () => { this.store.args.sort_processes_key = "name"; });
			hotkeys("o", () => { this.store.args.sort_processes_key = "cpu_num"; });
			hotkeys("i", () => { this.store.args.sort_processes_key = "io_counters"; });
			hotkeys("t", () => { this.store.args.sort_processes_key = "timemillis"; });

			// Toggle keys
			hotkeys("shift+A", () => { this.store.args.disable_amps = !this.store.args.disable_amps; });
			hotkeys("d", () => { this.store.args.disable_diskio = !this.store.args.disable_diskio; });
			hotkeys("shift+Q", () => { this.store.args.enable_irq = !this.store.args.enable_irq; });
			hotkeys("f", () => { this.store.args.disable_fs = !this.store.args.disable_fs; });
			hotkeys("j", () => { this.store.args.programs = !this.store.args.programs; });
			hotkeys("k", () => { this.store.args.disable_connections = !this.store.args.disable_connections; });
			hotkeys("n", () => { this.store.args.disable_network = !this.store.args.disable_network; });
			hotkeys("s", () => { this.store.args.disable_sensors = !this.store.args.disable_sensors; });
			hotkeys("2", () => { this.store.args.disable_left_sidebar = !this.store.args.disable_left_sidebar; });
			hotkeys("z", () => { this.store.args.disable_process = !this.store.args.disable_process; });
			hotkeys("shift+S", () => { this.store.args.process_short_name = !this.store.args.process_short_name; });
			hotkeys("shift+D", () => { this.store.args.disable_containers = !this.store.args.disable_containers; });
			hotkeys("b", () => { this.store.args.byte = !this.store.args.byte; });
			hotkeys("shift+B", () => {
				this.store.args.diskio_iops = !this.store.args.diskio_iops;
				if (this.store.args.diskio_iops) this.store.args.diskio_latency = false;
			});
			hotkeys("shift+L", () => {
				this.store.args.diskio_latency = !this.store.args.diskio_latency;
				if (this.store.args.diskio_latency) this.store.args.diskio_iops = false;
			});
			hotkeys("l", () => { this.store.args.disable_alert = !this.store.args.disable_alert; });
			hotkeys("1", () => { this.store.args.percpu = !this.store.args.percpu; });
			hotkeys("h", () => { this.store.args.help_tag = !this.store.args.help_tag; });
			hotkeys("shift+T", () => { this.store.args.network_sum = !this.store.args.network_sum; });
			hotkeys("shift+U", () => { this.store.args.network_cumul = !this.store.args.network_cumul; });
			hotkeys("shift+F", () => { this.store.args.fs_free_space = !this.store.args.fs_free_space; });
			hotkeys("3", () => { this.store.args.disable_quicklook = !this.store.args.disable_quicklook; });
			hotkeys("6", () => { this.store.args.meangpu = !this.store.args.meangpu; });
			hotkeys("7", () => { this.store.args.disable_npu = !this.store.args.disable_npu; });
			hotkeys("shift+G", () => { this.store.args.disable_gpu = !this.store.args.disable_gpu; });
			hotkeys("5", () => {
				this.store.args.disable_quicklook = !this.store.args.disable_quicklook;
				this.store.args.disable_cpu = !this.store.args.disable_cpu;
				this.store.args.disable_mem = !this.store.args.disable_mem;
				this.store.args.disable_memswap = !this.store.args.disable_memswap;
				this.store.args.disable_load = !this.store.args.disable_load;
				this.store.args.disable_gpu = !this.store.args.disable_gpu;
				this.store.args.disable_npu = !this.store.args.disable_npu;
			});
			hotkeys("shift+I", () => { this.store.args.disable_ip = !this.store.args.disable_ip; });
			hotkeys("shift+P", () => { this.store.args.disable_ports = !this.store.args.disable_ports; });
			hotkeys("shift+V", () => { this.store.args.disable_vms = !this.store.args.disable_vms; });
			hotkeys("shift+W", () => { this.store.args.disable_wifi = !this.store.args.disable_wifi; });
			hotkeys("0", () => { this.store.args.disable_irix = !this.store.args.disable_irix; });
		},
	},
};
</script>

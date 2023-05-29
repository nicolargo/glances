<template>
    <div v-if="!dataLoaded" class="container-fluid" id="loading-page">
        <div class="glances-logo"></div>
        <div class="loader">Loading...</div>
    </div>
    <glances-help v-else-if="args.help_tag"></glances-help>
    <main v-else>
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-24">
                    <div class="pull-left">
                        <glances-plugin-system :data="data"></glances-plugin-system>
                    </div>
                    <div class="pull-left" v-if="!args.disable_ip">
                        <glances-plugin-ip :data="data"></glances-plugin-ip>
                    </div>
                    <div class="pull-right">
                        <glances-plugin-uptime :data="data"></glances-plugin-uptime>
                    </div>
                </div>
            </div>
        </div>
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-24">
                    <div class="pull-left">
                        <glances-plugin-cloud :data="data"></glances-plugin-cloud>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="hidden-xs hidden-sm hidden-md col-lg-6" v-if="!args.disable_quicklook">
                    <glances-plugin-quicklook :data="data"></glances-plugin-quicklook>
                </div>
                <div class="col-sm-6 col-md-8 col-lg-6" v-if="!args.disable_cpu && !args.percpu">
                    <glances-plugin-cpu :data="data"></glances-plugin-cpu>
                </div>
                <div class="col-sm-12 col-md-8 col-lg-6" v-if="!args.disable_cpu && args.percpu">
                    <glances-plugin-percpu :data="data"></glances-plugin-percpu>
                </div>
                <div class="col-sm-6 col-md-4 col-lg-3" v-if="!args.disable_gpu && hasGpu">
                    <glances-plugin-gpu :data="data"></glances-plugin-gpu>
                </div>
                <div class="col-sm-6 col-md-4 col-lg-3" v-if="!args.disable_mem">
                    <glances-plugin-mem :data="data"></glances-plugin-mem>
                </div>
                <!-- NOTE: display if MEM enabled and GPU disabled -->
                <div
                    v-if="!args.disable_mem && !(!args.disable_gpu && hasGpu)"
                    class="hidden-xs hidden-sm col-md-4 col-lg-3"
                >
                    <glances-plugin-mem-more :data="data"></glances-plugin-mem-more>
                </div>
                <div class="col-sm-6 col-md-4 col-lg-3" v-if="!args.disable_memswap">
                    <glances-plugin-memswap :data="data"></glances-plugin-memswap>
                </div>
                <div class="col-sm-6 col-md-4 col-lg-3" v-if="!args.disable_load">
                    <glances-plugin-load :data="data"></glances-plugin-load>
                </div>
            </div>
        </div>
        <div class="container-fluid">
            <div class="row">
                <div class="col-sm-6 sidebar" v-if="!args.disable_left_sidebar">
                    <div class="table">
                        <glances-plugin-network
                            id="plugin-network"
                            class="plugin table-row-group"
                            v-if="!args.disable_network"
                            :data="data"
                        ></glances-plugin-network>
                        <glances-plugin-connections
                            id="plugin-connections"
                            class="plugin table-row-group"
                            v-if="isLinux && !args.disable_connections"
                            :data="data"
                        ></glances-plugin-connections>
                        <glances-plugin-wifi
                            id="plugin-wifi"
                            class="plugin table-row-group"
                            v-if="!args.disable_wifi"
                            :data="data"
                        ></glances-plugin-wifi>
                        <glances-plugin-ports
                            id="plugin-ports"
                            class="plugin table-row-group"
                            v-if="!args.disable_ports"
                            :data="data"
                        ></glances-plugin-ports>
                        <glances-plugin-diskio
                            id="plugin-diskio"
                            class="plugin table-row-group"
                            v-if="!args.disable_diskio"
                            :data="data"
                        ></glances-plugin-diskio>
                        <glances-plugin-fs
                            id="plugin-fs"
                            class="plugin table-row-group"
                            v-if="!args.disable_fs"
                            :data="data"
                        ></glances-plugin-fs>
                        <glances-plugin-irq
                            id="plugin-irq"
                            class="plugin table-row-group"
                            v-if="!args.disable_irq"
                            :data="data"
                        ></glances-plugin-irq>
                        <glances-plugin-smart
                            id="plugin-smart"
                            class="plugin table-row-group"
                            v-if="!args.disable_smart"
                            :data="data"
                        ></glances-plugin-smart>
                        <glances-plugin-folders
                            id="plugin-folders"
                            class="plugin table-row-group"
                            v-if="!args.disable_folders"
                            :data="data"
                        ></glances-plugin-folders>
                        <glances-plugin-raid
                            id="plugin-raid"
                            class="plugin table-row-group"
                            v-if="!args.raid"
                            :data="data"
                        ></glances-plugin-raid>
                        <glances-plugin-sensors
                            id="plugin-sensors"
                            class="plugin table-row-group"
                            v-if="!args.disable_sensors"
                            :data="data"
                        ></glances-plugin-sensors>
                        <glances-plugin-now
                            id="plugin-now"
                            class="plugin table-row-group"
                            :data="data"
                        ></glances-plugin-now>
                    </div>
                </div>
                <div class="col-sm-18">
                    <glances-plugin-containers
                        v-if="!args.disable_containers"
                        :data="data"
                    ></glances-plugin-containers>
                    <glances-plugin-process :data="data"></glances-plugin-process>
                    <glances-plugin-alert
                        v-if="!args.disable_alert"
                        :data="data"
                    ></glances-plugin-alert>
                </div>
            </div>
        </div>
    </main>
</template>

<script>
import hotkeys from 'hotkeys-js';
import { GlancesStats } from './services.js';
import { store } from './store.js';

import GlancesHelp from './components/help.vue';
import GlancesPluginAlert from './components/plugin-alert.vue';
import GlancesPluginCloud from './components/plugin-cloud.vue';
import GlancesPluginConnections from './components/plugin-connections.vue';
import GlancesPluginCpu from './components/plugin-cpu.vue';
import GlancesPluginDiskio from './components/plugin-diskio.vue';
import GlancesPluginContainers from './components/plugin-containers.vue';
import GlancesPluginFolders from './components/plugin-folders.vue';
import GlancesPluginFs from './components/plugin-fs.vue';
import GlancesPluginGpu from './components/plugin-gpu.vue';
import GlancesPluginIp from './components/plugin-ip.vue';
import GlancesPluginIrq from './components/plugin-irq.vue';
import GlancesPluginLoad from './components/plugin-load.vue';
import GlancesPluginMem from './components/plugin-mem.vue';
import GlancesPluginMemMore from './components/plugin-mem-more.vue';
import GlancesPluginMemswap from './components/plugin-memswap.vue';
import GlancesPluginNetwork from './components/plugin-network.vue';
import GlancesPluginNow from './components/plugin-now.vue';
import GlancesPluginPercpu from './components/plugin-percpu.vue';
import GlancesPluginPorts from './components/plugin-ports.vue';
import GlancesPluginProcess from './components/plugin-process.vue';
import GlancesPluginQuicklook from './components/plugin-quicklook.vue';
import GlancesPluginRaid from './components/plugin-raid.vue';
import GlancesPluginSmart from './components/plugin-smart.vue';
import GlancesPluginSensors from './components/plugin-sensors.vue';
import GlancesPluginSystem from './components/plugin-system.vue';
import GlancesPluginUptime from './components/plugin-uptime.vue';
import GlancesPluginWifi from './components/plugin-wifi.vue';

export default {
    components: {
        GlancesHelp,
        GlancesPluginAlert,
        GlancesPluginCloud,
        GlancesPluginConnections,
        GlancesPluginCpu,
        GlancesPluginDiskio,
        GlancesPluginContainers,
        GlancesPluginFolders,
        GlancesPluginFs,
        GlancesPluginGpu,
        GlancesPluginIp,
        GlancesPluginIrq,
        GlancesPluginLoad,
        GlancesPluginMem,
        GlancesPluginMemMore,
        GlancesPluginMemswap,
        GlancesPluginNetwork,
        GlancesPluginNow,
        GlancesPluginPercpu,
        GlancesPluginPorts,
        GlancesPluginProcess,
        GlancesPluginQuicklook,
        GlancesPluginRaid,
        GlancesPluginSensors,
        GlancesPluginSmart,
        GlancesPluginSystem,
        GlancesPluginUptime,
        GlancesPluginWifi
    },
    data() {
        return {
            store
        };
    },
    computed: {
        args() {
            return this.store.args || {};
        },
        data() {
            return this.store.data || {};
        },
        dataLoaded() {
            return this.store.data !== undefined;
        },
        hasGpu() {
            return this.store.data.stats.gpu.length > 0;
        },
        isLinux() {
            return this.store.data.isLinux;
        },
        title() {
            const { data } = this;
            const title = (data.stats && data.stats.system && data.stats.system.hostname) || '';
            return title ? `${title} - Glances` : 'Glances';
        }
    },
    watch: {
        title() {
            if (document) {
                document.title = this.title;
            }
        }
    },
    methods: {
        setupHotKeys() {
            // a => Sort processes/containers automatically
            hotkeys('a', () => {
                this.store.args.sort_processes_key = null;
            });

            // c => Sort processes/containers by CPU%
            hotkeys('c', () => {
                this.store.args.sort_processes_key = 'cpu_percent';
            });

            // m => Sort processes/containers by MEM%
            hotkeys('m', () => {
                this.store.args.sort_processes_key = 'memory_percent';
            });

            // u => Sort processes/containers by user
            hotkeys('u', () => {
                this.store.args.sort_processes_key = 'username';
            });

            // p => Sort processes/containers by name
            hotkeys('p', () => {
                this.store.args.sort_processes_key = 'name';
            });

            // i => Sort processes/containers by I/O rate
            hotkeys('i', () => {
                this.store.args.sort_processes_key = 'io_counters';
            });

            // t => Sort processes/containers by time
            hotkeys('t', () => {
                this.store.args.sort_processes_key = 'timemillis';
            });

            // A => Enable/disable AMPs
            hotkeys('shift+A', () => {
                this.store.args.disable_amps = !this.store.args.disable_amps;
            });

            // d => Show/hide disk I/O stats
            hotkeys('d', () => {
                this.store.args.disable_diskio = !this.store.args.disable_diskio;
            });

            // Q => Show/hide IRQ
            hotkeys('shift+Q', () => {
                this.store.args.enable_irq = !this.store.args.enable_irq;
            });

            // f => Show/hide filesystem stats
            hotkeys('f', () => {
                this.store.args.disable_fs = !this.store.args.disable_fs;
            });

            // j => Accumulate processes by program
            hotkeys('j', () => {
                this.store.args.programs = !this.store.args.programs;
            });

            // k => Show/hide connections stats
            hotkeys('k', () => {
                this.store.args.disable_connections = !this.store.args.disable_connections;
            });

            // n => Show/hide network stats
            hotkeys('n', () => {
                this.store.args.disable_network = !this.store.args.disable_network;
            });

            // s => Show/hide sensors stats
            hotkeys('s', () => {
                this.store.args.disable_sensors = !this.store.args.disable_sensors;
            });

            // 2 => Show/hide left sidebar
            hotkeys('2', () => {
                this.store.args.disable_left_sidebar = !this.store.args.disable_left_sidebar;
            });

            // z => Enable/disable processes stats
            hotkeys('z', () => {
                this.store.args.disable_process = !this.store.args.disable_process;
            });

            // SLASH => Enable/disable short processes name
            hotkeys('/', () => {
                this.store.args.process_short_name = !this.store.args.process_short_name;
            });

            // D => Enable/disable containers stats
            hotkeys('shift+D', () => {
                this.store.args.disable_containers = !this.store.args.disable_containers;
            });

            // b => Bytes or bits for network I/O
            hotkeys('b', () => {
                this.store.args.byte = !this.store.args.byte;
            });

            // 'B' => Switch between bit/s and IO/s for Disk IO
            hotkeys('shift+B', () => {
                this.store.args.diskio_iops = !this.store.args.diskio_iops;
            });

            // l => Show/hide alert logs
            hotkeys('l', () => {
                this.store.args.disable_alert = !this.store.args.disable_alert;
            });

            // 1 => Global CPU or per-CPU stats
            hotkeys('1', () => {
                this.store.args.percpu = !this.store.args.percpu;
            });

            // h => Show/hide this help screen
            hotkeys('h', () => {
                this.store.args.help_tag = !this.store.args.help_tag;
            });

            // T => View network I/O as combination
            hotkeys('shift+T', () => {
                this.store.args.network_sum = !this.store.args.network_sum;
            });

            // U => View cumulative network I/O
            hotkeys('shift+U', () => {
                this.store.args.network_cumul = !this.store.args.network_cumul;
            });

            // F => Show filesystem free space
            hotkeys('shift+F', () => {
                this.store.args.fs_free_space = !this.store.args.fs_free_space;
            });

            // 3 => Enable/disable quick look plugin
            hotkeys('3', () => {
                this.store.args.disable_quicklook = !this.store.args.disable_quicklook;
            });

            // 6 => Enable/disable mean gpu
            hotkeys('6', () => {
                this.store.args.meangpu = !this.store.args.meangpu;
            });

            // G => Enable/disable gpu
            hotkeys('shift+G', () => {
                this.store.args.disable_gpu = !this.store.args.disable_gpu;
            });

            hotkeys('5', () => {
                this.store.args.disable_quicklook = !this.store.args.disable_quicklook;
                this.store.args.disable_cpu = !this.store.args.disable_cpu;
                this.store.args.disable_mem = !this.store.args.disable_mem;
                this.store.args.disable_memswap = !this.store.args.disable_memswap;
                this.store.args.disable_load = !this.store.args.disable_load;
                this.store.args.disable_gpu = !this.store.args.disable_gpu;
            });

            // I => Show/hide IP module
            hotkeys('shift+I', () => {
                this.store.args.disable_ip = !this.store.args.disable_ip;
            });

            // P => Enable/disable ports module
            hotkeys('shift+P', () => {
                this.store.args.disable_ports = !this.store.args.disable_ports;
            });

            // 'W' > Enable/Disable Wifi plugin
            hotkeys('shift+W', () => {
                this.store.args.disable_wifi = !this.store.args.disable_wifi;
            });
        }
    },
    mounted() {
        const GLANCES = window.__GLANCES__ || {};
        const refreshTime = isFinite(GLANCES['refresh-time'])
            ? parseInt(GLANCES['refresh-time'], 10)
            : undefined;
        GlancesStats.init(refreshTime);
        this.setupHotKeys();
    },
    beforeUnmount() {
        hotkeys.unbind();
    }
};
</script>
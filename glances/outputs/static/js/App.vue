<template>
    <div v-if="!dataLoaded" id="loading-page" class="container-fluid">
        <div class="loader">Glances is loading...</div>
    </div>
    <glances-help v-else-if="args.help_tag"></glances-help>
    <main v-else>
        <!-- Display minimal header on low screen size (smarthphone) -->
        <div class="d-sm-none">
            <div class="header-small">
                <div v-if="!args.disable_system"><glances-plugin-hostname :data="data"></glances-plugin-hostname></div>
                <div v-if="!args.disable_uptime"><glances-plugin-uptime :data="data"></glances-plugin-uptime></div>
            </div>
        </div>
        <!-- Display standard header on others screen sizes -->
        <div class="d-none d-sm-block">
            <div class="header d-flex justify-content-between flex-row">
                <div v-if="!args.disable_system" class=""><glances-plugin-system :data="data"></glances-plugin-system>
                </div>
                <div v-if="!args.disable_ip" class="d-none d-lg-block"><glances-plugin-ip
                        :data="data"></glances-plugin-ip>
                </div>
                <div v-if="!args.disable_now" class="d-none d-xl-block"><glances-plugin-now
                        :data="data"></glances-plugin-now></div>
                <div v-if="!args.disable_uptime" class="d-none d-md-block"><glances-plugin-uptime
                        :data="data"></glances-plugin-uptime></div>
            </div>
        </div>
        <div class="d-flex d-none d-sm-block">
            <div v-if="!args.disable_cloud">
                <glances-plugin-cloud :data="data"></glances-plugin-cloud>
            </div>
        </div>
        <!-- Display top menu with CPU, MEM, LOAD...-->
        <div class="top d-flex justify-content-between flex-row">
            <!-- Quicklook -->
            <div v-if="!args.disable_quicklook" class="d-none d-md-block">
                <glances-plugin-quicklook :data="data"></glances-plugin-quicklook>
            </div>
            <!-- CPU -->
            <div v-if="!args.disable_cpu || !args.percpu" class="">
                <glances-plugin-cpu :data="data"></glances-plugin-cpu>
            </div>
            <!-- TODO: percpu need to be refactor
                <div class="col"
                        v-if="!args.disable_cpu && !args.percpu">
                    <glances-plugin-cpu :data="data"></glances-plugin-cpu>
                </div>
                <div class="col"
                        v-if="!args.disable_cpu && args.percpu">
                    <glances-plugin-percpu :data="data"></glances-plugin-percpu>
                </div> -->

            <!-- GPU -->
            <div v-if="!args.disable_gpu && hasGpu" class="d-none d-xl-block">
                <glances-plugin-gpu :data="data"></glances-plugin-gpu>
            </div>
            <!-- MEM -->
            <div v-if="!args.disable_mem" class="">
                <glances-plugin-mem :data="data"></glances-plugin-mem>
            </div>
            <!-- SWAP -->
            <div v-if="!args.disable_memswap" class="d-none d-lg-block">
                <glances-plugin-memswap :data="data"></glances-plugin-memswap>
            </div>
            <!-- LOAD -->
            <div v-if="!args.disable_load" class="d-none d-sm-block">
                <glances-plugin-load :data="data"></glances-plugin-load>
            </div>
        </div>
        <!-- Display bottom of the screen with sidebar and processlist -->
        <div class="bottom container-fluid">
            <div class="row">
                <div v-if="!args.disable_left_sidebar" class="col-3 d-none d-md-block"
                    :class="{ 'sidebar-min': !args.percpu, 'sidebar-max': args.percpu }">
                    <template v-for="plugin in leftMenu">
                        <component :is="`glances-plugin-${plugin}`" v-if="!args[`disable_${plugin}`]" :id="`${plugin}`"
                            :data="data">
                        </component>
                    </template>
                </div>
                <div class="col" :class="{ 'sidebar-min': !args.percpu, 'sidebar-max': args.percpu }">
                    <glances-plugin-vms v-if="!args.disable_vms" :data="data"></glances-plugin-vms>
                    <glances-plugin-containers v-if="!args.disable_containers" :data="data"></glances-plugin-containers>
                    <glances-plugin-process :data="data"></glances-plugin-process>
                    <glances-plugin-alert v-if="!args.disable_alert" :data="data"></glances-plugin-alert>
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
import GlancesPluginHostname from './components/plugin-hostname.vue';
import GlancesPluginIp from './components/plugin-ip.vue';
import GlancesPluginIrq from './components/plugin-irq.vue';
import GlancesPluginLoad from './components/plugin-load.vue';
import GlancesPluginMem from './components/plugin-mem.vue';
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
import GlancesPluginVms from './components/plugin-vms.vue';
import GlancesPluginWifi from './components/plugin-wifi.vue';

import uiconfig from './uiconfig.json';

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
        GlancesPluginHostname,
        GlancesPluginIp,
        GlancesPluginIrq,
        GlancesPluginLoad,
        GlancesPluginMem,
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
        GlancesPluginVms,
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
        config() {
            return this.store.config || {};
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
        },
        leftMenu() {
            return this.config.outputs !== undefined && this.config.outputs.left_menu !== undefined
                ? this.config.outputs.left_menu.split(',')
                : uiconfig.leftMenu;
        }
    },
    watch: {
        title() {
            if (document) {
                document.title = this.title;
            }
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

            // S => Enable/disable short processes name
            hotkeys('shift+S', () => {
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

            // V => Enable/disable VMs stats
            hotkeys('shift+V', () => {
                this.store.args.disable_vms = !this.store.args.disable_vms;
            });

            // 'W' > Enable/Disable Wifi plugin
            hotkeys('shift+W', () => {
                this.store.args.disable_wifi = !this.store.args.disable_wifi;
            });

            // 0 => Enable/disable IRIX mode (see issue #3158)
            hotkeys('0', () => {
                this.store.args.disable_irix = !this.store.args.disable_irix;
            });
        }
    }
};
</script>
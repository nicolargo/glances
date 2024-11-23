<template>
    <section class="plugin" id="processlist" v-if="!args.programs">
        <!-- Display processes -->
        <table class="table table-sm table-borderless table-striped table-hover">
            <thead>
                <tr>
                    <td scope="col" :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                        @click="$emit('update:sorter', 'cpu_percent')"
                        v-show="!getDisableStats().includes('cpu_percent')">
                        CPU%
                    </td>
                    <td scope="col" :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                        @click="$emit('update:sorter', 'memory_percent')"
                        v-show="!getDisableStats().includes('memory_percent')">
                        MEM%
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('memory_info')">
                        VIRT
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('memory_info')">
                        RES
                    </td>
                    <td scope="col" v-show="!getDisableStats().includes('pid')">
                        PID
                    </td>
                    <td scope="col" :class="['sortable', sorter.column === 'username' && 'sort']"
                        @click="$emit('update:sorter', 'username')" v-show="!getDisableStats().includes('username')">
                        USER
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'timemillis' && 'sort']"
                        @click="$emit('update:sorter', 'timemillis')" v-show="!getDisableStats().includes('cpu_times')">
                        TIME+
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'num_threads' && 'sort']"
                        @click="$emit('update:sorter', 'num_threads')"
                        v-show="!getDisableStats().includes('num_threads')">
                        THR
                    </td>
                    <td scope="col" v-show="!getDisableStats().includes('nice')">NI</td>
                    <td scope="col" class="table-cell widtd-60" v-show="!getDisableStats().includes('status')">S
                    </td>
                    <td scope="col" v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')"
                        class="hidden-xs hidden-sm" :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                        @click="$emit('update:sorter', 'io_counters')">
                        IOR/s
                    </td>
                    <td scope="col" v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')"
                        class="text-start hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                        @click="$emit('update:sorter', 'io_counters')">
                        IOW/s
                    </td>
                    <td scope="col" :class="['sortable', sorter.column === 'name' && 'sort']"
                        @click="$emit('update:sorter', 'name')" v-show="!getDisableStats().includes('cmdline')">
                        Command
                    </td>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(process, processId) in processes" :key="processId">
                    <td scope="row" :class="getCpuPercentAlert(process)"
                        v-show="!getDisableStats().includes('cpu_percent')">
                        {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent, 1) }}
                    </td>
                    <td scope="row" :class="getMemoryPercentAlert(process)"
                        v-show="!getDisableStats().includes('memory_percent')">
                        {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('memory_info')">
                        {{ $filters.bytes(process.memvirt) }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('memory_info')">
                        {{ $filters.bytes(process.memres) }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('pid')">
                        {{ process.pid }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('username')">
                        {{ process.username }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('cpu_times')">
                        {{ process.timeforhuman }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-if="process.timeplus == '?'"
                        v-show="!getDisableStats().includes('cpu_times')">?</td>
                    <td scope="row" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('num_threads')">
                        {{ process.num_threads == -1 ? '?' : process.num_threads }}
                    </td>
                    <td scope="row" :class="{ nice: process.isNice }" v-show="!getDisableStats().includes('nice')">
                        {{ $filters.exclamation(process.nice) }}
                    </td>
                    <td scope="row" :class="{ status: process.status == 'R' }"
                        v-show="!getDisableStats().includes('status')">
                        {{ process.status }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')">
                        {{ $filters.bytes(process.io_read) }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')">
                        {{ $filters.bytes(process.io_write) }}
                    </td>
                    <td scope="row" class="text-truncate"
                        v-show="args.process_short_name && !getDisableStats().includes('cmdline')">
                        {{ process.name }}
                    </td>
                    <td scope="row" v-show="!args.process_short_name && !getDisableStats().includes('cmdline')">
                        {{ process.cmdline }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
    <section class="plugin" id="processlist" v-if="args.programs">
        <!-- Display programs -->
        <table class=" table table-sm table-borderless table-striped table-hover">
            <thead>
                <tr>
                    <td scope="col" :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                        @click="$emit('update:sorter', 'cpu_percent')"
                        v-show="!getDisableStats().includes('cpu_percent')">
                        CPU%
                    </td>
                    <td scope="col" :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                        @click="$emit('update:sorter', 'memory_percent')"
                        v-show="!getDisableStats().includes('memory_percent')">
                        MEM%
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('memory_info')">
                        VIRT
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('memory_info')">
                        RES
                    </td>
                    <td scope="col" v-show="!getDisableStats().includes('nprocs')">
                        NPROCS
                    </td>
                    <td scope="row" :class="['sortable', sorter.column === 'username' && 'sort']"
                        @click="$emit('update:sorter', 'username')" v-show="!getDisableStats().includes('username')">
                        USER
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'timemillis' && 'sort']"
                        @click="$emit('update:sorter', 'timemillis')" v-show="!getDisableStats().includes('cpu_times')">
                        TIME+
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'num_threads' && 'sort']"
                        @click="$emit('update:sorter', 'num_threads')"
                        v-show="!getDisableStats().includes('num_threads')">
                        THR
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('nice')">NI</td>
                    <td scope="row" class="table-cell widtd-60" v-show="!getDisableStats().includes('status')">S
                    </td>
                    <td scope="row" v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')"
                        class="hidden-xs hidden-sm" :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                        @click="$emit('update:sorter', 'io_counters')">
                        IOR/s
                    </td>
                    <td scope="row" v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')"
                        class="text-start hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                        @click="$emit('update:sorter', 'io_counters')">
                        IOW/s
                    </td>
                    <td scope="row" :class="['sortable', sorter.column === 'name' && 'sort']"
                        @click="$emit('update:sorter', 'name')" v-show="!getDisableStats().includes('cmdline')">
                        Command
                    </td>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(process, processId) in programs" :key="processId">
                    <td scope="row" :class="getCpuPercentAlert(process)"
                        v-show="!getDisableStats().includes('cpu_percent')">
                        {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent, 1) }}
                    </td>
                    <td scope="row" :class="getMemoryPercentAlert(process)"
                        v-show="!getDisableStats().includes('memory_percent')">
                        {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('memory_info')">
                        {{ $filters.bytes(process.memvirt) }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('memory_info')">
                        {{ $filters.bytes(process.memres) }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('nprocs')">
                        {{ process.nprocs }}
                    </td>
                    <td scope="row" v-show="!getDisableStats().includes('username')">
                        {{ process.username }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('cpu_times')">
                        {{ process.timeforhuman }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-show="!getDisableStats().includes('num_threads')">
                        {{ process.num_threads == -1 ? '?' : process.num_threads }}
                    </td>
                    <td scope="row" :class="{ nice: process.isNice }" v-show="!getDisableStats().includes('nice')">
                        {{ $filters.exclamation(process.nice) }}
                    </td>
                    <td scope="row" :class="{ status: process.status == 'R' }"
                        v-show="!getDisableStats().includes('status')">
                        {{ process.status }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')">
                        {{ $filters.bytes(process.io_read) }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')">
                        {{ $filters.bytes(process.io_write) }}
                    </td>
                    <td scope="row" class="text-truncate"
                        v-show="args.process_short_name && !getDisableStats().includes('cmdline')">
                        {{ process.name }}
                    </td>
                    <td scope="row" v-show="!args.process_short_name && !getDisableStats().includes('cmdline')">
                        {{ process.cmdline }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
</template>

<script>
import { orderBy, last } from 'lodash';
import { timemillis, timedelta } from '../filters.js';
import { GlancesHelper } from '../services.js';
import { store } from '../store.js';

export default {
    props: {
        data: {
            type: Object
        },
        sorter: {
            type: Object
        }
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
        stats_processlist() {
            return this.data.stats['processlist'];
        },
        processes() {
            const { sorter } = this;
            const isWindows = this.data.stats['isWindows'];
            const processes = (this.stats_processlist || []).map((process) => {
                process.memvirt = '?';
                process.memres = '?';
                if (process.memory_info) {
                    process.memvirt = process.memory_info.vms;
                    process.memres = process.memory_info.rss;
                }

                if (isWindows && process.username !== null) {
                    process.username = last(process.username.split('\\'));
                }

                process.timeforhuman = '?';
                if (process.cpu_times) {
                    process.timeplus = timedelta([process.cpu_times['user'], process.cpu_times['system']]);
                    process.timeforhuman = process.timeplus.hours.toString().padStart(2, '0') + ':' +
                        process.timeplus.minutes.toString().padStart(2, '0') + ':' +
                        process.timeplus.seconds.toString().padStart(2, '0')
                }

                if (process.num_threads === null) {
                    process.num_threads = -1;
                }

                if (process.cpu_percent === null) {
                    process.cpu_percent = -1;
                }

                if (process.memory_percent === null) {
                    process.memory_percent = -1;
                }

                process.io_read = null;
                process.io_write = null;

                if (process.io_counters) {
                    process.io_read =
                        (process.io_counters[0] - process.io_counters[2]) /
                        process.time_since_update;
                    process.io_write =
                        (process.io_counters[1] - process.io_counters[3]) /
                        process.time_since_update;
                }

                process.isNice =
                    process.nice !== undefined &&
                    ((isWindows && process.nice != 32) || (!isWindows && process.nice != 0));

                if (Array.isArray(process.cmdline)) {
                    process.cmdline = process.cmdline.join(' ').replace(/\n/g, ' ');
                }

                if (process.cmdline === null || process.cmdline.length === 0) {
                    process.cmdline = process.name;
                }

                return process;
            });

            return orderBy(
                processes,
                [sorter.column].reduce((retval, col) => {
                    if (col === 'io_counters') {
                        col = ['io_read', 'io_write']
                    }
                    return retval.concat(col);
                }, []),
                [sorter.isReverseColumn(sorter.column) ? 'desc' : 'asc']
            ).slice(0, this.limit);
        },
        ioReadWritePresentProcesses() {
            return (this.stats_processlist || []).some(({ io_counters }) => io_counters);
        },
        stats_programlist() {
            return this.data.stats['programlist'];
        },
        programs() {
            const { sorter } = this;
            const isWindows = this.data.stats['isWindows'];
            const programs = (this.stats_programlist || []).map((process) => {
                process.memvirt = '?';
                process.memres = '?';
                if (process.memory_info) {
                    process.memvirt = process.memory_info.vms;
                    process.memres = process.memory_info.rss;
                }

                if (isWindows && process.username !== null) {
                    process.username = last(process.username.split('\\'));
                }

                process.timeforhuman = '?';
                if (process.cpu_times) {
                    process.timeplus = timedelta([process.cpu_times['user'], process.cpu_times['system']]);
                    process.timeforhuman = process.timeplus.hours.toString().padStart(2, '0') + ':' +
                        process.timeplus.minutes.toString().padStart(2, '0') + ':' +
                        process.timeplus.seconds.toString().padStart(2, '0')
                }

                if (process.num_threads === null) {
                    process.num_threads = -1;
                }

                if (process.cpu_percent === null) {
                    process.cpu_percent = -1;
                }

                if (process.memory_percent === null) {
                    process.memory_percent = -1;
                }

                process.io_read = null;
                process.io_write = null;

                if (process.io_counters) {
                    process.io_read =
                        (process.io_counters[0] - process.io_counters[2]) /
                        process.time_since_update;
                    process.io_write =
                        (process.io_counters[1] - process.io_counters[3]) /
                        process.time_since_update;
                }

                process.isNice =
                    process.nice !== undefined &&
                    ((isWindows && process.nice != 32) || (!isWindows && process.nice != 0));

                if (Array.isArray(process.cmdline)) {
                    process.cmdline = process.cmdline.join(' ').replace(/\n/g, ' ');
                }

                if (process.cmdline === null || process.cmdline.length === 0) {
                    process.cmdline = process.name;
                }

                return process;
            });

            return orderBy(
                programs,
                [sorter.column].reduce((retval, col) => {
                    if (col === 'io_counters') {
                        col = ['io_read', 'io_write']
                    }
                    return retval.concat(col);
                }, []),
                [sorter.isReverseColumn(sorter.column) ? 'desc' : 'asc']
            ).slice(0, this.limit);
        },
        ioReadWritePresentPrograms() {
            return (this.stats_programlist || []).some(({ io_counters }) => io_counters);
        },
        limit() {
            return this.config.outputs !== undefined
                ? this.config.outputs.max_processes_display
                : undefined;
        }
    },
    methods: {
        getCpuPercentAlert(process) {
            return GlancesHelper.getAlert('processlist', 'processlist_cpu_', process.cpu_percent);
        },
        getMemoryPercentAlert(process) {
            return GlancesHelper.getAlert('processlist', 'processlist_mem_', process.cpu_percent);
        },
        getDisableStats() {
            return GlancesHelper.getLimit('processlist', 'processlist_disable_stats') || [];
        }
    }
};
</script>
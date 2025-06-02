<template>

    <!-- Display processes -->
    <section v-if="!args.programs" id="processlist" class="plugin">
        <div v-if="extended_stats !== null" class="extendedstats">
            <div>
                <span class="title">Pinned task: </span>
                <span>{{ $filters.limitTo(extended_stats.cmdline, 80) }}</span>
                <span><button class="button" @click="disableExtendedStats()">Unpin</button></span>
            </div>
            <div>
                <span>CPU Min/Max/Mean: </span>
                <span class="careful">{{ $filters.number(extended_stats.cpu_min, 1)
                }}% / {{
                        $filters.number(extended_stats.cpu_max, 1) }}% / {{ $filters.number(extended_stats.cpu_mean, 1)
                    }}%</span>
                <span>Affinity: </span>
                <span class="careful">{{ extended_stats.cpu_affinity | length }}</span>
            </div>
            <div>
                <span>MEM Min/Max/Mean: </span>
                <span class="careful">{{ $filters.number(extended_stats.memory_min, 1) }}% / {{
                    $filters.number(extended_stats.memory_max, 1) }}% / {{ $filters.number(extended_stats.memory_mean,
                        1)
                    }}%</span>
                <span>Memory info: </span>
                <span class="careful">
                    {{ $filters.dictToString(extended_stats.memory_info) }}
                </span>
            </div>
        </div>
        <div class="table-responsive d-lg-none">
            <table class="table table-sm table-borderless table-striped table-hover">
                <thead>
                    <tr>
                        <td v-show="!getDisableStats().includes('cpu_percent')" scope="col"
                            :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                            @click="$emit('update:sorter', 'cpu_percent')">
                            <span v-show="!args.disable_irix">CPU%</span>
                            <span v-show="args.disable_irix">CPUi</span>
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')" scope="col"
                            :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                            @click="$emit('update:sorter', 'memory_percent')">
                            MEM%
                        </td>
                        <td v-show="!getDisableStats().includes('pid')" scope="col">
                            PID
                        </td>
                        <td v-show="!getDisableStats().includes('username')" scope="col"
                            :class="['sortable', sorter.column === 'username' && 'sort']"
                            @click="$emit('update:sorter', 'username')">
                            USER
                        </td>
                        <td v-show="!getDisableStats().includes('cmdline')" scope="col"
                            :class="['sortable', sorter.column === 'name' && 'sort']"
                            @click="$emit('update:sorter', 'name')">
                            Command (click to pin)
                        </td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(process, processId) in processes" :key="processId" style="cursor: pointer"
                        @click="setExtendedStats(process)">
                        <td v-show="!getDisableStats().includes('cpu_percent')" scope="row"
                            :class="getCpuPercentAlert(process)">
                            {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent / process.irix, 1)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')" scope="row"
                            :class="getMemoryPercentAlert(process)">
                            {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                        </td>
                        <td v-show="!getDisableStats().includes('pid')" scope="row">
                            {{ process.pid }}
                        </td>
                        <td v-show="args.process_short_name && !getDisableStats().includes('cmdline')" scope="row"
                            class="text-truncate">
                            {{ process.name }}
                        </td>
                        <td v-show="!args.process_short_name && !getDisableStats().includes('cmdline')" scope="row"
                            class="text-truncate">
                            {{ process.cmdline }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="table-responsive-md d-none d-lg-block">
            <table class="table table-sm table-borderless table-striped table-hover">
                <thead>
                    <tr>
                        <td v-show="!getDisableStats().includes('cpu_percent')" scope="col"
                            :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                            @click="$emit('update:sorter', 'cpu_percent')">
                            <span v-show="!args.disable_irix">CPU%</span>
                            <span v-show="args.disable_irix">CPUi</span>
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')" scope="col"
                            :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                            @click="$emit('update:sorter', 'memory_percent')">
                            MEM%
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" scope="col">
                            VIRT
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" scope="col">
                            RES
                        </td>
                        <td v-show="!getDisableStats().includes('pid')" scope="col">
                            PID
                        </td>
                        <td v-show="!getDisableStats().includes('username')" scope="col"
                            :class="['sortable', sorter.column === 'username' && 'sort']"
                            @click="$emit('update:sorter', 'username')">
                            USER
                        </td>
                        <td v-show="!getDisableStats().includes('cpu_times')" scope="col"
                            :class="['sortable', sorter.column === 'timemillis' && 'sort']"
                            @click="$emit('update:sorter', 'timemillis')">
                            TIME+
                        </td>
                        <td v-show="!getDisableStats().includes('num_threads')" scope="col"
                            :class="['sortable', sorter.column === 'num_threads' && 'sort']"
                            @click="$emit('update:sorter', 'num_threads')">
                            THR
                        </td>
                        <td v-show="!getDisableStats().includes('nice')" scope="col">NI</td>
                        <td v-show="!getDisableStats().includes('status')" scope="col">S
                        </td>
                        <td v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')"
                            scope="col" class="" :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                            @click="$emit('update:sorter', 'io_counters')">
                            IORps
                        </td>
                        <td v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')"
                            scope="col" class="text-start"
                            :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                            @click="$emit('update:sorter', 'io_counters')">
                            IOWps
                        </td>
                        <td v-show="!getDisableStats().includes('cmdline')" scope="col"
                            :class="['sortable', sorter.column === 'name' && 'sort']"
                            @click="$emit('update:sorter', 'name')">
                            Command (click to pin)
                        </td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(process, processId) in processes" :key="processId" style="cursor: pointer"
                        @click="setExtendedStats(process.pid)">
                        <td v-show="!getDisableStats().includes('cpu_percent')" scope="row"
                            :class="getCpuPercentAlert(process)">
                            {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent / process.irix, 1)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')" scope="row"
                            :class="getMemoryPercentAlert(process)">
                            {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" scope="row">
                            {{ $filters.bytes(process.memvirt) }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" scope="row">
                            {{ $filters.bytes(process.memres) }}
                        </td>
                        <td v-show="!getDisableStats().includes('pid')" scope="row">
                            {{ process.pid }}
                        </td>
                        <td v-show="!getDisableStats().includes('username')" scope="row">
                            {{ process.username }}
                        </td>
                        <td v-show="!getDisableStats().includes('cpu_times')" scope="row" class="">
                            {{ process.timeforhuman }}
                        </td>
                        <td v-if="process.timeplus == '?'" v-show="!getDisableStats().includes('cpu_times')" scope="row"
                            class="">?</td>
                        <td v-show="!getDisableStats().includes('num_threads')" scope="row" class="">
                            {{ process.num_threads == -1 ? '?' : process.num_threads }}
                        </td>
                        <td v-show="!getDisableStats().includes('nice')" scope="row" :class="{ nice: process.isNice }">
                            {{ $filters.exclamation(process.nice) }}
                        </td>
                        <td v-show="!getDisableStats().includes('status')" scope="row"
                            :class="{ status: process.status == 'R' }">
                            {{ process.status }}
                        </td>
                        <td v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')"
                            scope="row" class="">
                            {{ $filters.bytes(process.io_read) }}
                        </td>
                        <td v-show="ioReadWritePresentProcesses && !getDisableStats().includes('io_counters')"
                            scope="row" class="text-start">
                            {{ $filters.bytes(process.io_write) }}
                        </td>
                        <td v-show="args.process_short_name && !getDisableStats().includes('cmdline')" scope="row"
                            class="text-truncate">
                            {{ process.name }}
                        </td>
                        <td v-show="!args.process_short_name && !getDisableStats().includes('cmdline')" scope="row"
                            class="text-truncate">
                            {{ process.cmdline }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>


    <!-- Display programs -->
    <section v-if="args.programs" id="processlist" class="plugin">
        <div class="table-responsive d-lg-none">
            <table class="table table-sm table-borderless table-striped table-hover">
                <thead>
                    <tr>
                        <td v-show="!getDisableStats().includes('cpu_percent')"
                            :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                            @click="$emit('update:sorter', 'cpu_percent')">
                            <span v-show="!args.disable_irix">CPU%</span>
                            <span v-show="args.disable_irix">CPUi</span>
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')"
                            :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                            @click="$emit('update:sorter', 'memory_percent')">
                            MEM%
                        </td>
                        <td v-show="!getDisableStats().includes('nprocs')">
                            NPROCS
                        </td>
                        <td v-show="!getDisableStats().includes('cmdline')" scope="row"
                            :class="['sortable', sorter.column === 'name' && 'sort']"
                            @click="$emit('update:sorter', 'name')">
                            Command (click to pin)
                        </td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(process, processId) in programs" :key="processId">
                        <td v-show="!getDisableStats().includes('cpu_percent')" scope="row"
                            :class="getCpuPercentAlert(process)">
                            {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent / process.irix, 1)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')" scope="row"
                            :class="getMemoryPercentAlert(process)">
                            {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                        </td>
                        <td v-show="!getDisableStats().includes('nprocs')" scope="row">
                            {{ process.nprocs }}
                        </td>
                        <td v-show="args.process_short_name && !getDisableStats().includes('cmdline')" scope="row"
                            class="text-truncate">
                            {{ process.name }}
                        </td>
                        <td v-show="!args.process_short_name && !getDisableStats().includes('cmdline')" scope="row">
                            {{ process.cmdline }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="table-responsive d-none d-lg-block">
            <table class="table table-sm table-borderless table-striped table-hover">
                <thead>
                    <tr>
                        <td v-show="!getDisableStats().includes('cpu_percent')"
                            :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                            @click="$emit('update:sorter', 'cpu_percent')">
                            <span v-show="!args.disable_irix">CPU%</span>
                            <span v-show="args.disable_irix">CPUi</span>
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')"
                            :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                            @click="$emit('update:sorter', 'memory_percent')">
                            MEM%
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" class="">
                            VIRT
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" class="">
                            RES
                        </td>
                        <td v-show="!getDisableStats().includes('nprocs')">
                            NPROCS
                        </td>
                        <td v-show="!getDisableStats().includes('username')" scope="row"
                            :class="['sortable', sorter.column === 'username' && 'sort']"
                            @click="$emit('update:sorter', 'username')">
                            USER
                        </td>
                        <td v-show="!getDisableStats().includes('cpu_times')" scope="row" class=""
                            :class="['sortable', sorter.column === 'timemillis' && 'sort']"
                            @click="$emit('update:sorter', 'timemillis')">
                            TIME+
                        </td>
                        <td v-show="!getDisableStats().includes('num_threads')" scope="row" class=""
                            :class="['sortable', sorter.column === 'num_threads' && 'sort']"
                            @click="$emit('update:sorter', 'num_threads')">
                            THR
                        </td>
                        <td v-show="!getDisableStats().includes('nice')" scope="row">NI</td>
                        <td v-show="!getDisableStats().includes('status')" scope="row" class="table-cell widtd-60">S
                        </td>
                        <td v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')"
                            scope="row" class="" :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                            @click="$emit('update:sorter', 'io_counters')">
                            IORps
                        </td>
                        <td v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')"
                            scope="row" class="text-start"
                            :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                            @click="$emit('update:sorter', 'io_counters')">
                            IOWps
                        </td>
                        <td v-show="!getDisableStats().includes('cmdline')" scope="row"
                            :class="['sortable', sorter.column === 'name' && 'sort']"
                            @click="$emit('update:sorter', 'name')">
                            Command (click to pin)
                        </td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(process, processId) in programs" :key="processId">
                        <td v-show="!getDisableStats().includes('cpu_percent')" scope="row"
                            :class="getCpuPercentAlert(process)">
                            {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent / process.irix, 1)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_percent')" scope="row"
                            :class="getMemoryPercentAlert(process)">
                            {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" scope="row">
                            {{ $filters.bytes(process.memvirt) }}
                        </td>
                        <td v-show="!getDisableStats().includes('memory_info')" scope="row">
                            {{ $filters.bytes(process.memres) }}
                        </td>
                        <td v-show="!getDisableStats().includes('nprocs')" scope="row">
                            {{ process.nprocs }}
                        </td>
                        <td v-show="!getDisableStats().includes('username')" scope="row">
                            {{ process.username }}
                        </td>
                        <td v-show="!getDisableStats().includes('cpu_times')" scope="row" class="">
                            {{ process.timeforhuman }}
                        </td>
                        <td v-show="!getDisableStats().includes('num_threads')" scope="row" class="">
                            {{ process.num_threads == -1 ? '?' : process.num_threads }}
                        </td>
                        <td v-show="!getDisableStats().includes('nice')" scope="row" :class="{ nice: process.isNice }">
                            {{ $filters.exclamation(process.nice) }}
                        </td>
                        <td v-show="!getDisableStats().includes('status')" scope="row"
                            :class="{ status: process.status == 'R' }">
                            {{ process.status }}
                        </td>
                        <td v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')"
                            scope="row" class="">
                            {{ $filters.bytes(process.io_read) }}
                        </td>
                        <td v-show="ioReadWritePresentPrograms && !getDisableStats().includes('io_counters')"
                            scope="row" class="text-start">
                            {{ $filters.bytes(process.io_write) }}
                        </td>
                        <td v-show="args.process_short_name && !getDisableStats().includes('cmdline')" scope="row"
                            class="text-truncate">
                            {{ process.name }}
                        </td>
                        <td v-show="!args.process_short_name && !getDisableStats().includes('cmdline')" scope="row">
                            {{ process.cmdline }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>
</template>

<script>
import { orderBy, last } from 'lodash';
import { timemillis, timedelta, limitTo, number, dictToString } from '../filters.js';
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
        stats_core() {
            return this.data.stats['core'];
        },
        cpucore() {
            return (this.stats_core['log'] !== 0) ? this.stats_core['log'] : 1;
        },
        extended_stats() {
            return this.stats_processlist.find(item => item['extended_stats'] === true) || null;
        },
        processes() {
            const { sorter } = this;
            const processes = (this.stats_processlist || []).map((process) => {
                return this.updateProcess(process, this.data.stats['isWindows'], this.args, this.cpucore);
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
        updateProcess(process, isWindows, args, cpucore) {
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

            process.irix = 1;
            if (process.cpu_percent === null) {
                process.cpu_percent = -1;
            } else {
                if (args.disable_irix) {
                    process.irix = cpucore
                }
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
                process.name = process.name + ' ' + process.cmdline.slice(1).join(' ').replace(/\n/g, ' ');
                process.cmdline = process.cmdline.join(' ').replace(/\n/g, ' ');
            }

            if (process.cmdline === null || process.cmdline.length === 0) {
                process.cmdline = process.name;
            }
            return process
        },
        getCpuPercentAlert(process) {
            return GlancesHelper.getAlert('processlist', 'processlist_cpu_', process.cpu_percent);
        },
        getMemoryPercentAlert(process) {
            return GlancesHelper.getAlert('processlist', 'processlist_mem_', process.cpu_percent);
        },
        getDisableStats() {
            return GlancesHelper.getLimit('processlist', 'processlist_disable_stats') || [];
        },
        setExtendedStats(pid) {
            fetch('api/4/processes/extended/' + pid.toString(), { method: 'POST' })
                .then((response) => response.json());
            this.$forceUpdate()
        },
        disableExtendedStats() {
            fetch('api/4/processes/extended/disable', { method: 'POST' })
                .then((response) => response.json());
            this.$forceUpdate()
        }
    }
};
</script>

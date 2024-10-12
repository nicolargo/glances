<template>
    <section class="plugin" id="processlist">
        <table class="table table-sm table-borderless table-striped table-hover">
            <thead>
                <tr>
                    <td scope="col"
                        :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                        @click="$emit('update:sorter', 'cpu_percent')">
                        CPU%
                    </td>
                    <td scope="col"
                        :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                        @click="$emit('update:sorter', 'memory_percent')">
                        MEM%
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm">
                        VIRT
                    </td>
                    <td scope="col" class="hidden-xs hidden-sm">
                        RES
                    </td>
                    <td scope="col">
                        PID
                    </td>
                    <td scope="row" :class="['sortable', sorter.column === 'username' && 'sort']"
                        @click="$emit('update:sorter', 'username')">
                        USER
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'timemillis' && 'sort']"
                        @click="$emit('update:sorter', 'timemillis')">
                        TIME+
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'num_threads' && 'sort']"
                        @click="$emit('update:sorter', 'num_threads')">
                        THR
                    </td>
                    <td scope="row">NI</td>
                    <td scope="row" class="table-cell widtd-60">S</td>
                    <td scope="row"
                        v-show="ioReadWritePresent"
                        class="hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                        @click="$emit('update:sorter', 'io_counters')">
                        IOR/s
                    </td>
                    <td scope="row"
                        v-show="ioReadWritePresent" class="text-start hidden-xs hidden-sm"
                        :class="['sortable', sorter.column === 'io_counters' && 'sort']"
                        @click="$emit('update:sorter', 'io_counters')">
                        IOW/s
                    </td>
                    <td scope="row"
                        :class="['sortable', sorter.column === 'name' && 'sort']"
                        @click="$emit('update:sorter', 'name')">
                        Command
                    </td>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(process, processId) in processes" :key="processId">
                    <td scope="row" :class="getCpuPercentAlert(process)">
                        {{ process.cpu_percent == -1 ? '?' : $filters.number(process.cpu_percent, 1) }}
                    </td>
                    <td scope="row" :class="getMemoryPercentAlert(process)">
                        {{ process.memory_percent == -1 ? '?' : $filters.number(process.memory_percent, 1) }}
                    </td>
                    <td scope="row">
                        {{ $filters.bytes(process.memvirt) }}
                    </td>
                    <td scope="row">
                        {{ $filters.bytes(process.memres) }}
                    </td>
                    <td scope="row">
                        {{ process.pid }}
                    </td>
                    <td scope="row">
                        {{ process.username }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-if="process.timeplus != '?'">
                        <span v-show="process.timeplus.hours > 0" class="highlight">{{ process.timeplus.hours }}h</span>
                        {{ $filters.leftPad(process.timeplus.minutes, 2, '0') }}:{{ $filters.leftPad(process.timeplus.seconds,
                            2, '0') }}
                        <span v-show="process.timeplus.hours <= 0">.{{ $filters.leftPad(process.timeplus.milliseconds, 2, '0')
                        }}</span>
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-if="process.timeplus == '?'">?</td>
                    <td scope="row" class="hidden-xs hidden-sm">
                        {{ process.num_threads == -1 ? '?' : process.num_threads }}
                    </td>
                    <td scope="row" :class="{ nice: process.isNice }">
                        {{ $filters.exclamation(process.nice) }}
                    </td>
                    <td scope="row" :class="{ status: process.status == 'R' }">
                        {{ process.status }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-show="ioReadWritePresent">
                        {{ $filters.bytes(process.io_read) }}
                    </td>
                    <td scope="row" class="hidden-xs hidden-sm" v-show="ioReadWritePresent">
                        {{ $filters.bytes(process.io_write) }}
                    </td>
                    <td scope="row" class="text-truncate" v-show="args.process_short_name">
                        {{ process.name }}
                    </td>
                    <td scope="row" v-show="!args.process_short_name">
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
        stats() {
            return this.data.stats['processlist'];
        },
        processes() {
            const { sorter } = this;
            const isWindows = this.data.stats['isWindows'];
            const processes = (this.stats || []).map((process) => {
                process.memvirt = '?';
                process.memres = '?';
                if (process.memory_info) {
                    process.memvirt = process.memory_info.vms;
                    process.memres = process.memory_info.rss;
                }

                if (isWindows && process.username !== null) {
                    process.username = last(process.username.split('\\'));
                }

                process.timeplus = '?';
                process.timemillis = '?';
                if (process.cpu_times) {
                    process.timeplus = timedelta(process.cpu_times);
                    process.timemillis = timemillis(process.cpu_times);
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
        ioReadWritePresent() {
            return (this.stats || []).some(({ io_counters }) => io_counters);
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
        }
    }
};
</script>
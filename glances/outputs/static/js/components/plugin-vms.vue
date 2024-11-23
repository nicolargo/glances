<template>
    <section class="plugin" id="vms" v-if="vms.length">
        <span class="title">VMs</span>
        <span v-show="vms.length > 1">{{ vms.length }} sorted by {{ sorter.getColumnLabel(sorter.column) }}</span>
        <table class="table table-sm table-borderless table-striped table-hover">
            <thead>
                <tr>
                    <td v-show="showEngine">Engine</td>
                    <td :class="['sortable', sorter.column === 'name' && 'sort']"
                        @click="args.sort_processes_key = 'name'">
                        Name
                    </td>
                    <td>Status</td>
                    <td>Core</td>
                    <td :class="['sortable', sorter.column === 'memory_usage' && 'sort']"
                        @click="args.sort_processes_key = 'memory_usage'">
                        MEM
                    </td>
                    <td>/ MAX</td>
                    <td :class="['sortable', sorter.column === 'load_1min' && 'sort']"
                        @click="args.sort_processes_key = 'load_1min'">
                        LOAD 1/5/15min
                    </td>
                    <td>Release</td>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(vm, vmId) in vms" :key="vmId">
                    <td v-show="showEngine">{{ vm.engine }}</td>
                    <td>{{ vm.name }}</td>
                    <td :class="vm.status == 'stopped' ? 'careful' : 'ok'">
                        {{ vm.status }}
                    </td>
                    <td>
                        {{ $filters.number(vm.cpu_count, 1) }}
                    </td>
                    <td>
                        {{ $filters.bytes(vm.memory_usage) }}
                    </td>
                    <td>
                        / {{ $filters.bytes(vm.memory_total) }}
                    </td>
                    <td>
                        {{ $filters.number(vm.load_1min) }}/{{ $filters.number(vm.load_5min) }}/{{
                            $filters.number(vm.load_15min) }}
                    </td>
                    <td>
                        {{ vm.release }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
</template>

<script>
import { orderBy } from 'lodash';
import { store } from '../store.js';

export default {
    props: {
        data: {
            type: Object
        }
    },
    data() {
        return {
            store,
            sorter: undefined
        };
    },
    computed: {
        args() {
            return this.store.args || {};
        },
        sortProcessesKey() {
            return this.args.sort_processes_key;
        },
        stats() {
            return this.data.stats['vms'];
        },
        views() {
            return this.data.views['vms'];
        },
        vms() {
            const { sorter } = this;
            const vms = (this.stats || []).map(
                (vmData) => {
                    return {
                        'id': vmData.id,
                        'name': vmData.name,
                        'status': vmData.status != undefined ? vmData.status : '?',
                        'cpu_count': vmData.cpu_count != undefined ? vmData.cpu_count : '?',
                        'memory_usage': vmData.memory_usage != undefined ? vmData.memory_usage : '?',
                        'memory_total': vmData.memory_total != undefined ? vmData.memory_total : '?',
                        'load_1min': vmData.load_1min != undefined ? vmData.load_1min : '?',
                        'load_5min': vmData.load_5min != undefined ? vmData.load_5min : '?',
                        'load_15min': vmData.load_15min != undefined ? vmData.load_15min : '?',
                        'release': vmData.release,
                        'image': vmData.image,
                        'engine': vmData.engine,
                        'engine_version': vmData.engine_version,
                    };
                }
            );
            return orderBy(
                vms,
                [sorter.column].reduce((retval, col) => {
                    if (col === 'memory_usage') {
                        col = ['memory_usage'];
                    }
                    return retval.concat(col);
                }, []),
                [sorter.isReverseColumn(sorter.column) ? 'desc' : 'asc']
            );
        },
        showEngine() {
            return this.views.show_engine_name;
        },
    },
    watch: {
        sortProcessesKey: {
            immediate: true,
            handler(sortProcessesKey) {
                const sortable = ['load_1min', 'memory_usage', 'name'];
                function isReverseColumn(column) {
                    return !['name'].includes(column);
                }
                function getColumnLabel(value) {
                    const labels = {
                        load_1min: 'load',
                        memory_usage: 'memory consumption',
                        name: 'VM name',
                        None: 'None'
                    };
                    return labels[value] || value;
                }
                if (!sortProcessesKey || sortable.includes(sortProcessesKey)) {
                    this.sorter = {
                        column: this.args.sort_processes_key || 'load_1min',
                        auto: !this.args.sort_processes_key,
                        isReverseColumn,
                        getColumnLabel
                    };
                }
            }
        }
    }
};
</script>

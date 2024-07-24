<template>
    <section id="vms-plugin" class="plugin" v-if="vms.length">
        <span class="title">VMs</span>
        {{ vms.length }} sorted by {{ sorter.getColumnLabel(sorter.column) }}
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left" v-show="showEngine">Engine</div>
                <div
                    class="table-cell text-left"
                    :class="['sortable', sorter.column === 'name' && 'sort']"
                    @click="args.sort_processes_key = 'name'"
                >
                    Name
                </div>
                <div class="table-cell">Status</div>
                <div class="table-cell">Core</div>
                <div
                    class="table-cell"
                    :class="['sortable', sorter.column === 'memory_usage' && 'sort']"
                    @click="args.sort_processes_key = 'memory_usage'"
                >
                    MEM
                </div>
                <div class="table-cell text-left">/MAX</div>
                <div
                    class="table-cell"
                    :class="['sortable', sorter.column === 'load_1min' && 'sort']"
                    @click="args.sort_processes_key = 'load_1min'"
                >
                     LOAD 1/5/15min
                </div>
                <div class="table-cell text-right">Release</div>
            </div>
            <div
                class="table-row"
                v-for="(vm, vmId) in vms"
                :key="vmId"
            >
                <div class="table-cell text-left" v-show="showEngine">{{ vm.engine }}</div>
                <div class="table-cell text-left">{{ vm.name }}</div>
                <div class="table-cell" :class="vm.status == 'stopped' ? 'careful' : 'ok'">
                    {{ vm.status }}
                </div>
                <div class="table-cell">
                    {{ $filters.number(vm.cpu_count, 1) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bytes(vm.memory_usage) }}
                </div>
                <div class="table-cell text-left">
                    /{{ $filters.bytes(vm.memory_total) }}
                </div>
                <div class="table-cell">
                    {{ $filters.number(vm.load_1min) }}/{{ $filters.number(vm.load_5min) }}/{{ $filters.number(vm.load_15min) }}
                </div>
                <div class="table-cell text-right">
                    {{ vm.release }}
                </div>
            </div>
        </div>
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

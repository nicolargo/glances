<template>
    <section class="plugin" id="containers" v-if="containers.length">
        <span class="title">CONTAINERS</span>
        <span v-show="containers.length > 1"> {{ containers.length }} sorted by {{ sorter.getColumnLabel(sorter.column) }}</span>
        <table class="table table-sm table-borderless table-striped table-hover">
            <thead>
                <tr>
                    <td v-show="showEngine">Engine</td>
                    <td v-show="showPod">Pod</td>
                    <td :class="['sortable', sorter.column === 'name' && 'sort']"
                        @click="args.sort_processes_key = 'name'">
                        Name
                    </td>
                    <td>Status</td>
                    <td>Uptime</td>
                    <td :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                        @click="args.sort_processes_key = 'cpu_percent'">
                        CPU%
                    </td>
                    <td :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                        @click="args.sort_processes_key = 'memory_percent'">
                        MEM
                    </td>
                    <td>/ MAX</td>
                    <td>IOR/s</td>
                    <td>IOW/s</td>
                    <td>RX/s</td>
                    <td>TX/s</td>
                    <td>Command</td>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(container, containerId) in containers" :key="containerId">
                    <td v-show="showEngine">{{ container.engine }}</td>
                    <td v-show="showPod">{{ container.pod_id || '-' }}</td>
                    <td>{{ container.name }}</td>
                    <td :class="container.status == 'Paused' ? 'careful' : 'ok'">
                        {{ container.status }}
                    </td>
                    <td>
                        {{ container.uptime }}
                    </td>
                    <td>
                        {{ $filters.number(container.cpu_percent, 1) }}
                    </td>
                    <td>
                        {{ $filters.bytes(container.memory_usage) }}
                    </td>
                    <td>
                        / {{ $filters.bytes(container.limit) }}
                    </td>
                    <td>
                        {{ $filters.bytes(container.io_rx) }}
                    </td>
                    <td>
                        {{ $filters.bytes(container.io_wx) }}
                    </td>
                    <td>
                        {{ $filters.bits(container.network_rx) }}
                    </td>
                    <td>
                        {{ $filters.bits(container.network_tx) }}
                    </td>
                    <td>
                        {{ container.command }}
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
            return this.data.stats['containers'];
        },
        views() {
            return this.data.views['containers'];
        },
        containers() {
            const { sorter } = this;
            const containers = (this.stats || []).map(
                (containerData) => {
                    let memory_usage_no_cache = '?'
                    if (containerData.memory.usage != undefined) {
                        memory_usage_no_cache = containerData.memory.usage;
                        if (containerData.memory.inactive_file != undefined) {
                            memory_usage_no_cache = memory_usage_no_cache - containerData.memory.inactive_file;
                        }
                    }

                    return {
                        'id': containerData.id,
                        'name': containerData.name,
                        'status': containerData.status,
                        'uptime': containerData.uptime,
                        'cpu_percent': containerData.cpu.total,
                        'memory_usage': memory_usage_no_cache,
                        'limit': containerData.memory.limit != undefined ? containerData.memory.limit : '?',
                        'io_rx': containerData.io_rx != undefined ? containerData.io_rx : '?',
                        'io_wx': containerData.io_wx != undefined ? containerData.io_wx : '?',
                        'network_rx': containerData.network_rx != undefined ? containerData.network_rx : '?',
                        'network_tx': containerData.network_tx != undefined ? containerData.network_tx : '?',
                        'command': containerData.command,
                        'image': containerData.image,
                        'engine': containerData.engine,
                        'pod_id': containerData.pod_id
                    };
                }
            );
            return orderBy(
                containers,
                [sorter.column].reduce((retval, col) => {
                    if (col === 'memory_percent') {
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
        showPod() {
            return this.views.show_pod_name;
        }
    },
    watch: {
        sortProcessesKey: {
            immediate: true,
            handler(sortProcessesKey) {
                const sortable = ['cpu_percent', 'memory_percent', 'name'];
                function isReverseColumn(column) {
                    return !['name'].includes(column);
                }
                function getColumnLabel(value) {
                    const labels = {
                        io_counters: 'disk IO',
                        cpu_percent: 'CPU consumption',
                        memory_usage: 'memory consumption',
                        cpu_times: 'uptime',
                        name: 'container name',
                        None: 'None'
                    };
                    return labels[value] || value;
                }
                if (!sortProcessesKey || sortable.includes(sortProcessesKey)) {
                    this.sorter = {
                        column: this.args.sort_processes_key || 'cpu_percent',
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

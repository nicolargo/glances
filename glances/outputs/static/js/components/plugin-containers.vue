<template>
    <section v-if="containers.length" id="containers" class="plugin">
        <span class="title">CONTAINERS</span>
        <span v-show="containers.length > 1">
            {{ containers.length }} sorted by {{ sorter.getColumnLabel(sorter.column) }}
        </span>
        <div class="table-responsive d-md-none">
            <table class="table table-sm table-borderless table-striped table-hover">
                <thead>
                    <tr>
                        <td v-show="showPod" scope="col">Pod</td>
                        <td v-show="!getDisableStats().includes('name')" scope="col"
                            :class="['sortable', sorter.column === 'name' && 'sort']"
                            @click="args.sort_processes_key = 'name'">
                            Name
                        </td>
                        <td v-show="!getDisableStats().includes('status')" scope="col">Status</td>
                        <td v-show="!getDisableStats().includes('cpu')" scope="col"
                            :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                            @click="args.sort_processes_key = 'cpu_percent'">
                            CPU%
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="col"
                            :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                            @click="args.sort_processes_key = 'memory_percent'">
                            MEM
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="col">MAX</td>
                        <td v-show="!getDisableStats().includes('command')" scope="col">Command</td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(container, containerId) in containers" :key="containerId">
                        <td v-show="showPod" scope="row">{{ container.pod_id || '-' }}</td>
                        <td v-show="!getDisableStats().includes('name')" scope="row">
                            {{ container.name }}
                        </td>
                        <td v-show="!getDisableStats().includes('status')" scope="row" :class="[
                            container.status === 'Paused' && 'careful',
                            container.status === 'exited' && 'warning',
                            !['Paused', 'exited'].includes(container.status) && 'ok'
                        ]">
                            {{ container.status }}
                        </td>
                        <td v-show="!getDisableStats().includes('cpu')" scope="row">
                            {{ $filters.number(container.cpu_percent, 1) }}
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="row">
                            {{
                                isNaN(container.memory_usage ?? NaN)
                                    ? '-'
                                    : $filters.bytes(container.memory_usage)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="row">
                            {{
                                isNaN(container.limit ?? NaN)
                                    ? '-'
                                    : $filters.bytes(container.limit)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('command')" scope="row" class="text-truncate">
                            {{ container.command }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="table-responsive d-none d-md-block">
            <table class="table table-sm table-borderless table-striped table-hover">
                <thead>
                    <tr>
                        <td v-show="showEngine" scope="col">Engine</td>
                        <td v-show="showPod" scope="col">Pod</td>
                        <td v-show="!getDisableStats().includes('name')" scope="col"
                            :class="['sortable', sorter.column === 'name' && 'sort']"
                            @click="args.sort_processes_key = 'name'">
                            Name
                        </td>
                        <td v-show="!getDisableStats().includes('status')" scope="col">Status</td>
                        <td v-show="!getDisableStats().includes('uptime')" scope="col">Uptime</td>
                        <td v-show="!getDisableStats().includes('cpu')" scope="col"
                            :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                            @click="args.sort_processes_key = 'cpu_percent'">
                            CPU%
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="col"
                            :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                            @click="args.sort_processes_key = 'memory_percent'">
                            MEM
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="col">MAX</td>
                        <td v-show="!getDisableStats().includes('diskio')" scope="col">IORps</td>
                        <td v-show="!getDisableStats().includes('diskio')" scope="col">IOWps</td>
                        <td v-show="!getDisableStats().includes('networkio')" scope="col">RXps</td>
                        <td v-show="!getDisableStats().includes('networkio')" scope="col">TXps</td>
                        <td v-show="!getDisableStats().includes('command')" scope="col">Command</td>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(container, containerId) in containers" :key="containerId">
                        <td v-show="showEngine" scope="row">{{ container.engine }}</td>
                        <td v-show="showPod" scope="row">{{ container.pod_id || '-' }}</td>
                        <td v-show="!getDisableStats().includes('name')" scope="row">
                            {{ container.name }}
                        </td>
                        <td v-show="!getDisableStats().includes('status')" scope="row" :class="[
                            container.status === 'Paused' && 'careful',
                            container.status === 'exited' && 'warning',
                            !['Paused', 'exited'].includes(container.status) && 'ok'
                        ]">
                            {{ container.status }}
                        </td>
                        <td v-show="!getDisableStats().includes('uptime')" scope="row">
                            {{ container.uptime }}
                        </td>
                        <td v-show="!getDisableStats().includes('cpu')" scope="row">
                            {{ $filters.number(container.cpu_percent, 1) }}
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="row">
                            {{
                                isNaN(container.memory_usage ?? NaN)
                                    ? '-'
                                    : $filters.bytes(container.memory_usage)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('mem')" scope="row">
                            {{
                                isNaN(container.limit ?? NaN)
                                    ? '-'
                                    : $filters.bytes(container.limit)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('iodisk')" scope="row">
                            {{
                                isNaN(container.io_rx ?? NaN)
                                    ? '-'
                                    : $filters.bytes(container.io_rx)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('iodisk')" scope="row">
                            {{
                                isNaN(container.io_wx ?? NaN)
                                    ? '-'
                                    : $filters.bytes(container.io_wx)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('networkio')" scope="row">
                            {{
                                isNaN(container.network_rx ?? NaN)
                                    ? '-'
                                    : $filters.bits(container.network_rx)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('networkio')" scope="row">
                            {{
                                isNaN(container.network_tx ?? NaN)
                                    ? '-'
                                    : $filters.bits(container.network_tx)
                            }}
                        </td>
                        <td v-show="!getDisableStats().includes('command')" scope="row" class="text-truncate">
                            {{ container.command }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>
</template>

<script>
import { orderBy } from 'lodash';
import { GlancesHelper } from '../services.js';
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
            const containers = (this.stats || []) //
                .map((containerData) => {
                    // Memory usage no cache is reflected the algorithm used in Docker top
                    let memory_usage_no_cache;

                    if (containerData.memory_usage != undefined) {
                        memory_usage_no_cache = containerData.memory_usage;
                        if (containerData.memory_inactive_file != undefined) {
                            memory_usage_no_cache =
                                memory_usage_no_cache - containerData.memory_inactive_file;
                        }
                    } else {
                        memory_usage_no_cache = undefined;
                    }

                    return {
                        id: containerData.id,
                        name: containerData.name,
                        status: containerData.status,
                        uptime: containerData.uptime,
                        cpu_percent: containerData.cpu.total,
                        memory_usage: memory_usage_no_cache,
                        limit: containerData.memory.limit,
                        io_rx: containerData.io_rx,
                        io_wx: containerData.io_wx,
                        network_rx: containerData.network_rx,
                        network_tx: containerData.network_tx,
                        command: containerData.command,
                        image: containerData.image,
                        engine: containerData.engine,
                        pod_id: containerData.pod_id
                    };
                });
            return orderBy(
                containers,
                [sorter.column].map((col) => {
                    const sorter = (item) =>
                        item[col === 'memory_percent' ? 'memory_usage' : col] ?? -Infinity;
                    return sorter;
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
    },
    methods: {
        getDisableStats() {
            return GlancesHelper.getLimit('containers', 'containers_disable_stats') || [];
        }
    }
};
</script>

<template>
    <section id="containers-plugin" class="plugin" v-if="containers.length">
        <span class="title">CONTAINERS</span>
        {{ containers.length }} sorted by {{ sorter.getColumnLabel(sorter.column) }}
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left">Engine</div>
                <div class="table-cell text-left">Pod</div>
                <div
                    class="table-cell text-left"
                    :class="['sortable', sorter.column === 'name' && 'sort']"
                    @click="args.sort_processes_key = 'name'"
                >
                    Name
                </div>
                <div class="table-cell">Status</div>
                <div class="table-cell">Uptime</div>
                <div
                    class="table-cell"
                    :class="['sortable', sorter.column === 'cpu_percent' && 'sort']"
                    @click="args.sort_processes_key = 'cpu_percent'"
                >
                    CPU%
                </div>
                <div
                    class="table-cell"
                    :class="['sortable', sorter.column === 'memory_percent' && 'sort']"
                    @click="args.sort_processes_key = 'memory_percent'"
                >
                    MEM
                </div>
                <div class="table-cell">/MAX</div>
                <div class="table-cell">IOR/s</div>
                <div class="table-cell">IOW/s</div>
                <div class="table-cell">RX/s</div>
                <div class="table-cell">TX/s</div>
                <div class="table-cell text-left">Command</div>
            </div>
            <div
                class="table-row"
                v-for="(container, containerId) in containers"
                :key="containerId"
            >
                <div class="table-cell text-left">{{ container.engine }}</div>
                <div class="table-cell text-left">{{ container.pod_id || '-' }}</div>
                <div class="table-cell text-left">{{ container.name }}</div>
                <div class="table-cell" :class="container.status == 'Paused' ? 'careful' : 'ok'">
                    {{ container.status }}
                </div>
                <div class="table-cell">
                    {{ container.uptime }}
                </div>
                <div class="table-cell">
                    {{ $filters.number(container.cpu_percent, 1) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bytes(container.memory_usage) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bytes(container.limit) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.ior / container.io_time_since_update) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.iow / container.io_time_since_update) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.rx / container.net_time_since_update) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.tx / container.net_time_since_update) }}
                </div>
                <div class="table-cell text-left">
                    {{ container.command }}
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
            return this.data.stats['containers'];
        },
        containers() {
            const { sorter } = this;
            const containers = ((this.stats && this.stats.containers) || []).map(
                (containerData) => {
                    // prettier-ignore
                    return {
                        'id': containerData.Id,
                        'name': containerData.name,
                        'status': containerData.Status,
                        'uptime': containerData.Uptime,
                        'cpu_percent': containerData.cpu.total,
                        'memory_usage': containerData.memory.usage != undefined ? containerData.memory.usage : '?',
                        'limit': containerData.memory.limit != undefined ? containerData.memory.limit : '?',
                        'ior': containerData.io.ior != undefined ? containerData.io.ior : '?',
                        'iow': containerData.io.iow != undefined ? containerData.io.iow : '?',
                        'io_time_since_update': containerData.io.time_since_update,
                        'rx': containerData.network.rx != undefined ? containerData.network.rx : '?',
                        'tx': containerData.network.tx != undefined ? containerData.network.tx : '?',
                        'net_time_since_update': containerData.network.time_since_update,
                        'command': containerData.Command.join(' '),
                        'image': containerData.Image,
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

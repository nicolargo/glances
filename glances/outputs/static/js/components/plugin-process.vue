<template>
    <div v-if="args.disable_process">PROCESSES DISABLED (press 'z' to display)</div>
    <div v-else>
        <glances-plugin-processcount :sorter="sorter" :data="data"></glances-plugin-processcount>
        <div class="row" v-if="!args.disable_amps">
            <div class="col-lg-18">
                <glances-plugin-amps :data="data"></glances-plugin-amps>
            </div>
        </div>
        <glances-plugin-processlist
            :sorter="sorter"
            :data="data"
            @update:sorter="args.sort_processes_key = $event"
        ></glances-plugin-processlist>
    </div>
</template>

<script>
import { store } from '../store.js';
import GlancesPluginAmps from './plugin-amps.vue';
import GlancesPluginProcesscount from './plugin-processcount.vue';
import GlancesPluginProcesslist from './plugin-processlist.vue';

export default {
    components: {
        GlancesPluginAmps,
        GlancesPluginProcesscount,
        GlancesPluginProcesslist
    },
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
        }
    },
    watch: {
        sortProcessesKey: {
            immediate: true,
            handler(sortProcessesKey) {
                const sortable = [
                    'cpu_percent',
                    'memory_percent',
                    'username',
                    'timemillis',
                    'num_threads',
                    'io_counters',
                    'name'
                ];
                function isReverseColumn(column) {
                    return !['username', 'name'].includes(column);
                }
                function getColumnLabel(value) {
                    const labels = {
                        cpu_percent: 'CPU consumption',
                        memory_percent: 'memory consumption',
                        username: 'user name',
                        timemillis: 'process time',
                        cpu_times: 'process time',
                        io_counters: 'disk IO',
                        name: 'process name',
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
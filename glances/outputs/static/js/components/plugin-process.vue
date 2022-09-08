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
            @update:sorter="sorter.column = $event"
        ></glances-plugin-processlist>
    </div>
</template>

<script>
import hotkeys from 'hotkeys-js';
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
            sorter: {
                column: 'cpu_percent',
                auto: true,
                isReverseColumn(column) {
                    return !(column === 'username' || column === 'name');
                },
                getColumnLabel(column) {
                    if (column === 'io_read' || column === 'io_write') {
                        return 'io_counters';
                    } else {
                        return column;
                    }
                }
            }
        };
    },
    computed: {
        args() {
            return this.store.args || {};
        }
    },
    methods: {
        setupHotKeys() {
            // a => Sort processes automatically
            hotkeys('a', () => {
                this.sorter.column = 'cpu_percent';
                this.sorter.auto = true;
            });

            // c => Sort processes by CPU%
            hotkeys('c', () => {
                this.sorter.column = 'cpu_percent';
                this.sorter.auto = false;
            });

            // m => Sort processes by MEM%
            hotkeys('m', () => {
                this.sorter.column = 'memory_percent';
                this.sorter.auto = false;
            });

            // u => Sort processes by user
            hotkeys('u', () => {
                this.sorter.column = 'username';
                this.sorter.auto = false;
            });

            // p => Sort processes by name
            hotkeys('p', () => {
                this.sorter.column = 'name';
                this.sorter.auto = false;
            });

            // i => Sort processes by I/O rate
            hotkeys('i', () => {
                this.sorter.column = ['io_read', 'io_write'];
                this.sorter.auto = false;
            });

            // t => Sort processes by time
            hotkeys('t', () => {
                this.sorter.column = 'timemillis';
                this.sorter.auto = false;
            });
        }
    },
    mounted() {
        this.setupHotKeys();
    },
    beforeUnmount() {
        hotkeys.unbind('a');
        hotkeys.unbind('c');
        hotkeys.unbind('m');
        hotkeys.unbind('u');
        hotkeys.unbind('p');
        hotkeys.unbind('i');
        hotkeys.unbind('t');
    }
};
</script>
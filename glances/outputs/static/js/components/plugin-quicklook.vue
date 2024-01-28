<template>
    <section id="quicklook" class="plugin">
        <div class="cpu-name">
            {{ cpu_name }}
        </div>
        <div class="table">
            <div class="table-row" v-if="!args.percpu">
                <div class="table-cell text-left">CPU</div>
                <div class="table-cell">
                    <div class="progress">
                        <div
                            :class="`progress-bar progress-bar-${getDecoration('cpu')}`"
                            role="progressbar"
                            :aria-valuenow="cpu"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            :style="`width: ${cpu}%;`"
                        >
                            &nbsp;
                        </div>
                    </div>
                </div>
                <div class="table-cell">{{ cpu }}%</div>
            </div>
            <template v-if="args.percpu">
                <div class="table-row" v-for="(percpu, percpuId) in percpus" :key="percpuId">
                    <div class="table-cell text-left">CPU{{ percpu.number }}</div>
                    <div class="table-cell">
                        <div class="progress">
                            <div
                                :class="`progress-bar progress-bar-${getDecoration('cpu')}`"
                                role="progressbar"
                                :aria-valuenow="percpu.total"
                                aria-valuemin="0"
                                aria-valuemax="100"
                                :style="`width: ${percpu.total}%;`"
                            >
                                &nbsp;
                            </div>
                        </div>
                    </div>
                    <div class="table-cell">{{ percpu.total }}%</div>
                </div>
            </template>
            <div class="table-row" v-for="(key) in stats_list_after_cpu">
                <div class="table-cell text-left">{{ key.toUpperCase() }}</div>
                <div class="table-cell">
                    <div class="progress">
                        <div
                            :class="`progress-bar progress-bar-${getDecoration(key)}`"
                            role="progressbar"
                            :aria-valuenow="stats[key]"
                            aria-valuemin="0"
                            aria-valuemax="100"
                            :style="`width: ${stats[key]}%;`"
                        >
                            &nbsp;
                        </div>
                    </div>
                </div>
                <div class="table-cell">{{ stats[key] }}%</div>
            </div>
        </div>
    </section>
</template>

<script>
import { store } from '../store.js';

export default {
    props: {
        data: {
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
        stats() {
            return this.data.stats['quicklook'];
        },
        view() {
            return this.data.views['quicklook'];
        },
        cpu() {
            return this.stats.cpu;
        },
        cpu_name() {
            return this.stats.cpu_name;
        },
        cpu_hz_current() {
            return this.stats.cpu_hz_current;
        },
        cpu_hz() {
            return this.stats.cpu_hz;
        },
        percpus() {
            return this.stats.percpu.map(({ cpu_number: number, total }) => ({
                number,
                total
            }));
        },
        stats_list_after_cpu() {
            return this.view.list.filter((key) => !key.includes('cpu'));
        },
    },
    methods: {
        getDecoration(value) {
            if (this.view[value] === undefined) {
                return;
            }
            return this.view[value].decoration.toLowerCase();
        }
    }
};
</script>